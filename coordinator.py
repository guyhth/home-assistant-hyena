"""BLE coordinator for Hyena E-Bike integration."""

from __future__ import annotations

import asyncio
import logging
import struct
from datetime import datetime, timedelta
from typing import Any

from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.exc import BleakError
from bleak_retry_connector import (
    BleakClientWithServiceCache,
    establish_connection,
)
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    DOMAIN,
    FRAME_DELIMITER,
    MAIN_CHARACTERISTIC_UUID,
    PACKET_ID_BATTERY_SOC,
    PACKET_ID_TEMPERATURE,
    SENSOR_BATTERY,
    SENSOR_TEMPERATURE,
    SENSOR_BATTERY_VOLTAGE,
    SENSOR_BATTERY_CURRENT,
    SENSOR_BATTERY_POWER,
)

_LOGGER = logging.getLogger(__name__)

# Connection timeout and retry settings
CONNECTION_TIMEOUT = 30
DISCONNECT_DELAY = 120  # Disconnect after 2 minutes of no updates


class HyenaEBikeCoordinator(DataUpdateCoordinator):
    """Coordinator to manage BLE connection and data updates for Hyena E-Bike."""

    def __init__(
        self,
        hass: HomeAssistant,
        device_address: str,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=60),  # Fallback polling interval
        )

        self.device_address = device_address
        self._client: BleakClientWithServiceCache | None = None
        self._connection_lock = asyncio.Lock()
        self._disconnect_task: asyncio.Task | None = None
        self._expected_disconnect = False

        # Store telemetry data
        self.data: dict[str, Any] = {
            SENSOR_BATTERY: None,
            SENSOR_TEMPERATURE: None,
            SENSOR_BATTERY_VOLTAGE: None,
            SENSOR_BATTERY_CURRENT: None,
            SENSOR_BATTERY_POWER: None,
        }

    @property
    def is_connected(self) -> bool:
        """Return whether the e-bike is currently connected."""
        return self._client is not None and self._client.is_connected

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via BLE connection.

        This is called by the coordinator on the update_interval.
        Most updates come via notifications, this is just a fallback.
        """
        if not self._client or not self._client.is_connected:
            await self._ensure_connection()

        return self.data

    async def _ensure_connection(self) -> None:
        """Ensure connection to the device."""
        async with self._connection_lock:
            if self._client and self._client.is_connected:
                return

            _LOGGER.debug(
                "Connecting to Hyena E-Bike at %s",
                self.device_address,
            )

            try:
                # Get BLE device from Home Assistant's bluetooth integration
                ble_device = bluetooth.async_ble_device_from_address(
                    self.hass,
                    self.device_address,
                    connectable=True,
                )

                if not ble_device:
                    raise UpdateFailed(
                        "Could not find Hyena E-Bike device "
                        f"with address {self.device_address}"
                    )

                # Establish connection using bleak_retry_connector
                self._client = await establish_connection(
                    BleakClientWithServiceCache,
                    ble_device,
                    self.device_address,
                    self._disconnected_callback,
                    use_services_cache=True,
                    ble_device_callback=lambda: (
                        bluetooth.async_ble_device_from_address(
                            self.hass,
                            self.device_address,
                            connectable=True,
                        )
                    ),
                )

                _LOGGER.info("Connected to Hyena E-Bike")

                # Start debug block
                _LOGGER.warning(
                    "Connected to Hyena E-Bike. Services: %s",
                    [
                        str(service.uuid)
                        for service in self._client.services
                    ],
                )

                characteristic = self._client.services.get_characteristic(
                    MAIN_CHARACTERISTIC_UUID
                )

                if characteristic:
                    _LOGGER.warning(
                        "Found characteristic %s - properties: %s",
                        characteristic.uuid,
                        characteristic.properties,
                    )
                else:
                    _LOGGER.warning(
                        "Could not find characteristic %s",
                        MAIN_CHARACTERISTIC_UUID,
                    )

                # End debug block

                # Subscribe to notifications
                await self._client.start_notify(
                    MAIN_CHARACTERISTIC_UUID,
                    self._notification_handler,
                )

                _LOGGER.debug("Subscribed to telemetry notifications")

                # Notify entities that the connection state has changed
                self.async_update_listeners()

            except (BleakError, asyncio.TimeoutError) as ex:
                _LOGGER.warning(
                    "Failed to connect to Hyena E-Bike: %s",
                    ex,
                )
                raise UpdateFailed(
                    f"Connection failed: {ex}"
                ) from ex

    @callback
    def _disconnected_callback(self, client: BleakClient) -> None:
        """Handle disconnection from device."""
        if self._expected_disconnect:
            _LOGGER.debug(
                "Expected disconnection from Hyena E-Bike"
            )
            return

        _LOGGER.warning(
            "Unexpected disconnection from Hyena E-Bike"
        )

        self._client = None

        # Notify entities that the connection state has changed
        self.async_update_listeners()

        # Schedule reconnection attempt
        self.hass.async_create_task(
            self._async_update_data()
        )

    def _notification_handler(
        self,
        characteristic: BleakGATTCharacteristic,
        data: bytes,
    ) -> None:
        """Handle incoming BLE notifications."""

        # Debug block
        _LOGGER.debug(
            "Hyena notification: %s",
            bytes(data).hex(" "),
        )
        # Debug end

        # Ignore frame delimiters
        if data == FRAME_DELIMITER:
            return

        # Parse the packet
        packet_info = self._parse_packet(data)

        if not packet_info:
            return

        # Update data based on packet type
        packet_id = packet_info["packet_id"]
        parsed_value = packet_info.get("parsed_value")

        updated = False

        if packet_id in (PACKET_ID_BATTERY_SOC, 0x0402):
            # Battery SOC percentage (0-100)
            if parsed_value is None:
                return

            self.data[SENSOR_BATTERY] = parsed_value
            updated = True

            _LOGGER.debug(
                "Battery SOC: %s%%",
                parsed_value,
            )

        elif packet_id == 0x0401:
            voltage = packet_info.get("voltage")
            current = packet_info.get("current")
            power = packet_info.get("power")

            if (
                voltage is None
                or current is None
                or power is None
            ):
                return

            self.data[SENSOR_BATTERY_VOLTAGE] = voltage
            self.data[SENSOR_BATTERY_CURRENT] = current
            self.data[SENSOR_BATTERY_POWER] = power
            updated = True

            _LOGGER.debug(
                "Battery telemetry: %.3f V, %.3f A, %.1f W",
                voltage,
                current,
                power,
            )

        elif packet_id == PACKET_ID_TEMPERATURE:
            # Temperature in °C (divide raw value by 10)
            if parsed_value is None:
                return

            temperature_celsius = parsed_value / 10.0
            self.data[SENSOR_TEMPERATURE] = temperature_celsius
            updated = True

            _LOGGER.debug(
                "Temperature: %.1f°C",
                temperature_celsius,
            )

        # Notify listeners if data was updated
        if updated:
            self.async_set_updated_data(self.data)

            # Reset disconnect timer on activity
            self._reset_disconnect_timer()

    def _parse_packet(
        self,
        data: bytes,
    ) -> dict[str, Any] | None:
        """Parse incoming telemetry packet according to protocol.

        Adapted from the original Python monitoring script.
        """
        if len(data) < 2:
            return None

        # DITK protocol frames begin with 00 00, followed by:
        #   bytes 2-3: 16-bit packet ID (big-endian)
        #   byte 4: payload length
        #   bytes 5+: payload
        #
        # Battery SOC is packet 0x0402, with SOC (%) in payload byte 0.
        #
        # Battery voltage/current is packet 0x0401:
        #   payload bytes 0-1: voltage in mV, little-endian
        #   payload bytes 2-3: currently unknown
        #   payload bytes 4-7: current in mA, signed little-endian

        if data[:2] == b"\x00\x00" and len(data) >= 5:
            ditk_packet_id = int.from_bytes(
                data[2:4],
                byteorder="big",
            )

            payload_length = data[4]

            if len(data) >= 5 + payload_length:
                ditk_payload = data[5 : 5 + payload_length]

                if (
                    ditk_packet_id == 0x0402
                    and len(ditk_payload) >= 1
                ):
                    soc = ditk_payload[0]

                    if 0 <= soc <= 100:
                        _LOGGER.debug(
                            "DITK battery SOC: %d%%",
                            soc,
                        )

                        return {
                            "packet_id": ditk_packet_id,
                            "raw_data": data.hex(),
                            "parsed_value": soc,
                        }

                if (
                    ditk_packet_id == 0x0401
                    and len(ditk_payload) >= 8
                ):
                    voltage_mv = int.from_bytes(
                        ditk_payload[0:2],
                        byteorder="little",
                        signed=False,
                    )

                    current_ma = int.from_bytes(
                        ditk_payload[4:8],
                        byteorder="little",
                        signed=True,
                    )

                    voltage = voltage_mv / 1000.0
                    current = current_ma / 1000.0
                    power = voltage * current

                    _LOGGER.debug(
                        "DITK battery: %.3f V, %.3f A, %.1f W",
                        voltage,
                        current,
                        power,
                    )

                    return {
                        "packet_id": ditk_packet_id,
                        "raw_data": data.hex(),
                        "parsed_value": None,
                        "voltage": voltage,
                        "current": current,
                        "power": power,
                    }

        packet_id = data[0]
        packet_data = data[1:]

        packet_info = {
            "packet_id": packet_id,
            "raw_data": data.hex(),
            "parsed_value": None,
        }

        try:
            # Battery SOC
            if (
                packet_id == PACKET_ID_BATTERY_SOC
                and len(packet_data) >= 1
            ):
                packet_info["parsed_value"] = packet_data[0]

            # Temperature
            elif (
                packet_id == PACKET_ID_TEMPERATURE
                and len(packet_data) >= 2
            ):
                temp_raw = struct.unpack(
                    ">H",
                    packet_data[:2],
                )[0]

                packet_info["parsed_value"] = temp_raw

            # Other packet types we don't care about yet
            else:
                return None

        except struct.error as ex:
            _LOGGER.debug(
                "Failed to parse packet: %s",
                ex,
            )
            return None

        return packet_info

    def _reset_disconnect_timer(self) -> None:
        """Reset the disconnect timer."""
        if self._disconnect_task:
            self._disconnect_task.cancel()
            self._disconnect_task = None

        # Schedule disconnect after period of inactivity
        # This helps save BLE connection slots on the proxy
        self._disconnect_task = self.hass.async_create_task(
            self._disconnect_after_delay()
        )

    async def _disconnect_after_delay(self) -> None:
        """Disconnect from device after delay to save connection slots."""
        try:
            await asyncio.sleep(DISCONNECT_DELAY)
            await self._async_disconnect()

        except asyncio.CancelledError:
            pass

    async def _async_disconnect(self) -> None:
        """Disconnect from the device."""
        async with self._connection_lock:
            if not self._client or not self._client.is_connected:
                return

            _LOGGER.debug(
                "Disconnecting from Hyena E-Bike"
            )

            self._expected_disconnect = True

            try:
                await self._client.stop_notify(
                    MAIN_CHARACTERISTIC_UUID
                )

                await self._client.disconnect()

            except BleakError as ex:
                _LOGGER.debug(
                    "Error during disconnect: %s",
                    ex,
                )

            finally:
                self._client = None
                self._expected_disconnect = False

                # Notify entities that the connection state has changed
                self.async_update_listeners()

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator and disconnect."""
        if self._disconnect_task:
            self._disconnect_task.cancel()
            self._disconnect_task = None

        await self._async_disconnect()