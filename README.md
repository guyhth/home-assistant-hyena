# Hyena E-Bike Home Assistant Integration

Home Assistant custom integration for monitoring Trek e-bikes equipped with Hyena motor systems via Bluetooth Low Energy (BLE).

This integration was originally based on the work of [mpkogli/home-assistant-hyena](https://github.com/mpkogli/home-assistant-hyena), and has subsequently been extended and tested with a Trek FX+ 2 using the DITK variant of the Hyena BLE protocol.

## Disclaimer

This integration is provided "as is" without warranty of any kind, express or implied. The author is not responsible for any damage, data loss, or other issues that may arise from using this integration. Use at your own risk.

### AI-assisted development

AI tools have been used extensively during the development of this integration, including for code development, debugging, protocol analysis, and documentation.

AI has been used as an assistant rather than as an autonomous developer. Changes have been reviewed, tested, and validated by a human, including testing against real e-bike hardware where possible.

Some aspects of the Hyena BLE protocol are still being reverse-engineered, so interpretations of undocumented telemetry data should be considered provisional unless explicitly described as confirmed.

## Compatible Devices

### Tested

The integration has been tested and confirmed working with:

- **Trek FX+ 2** e-bike with Hyena motor system
- **DITK-series** Bluetooth implementation
- Bluetooth device name beginning with `DITK`

### XWTK compatibility

The original integration was developed for Hyena e-bikes using the XWTK Bluetooth implementation. However, the telemetry protocol used by XWTK and DITK devices appears to differ significantly and, as I do not have suitable hardware to test with, support for XWTK Hyena e-bikes has been removed.

If you have an XWTK Hyena e-bike and are willing to help test or develop compatibility, contributions and protocol captures would be very welcome. Alternatively, the original project might work for you: [mpkogli/home-assistant-hyena](https://github.com/mpkogli/home-assistant-hyena).

## Prerequisites

Before installing this integration, ensure you have:

1. **Home Assistant 2024.8.0 or newer**
2. **ESPHome Bluetooth Proxy** configured and running
   - The proxy should be within Bluetooth range of the e-bike
   - The ESPHome `bluetooth_proxy` component must be enabled
   - An ESPHome proxy capable of active GATT connections is required for the current DITK implementation
3. **Bluetooth Integration** enabled in Home Assistant

## Installation

### HACS

The integration is available as a custom repository for HACS.

Add this repository as a custom integration repository in HACS, then install **Hyena E-Bike**.

After installation, restart Home Assistant.

### Manual Installation

1. Download or clone this repository.

2. Copy the repository contents into:

   `custom_components/hyena_ebike/`

3. Restart Home Assistant.

4. Proceed to the [Setup](#setup) section.

## Setup

1. Ensure your e-bike is powered on and within Bluetooth range of your ESPHome Bluetooth Proxy.
2. Navigate to **Settings → Devices & Services**.
3. Select **Add Integration**.
4. Search for **Hyena E-Bike**.
5. Follow the configuration flow.
   - If the e-bike is in range, it should be automatically discovered.
   - Alternatively, the Bluetooth MAC address can be entered manually.

You can also use the Home Assistant configuration-flow button:



## Devices and Entities

The integration creates a single Home Assistant device named **Hyena E-Bike**, grouping the entities associated with the bike.

The device currently identifies itself as:

- **Manufacturer:** Hyena
- **Model:** Trek FX+ 2
- **Connection:** Bluetooth

### Currently available entities

| Entity               | Type          | Description                                                                                     |
| -------------------- | ------------- | ----------------------------------------------------------------------------------------------- |
| **Connected**        | Binary sensor | Indicates whether an active BLE connection to the e-bike is established.                        |
| **Battery SoC**      | Sensor        | Battery state of charge (0–100%).                                                               |
| **Battery SoH**      | Sensor        | Battery state of health (0–100%).                                                               |
| **Battery Charging** | Binary sensor | Indicates whether the battery is currently charging.                                            |
| **Battery Voltage**  | Sensor        | Battery voltage in volts.                                                                       |
| **Battery Current**  | Sensor        | Battery current in amps. Positive values indicate discharge; negative values indicate charging. |
| **Battery Power**    | Sensor        | Calculated battery power in watts.                                                              |
| **Odometer**         | Sensor        | Lifetime distance travelled by the e-bike, in kilometres.                                       |

### Entity Availability

The **Connected** sensor reports the actual state of the BLE GATT connection:

- **On:** an active BLE connection exists
- **Off:** the bike is not currently connected

Telemetry sensors retain their last received values where appropriate.

## Features

- **Real-time Updates:** Uses BLE notifications for immediate data updates rather than polling.
- **Battery Monitoring:** Provides battery SoC, SoH, voltage, current, power and charging state.
- **Odometer:** Reports the lifetime distance recorded by the bike.
- **Automatic Discovery:** Automatically discovers compatible e-bikes via Bluetooth.
- **Connection Management:** Handles disconnections gracefully and automatically reconnects.
- **ESPHome Proxy Compatible:** Works with an ESPHome Bluetooth Proxy capable of active GATT connections.
- **Low Power Impact:** Uses the bike's existing BLE telemetry rather than repeatedly polling the device.

## DITK Protocol Support

The DITK implementation has been reverse-engineered using BLE captures from a Trek FX+2 and analysis of the Hyena Android application.

The DITK implementation uses:

- **Primary service:** `48592800-6879-656E-6174-656B2E485550`
- **Telemetry characteristic:** `4859FF01-6879-656E-6174-656B2E485550`
- **Transport:** Bluetooth Low Energy notifications

The integration uses event-driven BLE notifications rather than repeatedly polling the bike.

### Confirmed and identified telemetry

| Packet | Data                  | Interpretation                  | Status         |
| ------ | --------------------- | ------------------------------- | -------------- |
| `0400` | Payload byte 2, bit 7 | Battery charging state          | **Confirmed**  |
| `0401` | Payload bytes 0–3     | Battery voltage (mV)            | **Confirmed**  |
| `0401` | Payload bytes 4–7     | Battery current (mA)            | **Confirmed**  |
| `0401` | Voltage × current     | Battery power                   | **Calculated** |
| `0402` | Payload bytes 0–3     | Battery SOC (%)                 | **Confirmed**  |
| `0402` | Payload bytes 4–7     | Remaining battery energy (mWh)  | **Confirmed**  |
| `0403` | Payload bytes 0–1     | Battery SOH (%)                 | **Confirmed**  |
| `0403` | Payload bytes 4–7     | Reported battery capacity (mWh) | **Confirmed**  |
| `0202` | Payload bytes 4–7     | Lifetime odometer (km)          | **Confirmed**  |
| `0203` | Payload bytes 0–1     | Raw pedal cadence signal        | **Confirmed**  |
| `0203` | Raw cadence ÷ 40      | Pedal cadence (RPM)             | **Confirmed**  |
| `0201` | Payload bytes 0–1     | Bike speed (km/h)               | **Confirmed**  |
| `0201` | Payload byte 7        | Controller temperature (°C)     | **Confirmed**  |
| `0202` | Payload byte 1        | Motor temperature (°C)          | **Confirmed**  |
| `0202` | Payload bytes 2–3     | Raw speed-limit value           | **Identified** |
| `0207` | Payload bytes 0–1     | Unknown                         | **Unknown**    |

Not all identified values are currently exposed as Home Assistant entities. Further protocol investigation is ongoing.

### Battery state of charge

Battery SoC is reported by packet `0x0402`.

The first four payload bytes contain the SoC as a little-endian unsigned 32-bit value representing a percentage.

For example:

```text
0402 08 57 0000 006C F402 00
```

The payload begins:

```text
57 00 00 00
```

which represents **87%**.

The same packet also contains an absolute remaining-energy value in payload bytes 4–7, expressed in mWh.

### Battery state of health

Battery SoH is reported by packet `0x0403`.

Payload bytes 0–1 contain the battery state of health as a little-endian unsigned 16-bit percentage.

Payload bytes 4–7 contain the reported battery capacity in mWh.

For example, a packet containing:

```text
64 00 00 00 E0 67 03 00
```

reports:

- **100% SoH**
- **223,200 mWh** reported capacity

### Battery charging state

Battery charging status is reported by packet `0x0400`.

The charging flag is **bit 7 of payload byte 2**:

```text
charging = bool(payload[2] & 0x80)
```

This has been confirmed using a controlled charger test. When the charger was disconnected, payload byte 2 was `0x4C` (bit 7 clear). When charging began, it changed to `0xCC` (bit 7 set).

### Battery current and power

Packet `0x0401` contains battery voltage and current.

The integration converts these values into Home Assistant-friendly units:

- Voltage: mV → V
- Current: mA → A
- Power: calculated from voltage × current

Positive current represents battery discharge and negative current represents charging.

### Odometer

Packet `0x0202` contains the lifetime odometer in payload bytes 4–7.

The value is a little-endian 32-bit integer representing metres, which is divided by 1000 to obtain kilometres.

### Cadence

Packet `0x0203` contains a raw cadence value in payload bytes 0–1.

The Hyena application source decodes this as:

```text
raw value × 0.025
```

or equivalently:

```text
raw value ÷ 40
```

giving cadence in RPM.

The protocol interpretation has been confirmed from the application source.

### Protocol status

The DITK protocol is only partially documented.

Where packet meanings have been established through application-source analysis, deliberate tests, or repeated observations, they are marked as confirmed. Unknown packets are deliberately not exposed as sensors until their meaning can be established with reasonable confidence.

## Connection Management

The integration maintains a BLE GATT connection while telemetry is being received.

It:

- Automatically reconnects after an unexpected disconnection
- Reports connection state through the Connected binary sensor
- Uses BLE notifications for telemetry
- Disconnects after a period of telemetry inactivity to avoid unnecessarily occupying a Bluetooth connection
- Automatically reconnects when further data is required

## Bluetooth Proxy

An ESPHome Bluetooth Proxy is recommended.

The DITK implementation requires an active GATT connection to subscribe to the telemetry characteristic. Passive Bluetooth scanning alone is therefore insufficient.

For best results:

1. Position the Bluetooth Proxy close to the bike.
2. Avoid excessive 2.4 GHz interference.
3. Ensure the proxy has a reliable network connection.
4. Ensure the proxy has sufficient power.

## Troubleshooting

### Device Not Discovered

Check:

1. The e-bike is powered on.
2. The e-bike is within Bluetooth range of the proxy.
3. The Bluetooth integration is enabled in Home Assistant.
4. The ESPHome Bluetooth Proxy is operating correctly.
5. The bike's Bluetooth device is visible under **Settings → Devices & Services → Bluetooth**.

The integration currently recognises device names beginning with `DITK`.

### Connected Sensor Shows "Off"

This means that Home Assistant currently does not have an active BLE GATT connection to the bike.

Check:

1. The bike is powered on.
2. The bike is within range.
3. The Bluetooth Proxy is online.
4. The proxy supports active GATT connections.
5. Home Assistant logs for `hyena_ebike` connection errors.

### Sensors Show No Data

Check that:

1. The bike is powered on.
2. The bike is within Bluetooth range.
3. The Connected sensor reports **On**.
4. The ESPHome Bluetooth Proxy is operating correctly.
5. Home Assistant logs do not contain BLE or connection errors.

You can reload the integration from:

**Settings → Devices & Services → Hyena E-Bike → ⋮ → Reload**

### Connection Drops Frequently

Try:

1. Moving the Bluetooth Proxy closer to the bike.
2. Reducing interference from other Bluetooth devices.
3. Reducing 2.4 GHz Wi-Fi interference.
4. Checking the proxy's network connection.
5. Checking ESPHome logs for Bluetooth errors.

## Development and Protocol Research

This project is partly a protocol-research project.

The DITK telemetry protocol is being investigated by capturing BLE notifications and comparing packet contents against known bike states, deliberate tests, and the behaviour of the Hyena Android application.

Examples include:

- Comparing battery telemetry with known state of charge.
- Comparing voltage and current values against charging behaviour.
- Testing battery charging-state transitions.
- Deliberately pedalling at known cadence to establish scaling factors.
- Comparing wheel-speed signals with observed wheel movement and GPS speed.
- Monitoring packets while the bike is stationary, moving, charging, and disconnected.
- Analysing the Hyena application source to identify packet structures and scaling factors.

Contributions containing BLE captures from other Hyena systems are particularly useful for improving compatibility.

## Future Work

Potential future improvements include:

- Additional speed and cadence sensors
- Motor RPM
- Additional battery telemetry
- Further investigation of `0207`
- Improved identification of DITK telemetry packets
- Temperature protocol investigation
- Improved instantaneous-data availability handling
- Reinstate support for XWTK systems
- Support for additional Hyena-equipped e-bike models

## Support and Contributions

For bug reports, feature requests, protocol discoveries, or questions, please open an issue or pull request on GitHub.

When reporting a problem, please include:

- Home Assistant version
- ESPHome version
- E-bike model
- Bluetooth device name
- Relevant `hyena_ebike` log entries
- Any relevant BLE packet captures

If you have an XWTK bike or another Hyena system and are interested in helping with protocol compatibility, please get in touch through the GitHub repository.

## License

This integration is released under the MIT License. See the `LICENSE` file for details.
