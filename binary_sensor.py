"""Binary sensor platform for Hyena E-Bike integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HyenaEBikeConfigEntry
from .coordinator import HyenaEBikeCoordinator
from .entity import HyenaEBikeEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: HyenaEBikeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hyena E-Bike binary sensors."""

    coordinator = config_entry.runtime_data

    async_add_entities([HyenaConnectionSensor(coordinator)])


class HyenaConnectionSensor(HyenaEBikeEntity, BinarySensorEntity):
    """Binary sensor showing whether the e-bike is connected."""

    _attr_name = "Connected"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: HyenaEBikeCoordinator) -> None:
        """Initialize the connection sensor."""
        super().__init__(coordinator)

        self._attr_unique_id = f"{coordinator.device_address}_connection"

    @property
    def available(self) -> bool:
        """Return whether the connection state is known."""
        return True

    @property
    def is_on(self) -> bool:
        """Return True if the bike is currently connected."""
        return self.coordinator.is_connected