"""Sensor platform for Hyena E-Bike integration."""
from __future__ import annotations

import logging
from typing import Any

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
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_DEVICE_ADDRESS,
    DOMAIN,
    MANUFACTURER,
    MODEL,
    SENSOR_BATTERY,
    SENSOR_TEMPERATURE,
    SENSOR_BATTERY_VOLTAGE,
    SENSOR_BATTERY_CURRENT,
    SENSOR_BATTERY_POWER,
)
from .coordinator import HyenaEBikeCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hyena E-Bike sensors from a config entry."""
    coordinator: HyenaEBikeCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Create sensor entities
    entities = [
        HyenaBatterySensor(coordinator, config_entry),
        HyenaBatteryVoltageSensor(coordinator, config_entry),
        HyenaBatteryCurrentSensor(coordinator, config_entry),
        HyenaBatteryPowerSensor(coordinator, config_entry),
        HyenaTemperatureSensor(coordinator, config_entry),
    ]

    async_add_entities(entities)


class HyenaEBikeSensorBase(CoordinatorEntity[HyenaEBikeCoordinator], SensorEntity):
    """Base class for Hyena E-Bike sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HyenaEBikeCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_address)},
            name="Hyena E-Bike",
            manufacturer=MANUFACTURER,
            model=MODEL,
            connections={("bluetooth", coordinator.device_address)},
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self.native_value is not None


class HyenaBatterySensor(HyenaEBikeSensorBase):
    """Battery SOC sensor for Hyena E-Bike."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_name = "Battery"

    def __init__(
        self,
        coordinator: HyenaEBikeCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the battery sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{coordinator.device_address}_{SENSOR_BATTERY}"

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


class HyenaTemperatureSensor(HyenaEBikeSensorBase):
    """Battery temperature sensor for Hyena E-Bike."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_name = "Battery Temperature"

    def __init__(
        self,
        coordinator: HyenaEBikeCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the temperature sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{coordinator.device_address}_{SENSOR_TEMPERATURE}"

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        return self.coordinator.data.get(SENSOR_TEMPERATURE)


class HyenaBatteryVoltageSensor(HyenaEBikeSensorBase):
    """Battery voltage sensor for Hyena E-Bike."""

    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_name = "Battery Voltage"

    def __init__(
        self,
        coordinator: HyenaEBikeCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the battery voltage sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = (
            f"{coordinator.device_address}_{SENSOR_BATTERY_VOLTAGE}"
        )

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        return self.coordinator.data.get(SENSOR_BATTERY_VOLTAGE)


class HyenaBatteryCurrentSensor(HyenaEBikeSensorBase):
    """Battery current sensor for Hyena E-Bike."""

    _attr_device_class = SensorDeviceClass.CURRENT
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_name = "Battery Current"

    def __init__(
        self,
        coordinator: HyenaEBikeCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the battery current sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = (
            f"{coordinator.device_address}_{SENSOR_BATTERY_CURRENT}"
        )

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        return self.coordinator.data.get(SENSOR_BATTERY_CURRENT)


class HyenaBatteryPowerSensor(HyenaEBikeSensorBase):
    """Battery power sensor for Hyena E-Bike."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_name = "Battery Power"

    def __init__(
        self,
        coordinator: HyenaEBikeCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the battery power sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = (
            f"{coordinator.device_address}_{SENSOR_BATTERY_POWER}"
        )

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        return self.coordinator.data.get(SENSOR_BATTERY_POWER)
