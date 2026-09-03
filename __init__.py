"""The Hyena E-Bike integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_DEVICE_ADDRESS
from .coordinator import HyenaEBikeCoordinator

_LOGGER = logging.getLogger(__name__)

type HyenaEBikeConfigEntry = ConfigEntry[HyenaEBikeCoordinator]

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]


async def async_setup_entry(
    hass: HomeAssistant, entry: HyenaEBikeConfigEntry
) -> bool:
    """Set up Hyena E-Bike from a config entry."""
    device_address = entry.data[CONF_DEVICE_ADDRESS]

    _LOGGER.debug(
        "Setting up Hyena E-Bike integration for device %s",
        device_address,
    )

    coordinator = HyenaEBikeCoordinator(hass, device_address)

    # Perform initial data fetch.
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as ex:
        # If initial connection fails, still proceed but log warning.
        # The device might be out of range initially.
        _LOGGER.warning(
            "Initial connection to Hyena E-Bike failed, will retry: %s",
            ex,
        )

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: HyenaEBikeConfigEntry
) -> bool:
    """Unload Hyena E-Bike config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        await entry.runtime_data.async_shutdown()

    return unload_ok