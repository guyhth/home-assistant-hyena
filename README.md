# Hyena E-Bike Home Assistant Integration

![GitHub manifest version](https://img.shields.io/github/manifest-json/v/guyhth/home-assistant-hyena?filename=manifest.json)

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
- DITK-series Bluetooth implementation
- Bluetooth device name beginning with `DITK`

### XWTK compatibility

The original integration was developed for Hyena e-bikes using the XWTK Bluetooth implementation, and the integration continues to recognise Bluetooth device names beginning with `XWTK`.

However, the telemetry protocol used by XWTK and DITK devices appears to differ significantly.

XWTK compatibility has **not been tested by the current maintainer**, and new DITK-specific functionality may not be available on XWTK bikes.

If you have an XWTK Hyena e-bike and are willing to help test or develop compatibility, contributions and protocol captures would be very welcome.

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

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=hyena_ebike)

## Devices and Entities

The integration creates a single Home Assistant device named **Hyena E-Bike**, grouping the entities associated with the bike.

The device currently identifies itself as:

- **Manufacturer:** Hyena
- **Model:** Trek FX+ 2
- **Connection:** Bluetooth

### Currently available entities

| Entity | Type | Description |
|---|---|---|
| **Connected** | Binary sensor | Indicates whether an active BLE connection to the e-bike is established. |
| **Battery** | Sensor | Battery state of charge (0–100%). |
| **Battery Voltage** | Sensor | Battery voltage in volts. |
| **Battery Current** | Sensor | Battery current in amps. Positive values indicate discharge; negative values indicate charging. |
| **Battery Power** | Sensor | Calculated battery power in watts. |
| **Battery Temperature** | Sensor | Battery temperature in °C, where available. |

The **Connected** sensor reports the actual state of the BLE connection:

- **On:** an active BLE connection exists
- **Off:** the bike is not currently connected
- It does not become unavailable simply because telemetry has stopped arriving

Telemetry sensors retain their last received values where appropriate. Sensors representing instantaneous data may be made unavailable when sufficient protocol support is available to distinguish stale data from current data.

## DITK Protocol Support

The DITK implementation has been reverse-engineered using BLE captures from a Trek FX+2.

The DITK implementation uses:

- **Primary service:** `48592800-6879-656E-6174-656B2E485550`
- **Telemetry characteristic:** `4859FF01-6879-656E-6174-656B2E485550`
- **Transport:** Bluetooth Low Energy notifications

The integration uses event-driven BLE notifications rather than repeatedly polling the bike.

### Confirmed and identified telemetry

Several additional telemetry packets have been identified during protocol analysis:

| Packet | Data | Interpretation | Status |
|---|---|---|---|
| `0402` | Payload byte 0 | Battery SOC (%) | Confirmed |
| `0401` | Payload bytes 0–1 | Battery voltage (mV) | High confidence |
| `0401` | Payload bytes 4–7 | Battery current (mA, signed) | High confidence |
| `0401` | Voltage × current | Battery power | Calculated |
| `0202` | Payload bytes 4–5 | Lifetime odometer (m) | Very high confidence |
| `0203` | Payload bytes 0–1 | Pedal cadence signal | High confidence |
| `0203` | Signal ÷ 40 | Pedal cadence (RPM) | Provisional |
| `0207` | Payload bytes 0–1 | Wheel rotational-speed signal | High confidence |
| `0201` | Payload bytes 0–1 | Motor/wheel rotational-speed signal | Provisional |

Not all of these values are currently exposed as Home Assistant entities. Further protocol investigation is ongoing.

### Protocol status

The DITK protocol is only partially documented.

Where packet meanings have been inferred from repeated observations, deliberate tests, or correlations with known values, they are labelled accordingly. Unknown packets are deliberately not exposed as sensors until their meaning can be established with reasonable confidence.

## Connection Management

The integration maintains a BLE GATT connection while telemetry is being received.

It:

- Automatically reconnects after an unexpected disconnection
- Reports connection state through the **Connected** binary sensor
- Uses BLE notifications for telemetry
- Disconnects after a period of telemetry inactivity to avoid unnecessarily occupying a Bluetooth connection
- Automatically reconnects when further data is required

## Bluetooth Proxy

An ESPHome Bluetooth Proxy is recommended.

The DITK implementation requires an active GATT connection to subscribe to the telemetry characteristic. Passive Bluetooth scanning alone is therefore insufficient.

For best results:

- Position the Bluetooth Proxy close to the bike.
- Avoid excessive 2.4 GHz interference.
- Ensure the proxy has a reliable network connection.
- Ensure the proxy has sufficient power.

## Troubleshooting

### Device Not Discovered

Check:

1. The e-bike is powered on.
2. The e-bike is within Bluetooth range of the proxy.
3. The Bluetooth integration is enabled in Home Assistant.
4. The ESPHome Bluetooth Proxy is operating correctly.
5. The bike's Bluetooth device is visible under **Settings → Devices & Services → Bluetooth**.

The integration currently recognises device names beginning with:

- `DITK`
- `XWTK`

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

The DITK telemetry protocol is being investigated by capturing BLE notifications and comparing packet contents against known bike states and deliberate tests.

Examples include:

- Comparing battery telemetry with known state of charge.
- Comparing voltage and current values against charging behaviour.
- Deliberately pedalling at known cadence to establish scaling factors.
- Comparing wheel-speed signals with observed wheel movement and GPS speed.
- Monitoring packets while the bike is stationary, moving, charging, and disconnected.

Contributions containing BLE captures from other Hyena systems are particularly useful for improving compatibility.

## Future Work

Potential future improvements include:

- Additional speed and cadence sensors
- Odometer sensor
- Motor RPM
- Improved identification of DITK telemetry packets
- Temperature protocol investigation
- Improved instantaneous-data availability handling
- Better support for XWTK systems
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

This integration is released under the MIT License. See the `LICENSE` file in the repository for details.