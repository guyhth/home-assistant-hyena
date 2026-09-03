"""Binary sensor platform for Hyena E-Bike integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import HyenaEBikeCoordinator
from .entity import HyenaEBikeEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hyena E-Bike binary sensors."""

    coordinator: HyenaEBikeCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    async_add_entities([HyenaConnectionSensor(coordinator)])


class HyenaConnectionSensor(HyenaEBikeEntity, BinarySensorEntity):
    """Binary sensor showing whether the e-bike is connected."""

    _attr_name = "Connected"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    @property
    def available(self) -> bool:
        """Return whether the connection state is known."""
        return True

    @property
    def is_on(self) -> bool:
        """Return True if the bike is currently connected."""
        return self.coordinator.is_connected