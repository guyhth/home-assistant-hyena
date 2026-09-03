"""Config flow for Hyena E-Bike integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.const import CONF_ADDRESS
from homeassistant.data_entry_flow import ConfigFlowResult

from .const import CONF_DEVICE_ADDRESS, DEVICE_NAME_PREFIX, DOMAIN

_LOGGER = logging.getLogger(__name__)


class HyenaEBikeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hyena E-Bike."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered_devices: dict[str, BluetoothServiceInfoBleak] = {}

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle Bluetooth discovery step."""
        _LOGGER.debug(
            "Discovered Hyena E-Bike via Bluetooth: %s",
            discovery_info,
        )

        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        self._discovery_info = discovery_info
        self.context["title_placeholders"] = {
            "name": discovery_info.name,
        }

        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm discovered device."""
        if user_input is not None:
            return self.async_create_entry(
                title=f"Hyena E-Bike ({self._discovery_info.name})",
                data={
                    CONF_DEVICE_ADDRESS: self._discovery_info.address,
                },
            )

        self._set_confirm_only()

        return self.async_show_form(
            step_id="confirm",
            description_placeholders={
                "name": self._discovery_info.name,
                "address": self._discovery_info.address,
            },
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle user-initiated setup."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS]

            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"Hyena E-Bike ({address})",
                data={
                    CONF_DEVICE_ADDRESS: address,
                },
            )

        current_addresses = self._async_current_ids()
        devices = bluetooth.async_discovered_service_info(
            self.hass,
            connectable=True,
        )

        for device in devices:
            if (
                device.name
                and device.name.startswith(DEVICE_NAME_PREFIX)
                and device.address not in current_addresses
            ):
                self._discovered_devices[device.address] = device

        if not self._discovered_devices:
            data_schema = vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): str,
                }
            )
        else:
            data_schema = vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): vol.In(
                        {
                            address: f"{device.name} ({address})"
                            for address, device in self._discovered_devices.items()
                        }
                    ),
                }
            )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
        )