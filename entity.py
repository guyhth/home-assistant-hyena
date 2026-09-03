"""Base entity for Hyena E-Bike integration."""

from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import HyenaEBikeCoordinator


class HyenaEBikeEntity(CoordinatorEntity[HyenaEBikeCoordinator]):
    """Base entity for Hyena E-Bike."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: HyenaEBikeCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_address)},
            name="Hyena E-Bike",
            manufacturer=MANUFACTURER,
            model=MODEL,
            connections={("bluetooth", coordinator.device_address)},
        )