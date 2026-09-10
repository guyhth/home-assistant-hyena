"""BLE coordinator for Hyena E-Bike integration."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
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
    BIKE_CONTROL_LIGHT_OFF,
    BIKE_CONTROL_LIGHT_OFFSET,
    BIKE_CONTROL_LIGHT_ON,
    BIKE_CONTROL_PAYLOAD_LENGTH,
    BIKE_CONTROL_SEQUENCE_OFFSET,
    DOMAIN,
    MAIN_CHARACTERISTIC_UUID,
    PACKET_BATTERY_CHARGING,
    PACKET_BATTERY_SOC,
    PACKET_BATTERY_SOH,
    PACKET_BATTERY_TELEMETRY,
    PACKET_ODOMETER,
    PACKET_BIKE_CONTROL,
    WRITE_CHARACTERISTIC_UUID,
    SENSOR_BATTERY,
    SENSOR_BATTERY_VOLTAGE,
    SENSOR_BATTERY_CURRENT,
    SENSOR_BATTERY_POWER,
    SENSOR_ODOMETER,
    SENSOR_BATTERY_SOH,
    SENSOR_BATTERY_CHARGING,
)

_LOGGER = logging.getLogger(__name__)

# Disconnect after 2 minutes without telemetry.
DISCONNECT_DELAY = 120


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

        # Latest complete BikeControl00 (0x0300) payload.
        # This is the 8-byte payload only, not the complete HAP frame.
        self._bike_control_00: bytes | None = None

        self._light_command_lock = asyncio.Lock()
        self._light_confirmation_event = asyncio.Event()
        self._pending_light_confirmation: tuple[int, int] | None = None

        # Store telemetry data
        self.data: dict[str, Any] = {
            SENSOR_BATTERY: None,
            SENSOR_BATTERY_SOH: None,
            SENSOR_BATTERY_CHARGING: None,
            SENSOR_BATTERY_VOLTAGE: None,
            SENSOR_BATTERY_CURRENT: None,
            SENSOR_BATTERY_POWER: None,
            SENSOR_ODOMETER: None,
        }

    @property
    def is_connected(self) -> bool:
        """Return whether the e-bike is currently connected."""
        return self._client is not None and self._client.is_connected

    @property
    def bike_control_00(self) -> bytes | None:
        """Return the latest BikeControl00 payload."""
        return self._bike_control_00

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

                _LOGGER.debug(
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
                    _LOGGER.debug(
                        "Found characteristic %s - properties: %s",
                        characteristic.uuid,
                        characteristic.properties,
                    )
                else:
                    _LOGGER.debug(
                        "Could not find characteristic %s",
                        MAIN_CHARACTERISTIC_UUID,
                    )

                # A new connection requires a fresh BikeControl00 packet.
                self._bike_control_00 = None

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
        self._bike_control_00 = None
        self._pending_light_confirmation = None
        self._light_confirmation_event.set()

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

        _LOGGER.debug(
            "Hyena notification: %s",
            bytes(data).hex(" "),
        )

        packet_info = self._parse_packet(data)

        if not packet_info:
            return

        packet_id = packet_info["packet_id"]
        parsed_value = packet_info.get("parsed_value")
        updated = False

        if packet_id == PACKET_BIKE_CONTROL:
            payload = packet_info.get("payload")
            if payload is None or len(payload) < BIKE_CONTROL_PAYLOAD_LENGTH:
                return

            self._bike_control_00 = bytes(payload[:BIKE_CONTROL_PAYLOAD_LENGTH])
            updated = True

            _LOGGER.debug(
                "BikeControl00: %s",
                self._bike_control_00.hex(" "),
            )

            # Confirm a pending light command when the bike reports
            # both the requested state and the sequence number we sent.
            if self._pending_light_confirmation is not None:
                expected_state, expected_sequence = (
                    self._pending_light_confirmation
                )

                if (
                    self._bike_control_00[BIKE_CONTROL_LIGHT_OFFSET]
                    == expected_state
                    and self._bike_control_00[BIKE_CONTROL_SEQUENCE_OFFSET]
                    == expected_sequence
                ):
                    _LOGGER.debug(
                        "Light command confirmed: state=%s sequence=%02x",
                        "ON" if expected_state == BIKE_CONTROL_LIGHT_ON else "OFF",
                        expected_sequence,
                    )
                    self._light_confirmation_event.set()

        elif packet_id == PACKET_BATTERY_SOC:
            if parsed_value is None:
                return

            self.data[SENSOR_BATTERY] = parsed_value
            updated = True
            _LOGGER.debug("Battery SOC: %s%%", parsed_value)

        elif packet_id == PACKET_BATTERY_SOH:
            if parsed_value is None:
                return

            self.data[SENSOR_BATTERY_SOH] = parsed_value
            updated = True
            _LOGGER.debug("Battery SOH: %s%%", parsed_value)

        elif packet_id == PACKET_BATTERY_CHARGING:
            if parsed_value is None:
                return

            self.data[SENSOR_BATTERY_CHARGING] = parsed_value
            updated = True
            _LOGGER.debug("Battery charging: %s", parsed_value)

        elif packet_id == PACKET_BATTERY_TELEMETRY:
            voltage = packet_info.get("voltage")
            current = packet_info.get("current")
            power = packet_info.get("power")

            if voltage is None or current is None or power is None:
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

        elif packet_id == PACKET_ODOMETER:
            if parsed_value is None:
                return

            self.data[SENSOR_ODOMETER] = parsed_value
            updated = True
            _LOGGER.debug("Odometer: %.3f km", parsed_value)

        if updated:
            self.async_set_updated_data(self.data)
            self._reset_disconnect_timer()

    def _parse_packet(
        self,
        data: bytes,
    ) -> dict[str, Any] | None:
        """Parse incoming DITK telemetry packet."""
        if len(data) < 2:
            return None

        # DITK protocol frames begin with 00 00, followed by:
        #   bytes 2-3: 16-bit packet ID (big-endian)
        #   byte 4: payload length
        #   bytes 5+: payload
        #
        # Battery SOC is packet 0x0402, with SOC (%) in payload bytes 0-3.
        # Battery SOH is packet 0x0403, with SOH (%) in payload bytes 0-1.
        # Battery charging state is packet 0x0400, with the charging flag
        # in bit 7 of payload byte 2.
        # Battery voltage/current is packet 0x0401:
        #   payload bytes 0-1: voltage in mV, little-endian
        #   payload bytes 2-3: currently unknown
        #   payload bytes 4-7: current in mA, signed little-endian

        if data[:2] != b"\x00\x00" or len(data) < 5:
            return None

        ditk_packet_id = int.from_bytes(data[2:4], byteorder="big")
        payload_length = data[4]

        if len(data) < 5 + payload_length:
            return None

        ditk_payload = data[5 : 5 + payload_length]

        if (
            ditk_packet_id == PACKET_BIKE_CONTROL
            and len(ditk_payload) >= BIKE_CONTROL_PAYLOAD_LENGTH
        ):
            return {
                "packet_id": ditk_packet_id,
                "raw_data": data.hex(),
                "payload": bytes(ditk_payload[:BIKE_CONTROL_PAYLOAD_LENGTH]),
            }

        if ditk_packet_id == PACKET_BATTERY_SOC and len(ditk_payload) >= 4:
            soc = int.from_bytes(
                ditk_payload[0:4],
                byteorder="little",
                signed=False,
            )

            if 0 <= soc <= 100:
                _LOGGER.debug("DITK battery SOC: %d%%", soc)
                return {
                    "packet_id": ditk_packet_id,
                    "raw_data": data.hex(),
                    "parsed_value": soc,
                }

        if ditk_packet_id == PACKET_BATTERY_SOH and len(ditk_payload) >= 2:
            soh = int.from_bytes(
                ditk_payload[0:2],
                byteorder="little",
                signed=False,
            )

            if 0 <= soh <= 100:
                return {
                    "packet_id": ditk_packet_id,
                    "raw_data": data.hex(),
                    "parsed_value": soh,
                }

        if ditk_packet_id == PACKET_BATTERY_CHARGING and len(ditk_payload) >= 3:
            charging = bool(ditk_payload[2] & 0x80)
            return {
                "packet_id": ditk_packet_id,
                "raw_data": data.hex(),
                "parsed_value": charging,
            }

        if ditk_packet_id == PACKET_BATTERY_TELEMETRY and len(ditk_payload) >= 8:
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

        if ditk_packet_id == PACKET_ODOMETER and len(ditk_payload) >= 8:
            odometer_m = int.from_bytes(
                ditk_payload[4:8],
                byteorder="little",
                signed=False,
            )
            odometer_km = odometer_m / 1000.0

            _LOGGER.debug("DITK odometer: %.3f km", odometer_km)
            return {
                "packet_id": ditk_packet_id,
                "raw_data": data.hex(),
                "parsed_value": odometer_km,
            }

        return None

    async def async_set_light(self, light_on: bool) -> None:
        """Set the e-bike light state and wait for confirmation."""
        async with self._light_command_lock:
            await self._ensure_connection()

            if not self._client or not self._client.is_connected:
                raise UpdateFailed("E-bike is not connected")

            if self._bike_control_00 is None:
                raise UpdateFailed("No BikeControl00 packet available")

            data = bytearray(self._bike_control_00)
            expected_state = BIKE_CONTROL_LIGHT_ON if light_on else BIKE_CONTROL_LIGHT_OFF
            data[BIKE_CONTROL_LIGHT_OFFSET] = expected_state
            data[BIKE_CONTROL_SEQUENCE_OFFSET] = (
                data[BIKE_CONTROL_SEQUENCE_OFFSET] + 1
            ) & 0x0F
            expected_sequence = data[BIKE_CONTROL_SEQUENCE_OFFSET]

            # HAP/CAN frame: 4-byte EID, 1-byte payload length, 8-byte payload.
            packet = (
                b"\x00\x00\x03\x00"
                + bytes([BIKE_CONTROL_PAYLOAD_LENGTH])
                + bytes(data)
            )

            _LOGGER.debug(
                "Sending light command (%s): %s",
                "ON" if light_on else "OFF",
                packet.hex(" "),
            )

            self._light_confirmation_event.clear()
            self._pending_light_confirmation = (
                expected_state,
                expected_sequence,
            )

            try:
                await self._client.write_gatt_char(
                    WRITE_CHARACTERISTIC_UUID,
                    packet,
                    response=True,
                )

                try:
                    await asyncio.wait_for(
                        self._light_confirmation_event.wait(),
                        timeout=5.0,
                    )
                except asyncio.TimeoutError as ex:
                    _LOGGER.warning(
                        "Timed out waiting for light command confirmation"
                    )
                    raise UpdateFailed(
                        "Timed out waiting for light command confirmation"
                    ) from ex

            except BleakError as ex:
                _LOGGER.warning(
                    "Failed to send light command: %s",
                    ex,
                )
                raise UpdateFailed(
                    f"Failed to send light command: {ex}"
                ) from ex

            finally:
                self._pending_light_confirmation = None
                self._light_confirmation_event.clear()

    def _reset_disconnect_timer(self) -> None:
        """Reset the disconnect timer."""
        if self._disconnect_task:
            self._disconnect_task.cancel()
            self._disconnect_task = None

        self._disconnect_task = self.hass.async_create_task(
            self._disconnect_after_delay()
        )

    async def _disconnect_after_delay(self) -> None:
        """Disconnect from device after delay to save BLE connection slots."""
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

            _LOGGER.debug("Disconnecting from Hyena E-Bike")
            self._expected_disconnect = True

            try:
                await self._client.stop_notify(MAIN_CHARACTERISTIC_UUID)
                await self._client.disconnect()
            except BleakError as ex:
                _LOGGER.debug("Error during disconnect: %s", ex)
            finally:
                self._client = None
                self._expected_disconnect = False
                self._bike_control_00 = None
                self._pending_light_confirmation = None
                self._light_confirmation_event.set()
                self.async_update_listeners()

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator and disconnect."""
        if self._disconnect_task:
            self._disconnect_task.cancel()
            self._disconnect_task = None

        await self._async_disconnect()
