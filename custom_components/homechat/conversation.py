"""Conversation agent for HomeChat integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HomeChat conversation agent."""
    data = hass.data[DOMAIN][entry.entry_id]
    api = data["api"]
    coordinator = data.get("coordinator")

    async_add_entities([HomeChatConversationAgent(hass, entry, api, coordinator)])


class HomeChatConversationAgent(conversation.ConversationEntity):
    """HomeChat conversation agent entity."""

    _attr_has_entity_name = True
    _attr_name = "Conversation Agent"

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api,
        coordinator,
    ) -> None:
        """Initialize the conversation agent."""
        self.hass = hass
        self._entry = entry
        self._api = api
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_conversation"

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "HomeChat Server",
            "manufacturer": "HomeChat",
            "model": "Chat Server",
        }

    @property
    def supported_languages(self) -> list[str]:
        """Return supported languages."""
        return ["en"]

    async def async_process(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:
        """Process a conversation input."""
        text = user_input.text.lower().strip()

        # Parse common patterns
        if text.startswith("send ") or text.startswith("message "):
            return await self._handle_send_message(user_input, text)
        elif "status" in text and ("homechat" in text or "server" in text):
            return await self._handle_status_check(user_input)
        elif "channel" in text and ("list" in text or "show" in text):
            return await self._handle_list_channels(user_input)
        else:
            # Default: send the message to default channel
            return await self._send_to_homechat(user_input, text)

    async def _handle_send_message(
        self,
        user_input: conversation.ConversationInput,
        text: str,
    ) -> conversation.ConversationResult:
        """Handle send message intent."""
        # Parse "send [message] to [channel]" or "message [channel]: [message]"
        message = text
        channel = None

        if text.startswith("send "):
            message = text[5:]
        elif text.startswith("message "):
            message = text[8:]

        # Check for "to [channel]" pattern
        if " to " in message:
            parts = message.rsplit(" to ", 1)
            if len(parts) == 2:
                message = parts[0].strip()
                channel = parts[1].strip()

        return await self._send_to_homechat(user_input, message, channel)

    async def _send_to_homechat(
        self,
        user_input: conversation.ConversationInput,
        message: str,
        channel: str | None = None,
    ) -> conversation.ConversationResult:
        """Send a message to HomeChat."""
        try:
            # Find channel by name if specified
            room_id = channel
            if channel and self._coordinator:
                channels = self._coordinator.channels or []
                for ch in channels:
                    if ch.get("name", "").lower() == channel.lower():
                        room_id = ch.get("name")
                        break

            await self._api.async_send_message(
                message=f"[Voice] {message}",
                room_id=room_id,
                title="Voice Command",
            )

            response_text = f"Sent message to HomeChat"
            if room_id:
                response_text += f" in {room_id}"

            return conversation.ConversationResult(
                response=intent.IntentResponse(language=user_input.language),
                conversation_id=user_input.conversation_id,
            )

        except Exception as err:
            _LOGGER.error("Failed to send message to HomeChat: %s", err)
            response = intent.IntentResponse(language=user_input.language)
            response.async_set_error(
                intent.IntentResponseErrorCode.UNKNOWN,
                f"Failed to send message: {err}",
            )
            return conversation.ConversationResult(
                response=response,
                conversation_id=user_input.conversation_id,
            )

    async def _handle_status_check(
        self,
        user_input: conversation.ConversationInput,
    ) -> conversation.ConversationResult:
        """Handle status check request."""
        response = intent.IntentResponse(language=user_input.language)

        if self._coordinator:
            status = self._coordinator.server_status
            channel_count = len(self._coordinator.channels) if self._coordinator.channels else 0
            response.async_set_speech(
                f"HomeChat server is {status} with {channel_count} channels available."
            )
        else:
            response.async_set_speech("HomeChat server status is unknown.")

        return conversation.ConversationResult(
            response=response,
            conversation_id=user_input.conversation_id,
        )

    async def _handle_list_channels(
        self,
        user_input: conversation.ConversationInput,
    ) -> conversation.ConversationResult:
        """Handle list channels request."""
        response = intent.IntentResponse(language=user_input.language)

        if self._coordinator and self._coordinator.channels:
            channel_names = [c.get("name", "unnamed") for c in self._coordinator.channels]
            channels_str = ", ".join(channel_names)
            response.async_set_speech(f"Available channels: {channels_str}")
        else:
            response.async_set_speech("No channels available.")

        return conversation.ConversationResult(
            response=response,
            conversation_id=user_input.conversation_id,
        )
