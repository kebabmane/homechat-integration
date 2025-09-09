"""Constants for the HomeChat integration."""

DOMAIN = "homechat"

# Configuration keys
CONF_HOST = "host"
CONF_PORT = "port" 
CONF_SSL = "ssl"
CONF_API_TOKEN = "api_token"
CONF_WEBHOOK_ID = "webhook_id"
CONF_BOT_USERNAME = "bot_username"

# Default values
DEFAULT_PORT = 3000
DEFAULT_SSL = False
DEFAULT_BOT_USERNAME = "home_assistant_bot"

# API endpoints
API_SEND_MESSAGE = "/api/v1/messages"
API_CREATE_BOT = "/api/v1/bots"
API_BOT_STATUS = "/api/v1/bots/{bot_id}/status"

# Services
SERVICE_SEND_MESSAGE = "send_message"
SERVICE_SEND_NOTIFICATION = "send_notification"
SERVICE_CREATE_BOT = "create_bot"

# Platforms
PLATFORMS = ["notify"]

# Event types
EVENT_HOMECHAT_MESSAGE_RECEIVED = "homechat_message_received"
EVENT_HOMECHAT_BOT_MESSAGE = "homechat_bot_message"

# Error messages
ERROR_CANNOT_CONNECT = "cannot_connect"
ERROR_INVALID_AUTH = "invalid_auth"
ERROR_UNKNOWN = "unknown"