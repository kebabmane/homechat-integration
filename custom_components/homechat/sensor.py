"""Sensor platform for the HomeChat integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HomeChatDataCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HomeChat sensors based on a config entry."""
    coordinator: HomeChatDataCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities: list[SensorEntity] = [
        HomeChatStatusSensor(coordinator, entry),
        HomeChatChannelCountSensor(coordinator, entry),
    ]

    async_add_entities(entities)


class HomeChatBaseSensor(CoordinatorEntity[HomeChatDataCoordinator], SensorEntity):
    """Base class for HomeChat sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HomeChatDataCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "HomeChat Server",
            "manufacturer": "HomeChat",
            "model": "Chat Server",
            "configuration_url": f"http://{self._entry.data.get('host')}:{self._entry.data.get('port')}",
        }


class HomeChatStatusSensor(HomeChatBaseSensor):
    """Sensor for HomeChat server status."""

    _attr_name = "Server Status"
    _attr_icon = "mdi:server"

    def __init__(
        self,
        coordinator: HomeChatDataCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the status sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_status"

    @property
    def native_value(self) -> str:
        """Return the server status."""
        return self.coordinator.server_status

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            "host": self._entry.data.get("host"),
            "port": self._entry.data.get("port"),
            "ssl": self._entry.data.get("ssl", False),
        }


class HomeChatChannelCountSensor(HomeChatBaseSensor):
    """Sensor for HomeChat channel count."""

    _attr_name = "Channel Count"
    _attr_icon = "mdi:forum"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: HomeChatDataCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the channel count sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_channel_count"

    @property
    def native_value(self) -> int:
        """Return the channel count."""
        if self.coordinator.data:
            return self.coordinator.data.get("channel_count", 0)
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        channels = self.coordinator.channels
        return {
            "channels": [
                {"id": c.get("id"), "name": c.get("name"), "type": c.get("type")}
                for c in channels
            ]
        }
