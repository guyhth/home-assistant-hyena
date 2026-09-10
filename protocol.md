# Hyena E-Bike BLE / HAP Protocol Notes

> **Status:** Reverse-engineering notes — incomplete and subject to revision.
>
> This document records what has been established so far from the Hyena/HAP Android application, BLE captures, and the Home Assistant integration. Confirmed facts, observed behaviour, and hypotheses are deliberately distinguished.

## 1. Scope and terminology

The bike appears to use a Hyena protocol stack built around **HAP** and **HBP**, carried over BLE. The Android application embeds Hyena SDK classes including:

- `io.hylink.hap.protocol.v2`
- `io.hylink.hbp`

The application exposes CAN-oriented characteristics and sends HAP instruction frames through the HBP BLE manager.

This project refers to the packets observed on the notification characteristic as **DITK/HAP packets**. The exact relationship between all layers of the protocol is not yet completely documented.

---

## 2. BLE GATT structure

The following UUIDs have been identified in the Android application and confirmed against the bike:

| Purpose | UUID |
|---|---|
| HAP service | `48592800-6879-656E-6174-656B2E485550` |
| CAN notification characteristic | `4859FF01-6879-656E-6174-656B2E485550` |
| CAN write characteristic | `4859FF02-6879-656E-6174-656B2E485550` |
| CAN write-filter characteristic | `4859FF00-6879-656E-6174-656B2E485550` |

### 2.1 Android SDK mapping

`io.hylink.hbp.connector.HyBleManager` maps the characteristics as follows:

- `canCh` / `canCharacteristicsUUID` → `4859FF01`
- `canWriteCh` / `canCharacteristicsWriteUUID` → `4859FF02`
- `canWriteFilterCh` / `canCharacteristicsWriteFilterUUID` → `4859FF00`

`HyBleManager.writeToCan(byte[])` ultimately calls the Nordic BLE manager's `writeCharacteristic()` on `canWriteCh`.

The Home Assistant integration therefore listens on `4859FF01` and writes commands to `4859FF02`.

---

## 3. Common packet framing

Observed DITK/HAP packets have the following basic structure:

```text
00 00 PP PP LL [payload...]
```

Where:

| Bytes | Meaning |
|---|---|
| `0-1` | Frame prefix: `00 00` |
| `2-3` | Packet/CAN ID, 16-bit big-endian |
| `4` | Payload length |
| `5...` | Payload |

For the packets currently decoded, the packet ID is therefore read as:

```python
packet_id = int.from_bytes(data[2:4], byteorder="big")
```

The payload is:

```python
data[5 : 5 + payload_length]
```

### 3.1 Example

A `BikeControl00` packet looks like:

```text
00 00 03 00 08 00 5A 64 5A 00 00 00 0F
```

This consists of:

```text
00 00          frame prefix
03 00          packet ID 0x0300
08             payload length = 8
00 5A 64 5A 00 00 00 0F   8-byte payload
```

No additional CRC is present in this 13-byte light-control frame.

---

# 4. Packet 0x0300 — BikeControl00

`0x0300` is identified in the HAP SDK as `BikeControl00`.

The Java/Kotlin source gives it:

```text
SID = 768 decimal = 0x300
```

The packet has an 8-byte data bin.

The following fields are established:

| Payload byte | Meaning | Confidence |
|---:|---|---|
| `0` | Profile request / profile value | Confirmed by SDK accessor `getProfileReq()` | 
| `1` | Unknown | Unknown |
| `2` | Light state | Confirmed | 
| `3` | Unknown | Unknown |
| `4` | Unknown | Unknown |
| `5` | Unknown | Unknown |
| `6` | Unknown | Unknown |
| `7` | 4-bit rolling sequence counter | Confirmed for light commands |

### 4.1 Light-state field

The SDK's `BikeControl00` class implements:

```java
getRawLightStateReq() = getDataBin()[2] & 255
getLightState() = rawLightStateReq > 0
```

Observed values are:

```text
0x00 = OFF
0x64 = ON
```

The application therefore treats byte 2 as the raw light-state request, with `100` (`0x64`) meaning ON.

### 4.2 Sequence counter

The Android application's light-control instruction modifies byte 7 with:

```java
bArrCopyOf[7] = (byte) ((bArrCopyOf[7] + 1) & 15);
```

Therefore byte 7 is a **4-bit rolling counter**, incremented modulo 16.

Observed captures show the counter progressing through values such as:

```text
... 0E → 0F → 00 → 01 ...
```

The other bytes of the original `BikeControl00` payload are preserved when creating a light command.

---

# 5. Light-control command

The light-control implementation in the Android application is especially well understood.

## 5.1 Android application flow

`LightPartImpl.turnLight(boolean)` eventually delegates to `e.salmon.turnLight(boolean)`.

`e.salmon.turnLight(boolean)`:

1. Waits for the current `BikeControl00` data.
2. Creates `snail.cuttlefish` with the current 8-byte data bin and requested light state.
3. Builds/sends the resulting HAP instruction.
4. Waits for the protocol response.

The relevant instruction class is:

```text
snail.cuttlefish
```

Its constructor receives:

```text
originBikeControl00DataBin
requested light state
```

Its `flounder()` method makes a copy of the original data bin and then:

```java
if (bool != null) {
    bArrCopyOf[2] = bool.booleanValue() ? (byte) 100 : (byte) 0;
}

bArrCopyOf[7] = (byte) ((bArrCopyOf[7] + 1) & 15);
```

Thus the command modifies only:

- byte 2 — requested light state
- byte 7 — rolling sequence counter

All other bytes are copied unchanged.

## 5.2 HAP instruction framing

The base `seal.jellyfish.build()` method creates the command frame as:

1. 4-byte instruction ID
2. 1-byte payload length
3. instruction payload

The instruction ID is `0x300`.

The helper used to encode the ID is **big-endian**. Therefore:

```text
0x00000300 → 00 00 03 00
```

The light instruction payload is 8 bytes, so the complete frame is:

```text
00 00 03 00 08 [8-byte BikeControl00 payload]
```

For the common payload:

```text
00 5A 00 5A 00 00 00 XX
```

an OFF command is:

```text
00 00 03 00 08 00 5A 00 5A 00 00 00 XX'
```

and an ON command is:

```text
00 00 03 00 08 00 5A 64 5A 00 00 00 XX'
```

where:

```text
XX' = (XX + 1) & 0x0F
```

### 5.3 No CRC on the light command

The `snail.cuttlefish` instruction does **not** call the CRC-building helper used by some other protocol instructions. Its `build()` path therefore produces the 13-byte frame directly.

This is consistent with the observed BLE traffic and the Home Assistant test capture.

---

# 6. Light command observations from Home Assistant

A live Home Assistant capture (`hyena-test.log`) was used to compare commands sent by the integration with subsequent `0x0300` notifications from the bike.

This confirmed that the integration's 13-byte light command reaches the bike and that the bike subsequently reports `0x0300` state packets.

A particularly useful observation was that an OFF command can initially be followed by a `0x0300` packet containing the **same sequence number but the old ON state**. Therefore:

> A `0x0300` packet immediately following a write is not necessarily sufficient evidence that the requested light state has been applied.

A later command was followed by a `0x0300` packet matching both the requested state and sequence number.

This led to the current integration design principle:

**Light commands should be considered confirmed only when a subsequent `0x0300` packet reports both the requested light state and the sequence number used by the command.**

The Home Assistant integration should not optimistically assume that a successful GATT write means the light has changed.

---

# 7. Packet 0x0402 — Battery SoC

`0x0402` has been identified as the battery state-of-charge packet.

The current decoder uses payload byte 0:

```python
soc = payload[0]
```

Values from 0–100 are interpreted as percentage SoC.

Example interpretation:

```text
packet ID = 0x0402
payload[0] = 75
→ Battery SoC = 75%
```

The exact semantics of all remaining bytes in the `0x0402` payload have not yet been established.

---

# 8. Packet 0x0401 — Battery voltage/current/power

`0x0401` contains battery electrical telemetry.

The current decoder interprets it as:

| Payload bytes | Interpretation | Encoding |
|---|---|---|
| `0-1` | Voltage | unsigned little-endian, mV |
| `2-3` | Unknown | Unknown |
| `4-7` | Current | signed little-endian, mA |

Conversion:

```python
voltage = voltage_mv / 1000.0
current = current_ma / 1000.0
power = voltage * current
```

Power is therefore **calculated by the integration**, rather than being a directly decoded field.

The meaning of payload bytes 2–3 remains unknown.

The sign convention of current should be regarded as observed rather than fully documented until independently confirmed against charging/discharging conditions.

---

# 9. Packet 0x0202 — Odometer

`0x0202` has been identified as the odometer packet.

The current decoder interprets:

```python
odometer_m = int.from_bytes(
    payload[4:8],
    byteorder="little",
    signed=False,
)

odometer_km = odometer_m / 1000.0
```

Therefore:

```text
payload bytes 4–7 = odometer in metres
```

and the integration exposes the result in kilometres.

The meaning/encoding of payload bytes 0–3 is currently unknown.

---

# 10. Known packet summary

| ID | Name / purpose | Payload | Known fields | Status |
|---:|---|---:|---|---|
| `0x0202` | Odometer | ≥8 bytes | bytes 4–7 = metres, little-endian | Decoded |
| `0x0300` | `BikeControl00` | 8 bytes | byte 0 profile; byte 2 light; byte 7 sequence | Partially decoded |
| `0x0401` | Battery telemetry | ≥8 bytes | bytes 0–1 voltage; bytes 4–7 current | Partially decoded |
| `0x0402` | Battery SoC | ≥1 byte | byte 0 SoC % | Decoded |

Other packet IDs have been observed during reverse engineering but are not yet sufficiently understood to document as decoded protocol fields.

---

# 11. Connection and notification behaviour

The Home Assistant integration connects using `BleakClientWithServiceCache` via `bleak_retry_connector` and subscribes to notifications from `4859FF01`.

Most telemetry is notification-driven. The coordinator also has a fallback update interval, but normal data arrives through BLE notifications.

The integration currently resets its inactivity disconnect timer whenever decoded packet activity is received and disconnects after 120 seconds without telemetry.

On a new connection, the cached `BikeControl00` payload is cleared because commands should be based on a fresh packet from the bike rather than stale state from an earlier connection.

---

# 12. Current light-control implementation requirements

For a robust implementation, light control should follow these rules:

1. Ensure the BLE connection is active.
2. Wait until a current `0x0300` / `BikeControl00` payload is available.
3. Copy the complete 8-byte payload.
4. Set byte 2 to:
   - `0x64` for ON
   - `0x00` for OFF
5. Increment byte 7 modulo 16.
6. Construct:

```text
00 00 03 00 08 [8-byte modified payload]
```

7. Write the resulting 13 bytes to:

```text
4859FF02-6879-656E-6174-656B2E485550
```

8. Wait for a `0x0300` notification whose:
   - byte 2 matches the requested state, **and**
   - byte 7 matches the sequence number sent.
9. Only then regard the command as confirmed.

A command timeout should be treated as a failure to confirm the requested state, rather than as proof that the command was rejected.

Concurrent light commands should be serialized so that two commands cannot calculate/send conflicting sequence numbers from the same source packet.

---

# 13. Reverse-engineering evidence

The protocol knowledge in this document comes from three main evidence sources.

### 13.1 Android application source/decompilation

The embedded Hyena SDK provides direct evidence for:

- GATT characteristic UUID mappings
- `BikeControl00` SID `0x300`
- light state accessor behaviour
- light command construction
- sequence counter handling
- HAP instruction framing
- BLE write path

Where SDK source explicitly implements a field or transformation, this document treats it as confirmed.

### 13.2 BLE captures

nRF Connect captures from the bike show repeated `0x0300` packets with the expected light-state values and rolling sequence counter.

These captures independently support the SDK-derived interpretation.

### 13.3 Home Assistant live capture

`hyena-test.log` records commands generated by the Home Assistant integration and the bike's subsequent notifications. This is particularly useful for validating the command/write path and demonstrating that an immediate `0x0300` response does not always mean the requested state has already taken effect.

---

# 14. Unknowns / future investigation

The following areas remain incomplete:

- Meaning of all `BikeControl00` bytes other than the currently identified fields.
- Full semantics of the `0x0401` payload, particularly bytes 2–3.
- Remaining fields in `0x0402`.
- Meaning of `0x0202` payload bytes 0–3.
- Other observed packet IDs and their associated HAP classes.
- Complete semantics of the `4859FF00` write-filter characteristic.
- Complete HAP/HBP framing and whether there are additional layers or message types not yet encountered.
- Exact protocol-level acknowledgement/error semantics for all instruction types.
- Whether every write operation uses the same 13-byte framing and whether some commands add checksums/CRCs.
- The complete mapping between HAP instruction classes and the CAN packet IDs observed over BLE.

These should be investigated from the Android SDK and controlled BLE captures before being promoted from hypotheses to confirmed protocol behaviour.

---

# 15. Useful implementation constants

For the Home Assistant integration:

```python
PRIMARY_SERVICE_UUID = "48592800-6879-656E-6174-656B2E485550"
MAIN_CHARACTERISTIC_UUID = "4859FF01-6879-656E-6174-656B2E485550"
WRITE_CHARACTERISTIC_UUID = "4859FF02-6879-656E-6174-656B2E485550"

BIKE_CONTROL_PACKET_ID = 0x0300
```

Light command construction:

```python
payload = bytearray(bike_control_00)
payload[2] = 0x64 if light_on else 0x00
payload[7] = (payload[7] + 1) & 0x0F
packet = b"\x00\x00\x03\x00\x08" + bytes(payload)
```

---

## Disclaimer

This is a reverse-engineering record for interoperability and development of the Home Assistant integration. It is not an official Hyena protocol specification. Unknown or inferred fields should not be treated as authoritative until independently validated.
