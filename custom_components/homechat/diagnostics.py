"""Diagnostics support for HomeChat integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_API_TOKEN, CONF_WEBHOOK_SECRET

TO_REDACT = {CONF_API_TOKEN, CONF_WEBHOOK_SECRET, "api_token", "webhook_secret"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    coordinator = data.get("coordinator")

    diagnostics_data: dict[str, Any] = {
        "config_entry": {
            "entry_id": entry.entry_id,
            "version": entry.version,
            "domain": entry.domain,
            "title": entry.title,
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": async_redact_data(dict(entry.options), TO_REDACT),
        },
        "integration_data": {
            "webhook_id": data.get("webhook_id"),
            "bot_username": data.get("bot_username"),
            "has_api": data.get("api") is not None,
            "has_coordinator": coordinator is not None,
        },
    }

    if coordinator is not None:
        channels = coordinator.channels or []
        diagnostics_data["coordinator"] = {
            "last_update_success": coordinator.last_update_success,
            "server_status": coordinator.server_status,
            "channel_count": len(channels),
            "channel_types": sorted({c.get("type", "unknown") for c in channels}),
            "has_data": coordinator.data is not None,
        }

    return diagnostics_data
