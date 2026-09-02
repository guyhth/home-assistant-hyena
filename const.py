"""Constants for the Hyena E-Bike integration."""

# Integration domain
DOMAIN = "hyena_ebike"

# BLE Device identifiers
DEVICE_NAME_PREFIX = "DITK"
MANUFACTURER = "Hyena"
MODEL = "Trek FX+ 2"

# BLE Service and Characteristic UUIDs
PRIMARY_SERVICE_UUID = "48592800-6879-656E-6174-656B2E485550"
MAIN_CHARACTERISTIC_UUID = "4859FF01-6879-656E-6174-656B2E485550"

# Frame delimiter
FRAME_DELIMITER = bytes.fromhex("ee00000000000000")

# Sensor types
SENSOR_BATTERY = "battery"
SENSOR_BATTERY_VOLTAGE = "battery_voltage"
SENSOR_BATTERY_CURRENT = "battery_current"
SENSOR_BATTERY_POWER = "battery_power"

# Configuration
CONF_DEVICE_ADDRESS = "device_address"
