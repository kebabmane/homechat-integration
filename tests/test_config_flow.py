"""Tests for HomeChat config flow."""

import pytest
from unittest.mock import MagicMock, patch

from custom_components.homechat.config_flow import (
    ConfigFlow,
    CannotConnect,
    InvalidAuth,
    InsufficientScopes,
    validate_input,
)
from custom_components.homechat.const import DOMAIN
from tests.conftest import MockZeroconfServiceInfo, FakeAiohttpResponse
from custom_components.homechat.config_flow import aiohttp as mock_aiohttp


@pytest.fixture
def flow(hass):
    """Create a ConfigFlow instance with hass set."""
    f = ConfigFlow()
    f.hass = hass
    return f


@pytest.mark.asyncio
async def test_user_step_valid_credentials(flow, hass, mock_session):
    """Test user step with valid credentials proceeds to bot step."""

    def mock_get(url, **kwargs):
        if "health" in url:
            return FakeAiohttpResponse(200, {"service": "HomeChat", "version": "1.0"})
        if "messages" in url:
            return FakeAiohttpResponse(200)
        if "channels" in url:
            return FakeAiohttpResponse(200)
        return FakeAiohttpResponse(200)

    mock_session.get = MagicMock(side_effect=mock_get)

    with patch("custom_components.homechat.config_flow.async_get_clientsession", return_value=mock_session):
        result = await flow.async_step_user({
            "host": "localhost",
            "port": 3000,
            "ssl": False,
            "api_token": "valid_token",
        })

    assert result["type"] == "form"
    assert result["step_id"] == "bot"


@pytest.mark.asyncio
async def test_user_step_cannot_connect(flow, hass, mock_session):
    """Test user step shows cannot_connect error when health endpoint fails."""
    mock_session.get = MagicMock(side_effect=mock_aiohttp.ClientError("Connection refused"))

    with patch("custom_components.homechat.config_flow.async_get_clientsession", return_value=mock_session):
        result = await flow.async_step_user({
            "host": "localhost",
            "port": 3000,
            "ssl": False,
            "api_token": "token",
        })

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"]["base"] == "cannot_connect"


@pytest.mark.asyncio
async def test_user_step_invalid_auth(flow, hass, mock_session):
    """Test user step shows invalid_auth error when messages endpoint returns 401."""

    def mock_get(url, **kwargs):
        if "health" in url:
            return FakeAiohttpResponse(200, {"service": "HomeChat"})
        if "messages" in url:
            return FakeAiohttpResponse(401)
        return FakeAiohttpResponse(200)

    mock_session.get = MagicMock(side_effect=mock_get)

    with patch("custom_components.homechat.config_flow.async_get_clientsession", return_value=mock_session):
        result = await flow.async_step_user({
            "host": "localhost",
            "port": 3000,
            "ssl": False,
            "api_token": "bad_token",
        })

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"]["base"] == "invalid_auth"


@pytest.mark.asyncio
async def test_zeroconf_discovery(flow, hass):
    """Test zeroconf discovery flow stores discovered info and shows confirmation form."""
    info = MockZeroconfServiceInfo(
        host="192.168.1.100",
        port=3000,
        properties={"secure": "true", "version": "1.0"},
        name="MyHomeChat._homechat._tcp.local.",
    )

    result = await flow.async_step_zeroconf(info)

    assert result["type"] == "form"
    assert result["step_id"] == "zeroconf_confirm"
    assert flow._discovered_host == "192.168.1.100"
    assert flow._discovered_port == 3000
    assert flow._discovered_ssl is True


@pytest.mark.asyncio
async def test_zeroconf_confirm_valid(flow, hass, mock_session):
    """Test zeroconf confirm step with valid token proceeds to bot step."""
    info = MockZeroconfServiceInfo(
        host="192.168.1.100",
        port=3000,
        properties={"secure": "false", "version": "1.0"},
        name="MyHomeChat._homechat._tcp.local.",
    )
    await flow.async_step_zeroconf(info)

    def mock_get(url, **kwargs):
        if "health" in url:
            return FakeAiohttpResponse(200, {"service": "HomeChat", "version": "1.0"})
        if "messages" in url:
            return FakeAiohttpResponse(200)
        if "channels" in url:
            return FakeAiohttpResponse(200)
        return FakeAiohttpResponse(200)

    mock_session.get = MagicMock(side_effect=mock_get)

    with patch("custom_components.homechat.config_flow.async_get_clientsession", return_value=mock_session):
        result = await flow.async_step_zeroconf_confirm({
            "api_token": "valid_token",
        })

    assert result["type"] == "form"
    assert result["step_id"] == "bot"


@pytest.mark.asyncio
async def test_bot_step_creates_entry(flow, hass):
    """Test bot step creates a config entry with webhook ID."""
    flow.data = {
        "host": "localhost",
        "port": 3000,
        "ssl": False,
        "api_token": "token",
        "title": "HomeChat (localhost:3000)",
    }

    result = await flow.async_step_bot({
        "bot_username": "my_bot",
        "enable_webhook": True,
    })

    assert result["type"] == "create_entry"
    assert result["data"]["bot_username"] == "my_bot"
    assert result["data"]["webhook_id"] == "test-webhook-id"


@pytest.mark.asyncio
async def test_reconfigure_success(flow, hass, mock_session):
    """Test reconfiguration updates the config entry."""
    from tests.conftest import MockConfigEntry

    entry = MockConfigEntry({
        "host": "oldhost",
        "port": 3000,
        "ssl": False,
        "api_token": "old_token",
    })
    hass.config_entries.async_get_entry = MagicMock(return_value=entry)

    def mock_get(url, **kwargs):
        if "health" in url:
            return FakeAiohttpResponse(200, {"service": "HomeChat", "version": "1.0"})
        if "messages" in url:
            return FakeAiohttpResponse(200)
        return FakeAiohttpResponse(200)

    mock_session.get = MagicMock(side_effect=mock_get)

    flow.context["entry_id"] = entry.entry_id

    with patch("custom_components.homechat.config_flow.async_get_clientsession", return_value=mock_session):
        result = await flow.async_step_reconfigure({
            "host": "newhost",
            "port": 3000,
            "ssl": False,
            "api_token": "new_token",
        })

    assert result["type"] == "abort"
    assert result["reason"] == "reconfigure_successful"
    assert entry.data["host"] == "newhost"
    assert entry.data["api_token"] == "new_token"
