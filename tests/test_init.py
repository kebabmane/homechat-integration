"""Tests for HomeChat API client and webhook utilities."""

import pytest
from unittest.mock import MagicMock, patch
import hashlib
import hmac

from custom_components.homechat import HomeChatAPI, _verify_webhook_signature
from tests.conftest import FakeAiohttpResponse


@pytest.mark.asyncio
async def test_api_test_connection_success(hass, mock_session):
    """Test health check returns True on 200 status."""
    mock_session.get = MagicMock(return_value=FakeAiohttpResponse(200))
    with patch("custom_components.homechat.async_get_clientsession", return_value=mock_session):
        api = HomeChatAPI(hass, "localhost", 3000, False, "token")
        result = await api.async_test_connection()
    assert result is True


@pytest.mark.asyncio
async def test_api_test_connection_failure(hass, mock_session):
    """Test health check returns False on connection error."""
    mock_session.get = MagicMock(side_effect=Exception("Connection refused"))
    with patch("custom_components.homechat.async_get_clientsession", return_value=mock_session):
        api = HomeChatAPI(hass, "localhost", 3000, False, "token")
        result = await api.async_test_connection()
    assert result is False


@pytest.mark.asyncio
async def test_api_test_connection_non_200(hass, mock_session):
    """Test health check returns False on non-200 status."""
    mock_session.get = MagicMock(return_value=FakeAiohttpResponse(500))
    with patch("custom_components.homechat.async_get_clientsession", return_value=mock_session):
        api = HomeChatAPI(hass, "localhost", 3000, False, "token")
        result = await api.async_test_connection()
    assert result is False


@pytest.mark.asyncio
async def test_api_send_message(hass, mock_session):
    """Test send message calls the correct endpoint and returns response."""
    mock_session.post = MagicMock(return_value=FakeAiohttpResponse(200, {"id": 123, "status": "ok"}))
    with patch("custom_components.homechat.async_get_clientsession", return_value=mock_session):
        api = HomeChatAPI(hass, "localhost", 3000, False, "token")
        result = await api.async_send_message("Hello world", room_id="general")

    assert result == {"id": 123, "status": "ok"}
    mock_session.post.assert_called_once()
    call_args = mock_session.post.call_args
    assert call_args[0][0] == "http://localhost:3000/api/v1/messages"


@pytest.mark.asyncio
async def test_api_send_message_with_user_id(hass, mock_session):
    """Test send message with user_id instead of room_id."""
    mock_session.post = MagicMock(return_value=FakeAiohttpResponse(200, {"id": 456}))
    with patch("custom_components.homechat.async_get_clientsession", return_value=mock_session):
        api = HomeChatAPI(hass, "localhost", 3000, False, "token")
        result = await api.async_send_message("DM text", user_id="42", title="Greeting")

    assert result == {"id": 456}
    call_kwargs = mock_session.post.call_args[1]
    json_data = call_kwargs.get("json")
    assert json_data["user_id"] == "42"
    assert json_data["title"] == "Greeting"


@pytest.mark.asyncio
async def test_api_send_message_raises_on_error(hass, mock_session):
    """Test send message propagates aiohttp client errors."""
    mock_session.post = MagicMock(side_effect=Exception("Network error"))
    with patch("custom_components.homechat.async_get_clientsession", return_value=mock_session):
        api = HomeChatAPI(hass, "localhost", 3000, False, "token")
        with pytest.raises(Exception, match="Network error"):
            await api.async_send_message("Hello")


def test_verify_webhook_signature_success():
    """Test HMAC verification with valid signature."""
    secret = "mysecret"
    payload = b'{"message":"hello"}'
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    signature = f"sha256={expected}"
    assert _verify_webhook_signature(payload, signature, secret) is True


def test_verify_webhook_signature_failure():
    """Test HMAC verification rejects invalid signature."""
    secret = "mysecret"
    payload = b'{"message":"hello"}'
    assert _verify_webhook_signature(payload, "sha256=badsignature", secret) is False


def test_verify_webhook_signature_missing_secret():
    """Test HMAC verification fails when secret is empty."""
    assert _verify_webhook_signature(b"test", "sig", "") is False


def test_verify_webhook_signature_missing_signature():
    """Test HMAC verification fails when signature is empty."""
    assert _verify_webhook_signature(b"test", "", "secret") is False


def test_verify_webhook_signature_tampered_payload():
    """Test HMAC verification fails when payload is tampered."""
    secret = "mysecret"
    payload = b'{"message":"hello"}'
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    signature = f"sha256={expected}"
    tampered_payload = b'{"message":"hacked"}'
    assert _verify_webhook_signature(tampered_payload, signature, secret) is False
