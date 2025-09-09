"""The HomeChat integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.components.webhook import async_register, async_unregister

from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_HOST,
    CONF_PORT,
    CONF_SSL,
    CONF_API_TOKEN,
    CONF_WEBHOOK_ID,
    CONF_BOT_USERNAME,
    SERVICE_SEND_MESSAGE,
    SERVICE_SEND_NOTIFICATION,
    SERVICE_CREATE_BOT,
    EVENT_HOMECHAT_MESSAGE_RECEIVED,
    EVENT_HOMECHAT_BOT_MESSAGE,
    API_SEND_MESSAGE,
    API_CREATE_BOT,
)

_LOGGER = logging.getLogger(__name__)

# Service schemas
SEND_MESSAGE_SCHEMA = vol.Schema(
    {
        vol.Required("message"): cv.string,
        vol.Optional("room_id"): cv.string,
        vol.Optional("user_id"): cv.string,
        vol.Optional("title"): cv.string,
    }
)

SEND_NOTIFICATION_SCHEMA = vol.Schema(
    {
        vol.Required("message"): cv.string,
        vol.Optional("title"): cv.string,
        vol.Optional("priority", default="normal"): vol.In(["low", "normal", "high", "urgent"]),
        vol.Optional("room_id"): cv.string,
    }
)

CREATE_BOT_SCHEMA = vol.Schema(
    {
        vol.Required("name"): cv.string,
        vol.Optional("description"): cv.string,
        vol.Optional("webhook_id"): cv.string,
    }
)


class HomeChatAPI:
    """API client for HomeChat."""

    def __init__(self, hass: HomeAssistant, host: str, port: int, ssl: bool, api_token: str):
        """Initialize the API client."""
        self.hass = hass
        self.host = host
        self.port = port
        self.ssl = ssl
        self.api_token = api_token
        self._session = async_get_clientsession(hass)
        
        scheme = "https" if ssl else "http"
        self.base_url = f"{scheme}://{host}:{port}"

    async def async_send_message(
        self, message: str, room_id: str | None = None, user_id: str | None = None, title: str | None = None
    ) -> dict[str, Any]:
        """Send a message to HomeChat."""
        url = f"{self.base_url}{API_SEND_MESSAGE}"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
        data = {
            "message": message,
            "sender": "Home Assistant",
        }
        
        if room_id:
            data["room_id"] = room_id
        if user_id:
            data["user_id"] = user_id
        if title:
            data["title"] = title

        try:
            async with self._session.post(url, json=data, headers=headers) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as err:
            _LOGGER.error("Error sending message to HomeChat: %s", err)
            raise

    async def async_create_bot(self, name: str, description: str | None = None, webhook_id: str | None = None) -> dict[str, Any]:
        """Create a bot in HomeChat."""
        url = f"{self.base_url}{API_CREATE_BOT}"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
        data = {
            "name": name,
            "type": "webhook" if webhook_id else "api",
        }
        
        if description:
            data["description"] = description
        if webhook_id:
            data["webhook_id"] = webhook_id

        try:
            async with self._session.post(url, json=data, headers=headers) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as err:
            _LOGGER.error("Error creating bot in HomeChat: %s", err)
            raise

    async def async_test_connection(self) -> bool:
        """Test connection to HomeChat."""
        try:
            url = f"{self.base_url}/api/v1/health"
            headers = {"Authorization": f"Bearer {self.api_token}"}
            
            async with self._session.get(url, headers=headers, timeout=10) as response:
                return response.status == 200
        except Exception as err:
            _LOGGER.error("Error testing connection to HomeChat: %s", err)
            return False


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HomeChat from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    ssl = entry.data.get(CONF_SSL, False)
    api_token = entry.data[CONF_API_TOKEN]
    webhook_id = entry.data.get(CONF_WEBHOOK_ID)
    bot_username = entry.data.get(CONF_BOT_USERNAME)

    # Create API client
    api = HomeChatAPI(hass, host, port, ssl, api_token)
    
    # Test connection
    if not await api.async_test_connection():
        _LOGGER.error("Failed to connect to HomeChat at %s:%s", host, port)
        return False

    # Store API client
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "webhook_id": webhook_id,
        "bot_username": bot_username,
    }

    # Register webhook if configured
    if webhook_id:
        await async_register_webhook(hass, entry.entry_id, webhook_id)

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    await async_register_services(hass, api)

    # Create bot if configured
    if bot_username and webhook_id:
        try:
            await api.async_create_bot(
                name=bot_username,
                description="Home Assistant Bot for two-way communication",
                webhook_id=webhook_id,
            )
            _LOGGER.info("Created HomeChat bot: %s", bot_username)
        except Exception as err:
            _LOGGER.warning("Failed to create HomeChat bot: %s", err)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    webhook_id = hass.data[DOMAIN][entry.entry_id].get("webhook_id")
    
    # Unregister webhook
    if webhook_id:
        async_unregister(hass, DOMAIN, webhook_id)

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        
        # Remove services if no more entries
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_SEND_MESSAGE)
            hass.services.async_remove(DOMAIN, SERVICE_SEND_NOTIFICATION)
            hass.services.async_remove(DOMAIN, SERVICE_CREATE_BOT)

    return unload_ok


async def async_register_webhook(hass: HomeAssistant, entry_id: str, webhook_id: str) -> None:
    """Register webhook for receiving messages from HomeChat."""
    
    @callback
    def handle_webhook(hass: HomeAssistant, webhook_id: str, request) -> dict[str, str]:
        """Handle webhook data from HomeChat."""
        try:
            data = request.json
            _LOGGER.debug("Received HomeChat webhook: %s", data)
            
            # Fire event for automations
            event_data = {
                "webhook_id": webhook_id,
                "message": data.get("message"),
                "sender": data.get("sender"),
                "room_id": data.get("room_id"),
                "timestamp": data.get("timestamp"),
                "message_type": data.get("type", "message"),
            }
            
            if data.get("type") == "bot_message":
                hass.bus.async_fire(EVENT_HOMECHAT_BOT_MESSAGE, event_data)
            else:
                hass.bus.async_fire(EVENT_HOMECHAT_MESSAGE_RECEIVED, event_data)
            
            return {"status": "ok"}
            
        except Exception as err:
            _LOGGER.error("Error processing HomeChat webhook: %s", err)
            return {"status": "error", "message": str(err)}

    async_register(hass, DOMAIN, "HomeChat", webhook_id, handle_webhook)
    _LOGGER.info("Registered HomeChat webhook: %s", webhook_id)


async def async_register_services(hass: HomeAssistant, api: HomeChatAPI) -> None:
    """Register HomeChat services."""

    async def send_message(call: ServiceCall) -> None:
        """Handle send_message service call."""
        message = call.data["message"]
        room_id = call.data.get("room_id")
        user_id = call.data.get("user_id")
        title = call.data.get("title")
        
        try:
            await api.async_send_message(message, room_id, user_id, title)
            _LOGGER.info("Sent message to HomeChat: %s", message)
        except Exception as err:
            _LOGGER.error("Failed to send message to HomeChat: %s", err)

    async def send_notification(call: ServiceCall) -> None:
        """Handle send_notification service call."""
        message = call.data["message"]
        title = call.data.get("title", "Home Assistant Notification")
        priority = call.data.get("priority", "normal")
        room_id = call.data.get("room_id")
        
        # Format as notification
        formatted_message = f"🏠 **{title}**\n{message}"
        if priority in ("high", "urgent"):
            formatted_message = f"⚠️ {formatted_message}"
        
        try:
            await api.async_send_message(formatted_message, room_id=room_id, title=title)
            _LOGGER.info("Sent notification to HomeChat: %s", title)
        except Exception as err:
            _LOGGER.error("Failed to send notification to HomeChat: %s", err)

    async def create_bot(call: ServiceCall) -> None:
        """Handle create_bot service call."""
        name = call.data["name"]
        description = call.data.get("description")
        webhook_id = call.data.get("webhook_id")
        
        try:
            result = await api.async_create_bot(name, description, webhook_id)
            _LOGGER.info("Created HomeChat bot: %s", result)
        except Exception as err:
            _LOGGER.error("Failed to create HomeChat bot: %s", err)

    # Register services only once
    if not hass.services.has_service(DOMAIN, SERVICE_SEND_MESSAGE):
        hass.services.async_register(
            DOMAIN, SERVICE_SEND_MESSAGE, send_message, schema=SEND_MESSAGE_SCHEMA
        )
        hass.services.async_register(
            DOMAIN, SERVICE_SEND_NOTIFICATION, send_notification, schema=SEND_NOTIFICATION_SCHEMA
        )
        hass.services.async_register(
            DOMAIN, SERVICE_CREATE_BOT, create_bot, schema=CREATE_BOT_SCHEMA
        )