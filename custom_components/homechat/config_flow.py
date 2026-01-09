"""Config flow for HomeChat integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SSL
from homeassistant.components.zeroconf import ZeroconfServiceInfo
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

# Schema for zeroconf-discovered servers (only need API token)
STEP_ZEROCONF_CONFIRM_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_TOKEN): cv.string,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HomeChat."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.data: dict[str, Any] = {}
        self._discovered_host: str | None = None
        self._discovered_port: int = DEFAULT_PORT
        self._discovered_ssl: bool = DEFAULT_SSL
        self._discovered_name: str | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlow(config_entry)

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> FlowResult:
        """Handle zeroconf discovery of a HomeChat server."""
        _LOGGER.debug("Zeroconf discovery: %s", discovery_info)

        # Extract host and port from discovery info
        host = str(discovery_info.host)
        port = discovery_info.port or DEFAULT_PORT

        # Check if already configured
        await self.async_set_unique_id(f"{host}:{port}")
        self._abort_if_unique_id_configured()

        # Extract properties from TXT record
        properties = discovery_info.properties or {}
        server_name = discovery_info.name.replace("._homechat._tcp.local.", "")
        is_secure = properties.get("secure", "false").lower() == "true"
        version = properties.get("version", "unknown")

        # Store discovered info
        self._discovered_host = host
        self._discovered_port = port
        self._discovered_ssl = is_secure
        self._discovered_name = server_name

        # Set the title for the discovery notification
        self.context["title_placeholders"] = {
            "name": server_name,
            "host": host,
        }

        _LOGGER.info(
            "Discovered HomeChat server: %s at %s:%s (secure=%s, version=%s)",
            server_name, host, port, is_secure, version
        )

        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm zeroconf discovery and get API token."""
        if user_input is None:
            return self.async_show_form(
                step_id="zeroconf_confirm",
                data_schema=STEP_ZEROCONF_CONFIRM_SCHEMA,
                description_placeholders={
                    "name": self._discovered_name,
                    "host": self._discovered_host,
                    "port": str(self._discovered_port),
                },
            )

        errors = {}

        # Build data with discovered info + user-provided token
        data = {
            CONF_HOST: self._discovered_host,
            CONF_PORT: self._discovered_port,
            CONF_SSL: self._discovered_ssl,
            CONF_API_TOKEN: user_input[CONF_API_TOKEN],
        }

        try:
            info = await validate_input(self.hass, data)
        except CannotConnect:
            errors["base"] = ERROR_CANNOT_CONNECT
        except InvalidAuth:
            errors["base"] = ERROR_INVALID_AUTH
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = ERROR_UNKNOWN
        else:
            self.data.update(data)
            self.data["title"] = info["title"]
            return await self.async_step_bot()

        return self.async_show_form(
            step_id="zeroconf_confirm",
            data_schema=STEP_ZEROCONF_CONFIRM_SCHEMA,
            errors=errors,
            description_placeholders={
                "name": self._discovered_name,
                "host": self._discovered_host,
                "port": str(self._discovered_port),
            },
        )

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

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reconfiguration of the integration."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        if entry is None:
            return self.async_abort(reason="reconfigure_failed")

        if user_input is None:
            return self.async_show_form(
                step_id="reconfigure",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_HOST, default=entry.data.get(CONF_HOST)): cv.string,
                        vol.Optional(CONF_PORT, default=entry.data.get(CONF_PORT, DEFAULT_PORT)): cv.port,
                        vol.Optional(CONF_SSL, default=entry.data.get(CONF_SSL, DEFAULT_SSL)): cv.boolean,
                        vol.Required(CONF_API_TOKEN, default=entry.data.get(CONF_API_TOKEN)): cv.string,
                    }
                ),
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = ERROR_CANNOT_CONNECT
        except InvalidAuth:
            errors["base"] = ERROR_INVALID_AUTH
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception during reconfigure")
            errors["base"] = ERROR_UNKNOWN
        else:
            # Update the entry with new data, preserving webhook and bot settings
            new_data = {
                **entry.data,
                CONF_HOST: user_input[CONF_HOST],
                CONF_PORT: user_input[CONF_PORT],
                CONF_SSL: user_input.get(CONF_SSL, DEFAULT_SSL),
                CONF_API_TOKEN: user_input[CONF_API_TOKEN],
            }
            self.hass.config_entries.async_update_entry(
                entry,
                title=info["title"],
                data=new_data,
            )
            await self.hass.config_entries.async_reload(entry.entry_id)
            return self.async_abort(reason="reconfigure_successful")

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=user_input.get(CONF_HOST)): cv.string,
                    vol.Optional(CONF_PORT, default=user_input.get(CONF_PORT, DEFAULT_PORT)): cv.port,
                    vol.Optional(CONF_SSL, default=user_input.get(CONF_SSL, DEFAULT_SSL)): cv.boolean,
                    vol.Required(CONF_API_TOKEN, default=user_input.get(CONF_API_TOKEN)): cv.string,
                }
            ),
            errors=errors,
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
            # Update entry data with new bot settings
            new_data = dict(self.config_entry.data)
            new_data[CONF_BOT_USERNAME] = user_input.get(CONF_BOT_USERNAME, DEFAULT_BOT_USERNAME)

            # Handle webhook enable/disable
            if user_input.get("enable_webhook", False):
                if new_data.get(CONF_WEBHOOK_ID) is None:
                    new_data[CONF_WEBHOOK_ID] = async_generate_id()
            else:
                new_data[CONF_WEBHOOK_ID] = None

            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data=new_data,
            )
            return self.async_create_entry(title="", data={})

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