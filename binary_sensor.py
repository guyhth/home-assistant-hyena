"""Binary sensor platform for Hyena E-Bike integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import HyenaEBikeCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hyena E-Bike binary sensors from a config entry."""
    coordinator: HyenaEBikeCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    async_add_entities(
        [
            HyenaConnectionSensor(coordinator),
        ]
    )


class HyenaConnectionSensor(
    CoordinatorEntity[HyenaEBikeCoordinator],
    BinarySensorEntity,
):
    """Binary sensor indicating whether the e-bike is connected."""

    _attr_has_entity_name = True
    _attr_name = "Connected"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: HyenaEBikeCoordinator) -> None:
        """Initialize the connection sensor."""
        super().__init__(coordinator)

        self._attr_unique_id = f"{coordinator.device_address}_connected"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_address)},
            name="Hyena E-Bike",
            manufacturer=MANUFACTURER,
            model=MODEL,
            connections={("bluetooth", coordinator.device_address)},
        )

    @property
    def is_on(self) -> bool:
        """Return True when the e-bike is connected."""
        return self.coordinator.is_connected