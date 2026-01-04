"""Exceptions for the HomeChat integration."""
from homeassistant.exceptions import HomeAssistantError


class HomeChatError(HomeAssistantError):
    """Base exception for HomeChat errors."""


class CannotConnect(HomeChatError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeChatError):
    """Error to indicate there is invalid auth."""


class InvalidResponse(HomeChatError):
    """Error to indicate an invalid response from the server."""
