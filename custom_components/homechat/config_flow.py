"""Config flow for HomeChat integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SSL
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.components.webhook import async_generate_id

from .const import (
    DOMAIN,
    CONF_API_TOKEN,
    CONF_WEBHOOK_ID,
    CONF_BOT_USERNAME,
    DEFAULT_PORT,
    DEFAULT_SSL,
    DEFAULT_BOT_USERNAME,
    ERROR_CANNOT_CONNECT,
    ERROR_INVALID_AUTH,
    ERROR_UNKNOWN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Optional(CONF_SSL, default=DEFAULT_SSL): cv.boolean,
        vol.Required(CONF_API_TOKEN): cv.string,
    }
)

STEP_BOT_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_BOT_USERNAME, default=DEFAULT_BOT_USERNAME): cv.string,
        vol.Optional("enable_webhook", default=True): cv.boolean,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HomeChat."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = ERROR_CANNOT_CONNECT
        except InvalidAuth:
            errors["base"] = ERROR_INVALID_AUTH
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = ERROR_UNKNOWN
        else:
            self.data.update(user_input)
            self.data["title"] = info["title"]
            return await self.async_step_bot()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_bot(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the bot configuration step."""
        if user_input is None:
            return self.async_show_form(
                step_id="bot", data_schema=STEP_BOT_DATA_SCHEMA
            )

        # Generate webhook ID if webhook is enabled
        webhook_id = None
        if user_input.get("enable_webhook", True):
            webhook_id = async_generate_id()

        self.data.update({
            CONF_BOT_USERNAME: user_input[CONF_BOT_USERNAME],
            CONF_WEBHOOK_ID: webhook_id,
        })

        # Create entry
        return self.async_create_entry(
            title=self.data["title"],
            data=self.data,
        )

    async def async_step_import(self, import_info: dict[str, Any]) -> FlowResult:
        """Handle import from configuration.yaml."""
        try:
            info = await validate_input(self.hass, import_info)
        except CannotConnect:
            return self.async_abort(reason=ERROR_CANNOT_CONNECT)
        except InvalidAuth:
            return self.async_abort(reason=ERROR_INVALID_AUTH)
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception during import")
            return self.async_abort(reason=ERROR_UNKNOWN)

        return self.async_create_entry(
            title=info["title"],
            data=import_info,
        )


class OptionsFlow(config_entries.OptionsFlow):
    """Handle options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_bot_username = self.config_entry.data.get(CONF_BOT_USERNAME, DEFAULT_BOT_USERNAME)
        has_webhook = self.config_entry.data.get(CONF_WEBHOOK_ID) is not None

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_BOT_USERNAME, default=current_bot_username
                    ): cv.string,
                    vol.Optional("enable_webhook", default=has_webhook): cv.boolean,
                }
            ),
        )


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""


class InvalidAuth(Exception):
    """Error to indicate there is invalid auth."""


async def validate_input(hass, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    host = data[CONF_HOST]
    port = data[CONF_PORT]
    ssl = data.get(CONF_SSL, DEFAULT_SSL)
    api_token = data[CONF_API_TOKEN]

    session = async_get_clientsession(hass)
    scheme = "https" if ssl else "http"
    base_url = f"{scheme}://{host}:{port}"

    # Test health endpoint
    health_url = f"{base_url}/api/v1/health"
    try:
        async with session.get(health_url, timeout=10) as response:
            if response.status != 200:
                raise CannotConnect
            health_data = await response.json()
    except aiohttp.ClientError as err:
        _LOGGER.error("Connection error: %s", err)
        raise CannotConnect from err

    # Test authentication
    auth_url = f"{base_url}/api/v1/messages"
    headers = {"Authorization": f"Bearer {api_token}"}
    try:
        async with session.get(auth_url, headers=headers, timeout=10) as response:
            if response.status == 401:
                raise InvalidAuth
            # Any other status is fine for now - we just need to test auth
    except aiohttp.ClientError as err:
        if "401" in str(err):
            raise InvalidAuth from err
        _LOGGER.error("Auth test error: %s", err)
        raise CannotConnect from err

    # Return info that you want to store in the config entry.
    return {
        "title": f"HomeChat ({host}:{port})",
        "service": health_data.get("service", "HomeChat"),
        "version": health_data.get("version", "unknown"),
    }