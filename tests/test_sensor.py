"""Tests for HomeChat sensor platform."""

import pytest

from custom_components.homechat.sensor import (
    async_setup_entry,
    HomeChatStatusSensor,
    HomeChatChannelCountSensor,
)


class FakeCoordinator:
    """Minimal fake coordinator for sensor tests."""

    def __init__(self, data=None, status="online", channels=None):
        self.data = data or {}
        self.server_status = status
        self.channels = channels or []
        self.last_update_success = True


@pytest.mark.asyncio
async def test_async_setup_entry_creates_sensors(hass, config_entry):
    """Test that async_setup_entry creates the expected sensors."""
    coordinator = FakeCoordinator()
    hass.data["homechat"] = {config_entry.entry_id: {"coordinator": coordinator}}

    added = []

    def add_entities(entities):
        added.extend(entities)

    await async_setup_entry(hass, config_entry, add_entities)

    assert len(added) == 2
    assert isinstance(added[0], HomeChatStatusSensor)
    assert isinstance(added[1], HomeChatChannelCountSensor)


def test_status_sensor_state(hass, config_entry):
    """Test status sensor returns coordinator server_status."""
    coordinator = FakeCoordinator(status="online")
    sensor = HomeChatStatusSensor(coordinator, config_entry)
    assert sensor.native_value == "online"


def test_status_sensor_extra_attributes(hass, config_entry):
    """Test status sensor exposes host/port/ssl attributes."""
    coordinator = FakeCoordinator()
    sensor = HomeChatStatusSensor(coordinator, config_entry)
    attrs = sensor.extra_state_attributes
    assert attrs["host"] == "localhost"
    assert attrs["port"] == 3000
    assert attrs["ssl"] is False


def test_channel_count_sensor_state(hass, config_entry):
    """Test channel count sensor returns count from coordinator data."""
    coordinator = FakeCoordinator(data={"channel_count": 5})
    sensor = HomeChatChannelCountSensor(coordinator, config_entry)
    assert sensor.native_value == 5


def test_channel_count_sensor_default_zero(hass, config_entry):
    """Test channel count sensor defaults to 0 when data is empty."""
    coordinator = FakeCoordinator(data={})
    sensor = HomeChatChannelCountSensor(coordinator, config_entry)
    assert sensor.native_value == 0


def test_channel_count_sensor_extra_attributes(hass, config_entry):
    """Test channel count sensor exposes channel list."""
    coordinator = FakeCoordinator(channels=[
        {"id": 1, "name": "general", "type": "public"},
        {"id": 2, "name": "alerts", "type": "private"},
    ])
    sensor = HomeChatChannelCountSensor(coordinator, config_entry)
    attrs = sensor.extra_state_attributes
    assert len(attrs["channels"]) == 2
    assert attrs["channels"][0] == {"id": 1, "name": "general", "type": "public"}


def test_sensor_state_updates_on_coordinator_refresh(hass, config_entry):
    """Test that sensor states reflect coordinator data updates."""
    coordinator = FakeCoordinator(status="offline", data={"channel_count": 0})
    status_sensor = HomeChatStatusSensor(coordinator, config_entry)
    count_sensor = HomeChatChannelCountSensor(coordinator, config_entry)

    assert status_sensor.native_value == "offline"
    assert count_sensor.native_value == 0

    # Simulate coordinator refresh with new data
    coordinator.server_status = "online"
    coordinator.data = {"channel_count": 3}

    assert status_sensor.native_value == "online"
    assert count_sensor.native_value == 3
