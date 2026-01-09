"""HomeChat notification platform for Home Assistant."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.notify import (
    ATTR_TITLE,
    ATTR_TARGET,
    ATTR_DATA,
    BaseNotificationService,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_get_service(
    hass: HomeAssistant,
    config: ConfigType,
    discovery_info: DiscoveryInfoType | None = None,
) -> HomeChatNotificationService | None:
    """Get the HomeChat notification service."""
    if discovery_info is None:
        return None

    entry_id = discovery_info["entry_id"]
    if entry_id not in hass.data[DOMAIN]:
        return None

    data = hass.data[DOMAIN][entry_id]
    api = data["api"]
    coordinator = data.get("coordinator")
    return HomeChatNotificationService(hass, api, entry_id, coordinator)


class HomeChatNotificationService(BaseNotificationService):
    """Implementation of a notification service for HomeChat."""

    def __init__(
        self,
        hass: HomeAssistant,
        api,
        entry_id: str,
        coordinator=None,
    ) -> None:
        """Initialize the service."""
        self.hass = hass
        self.api = api
        self._entry_id = entry_id
        self._coordinator = coordinator

    @property
    def targets(self) -> dict[str, str] | None:
        """Return a dictionary of targets available for the notification service."""
        # Get dynamic channels from coordinator
        if self._coordinator and self._coordinator.channels:
            targets = {}
            for channel in self._coordinator.channels:
                channel_id = channel.get("id")
                channel_name = channel.get("name", f"channel_{channel_id}")
                channel_type = channel.get("type", "channel")
                # Use name as key, formatted description as value
                targets[channel_name] = f"{channel_name} ({channel_type})"
            return targets if targets else None

        # Fallback to static targets if coordinator unavailable
        return {
            "home": "Home Channel",
            "general": "General Chat",
        }

    async def async_send_message(self, message: str = "", **kwargs: Any) -> None:
        """Send a message to HomeChat."""
        title = kwargs.get(ATTR_TITLE)
        targets = kwargs.get(ATTR_TARGET)
        data = kwargs.get(ATTR_DATA) or {}

        # Extract additional data
        room_id = data.get("room_id")
        user_id = data.get("user_id") 
        priority = data.get("priority", "normal")
        message_type = data.get("type", "notification")

        # Handle targets (room names)
        if targets:
            if isinstance(targets, str):
                targets = [targets]
            
            for target in targets:
                await self._send_to_target(message, title, target, priority, message_type, data)
        else:
            # Send to default room or general chat
            await self._send_to_target(message, title, room_id, priority, message_type, data)

    async def _send_to_target(
        self, 
        message: str, 
        title: str | None, 
        room_id: str | None, 
        priority: str,
        message_type: str,
        data: dict[str, Any]
    ) -> None:
        """Send message to a specific target."""
        try:
            # Format message based on type
            formatted_message = self._format_message(message, title, priority, message_type, data)
            
            # Send message via API
            await self.api.async_send_message(
                message=formatted_message,
                room_id=room_id,
                title=title,
            )
            
            _LOGGER.debug(
                "Sent HomeChat notification - Title: %s, Room: %s, Priority: %s",
                title,
                room_id or "default",
                priority
            )
            
        except Exception as err:
            _LOGGER.error("Failed to send HomeChat notification: %s", err)

    def _format_message(
        self, 
        message: str, 
        title: str | None, 
        priority: str,
        message_type: str,
        data: dict[str, Any]
    ) -> str:
        """Format the message based on type and priority."""
        formatted_message = message
        
        # Add priority indicators
        if priority == "urgent":
            formatted_message = f"🚨 **URGENT** 🚨\n{formatted_message}"
        elif priority == "high":
            formatted_message = f"⚠️ **HIGH PRIORITY**\n{formatted_message}"
        elif priority == "low":
            formatted_message = f"ℹ️ {formatted_message}"
        
        # Add title if provided
        if title and message_type == "notification":
            formatted_message = f"🏠 **{title}**\n{formatted_message}"
        
        # Handle different message types
        if message_type == "alert":
            formatted_message = f"🔔 **ALERT**\n{formatted_message}"
        elif message_type == "automation":
            formatted_message = f"🤖 **Automation**\n{formatted_message}"
        elif message_type == "device":
            device_name = data.get("device_name", "Unknown Device")
            formatted_message = f"📱 **{device_name}**\n{formatted_message}"
        elif message_type == "security":
            formatted_message = f"🔒 **Security**\n{formatted_message}"
        
        # Add timestamp if requested
        if data.get("include_timestamp", True):
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_message = f"{formatted_message}\n\n_Sent at {timestamp}_"
            
        return formatted_message