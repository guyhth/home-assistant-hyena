# Hyena E-Bike BLE / HAP Protocol Notes

> **Status:** Reverse-engineering notes — incomplete and subject to revision.
>
> This document records protocol behaviour established from the Hyena Android application, decompiled Hyena SDK source, BLE captures from a Trek FX+ 2, controlled tests, and the Home Assistant integration. Confirmed facts, observations and hypotheses are deliberately distinguished.

## 1. Scope

The tested bike is a **Trek FX+ 2** using the **DITK** Hyena Bluetooth implementation.

The Android application embeds Hyena SDK packages including:

- `io.hylink.hap.protocol.v2`
- `io.hylink.hbp`

The BLE transport exposes CAN-oriented characteristics and the application sends HAP instruction frames through its HBP BLE manager.

The relationship between every HAP/HBP layer and every packet seen over BLE has not yet been completely documented.

## 2. BLE GATT structure

The following UUIDs have been identified in the Android application and confirmed against the bike:

| Purpose | UUID |
|---|---|
| HAP service | `48592800-6879-656E-6174-656B2E485550` |
| CAN write-filter characteristic | `4859FF00-6879-656E-6174-656B2E485550` |
| CAN notification characteristic | `4859FF01-6879-656E-6174-656B2E485550` |
| CAN write characteristic | `4859FF02-6879-656E-6174-656B2E485550` |

`io.hylink.hbp.connector.HyBleManager` maps these as follows:

- `canCh` / `canCharacteristicsUUID` → `4859FF01`
- `canWriteCh` / `canCharacteristicsWriteUUID` → `4859FF02`
- `canWriteFilterCh` / `canCharacteristicsWriteFilterUUID` → `4859FF00`

`HyBleManager.writeToCan(byte[])` ultimately writes to the CAN write characteristic. The Home Assistant integration therefore subscribes to `4859FF01` and writes commands to `4859FF02`.

## 3. Common packet framing

Observed DITK/HAP telemetry uses the following frame structure:

```text
00 00 PP PP LL [payload...]
```

| Bytes | Meaning |
|---|---|
| `0-1` | Frame prefix `00 00` |
| `2-3` | Packet/CAN ID, 16-bit big-endian |
| `4` | Payload length |
| `5...` | Payload |

Packet ID decoding:

```python
packet_id = int.from_bytes(data[2:4], byteorder="big")
```

Payload extraction:

```python
payload = data[5 : 5 + payload_length]
```

A typical `0x0300` frame is 13 bytes long: 5 bytes of framing followed by an 8-byte payload.

## 4. Packet 0x0300 — BikeControl00

The HAP SDK identifies `BikeControl00` with:

```text
SID = 768 decimal = 0x0300
```

It contains an 8-byte data bin.

| Payload byte | Meaning | Status |
|---:|---|---|
| `0` | Profile request/value (`getProfileReq()`) | Confirmed by SDK |
| `1` | Unknown | Unknown |
| `2` | Raw light-state request | Confirmed by SDK |
| `3` | Unknown | Unknown |
| `4` | Unknown | Unknown |
| `5` | Unknown | Unknown |
| `6` | Unknown | Unknown |
| `7` | 4-bit rolling sequence counter for light commands | Confirmed by SDK |

The SDK exposes `getRawLightStateReq()` from byte 2 and `getLightState()` as `rawLightStateReq > 0`.

Observed light-state values are:

```text
0x00 = OFF
0x64 = ON
```

The rest of the payload should be preserved when constructing a light command.

## 5. Light-control command

The light-control path is one of the best-understood parts of the protocol.

The Android application waits for current `BikeControl00` data and then constructs an instruction using the current 8-byte payload. The relevant instruction class is `snail.cuttlefish`.

Its transformation is effectively:

```python
payload = bytearray(current_bike_control_00)
payload[2] = 0x64 if light_on else 0x00
payload[7] = (payload[7] + 1) & 0x0F
```

Only byte 2 and byte 7 are changed. Byte 7 is therefore a 4-bit rolling sequence counter, incremented modulo 16.

### 5.1 HAP command framing

The base `seal.jellyfish.build()` method constructs the instruction as:

1. 4-byte instruction ID
2. 1-byte payload length
3. payload

The instruction ID is `0x300`, encoded big-endian:

```text
0x00000300 → 00 00 03 00
```

For an 8-byte `BikeControl00` payload, the complete command is:

```text
00 00 03 00 08 [8-byte payload]
```

For a representative payload:

```text
00 5A 00 5A 00 00 00 XX
```

OFF is:

```text
00 00 03 00 08 00 5A 00 5A 00 00 00 XX'
```

ON is:

```text
00 00 03 00 08 00 5A 64 5A 00 00 00 XX'
```

where:

```text
XX' = (XX + 1) & 0x0F
```

The `snail.cuttlefish` build path does not add the CRC used by some other instruction classes. The light command is therefore the 13-byte frame shown above.

### 5.2 Confirmation behaviour

BLE write acknowledgement alone is not sufficient to establish that the light changed state.

A Home Assistant live capture showed that an OFF command could be followed immediately by a `0x0300` notification with the same sequence number but the old ON state. A subsequent notification reported the requested state.

The reliable confirmation rule used by the integration is therefore:

> A light command is confirmed only when a subsequent `0x0300` notification contains both the requested light state in byte 2 and the sequence number sent in byte 7.

The integration serializes light commands so that two commands cannot race while calculating a new sequence number from the same source payload.

## 6. Battery telemetry

### 6.1 Packet 0x0400 — charging state

`0x0400` reports battery charging state.

The charging flag is **bit 7 of payload byte 2**:

```python
charging = bool(payload[2] & 0x80)
```

This was confirmed with a controlled charger test. With the charger disconnected, payload byte 2 was observed as `0x4C`; when charging began it changed to `0xCC`.

### 6.2 Packet 0x0401 — voltage/current/power

`0x0401` contains battery electrical telemetry:

| Payload bytes | Interpretation | Encoding |
|---|---|---|
| `0-1` | Battery voltage | unsigned little-endian, mV |
| `2-3` | Unknown | Unknown |
| `4-7` | Battery current | signed little-endian, mA |

The integration converts the values as follows:

```python
voltage = voltage_mv / 1000.0
current = current_ma / 1000.0
power = voltage * current
```

Power is calculated rather than read directly from a protocol field.

Positive current has been observed during discharge and negative current during charging; this sign convention is treated as an observed interpretation rather than a complete SDK-level specification.

### 6.3 Packet 0x0402 — battery SoC and remaining energy

`0x0402` reports battery state of charge.

The first four payload bytes contain a little-endian unsigned 32-bit percentage:

```python
soc = int.from_bytes(payload[0:4], "little", signed=False)
```

Values from 0–100 are interpreted as SoC percentage.

The remaining four payload bytes are an absolute remaining-energy value in **mWh**. This field is confirmed by the application data model and captures.

For example:

```text
57 00 00 00 ...
```

represents **87%** SoC.

### 6.4 Packet 0x0403 — battery SoH and reported capacity

`0x0403` reports battery state of health.

| Payload bytes | Interpretation | Encoding |
|---|---|---|
| `0-1` | Battery SoH | unsigned little-endian percentage |
| `2-3` | Unknown | Unknown |
| `4-7` | Reported battery capacity | unsigned little-endian mWh |

A representative payload:

```text
64 00 00 00 E0 67 03 00
```

reports:

- **100% SoH**
- **223,200 mWh** reported capacity

## 7. Motion, speed and distance packets

### 7.1 Packet 0x0201 — bike speed / controller temperature

The reverse-engineering work identifies:

| Payload | Interpretation | Status |
|---|---|---|
| `0-1` | Bike speed in km/h | Confirmed |
| `7` | Controller temperature in °C | Confirmed |

These fields are not currently exposed as Home Assistant entities.

### 7.2 Packet 0x0202 — odometer / motor temperature / speed limit

The lifetime odometer is stored in payload bytes `4-7` as an unsigned little-endian value in metres:

```python
odometer_m = int.from_bytes(payload[4:8], "little", signed=False)
odometer_km = odometer_m / 1000.0
```

Additional reverse-engineering findings for this packet are:

| Payload | Interpretation | Status |
|---|---|---|
| `0-?` | Other packet data | Partially understood |
| `1` | Motor temperature in °C | Confirmed |
| `2-3` | Raw speed-limit value | Identified |
| `4-7` | Lifetime odometer in metres | Confirmed |

The exact encoding of the speed-limit value remains to be established.

### 7.3 Packet 0x0203 — cadence

`0x0203` contains a raw pedal cadence value in payload bytes `0-1`.

The Hyena application source decodes the raw value using a scale factor of `0.025`, equivalent to:

```text
cadence RPM = raw value / 40
```

This interpretation is confirmed from the application source and independently supported by testing against known cadence. It is not currently exposed by the Home Assistant integration.

### 7.4 Packet 0x0207 — unknown wheel rotational signal

`0x0207` is repeatedly observed and is believed to contain a wheel-related rotational signal, but the meaning and scaling of payload bytes `0-1` have not been established with sufficient confidence.

It is therefore not exposed as an entity.

## 8. Known packet summary

| ID | Purpose | Known fields | Status |
|---:|---|---|---|
| `0x0201` | Speed / controller telemetry | bytes `0-1` speed; byte `7` controller temperature | Confirmed |
| `0x0202` | Odometer / motor telemetry | byte `1` motor temperature; bytes `2-3` speed-limit value; bytes `4-7` odometer | Partially decoded |
| `0x0203` | Cadence | bytes `0-1`, raw ÷ 40 = RPM | Confirmed |
| `0x0207` | Wheel rotational signal | bytes `0-1` unknown | Unknown |
| `0x0300` | `BikeControl00` | byte `0` profile; byte `2` light; byte `7` sequence | Partially decoded |
| `0x0400` | Battery charging | byte `2`, bit 7 | Confirmed |
| `0x0401` | Battery electrical telemetry | bytes `0-1` voltage; bytes `4-7` current | Confirmed |
| `0x0402` | Battery SoC / energy | bytes `0-3` SoC; bytes `4-7` remaining energy | Confirmed |
| `0x0403` | Battery SoH / capacity | bytes `0-1` SoH; bytes `4-7` reported capacity | Confirmed |

Not all decoded fields are currently exposed by Home Assistant.

## 9. Home Assistant implementation

The integration uses the notification characteristic for event-driven telemetry rather than repeatedly polling the bike.

It connects through `BleakClientWithServiceCache` using `bleak_retry_connector` and subscribes to `4859FF01`.

The coordinator currently exposes the following protocol-derived data to Home Assistant:

- Battery SoC
- Battery SoH
- Battery charging state
- Battery voltage
- Battery current
- Calculated battery power
- Odometer
- Bike light state/control through `0x0300`

The connection is reset after a period without telemetry. On a new connection, the cached `BikeControl00` payload is cleared so light commands cannot accidentally be based on stale state.

## 10. Reverse-engineering evidence

### Android application / SDK source

The embedded Hyena SDK provides direct evidence for:

- GATT characteristic mappings
- `BikeControl00` SID `0x300`
- light-state accessors
- light command construction
- sequence counter handling
- HAP instruction framing
- the BLE write path
- cadence scaling

Where the SDK explicitly implements a field or transformation, it is treated as confirmed unless contradicted by hardware testing.

### BLE captures

nRF Connect captures from the bike show repeated packet IDs and payloads matching the SDK-derived interpretations, including `0x0300` light state and rolling sequence values.

### Controlled tests

Controlled charger tests established the `0x0400` charging bit. Known cadence and live riding observations support the cadence and motion interpretations.

### Home Assistant live capture

A live Home Assistant capture was used to validate the light command path and, importantly, to establish that an immediate `0x0300` notification does not necessarily mean the requested light state has already taken effect.

## 11. Unknowns and future investigation

Areas still requiring investigation include:

- Remaining `BikeControl00` bytes.
- Full semantics of `0x0401` bytes `2-3`.
- Exact units/semantics of all `0x0402` and `0x0403` fields beyond the values already established.
- Full meaning of `0x0202` bytes `0` and the speed-limit field.
- Exact encoding of `0x0201` temperature and speed fields.
- Meaning and scaling of `0x0207`.
- Other observed packet IDs and their associated HAP SDK classes.
- Complete semantics of the `4859FF00` write-filter characteristic.
- Complete HAP/HBP framing and acknowledgement/error semantics for other instruction types.
- Whether every HAP instruction uses the same framing and whether other commands require CRCs.
- The complete mapping between HAP instruction classes and CAN packet IDs observed over BLE.

Unknown fields should be promoted to confirmed protocol definitions only after further source analysis or controlled captures.

## 12. Useful implementation constants

The main protocol constants are kept in `const.py` so the coordinator and entity platforms do not need to duplicate packet IDs or `BikeControl00` field offsets.

```python
PACKET_BIKE_SPEED = 0x0201
PACKET_ODOMETER = 0x0202
PACKET_CADENCE = 0x0203
PACKET_BIKE_CONTROL = 0x0300
PACKET_BATTERY_CHARGING = 0x0400
PACKET_BATTERY_TELEMETRY = 0x0401
PACKET_BATTERY_SOC = 0x0402
PACKET_BATTERY_SOH = 0x0403
PACKET_UNKNOWN_0207 = 0x0207

BIKE_CONTROL_LIGHT_OFFSET = 2
BIKE_CONTROL_SEQUENCE_OFFSET = 7
BIKE_CONTROL_LIGHT_OFF = 0x00
BIKE_CONTROL_LIGHT_ON = 0x64
BIKE_CONTROL_PAYLOAD_LENGTH = 8
```
