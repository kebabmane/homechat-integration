"""Pytest fixtures and mocks for HomeChat integration tests."""

import os
import sys
import types
from unittest.mock import MagicMock, AsyncMock
import pytest

# Ensure custom_components is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# === Metaclass for HA classes that accept kwargs like domain= ===
class _HAKMeta(type):
    def __new__(mcs, name, bases, namespace, **kwargs):
        return super().__new__(mcs, name, bases, namespace)


# === Mock HA core classes ===
class MockHomeAssistant:
    def __init__(self):
        self.data = {}
        self.bus = MagicMock()
        self.bus.async_fire = MagicMock()
        self.services = MagicMock()
        self.services.has_service = MagicMock(return_value=False)
        self.services.async_register = MagicMock()
        self.services.async_remove = MagicMock()
        self.config_entries = MagicMock()
        self.config_entries.async_forward_entry_setups = AsyncMock()
        self.config_entries.async_reload = AsyncMock()
        self.config_entries.async_get_entry = MagicMock(return_value=None)

        def _update_entry(entry, **kwargs):
            if "data" in kwargs:
                entry.data = kwargs["data"]
            if "title" in kwargs:
                entry.title = kwargs["title"]
            if "options" in kwargs:
                entry.options = kwargs["options"]

        self.config_entries.async_update_entry = MagicMock(side_effect=_update_entry)
        self.states = MagicMock()
        self.states.get = MagicMock(return_value=None)
        self.async_create_task = MagicMock()
        self.async_add_executor_job = AsyncMock()
        self.config = MagicMock()
        self.config.path = MagicMock(return_value="/mock/config")


class MockConfigEntry:
    def __init__(self, data, entry_id="test_entry_id", version=1, domain="homechat", title="Test"):
        self.data = data
        self.entry_id = entry_id
        self.version = version
        self.domain = domain
        self.title = title
        self.options = {}
        self._listeners = []
        self.add_update_listener = MagicMock(side_effect=self._add_listener)
        self.async_on_unload = MagicMock()

    def _add_listener(self, listener):
        self._listeners.append(listener)
        return lambda: None


class MockServiceCall:
    def __init__(self, data):
        self.data = data


class MockConfigFlow(metaclass=_HAKMeta):
    VERSION = 1
    context = {}
    data = {}
    hass = None

    def __init__(self):
        self.data = {}
        self.context = {}
        self.hass = None

    def async_show_form(self, step_id, data_schema=None, errors=None, description_placeholders=None):
        return {"type": "form", "step_id": step_id, "errors": errors, "description_placeholders": description_placeholders}

    def async_create_entry(self, title, data):
        return {"type": "create_entry", "title": title, "data": data}

    async def async_set_unique_id(self, unique_id):
        pass

    def _abort_if_unique_id_configured(self):
        pass

    def async_abort(self, reason):
        return {"type": "abort", "reason": reason}


class MockOptionsFlow:
    def __init__(self, config_entry):
        self.config_entry = config_entry
        self.hass = None

    def async_show_form(self, step_id, data_schema=None, errors=None, description_placeholders=None):
        return {"type": "form", "step_id": step_id, "errors": errors, "description_placeholders": description_placeholders}

    def async_create_entry(self, title, data):
        return {"type": "create_entry", "title": title, "data": data}


class MockSensorEntity:
    pass


class MockSensorStateClass:
    MEASUREMENT = "measurement"


class MockCoordinatorEntity:
    def __class_getitem__(cls, key):
        return cls

    def __init__(self, coordinator):
        self.coordinator = coordinator


class MockDataUpdateCoordinator:
    def __class_getitem__(cls, key):
        return cls

    def __init__(self, hass, logger, name, update_interval):
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_interval = update_interval
        self.data = None
        self.last_update_success = True


class MockUpdateFailed(Exception):
    pass


class MockConfigEntryAuthFailed(Exception):
    pass


class MockHomeAssistantError(Exception):
    pass


class MockZeroconfServiceInfo:
    def __init__(self, host, port, properties=None, name="test"):
        self.host = host
        self.port = port
        self.properties = properties or {}
        self.name = name


class MockFlowResult:
    pass


class MockConversationEntity:
    pass


class MockConversationInput:
    def __init__(self, text="", language="en", conversation_id=None):
        self.text = text
        self.language = language
        self.conversation_id = conversation_id


class MockConversationResult:
    def __init__(self, response=None, conversation_id=None):
        self.response = response
        self.conversation_id = conversation_id


class MockBaseNotificationService:
    pass


def mock_callback(func):
    return func


def mock_redact_data(data, to_redact):
    return {k: "***" if k in to_redact else v for k, v in data.items()}


# === Mock aiohttp ===
class MockClientTimeout:
    def __init__(self, total=30):
        self.total = total


class MockClientError(Exception):
    pass


class MockFormData:
    def __init__(self):
        self._fields = []

    def add_field(self, name, value, **kwargs):
        self._fields.append((name, value, kwargs))


class MockWebRequest:
    pass


class MockWebResponse:
    pass


def mock_json_response(data, status=200):
    return {"data": data, "status": status}


aiohttp_mod = types.ModuleType("aiohttp")
aiohttp_mod.ClientTimeout = MockClientTimeout
aiohttp_mod.ClientError = MockClientError
aiohttp_mod.FormData = MockFormData

aiohttp_web = types.ModuleType("aiohttp.web")
aiohttp_web.Request = MockWebRequest
aiohttp_web.Response = MockWebResponse
aiohttp_web.json_response = mock_json_response

sys.modules["aiohttp"] = aiohttp_mod
sys.modules["aiohttp.web"] = aiohttp_web

# === Build mock homeassistant package ===
ha = MagicMock()
ha.const = MagicMock()
ha.const.Platform = type("Platform", (), {"SENSOR": "sensor", "CONVERSATION": "conversation", "NOTIFY": "notify"})()
ha.const.SENSOR = "sensor"
ha.const.CONVERSATION = "conversation"
ha.const.CONF_HOST = "host"
ha.const.CONF_PORT = "port"
ha.const.CONF_SSL = "ssl"

ha.core = MagicMock()
ha.core.HomeAssistant = MockHomeAssistant
ha.core.ServiceCall = MockServiceCall
ha.core.callback = mock_callback

ha.config_entries = MagicMock()
ha.config_entries.ConfigEntry = MockConfigEntry
ha.config_entries.ConfigFlow = MockConfigFlow
ha.config_entries.OptionsFlow = MockOptionsFlow

ha.exceptions = MagicMock()
ha.exceptions.HomeAssistantError = MockHomeAssistantError
ha.exceptions.ConfigEntryAuthFailed = MockConfigEntryAuthFailed

ha.helpers = MagicMock()
ha.helpers.update_coordinator = MagicMock()
ha.helpers.update_coordinator.DataUpdateCoordinator = MockDataUpdateCoordinator
ha.helpers.update_coordinator.UpdateFailed = MockUpdateFailed
ha.helpers.update_coordinator.CoordinatorEntity = MockCoordinatorEntity

ha.helpers.entity_platform = MagicMock()
ha.helpers.entity_platform.AddEntitiesCallback = MagicMock()

ha.components = MagicMock()
ha.components.sensor = MagicMock()
ha.components.sensor.SensorEntity = MockSensorEntity
ha.components.sensor.SensorStateClass = MockSensorStateClass

ha.components.webhook = MagicMock()
ha.components.webhook.async_register = AsyncMock()
ha.components.webhook.async_unregister = AsyncMock()
ha.components.webhook.async_generate_id = MagicMock(return_value="test-webhook-id")

ha.components.diagnostics = MagicMock()
ha.components.diagnostics.async_redact_data = mock_redact_data

ha.components.notify = MagicMock()
ha.components.notify.ATTR_TITLE = "title"
ha.components.notify.ATTR_TARGET = "target"
ha.components.notify.ATTR_DATA = "data"
ha.components.notify.BaseNotificationService = MockBaseNotificationService

ha.components.conversation = MagicMock()
ha.components.conversation.ConversationEntity = MockConversationEntity
ha.components.conversation.ConversationInput = MockConversationInput
ha.components.conversation.ConversationResult = MockConversationResult

ha.helpers.service_info = MagicMock()
ha.helpers.service_info.zeroconf = MagicMock()
ha.helpers.service_info.zeroconf.ZeroconfServiceInfo = MockZeroconfServiceInfo

ha.data_entry_flow = MagicMock()
ha.data_entry_flow.FlowResult = MockFlowResult

ha.helpers.aiohttp_client = MagicMock()

ha.helpers.typing = MagicMock()
ha.helpers.typing.ConfigType = dict
ha.helpers.typing.DiscoveryInfoType = dict

ha.helpers.intent = MagicMock()
ha.helpers.intent.IntentResponse = MagicMock()
ha.helpers.intent.IntentResponseErrorCode = MagicMock()

sys.modules["homeassistant"] = ha
sys.modules["homeassistant.const"] = ha.const
sys.modules["homeassistant.core"] = ha.core
sys.modules["homeassistant.config_entries"] = ha.config_entries
sys.modules["homeassistant.exceptions"] = ha.exceptions
sys.modules["homeassistant.helpers"] = ha.helpers
sys.modules["homeassistant.helpers.update_coordinator"] = ha.helpers.update_coordinator
sys.modules["homeassistant.helpers.entity_platform"] = ha.helpers.entity_platform
sys.modules["homeassistant.components.sensor"] = ha.components.sensor
sys.modules["homeassistant.components.webhook"] = ha.components.webhook
sys.modules["homeassistant.components.diagnostics"] = ha.components.diagnostics
sys.modules["homeassistant.components.notify"] = ha.components.notify
sys.modules["homeassistant.components.conversation"] = ha.components.conversation
sys.modules["homeassistant.helpers.service_info"] = ha.helpers.service_info
sys.modules["homeassistant.helpers.service_info.zeroconf"] = ha.helpers.service_info.zeroconf
sys.modules["homeassistant.data_entry_flow"] = ha.data_entry_flow
sys.modules["homeassistant.helpers.aiohttp_client"] = ha.helpers.aiohttp_client
sys.modules["homeassistant.helpers.typing"] = ha.helpers.typing
sys.modules["homeassistant.helpers.intent"] = ha.helpers.intent
sys.modules["homeassistant.components.camera"] = MagicMock()

cv_mod = MagicMock()
cv_mod.string = str
cv_mod.boolean = bool
cv_mod.port = int
cv_mod.positive_int = int
sys.modules["homeassistant.helpers.config_validation"] = cv_mod

discovery_mod = MagicMock()
discovery_mod.async_load_platform = AsyncMock()
sys.modules["homeassistant.helpers.discovery"] = discovery_mod

# Minimal voluptuous mock
class _VolRequired:
    def __init__(self, key, default=None):
        self.key = key
        self.default = default

class _VolOptional:
    def __init__(self, key, default=None):
        self.key = key
        self.default = default

class _VolSchema:
    def __init__(self, fields):
        self.fields = fields

class _VolIn:
    def __init__(self, choices):
        self.choices = choices

vol_mod = MagicMock()
vol_mod.Schema = _VolSchema
vol_mod.Required = _VolRequired
vol_mod.Optional = _VolOptional
vol_mod.In = _VolIn
sys.modules["voluptuous"] = vol_mod
sys.modules["voluptuous.vol"] = vol_mod


# === Fixtures ===

@pytest.fixture
def hass():
    return MockHomeAssistant()


@pytest.fixture
def config_entry():
    return MockConfigEntry({
        "host": "localhost",
        "port": 3000,
        "ssl": False,
        "api_token": "test_token",
        "webhook_id": "test_webhook",
        "webhook_secret": "test_secret",
        "bot_username": "test_bot",
        "bot_id": None,
    })


class FakeAiohttpSession:
    """Fake aiohttp ClientSession with explicit get/post returning context managers."""

    def __init__(self):
        self.get = MagicMock()
        self.post = MagicMock()


@pytest.fixture
def mock_session():
    return FakeAiohttpSession()


@pytest.fixture
def mock_api_client(hass, mock_session):
    from custom_components.homechat import HomeChatAPI
    ha.helpers.aiohttp_client.async_get_clientsession = MagicMock(return_value=mock_session)
    api = HomeChatAPI(hass, "localhost", 3000, False, "test_token")
    return api


class FakeAiohttpResponse:
    """Fake aiohttp response for async context manager usage."""

    def __init__(self, status=200, json_data=None, text=""):
        self.status = status
        self._json = json_data or {}
        self._text = text

    async def json(self):
        return self._json

    async def text(self):
        return self._text

    def raise_for_status(self):
        if self.status >= 400:
            raise Exception(f"HTTP {self.status}")

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass
