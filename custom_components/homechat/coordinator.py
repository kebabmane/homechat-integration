"""DataUpdateCoordinator for the HomeChat integration."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import TYPE_CHECKING, Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryAuthFailed

from .const import DOMAIN

if TYPE_CHECKING:
    from . import HomeChatAPI

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(minutes=5)


class HomeChatDataCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for HomeChat data updates."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        api: "HomeChatAPI",
        entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.api = api
        self.config_entry = entry
        self.server_status: str = "unknown"
        self.channels: list[dict[str, Any]] = []

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from HomeChat API."""
        try:
            # Test connection
            if not await self.api.async_test_connection():
                self.server_status = "offline"
                raise UpdateFailed("Cannot connect to HomeChat server")

            self.server_status = "online"

            # Fetch channels
            try:
                channels_response = await self.api.async_get_channels()
                self.channels = channels_response.get("channels", [])
            except aiohttp.ClientResponseError as err:
                if err.status == 401:
                    self.server_status = "auth_failed"
                    raise ConfigEntryAuthFailed("Authentication failed") from err
                raise

            return {
                "status": self.server_status,
                "channel_count": len(self.channels),
                "channels": self.channels,
            }

        except aiohttp.ClientResponseError as err:
            if err.status == 401:
                self.server_status = "auth_failed"
                raise ConfigEntryAuthFailed("Authentication failed") from err
            self.server_status = "error"
            raise UpdateFailed(f"HTTP error: {err}") from err

        except aiohttp.ClientError as err:
            self.server_status = "error"
            raise UpdateFailed(f"Connection error: {err}") from err

        except Exception as err:
            self.server_status = "error"
            raise UpdateFailed(f"Error fetching data: {err}") from err

    def get_channel_name(self, channel_id: int) -> str | None:
        """Get channel name by ID."""
        for channel in self.channels:
            if channel.get("id") == channel_id:
                return channel.get("name")
        return None
