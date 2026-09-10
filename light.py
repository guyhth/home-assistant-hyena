"""Light platform for Hyena E-Bike."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import (
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import BIKE_CONTROL_LIGHT_ON
from .coordinator import HyenaEBikeCoordinator
from .entity import HyenaEBikeEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Hyena E-Bike light."""
    coordinator: HyenaEBikeCoordinator = entry.runtime_data
    async_add_entities([HyenaEBikeLight(coordinator)])


class HyenaEBikeLight(HyenaEBikeEntity, LightEntity):
    """Representation of the e-bike light."""

    _attr_has_entity_name = True
    _attr_name = "Lights"
    _attr_supported_color_modes = {ColorMode.ONOFF}

    def __init__(self, coordinator: HyenaEBikeCoordinator) -> None:
        """Initialize the light."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device_address}_light"

    @property
    def color_mode(self) -> ColorMode:
        """Return the light color mode."""
        return ColorMode.ONOFF

    @property
    def icon(self) -> str:
        return "mdi:car-light-dimmed"

    @property
    def is_on(self) -> bool | None:
        """Return whether the bike light is on."""
        payload = self.coordinator.bike_control_00

        if payload is None or len(payload) < 3:
            return None

        return payload[2] == BIKE_CONTROL_LIGHT_ON

    @property
    def available(self) -> bool:
        """Return whether the light is available."""
        return (
            self.coordinator.is_connected
            and self.coordinator.bike_control_00 is not None
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the bike light on."""
        await self.coordinator.async_set_light(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the bike light off."""
        await self.coordinator.async_set_light(False)
