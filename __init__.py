"""The Hyena E-Bike integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_DEVICE_ADDRESS, DOMAIN
from .coordinator import HyenaEBikeCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Hyena E-Bike from a config entry."""
    device_address = entry.data[CONF_DEVICE_ADDRESS]

    _LOGGER.debug(
        "Setting up Hyena E-Bike integration for device %s",
        device_address,
    )

    coordinator = HyenaEBikeCoordinator(hass, device_address)

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as ex:
        # The device might be out of range initially.
        _LOGGER.warning(
            "Initial connection to Hyena E-Bike failed, will retry: %s",
            ex,
        )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Hyena E-Bike integration")

    unload_ok = await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )

    if unload_ok:
        coordinator: HyenaEBikeCoordinator = hass.data[DOMAIN][entry.entry_id]
        await coordinator.async_shutdown()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok