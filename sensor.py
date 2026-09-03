"""Sensor platform for Hyena E-Bike integration."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    SENSOR_BATTERY,
    SENSOR_BATTERY_CURRENT,
    SENSOR_BATTERY_POWER,
    SENSOR_BATTERY_VOLTAGE,
)
from .coordinator import HyenaEBikeCoordinator
from .entity import HyenaEBikeEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hyena E-Bike sensors from a config entry."""

    coordinator: HyenaEBikeCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    async_add_entities(
        [
            HyenaBatterySensor(coordinator),
            HyenaBatteryVoltageSensor(coordinator),
            HyenaBatteryCurrentSensor(coordinator),
            HyenaBatteryPowerSensor(coordinator),
        ]
    )


class HyenaEBikeSensor(HyenaEBikeEntity, SensorEntity):
    """Base class for Hyena E-Bike sensors."""

    @property
    def available(self) -> bool:
        """Return if the entity is available."""
        return self.coordinator.last_update_success and self.native_value is not None


class HyenaBatterySensor(HyenaEBikeSensor):
    """Battery SOC sensor for Hyena E-Bike."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_name = "Battery"

    def __init__(self, coordinator: HyenaEBikeCoordinator) -> None:
        """Initialize the battery sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device_address}_{SENSOR_BATTERY}"

    @property
    def available(self) -> bool:
        """Return if a battery value has been received."""
        return self.coordinator.data.get(SENSOR_BATTERY) is not None

    @property
    def native_value(self) -> int | None:
        """Return the state of the sensor."""
        return self.coordinator.data.get(SENSOR_BATTERY)

    @property
    def icon(self) -> str:
        """Return the icon based on battery level."""
        battery_level = self.native_value

        if battery_level is None:
            return "mdi:battery-unknown"

        if battery_level >= 90:
            return "mdi:battery"
        if battery_level >= 80:
            return "mdi:battery-90"
        if battery_level >= 70:
            return "mdi:battery-80"
        if battery_level >= 60:
            return "mdi:battery-70"
        if battery_level >= 50:
            return "mdi:battery-60"
        if battery_level >= 40:
            return "mdi:battery-50"
        if battery_level >= 30:
            return "mdi:battery-40"
        if battery_level >= 20:
            return "mdi:battery-30"
        if battery_level >= 10:
            return "mdi:battery-20"

        return "mdi:battery-10"


class HyenaBatteryVoltageSensor(HyenaEBikeSensor):
    """Battery voltage sensor for Hyena E-Bike."""

    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_name = "Battery Voltage"

    def __init__(self, coordinator: HyenaEBikeCoordinator) -> None:
        """Initialize the battery voltage sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = (
            f"{coordinator.device_address}_{SENSOR_BATTERY_VOLTAGE}"
        )

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        return self.coordinator.data.get(SENSOR_BATTERY_VOLTAGE)


class HyenaBatteryCurrentSensor(HyenaEBikeSensor):
    """Battery current sensor for Hyena E-Bike."""

    _attr_device_class = SensorDeviceClass.CURRENT
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_name = "Battery Current"

    def __init__(self, coordinator: HyenaEBikeCoordinator) -> None:
        """Initialize the battery current sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = (
            f"{coordinator.device_address}_{SENSOR_BATTERY_CURRENT}"
        )

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        return self.coordinator.data.get(SENSOR_BATTERY_CURRENT)


class HyenaBatteryPowerSensor(HyenaEBikeSensor):
    """Battery power sensor for Hyena E-Bike."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_name = "Battery Power"

    def __init__(self, coordinator: HyenaEBikeCoordinator) -> None:
        """Initialize the battery power sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = (
            f"{coordinator.device_address}_{SENSOR_BATTERY_POWER}"
        )

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        return self.coordinator.data.get(SENSOR_BATTERY_POWER)