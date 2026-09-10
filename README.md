# Hyena E-Bike Home Assistant Integration

![GitHub manifest version](https://img.shields.io/github/manifest-json/v/guyhth/home-assistant-hyena?filename=manifest.json)

Home Assistant custom integration for monitoring Trek e-bikes equipped with Hyena motor systems via Bluetooth Low Energy (BLE).

This integration was originally based on the work of [mpkogli/home-assistant-hyena](https://github.com/mpkogli/home-assistant-hyena), and has subsequently been extended and tested with a Trek FX+ 2 using the DITK variant of the Hyena BLE protocol.

> For detailed reverse-engineering and protocol information, see [protocol.md](protocol.md).

## Disclaimer

This integration is provided "as is" without warranty of any kind, express or implied. The author is not responsible for any damage, data loss, or other issues that may arise from using the integration. Use at your own risk.

### AI-assisted development

AI tools have been used extensively during development, including for code development, debugging, protocol analysis, and documentation. Changes have been reviewed, tested, and validated by a human, including testing against real e-bike hardware where possible.

Some aspects of the Hyena BLE protocol are still being reverse-engineered, so undocumented telemetry should be treated as provisional unless explicitly described as confirmed.

## Compatible Devices

### Tested

The integration has been tested and confirmed working with:

- **Trek FX+ 2** e-bike with Hyena motor system
- **DITK-series** Bluetooth implementation
- Bluetooth device name beginning with `DITK`

### XWTK compatibility

The original integration was developed for Hyena e-bikes using the XWTK Bluetooth implementation. The telemetry protocol used by XWTK and DITK devices appears to differ significantly and, as there is no suitable XWTK hardware available for testing, XWTK support has been removed.

If you have an XWTK bike and can help test or develop compatibility, contributions and protocol captures are welcome. The original project may also be useful: [mpkogli/home-assistant-hyena](https://github.com/mpkogli/home-assistant-hyena).

## Prerequisites

Before installing, ensure you have:

1. **Home Assistant 2024.8.0 or newer**
2. **ESPHome Bluetooth Proxy** configured and running
   - The proxy should be within Bluetooth range of the e-bike.
   - The ESPHome `bluetooth_proxy` component must be enabled.
   - An ESPHome proxy capable of active GATT connections is required for the current DITK implementation.
3. **Bluetooth Integration** enabled in Home Assistant.

## Installation

### HACS

Add this repository as a custom integration repository in HACS, then install **Hyena E-Bike** and restart Home Assistant.

### Manual installation

1. Download or clone this repository.
2. Copy the repository contents into `custom_components/hyena_ebike/`.
3. Restart Home Assistant.
4. Follow the [Setup](#setup) steps below.

## Setup

1. Ensure the e-bike is powered on and within Bluetooth range of the ESPHome Bluetooth Proxy.
2. Go to **Settings → Devices & Services**.
3. Select **Add Integration**.
4. Search for **Hyena E-Bike**.
5. Follow the configuration flow.
   - If the bike is in range, it should be discovered automatically.
   - Alternatively, enter the Bluetooth MAC address manually.

## Devices and Entities

The integration creates a single Home Assistant device named **Hyena E-Bike**.

| Entity | Type | Description |
|---|---|---|
| **Connected** | Binary sensor | Whether an active BLE GATT connection to the e-bike exists. |
| **Light** | Light | E-bike light control and current state. |
| **Battery SoC** | Sensor | Battery state of charge, 0–100%. |
| **Battery SoH** | Sensor | Battery state of health, 0–100%. |
| **Battery Charging** | Binary sensor | Whether the battery is currently charging. |
| **Battery Voltage** | Sensor | Battery voltage in volts. |
| **Battery Current** | Sensor | Battery current in amps. Positive values indicate discharge; negative values indicate charging. |
| **Battery Power** | Sensor | Calculated battery power in watts. |
| **Odometer** | Sensor | Lifetime distance travelled, in kilometres. |

Telemetry entities update from BLE notifications and retain their last received value where appropriate. The Connected sensor reflects the actual GATT connection state.

## Features

- Real-time BLE notification-based telemetry.
- Battery SoC, SoH, voltage, current, power and charging state.
- Lifetime odometer.
- E-bike light control.
- Automatic Bluetooth discovery and connection management.
- Automatic reconnection after unexpected disconnections.
- ESPHome Bluetooth Proxy support for active GATT connections.
- Disconnects after a period of telemetry inactivity to avoid unnecessarily occupying a Bluetooth connection.

## Bluetooth Proxy

An ESPHome Bluetooth Proxy is recommended. The DITK implementation requires an active GATT connection to subscribe to the telemetry characteristic; passive Bluetooth scanning alone is insufficient.

For best results:

1. Position the Bluetooth Proxy close to the bike.
2. Avoid excessive 2.4 GHz interference.
3. Ensure the proxy has a reliable network connection.
4. Ensure the proxy has sufficient power.

## Troubleshooting

### Device not discovered

Check that:

1. The e-bike is powered on.
2. The e-bike is within Bluetooth range of the proxy.
3. The Home Assistant Bluetooth integration is enabled.
4. The ESPHome Bluetooth Proxy is operating correctly.
5. The bike is visible under **Settings → Devices & Services → Bluetooth**.

The integration currently recognises device names beginning with `DITK`.

### Connected shows Off

This means Home Assistant does not currently have an active BLE GATT connection to the bike.

Check:

1. The bike is powered on and in range.
2. The Bluetooth Proxy is online.
3. The proxy supports active GATT connections.
4. Home Assistant logs for `hyena_ebike` connection errors.

### Sensors show no data

Check that:

1. The bike is powered on and in range.
2. **Connected** reports On.
3. The ESPHome Bluetooth Proxy is operating correctly.
4. Home Assistant logs do not contain BLE or connection errors.

You can reload the integration from **Settings → Devices & Services → Hyena E-Bike → ⋮ → Reload**.

### Connection drops frequently

Try moving the Bluetooth Proxy closer to the bike, reducing 2.4 GHz interference, checking the proxy's network connection, and checking ESPHome logs for Bluetooth errors.

## Development and Contributions

This project is also a protocol-research project. Contributions containing BLE captures from other Hyena systems are particularly useful for improving compatibility.

When reporting a problem, please include:

- Home Assistant version
- ESPHome version
- E-bike model
- Bluetooth device name
- Relevant `hyena_ebike` log entries
- Relevant BLE packet captures, if available

For the detailed protocol reference and reverse-engineering evidence, see [protocol.md](protocol.md).

## License

This integration is released under the MIT License. See the `LICENSE` file for details.
