"""Constants for the HomeChat integration."""

DOMAIN = "homechat"

# Configuration keys
CONF_HOST = "host"
CONF_PORT = "port"
CONF_SSL = "ssl"
CONF_API_TOKEN = "api_token"
CONF_WEBHOOK_ID = "webhook_id"
CONF_WEBHOOK_SECRET = "webhook_secret"
CONF_BOT_USERNAME = "bot_username"
CONF_BOT_ID = "bot_id"

# Default values
DEFAULT_PORT = 3000
DEFAULT_SSL = False
DEFAULT_BOT_USERNAME = "home_assistant_bot"

# API endpoints
API_HEALTH = "/api/v1/health"
API_SEND_MESSAGE = "/api/v1/messages"
API_CHANNELS = "/api/v1/channels"
API_CHANNEL_DETAIL = "/api/v1/channels/{channel_id}"
API_CHANNEL_JOIN = "/api/v1/channels/{channel_id}/join"
API_CHANNEL_LEAVE = "/api/v1/channels/{channel_id}/leave"
API_CHANNEL_MEMBERS = "/api/v1/channels/{channel_id}/members"
API_CHANNEL_MESSAGES = "/api/v1/channels/{channel_id}/messages"
API_CHANNEL_MEDIA = "/api/v1/channels/{channel_id}/media"
API_DM_CHANNELS = "/api/v1/dm/channels"
API_DM_START = "/api/v1/dm/start"
API_USER_MESSAGES = "/api/v1/users/{user_id}/messages"
API_CREATE_BOT = "/api/v1/bots"
API_BOT_STATUS = "/api/v1/bots/{bot_id}/status"
API_SEARCH = "/api/v1/search"

# Services
SERVICE_SEND_MESSAGE = "send_message"
SERVICE_SEND_NOTIFICATION = "send_notification"
SERVICE_CREATE_BOT = "create_bot"
SERVICE_LIST_CHANNELS = "list_channels"
SERVICE_JOIN_CHANNEL = "join_channel"
SERVICE_LEAVE_CHANNEL = "leave_channel"
SERVICE_SEND_DM = "send_dm"
SERVICE_SEARCH = "search"

# Platforms
from homeassistant.const import Platform
PLATFORMS = [Platform.SENSOR, Platform.CONVERSATION]

# Event types
EVENT_HOMECHAT_MESSAGE_RECEIVED = "homechat_message_received"
EVENT_HOMECHAT_BOT_MESSAGE = "homechat_bot_message"

# Error messages
ERROR_CANNOT_CONNECT = "cannot_connect"
ERROR_INVALID_AUTH = "invalid_auth"
ERROR_INSUFFICIENT_SCOPES = "insufficient_scopes"
ERROR_UNKNOWN = "unknown"