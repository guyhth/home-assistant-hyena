# Hyena E-Bike Home Assistant Integration

![GitHub manifest version](https://img.shields.io/github/manifest-json/v/guyhth/home-assistant-hyena?filename=manifest.json)

Home Assistant custom integration for monitoring Trek e-bikes equipped with Hyena motor systems via Bluetooth Low Energy.

## Disclaimer

This integration is provided "as is" without warranty of any kind, express or implied. The author is not responsible for any damage, data loss, or other issues that may arise from using this integration. Use at your own risk.

## Compatible Devices

This integration has been tested and confirmed working with:
- **Trek FX+2** e-bike with Hyena motor system

Other Trek e-bikes using Hyena motor systems (identifiable by Bluetooth device name starting with "XWTK") may also be compatible but have not been tested.

## Prerequisites

Before installing this integration, ensure you have:

1. **Home Assistant 2024.8.0 or newer**
2. **ESPHome Bluetooth Proxy** configured and running
   - The proxy device must be within Bluetooth range (~20 feet) of your e-bike
   - The `bluetooth_proxy` component must be enabled in your ESPHome device configuration
3. **Bluetooth Integration** enabled in Home Assistant (Settings → Devices & Services → Bluetooth)

## Installation

### Manual Installation

1. Download the latest release from the [GitHub repository](https://github.com/mpkogli/home-assistant-hyena)
2. Copy the contents of the repository into your Home Assistant's `custom_components` directory
   - Path should be: `<config_directory>/custom_components/hyena_ebike/<repository contents>`
3. Restart Home Assistant
4. Proceed to the [Setup](#setup) section below

**Note**: If installing manually, you will need to manually check for updates by subscribing to releases on the GitHub repository.

## Setup

1. Ensure your e-bike is powered on and within Bluetooth range of your ESPHome proxy device
2. Navigate to the Home Assistant Integrations page (Settings → Devices & Services)
3. Click the `+ ADD INTEGRATION` button in the lower right-hand corner **I'm not certain this works, as I don't use HACS**
4. Search for `Hyena E-Bike`
5. Follow the configuration flow:
   - If your e-bike is in range, it should be automatically discovered
   - Alternatively, you can manually enter the Bluetooth MAC address of your e-bike

Alternatively, click on the button below to add the integration:

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=hyena_ebike)

## Devices

A device is created for your e-bike named **"Hyena E-Bike"** which groups all related sensor entities. The device information includes:
- Manufacturer: Hyena
- Model: Trek FX+2
- Bluetooth address

## Entities

The integration creates the following sensor entities for your e-bike:

| Entity | Entity Type | Description |
|--------|-------------|-------------|
| **Battery** | Sensor | Battery state of charge (0-100%). Updates in real-time when bike is in range. Includes dynamic battery icon based on charge level. |
| **Battery Temperature** | Sensor | Battery temperature in degrees Celsius. Marked as a diagnostic entity. Updates in real-time when bike is in range. |

### Entity Availability

Entities will show as "Unavailable" when:
- The e-bike is powered off
- The e-bike is out of Bluetooth range
- The ESPHome Bluetooth Proxy is offline

The integration will automatically reconnect and resume updates when the bike returns to range.

## Features

- **Real-time Updates**: Uses BLE notifications for immediate data updates (not polling)
- **Automatic Discovery**: Integration automatically discovers compatible e-bikes via Bluetooth
- **Connection Management**: Handles disconnections gracefully and automatically reconnects
- **Low Power Impact**: Efficient BLE implementation minimizes battery drain on proxy devices
- **ESPHome Proxy Compatible**: Works seamlessly with your existing ESPHome Bluetooth Proxy setup

## Troubleshooting

### Device Not Discovered

**Symptoms**: E-bike doesn't appear in the setup flow

**Solutions**:
1. Verify the e-bike is powered on (display is active)
2. Check that the bike is within ~20 feet of your ESPHome Bluetooth Proxy
3. Verify your ESPHome device shows as "Connected" in Settings → Devices & Services → Bluetooth
4. Check ESPHome device logs for Bluetooth errors
5. Try manually adding the integration using the bike's Bluetooth MAC address
   - You can find the MAC address in Settings → Devices & Services → Bluetooth

### Sensors Show "Unavailable"

**Symptoms**: Entities exist but show no data

**Solutions**:
1. Check that the bike is powered on and in range
2. Review Home Assistant logs for connection errors:
   - Settings → System → Logs
   - Filter by "hyena_ebike"
3. Restart the integration:
   - Settings → Devices & Services → Hyena E-Bike → ... (three dots) → Reload
4. Check ESPHome Bluetooth Proxy connection status

### Connection Drops Frequently

**Symptoms**: Sensors alternately show data then become unavailable

**Solutions**:
1. Move the ESPHome proxy device closer to the e-bike
2. Reduce interference from other Bluetooth devices
3. Check for WiFi interference (Bluetooth and 2.4GHz WiFi can conflict)
4. Verify the ESPHome device has adequate power supply
5. Check ESPHome device logs for Bluetooth stack errors

### Integration Fails to Load

**Symptoms**: Integration shows "Failed to setup" error

**Solutions**:
1. Verify you're running Home Assistant 2024.8.0 or newer
2. Check that the `bluetooth` integration is enabled
3. Review Home Assistant logs for specific error messages
4. Ensure all files were copied correctly during manual installation
5. Restart Home Assistant after installation

## Technical Details

### BLE Protocol

The integration communicates with the e-bike using:
- **Service UUID**: `48592800-6879-656E-6174-656B2E485550`
- **Characteristic UUID**: `48590001-6879-656E-6174-656B2E485550`
- **Update Method**: BLE notifications (event-driven, not polled)

### Packet Parsing

The integration parses telemetry packets according to the Hyena BLE protocol:
- **Battery SOC**: Packet ID `0x0A` - Single byte percentage (0-100)
- **Temperature**: Packet ID `0x07` - 2-byte big-endian value, divided by 10 for °C

## FAQ

**Q: Will this drain my e-bike battery?**
A: No. The integration uses passive BLE notifications which have minimal power impact. The e-bike already broadcasts this data continuously.

**Q: Can I monitor my bike while riding?**
A: Only if you remain within Bluetooth range (~20 feet) of your ESPHome proxy. This integration is primarily designed for monitoring while the bike is parked/charging.

**Q: Does this work with other Trek e-bike models?**
A: Potentially. Any Trek e-bike with a Hyena motor system that broadcasts with device name starting with "XWTK" should work, but only the FX+2 has been tested.

**Q: Can I add more sensors (speed, cadence, etc.)?**
A: The e-bike broadcasts additional telemetry data. Future versions of this integration may expose additional sensors. Check the GitHub repository for updates.

**Q: Do I need HACS?**
A: No. This integration can be installed manually. HACS support may be added in the future.

## Support

For bug reports, feature requests, or questions:
- Open an issue on the [GitHub repository](https://github.com/mpkogli/home-assistant-hyena/issues)
- Provide Home Assistant version, ESPHome version, and relevant log entries

## License

This integration is released under the MIT License. See the LICENSE file in the repository for details.
