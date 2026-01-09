"""
The HomeChat integration."""
from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any

import aiohttp
from aiohttp import ClientTimeout, web
import voluptuous as vol

# API timeout configuration
API_TIMEOUT = ClientTimeout(total=30)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv, discovery
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.components.webhook import async_register, async_unregister

from .coordinator import HomeChatDataCoordinator
from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_HOST,
    CONF_PORT,
    CONF_SSL,
    CONF_API_TOKEN,
    CONF_WEBHOOK_ID,
    CONF_WEBHOOK_SECRET,
    CONF_BOT_USERNAME,
    CONF_BOT_ID,
    SERVICE_SEND_MESSAGE,
    SERVICE_SEND_NOTIFICATION,
    SERVICE_CREATE_BOT,
    SERVICE_LIST_CHANNELS,
    SERVICE_JOIN_CHANNEL,
    SERVICE_LEAVE_CHANNEL,
    SERVICE_SEND_DM,
    SERVICE_SEARCH,
    EVENT_HOMECHAT_MESSAGE_RECEIVED,
    EVENT_HOMECHAT_BOT_MESSAGE,
    API_HEALTH,
    API_SEND_MESSAGE,
    API_CHANNELS,
    API_CHANNEL_JOIN,
    API_CHANNEL_LEAVE,
    API_CHANNEL_MEMBERS,
    API_CHANNEL_MESSAGES,
    API_DM_START,
    API_CREATE_BOT,
    API_BOT_STATUS,
    API_SEARCH,
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

JOIN_CHANNEL_SCHEMA = vol.Schema(
    {
        vol.Required("channel_id"): cv.positive_int,
    }
)

LEAVE_CHANNEL_SCHEMA = vol.Schema(
    {
        vol.Required("channel_id"): cv.positive_int,
    }
)

SEND_DM_SCHEMA = vol.Schema(
    {
        vol.Required("user_id"): cv.positive_int,
        vol.Required("message"): cv.string,
    }
)

SEARCH_SCHEMA = vol.Schema(
    {
        vol.Required("query"): cv.string,
        vol.Optional("type", default="all"): vol.In(["all", "users", "channels", "messages"]),
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
        self,
        message: str,
        room_id: str | None = None,
        user_id: str | None = None,
        title: str | None = None,
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
            async with self._session.post(url, json=data, headers=headers, timeout=API_TIMEOUT) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as err:
            _LOGGER.error("Error sending message to HomeChat: %s", err)
            raise

    async def async_create_bot(
        self, name: str, description: str | None = None, webhook_id: str | None = None
    ) -> dict[str, Any]:
        """Create a bot in HomeChat.

        Returns the bot data including webhook_secret if webhook_id was provided.
        """
        url = f"{self.base_url}{API_CREATE_BOT}"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
        # API expects data wrapped in "bot" object with "bot_type" field
        bot_data: dict[str, Any] = {
            "name": name,
            "bot_type": "webhook" if webhook_id else "api",
        }

        if description:
            bot_data["description"] = description
        if webhook_id:
            bot_data["webhook_id"] = webhook_id

        data = {"bot": bot_data}

        try:
            async with self._session.post(url, json=data, headers=headers, timeout=API_TIMEOUT) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as err:
            _LOGGER.error("Error creating bot in HomeChat: %s", err)
            raise

    async def async_test_connection(self) -> bool:
        """Test connection to HomeChat."""
        try:
            url = f"{self.base_url}{API_HEALTH}"
            headers = {"Authorization": f"Bearer {self.api_token}"}

            async with self._session.get(url, headers=headers, timeout=API_TIMEOUT) as response:
                return response.status == 200
        except Exception as err:
            _LOGGER.error("Error testing connection to HomeChat: %s", err)
            return False

    async def async_get_channels(self) -> dict[str, Any]:
        """Get list of channels from HomeChat."""
        url = f"{self.base_url}{API_CHANNELS}"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

        try:
            async with self._session.get(url, headers=headers, timeout=API_TIMEOUT) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as err:
            _LOGGER.error("Error getting channels from HomeChat: %s", err)
            raise

    async def async_get_channel_members(self, channel_id: int) -> dict[str, Any]:
        """Get members of a channel from HomeChat."""
        url = f"{self.base_url}{API_CHANNEL_MEMBERS.format(channel_id=channel_id)}"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

        try:
            async with self._session.get(url, headers=headers, timeout=API_TIMEOUT) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as err:
            _LOGGER.error("Error getting channel members from HomeChat: %s", err)
            raise

    async def async_join_channel(self, channel_id: int) -> dict[str, Any]:
        """Join a channel in HomeChat."""
        url = f"{self.base_url}{API_CHANNEL_JOIN.format(channel_id=channel_id)}"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

        try:
            async with self._session.post(url, headers=headers, timeout=API_TIMEOUT) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as err:
            _LOGGER.error("Error joining channel in HomeChat: %s", err)
            raise

    async def async_leave_channel(self, channel_id: int) -> dict[str, Any]:
        """Leave a channel in HomeChat."""
        url = f"{self.base_url}{API_CHANNEL_LEAVE.format(channel_id=channel_id)}"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

        try:
            async with self._session.post(url, headers=headers, timeout=API_TIMEOUT) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as err:
            _LOGGER.error("Error leaving channel in HomeChat: %s", err)
            raise

    async def async_send_channel_message(
        self, channel_id: int, message: str, message_type: str = "chat"
    ) -> dict[str, Any]:
        """Send a message to a specific channel in HomeChat."""
        url = f"{self.base_url}{API_CHANNEL_MESSAGES.format(channel_id=channel_id)}"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
        data = {
            "message": message,
            "message_type": message_type,
        }

        try:
            async with self._session.post(url, json=data, headers=headers, timeout=API_TIMEOUT) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as err:
            _LOGGER.error("Error sending channel message to HomeChat: %s", err)
            raise

    async def async_send_dm(self, user_id: int, message: str) -> dict[str, Any]:
        """Send a direct message to a user in HomeChat."""
        url = f"{self.base_url}{API_DM_START}"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
        data = {
            "user_id": user_id,
            "message": message,
        }

        try:
            async with self._session.post(url, json=data, headers=headers, timeout=API_TIMEOUT) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as err:
            _LOGGER.error("Error sending DM in HomeChat: %s", err)
            raise

    async def async_search(
        self, query: str, search_type: str = "all"
    ) -> dict[str, Any]:
        """Search in HomeChat."""
        url = f"{self.base_url}{API_SEARCH}"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
        params = {
            "q": query,
            "type": search_type,
        }

        try:
            async with self._session.get(url, headers=headers, params=params, timeout=API_TIMEOUT) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as err:
            _LOGGER.error("Error searching in HomeChat: %s", err)
            raise

    async def async_get_bot_status(self, bot_id: int) -> dict[str, Any]:
        """Get bot status from HomeChat."""
        url = f"{self.base_url}{API_BOT_STATUS.format(bot_id=bot_id)}"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

        try:
            async with self._session.get(url, headers=headers, timeout=API_TIMEOUT) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as err:
            _LOGGER.error("Error getting bot status from HomeChat: %s", err)
            raise


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HomeChat from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    ssl = entry.data.get(CONF_SSL, False)
    api_token = entry.data[CONF_API_TOKEN]
    webhook_id = entry.data.get(CONF_WEBHOOK_ID)
    webhook_secret = entry.data.get(CONF_WEBHOOK_SECRET)
    bot_username = entry.data.get(CONF_BOT_USERNAME)
    bot_id = entry.data.get(CONF_BOT_ID)

    # Create API client
    api = HomeChatAPI(hass, host, port, ssl, api_token)

    # Test connection
    if not await api.async_test_connection():
        _LOGGER.error("Failed to connect to HomeChat at %s:%s", host, port)
        return False

    # Create coordinator
    coordinator = HomeChatDataCoordinator(hass, api, entry)

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Store API client, coordinator, and data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
        "webhook_id": webhook_id,
        "webhook_secret": webhook_secret,
        "bot_username": bot_username,
        "bot_id": bot_id,
    }

    # Create bot if configured (before registering webhook to get secret)
    if bot_username and webhook_id and not bot_id:
        try:
            result = await api.async_create_bot(
                name=bot_username,
                description="Home Assistant Bot for two-way communication",
                webhook_id=webhook_id,
            )
            _LOGGER.info("Created HomeChat bot: %s", result)

            # Store the webhook_secret and bot_id from the response
            bot_data = result.get("bot", result)
            new_webhook_secret = bot_data.get("webhook_secret")
            new_bot_id = bot_data.get("id")

            if new_webhook_secret or new_bot_id:
                # Update entry data with new values
                new_data = dict(entry.data)
                if new_webhook_secret:
                    new_data[CONF_WEBHOOK_SECRET] = new_webhook_secret
                    webhook_secret = new_webhook_secret
                    hass.data[DOMAIN][entry.entry_id]["webhook_secret"] = new_webhook_secret
                if new_bot_id:
                    new_data[CONF_BOT_ID] = new_bot_id
                    hass.data[DOMAIN][entry.entry_id]["bot_id"] = new_bot_id

                hass.config_entries.async_update_entry(entry, data=new_data)

        except Exception as err:
            _LOGGER.warning("Failed to create HomeChat bot: %s", err)

    # Register webhook if configured (with secret for verification)
    if webhook_id:
        await async_register_webhook(hass, entry.entry_id, webhook_id, webhook_secret)

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Load notify platform (legacy)
    hass.async_create_task(
        discovery.async_load_platform(
            hass, Platform.NOTIFY, DOMAIN, {"entry_id": entry.entry_id}, entry
        )
    )

    # Register services
    await async_register_services(hass, api)

    # Register update listener
    entry.async_on_unload(entry.add_update_listener(update_listener))

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
            hass.services.async_remove(DOMAIN, SERVICE_LIST_CHANNELS)
            hass.services.async_remove(DOMAIN, SERVICE_JOIN_CHANNEL)
            hass.services.async_remove(DOMAIN, SERVICE_LEAVE_CHANNEL)
            hass.services.async_remove(DOMAIN, SERVICE_SEND_DM)
            hass.services.async_remove(DOMAIN, SERVICE_SEARCH)

    return unload_ok


def _verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify HMAC-SHA256 signature from HomeChat webhook."""
    if not signature or not secret:
        return False
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    expected_header = f"sha256={expected}"
    return hmac.compare_digest(expected_header, signature)


async def async_register_webhook(
    hass: HomeAssistant, entry_id: str, webhook_id: str, webhook_secret: str | None = None
) -> None:
    """Register webhook for receiving messages from HomeChat."""

    async def handle_webhook(
        hass: HomeAssistant, webhook_id: str, request: web.Request
    ) -> web.Response:
        """Handle webhook data from HomeChat."""
        try:
            # Read raw body for signature verification
            body = await request.read()

            # Verify signature if we have a secret
            if webhook_secret:
                signature = request.headers.get("X-HomeChat-Signature", "")
                if not _verify_webhook_signature(body, signature, webhook_secret):
                    _LOGGER.warning("Invalid webhook signature received")
                    return web.json_response(
                        {"status": "error", "message": "Invalid signature"},
                        status=401
                    )

            # Parse JSON body
            import json
            data = json.loads(body)
            _LOGGER.debug("Received HomeChat webhook: %s", data)

            # Fire event for automations
            event_data = {
                "webhook_id": webhook_id,
                "message": data.get("message"),
                "sender": data.get("sender"),
                "room_id": data.get("room_id"),
                "channel_id": data.get("channel_id"),
                "timestamp": data.get("timestamp"),
                "message_type": data.get("type", "message"),
            }

            if data.get("type") == "bot_message":
                hass.bus.async_fire(EVENT_HOMECHAT_BOT_MESSAGE, event_data)
            else:
                hass.bus.async_fire(EVENT_HOMECHAT_MESSAGE_RECEIVED, event_data)

            return web.json_response({"status": "ok"})

        except Exception as err:
            _LOGGER.error("Error processing HomeChat webhook: %s", err)
            return web.json_response(
                {"status": "error", "message": str(err)},
                status=500
            )

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

    async def list_channels(call: ServiceCall) -> None:
        """Handle list_channels service call."""
        try:
            result = await api.async_get_channels()
            channels = result.get("channels", [])
            _LOGGER.info("HomeChat channels: %s", [c.get("name") for c in channels])
            # Fire event with channels data
            hass.bus.async_fire(
                f"{DOMAIN}_channels_list",
                {"channels": channels}
            )
        except Exception as err:
            _LOGGER.error("Failed to list HomeChat channels: %s", err)

    async def join_channel(call: ServiceCall) -> None:
        """Handle join_channel service call."""
        channel_id = call.data["channel_id"]

        try:
            result = await api.async_join_channel(channel_id)
            _LOGGER.info("Joined HomeChat channel %s: %s", channel_id, result)
        except Exception as err:
            _LOGGER.error("Failed to join HomeChat channel %s: %s", channel_id, err)

    async def leave_channel(call: ServiceCall) -> None:
        """Handle leave_channel service call."""
        channel_id = call.data["channel_id"]

        try:
            result = await api.async_leave_channel(channel_id)
            _LOGGER.info("Left HomeChat channel %s: %s", channel_id, result)
        except Exception as err:
            _LOGGER.error("Failed to leave HomeChat channel %s: %s", channel_id, err)

    async def send_dm(call: ServiceCall) -> None:
        """Handle send_dm service call."""
        user_id = call.data["user_id"]
        message = call.data["message"]

        try:
            result = await api.async_send_dm(user_id, message)
            _LOGGER.info("Sent DM to user %s: %s", user_id, result)
        except Exception as err:
            _LOGGER.error("Failed to send DM to user %s: %s", user_id, err)

    async def search(call: ServiceCall) -> None:
        """Handle search service call."""
        query = call.data["query"]
        search_type = call.data.get("type", "all")

        try:
            result = await api.async_search(query, search_type)
            _LOGGER.info("HomeChat search for '%s': %s", query, result)
            # Fire event with search results
            hass.bus.async_fire(
                f"{DOMAIN}_search_results",
                {"query": query, "type": search_type, "results": result}
            )
        except Exception as err:
            _LOGGER.error("Failed to search HomeChat: %s", err)

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
        hass.services.async_register(
            DOMAIN, SERVICE_LIST_CHANNELS, list_channels
        )
        hass.services.async_register(
            DOMAIN, SERVICE_JOIN_CHANNEL, join_channel, schema=JOIN_CHANNEL_SCHEMA
        )
        hass.services.async_register(
            DOMAIN, SERVICE_LEAVE_CHANNEL, leave_channel, schema=LEAVE_CHANNEL_SCHEMA
        )
        hass.services.async_register(
            DOMAIN, SERVICE_SEND_DM, send_dm, schema=SEND_DM_SCHEMA
        )
        hass.services.async_register(
            DOMAIN, SERVICE_SEARCH, search, schema=SEARCH_SCHEMA
        )


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)