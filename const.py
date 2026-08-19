"""Constants for the Hyena E-Bike integration."""

# Integration domain
DOMAIN = "hyena_ebike"

# BLE Device identifiers
DEVICE_NAME_PREFIXES = (
    "XWTK",
    "DITK",
)
MANUFACTURER = "Hyena"
MODEL = "Trek FX+2"

# BLE Service and Characteristic UUIDs
PRIMARY_SERVICE_UUID = "48592800-6879-656E-6174-656B2E485550"
# MAIN_CHARACTERISTIC_UUID = "48590001-6879-656E-6174-656B2E485550"
MAIN_CHARACTERISTIC_UUID = "4859FF01-6879-656E-6174-656B2E485550"

# Packet identifiers from protocol documentation
PACKET_ID_BATTERY_SOC = 0x0A
PACKET_ID_VOLTAGE = 0x01
PACKET_ID_CURRENT_POWER = 0x06
PACKET_ID_TEMPERATURE = 0x07
PACKET_ID_SPEED_RPM = 0x05
PACKET_ID_PEDAL_CADENCE = 0x08
PACKET_ID_MOTOR_STATUS = 0x09

# Frame delimiter
FRAME_DELIMITER = bytes.fromhex("ee00000000000000")

# Sensor types
SENSOR_BATTERY = "battery"
SENSOR_TEMPERATURE = "temperature"
SENSOR_BATTERY_VOLTAGE = "battery_voltage"
SENSOR_BATTERY_CURRENT = "battery_current"
SENSOR_BATTERY_POWER = "battery_power"

# Configuration
CONF_DEVICE_ADDRESS = "device_address"

# Signal names for dispatcher
SIGNAL_DATA_UPDATED = f"{DOMAIN}_data_updated"
