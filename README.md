# HomeChat Home Assistant Integration

[![HACS][hacs-shield]][hacs-url]
[![Version][version-shield]][version-url]
[![License][license-shield]][license-url]

Connect Home Assistant to HomeChat for smart home notifications and two-way communication.

## Features

| Feature | Description |
|---------|-------------|
| **Notifications** | Send HA automation alerts to HomeChat |
| **Two-Way** | Trigger HA automations from chat messages |
| **Rich Formatting** | Priority levels, message types, timestamps |
| **Bot Integration** | Automated responders and commands |
| **Auto-Discovery** | Zeroconf/mDNS server detection |
| **Sensors** | Server status and channel count entities |

## Installation

### HACS (Recommended)

1. Add this repository to HACS as a custom repository
2. Search for "HomeChat" and install
3. Restart Home Assistant
4. Add integration via UI

### Manual Installation

```bash
# Copy to custom_components
cp -r custom_components/homechat <ha_config>/custom_components/

# Restart Home Assistant
```

## Configuration

### Prerequisites

1. **HomeChat Server** — Running (addon or Docker)
2. **API Token** — Generated in HomeChat admin panel
3. **Network Access** — HA must reach HomeChat server

### Setup Steps

1. Go to **Settings** > **Devices & Services** > **Add Integration**
2. Search for "HomeChat"
3. Enter connection details:
   - **Host**: HomeChat server hostname/IP
   - **Port**: 3000 (default)
   - **SSL**: Enable if using HTTPS
   - **API Token**: From HomeChat admin panel
4. Configure bot options (optional)

## Services

### notify.homechat

Send notifications to HomeChat rooms.

```yaml
service: notify.homechat
data:
  message: "Front door opened"
  title: "Security Alert"
  target: "security"
  data:
    priority: "high"
    type: "security"
```

### homechat.send_message

Send a basic message.

```yaml
service: homechat.send_message
data:
  message: "Kitchen light turned on"
  room_id: "home-automation"
  title: "Device Update"
```

### homechat.send_notification

Send a formatted notification with priority.

```yaml
service: homechat.send_notification
data:
  message: "Garage door open for 30 minutes"
  title: "Reminder"
  priority: "normal"
  room_id: "alerts"
```

### homechat.create_bot

Create a new bot in HomeChat.

```yaml
service: homechat.create_bot
data:
  name: "weather_bot"
  description: "Provides weather updates"
```

### homechat.send_dm

Send a direct message to a user by their ID.

```yaml
service: homechat.send_dm
data:
  message: "Your package has arrived"
  user_id: 2  # User ID from HomeChat (integer)
```

## Message Options

### Priority Levels

| Priority | Display |
|----------|---------|
| `urgent` | URGENT prefix |
| `high` | HIGH PRIORITY prefix |
| `normal` | Standard formatting |
| `low` | Info prefix |

### Message Types

| Type | Display |
|------|---------|
| `notification` | Home prefix |
| `alert` | ALERT prefix |
| `automation` | Automation prefix |
| `device` | Device name prefix |
| `security` | Security prefix |

## Automation Examples

### Motion Detection Alert

```yaml
automation:
  - alias: "Motion Alert"
    trigger:
      platform: state
      entity_id: binary_sensor.motion_detector
      to: "on"
    action:
      service: notify.homechat
      data:
        message: "Motion detected in {{ trigger.entity_id.split('.')[1] | replace('_', ' ') | title }}"
        title: "Motion Alert"
        data:
          priority: "high"
          type: "security"
```

### Device Offline Notification

```yaml
automation:
  - alias: "Device Offline"
    trigger:
      platform: state
      entity_id: device_tracker.phone
      to: "not_home"
      for: "00:10:00"
    action:
      service: homechat.send_notification
      data:
        message: "{{ trigger.entity_id.attributes.friendly_name }} has been offline for 10 minutes"
        title: "Device Status"
        priority: "normal"
        room_id: "notifications"
```

### Daily Summary

```yaml
automation:
  - alias: "Daily Summary"
    trigger:
      platform: time
      at: "22:00:00"
    action:
      service: homechat.send_message
      data:
        message: |
          **Daily Summary**
          - Lights: {{ states.light | selectattr('state', 'eq', 'on') | list | length }} on
          - Sensors: {{ states.binary_sensor | selectattr('state', 'eq', 'on') | list | length }} active
          - Temperature: {{ states('sensor.living_room_temperature') }}C
        title: "End of Day Report"
        room_id: "daily-reports"
```

### Two-Way Command Handler

```yaml
automation:
  - alias: "HomeChat Command Handler"
    trigger:
      platform: event
      event_type: homechat_bot_message
    condition:
      condition: template
      value_template: "{{ 'lights off' in trigger.event.data.message.lower() }}"
    action:
      - service: light.turn_off
        target:
          entity_id: all
      - service: homechat.send_message
        data:
          message: "All lights turned off"
          room_id: "{{ trigger.event.data.room_id }}"
```

## Events

The integration fires events for two-way communication:

| Event | Trigger |
|-------|---------|
| `homechat_message_received` | Any message from HomeChat |
| `homechat_bot_message` | Bot-specific messages |

### Event Data

```yaml
event_data:
  message: "Message content"
  user: "username"
  room_id: "channel-name"
  timestamp: "2025-01-10T12:00:00Z"
```

## Sensors

The integration creates sensor entities:

| Entity | Description |
|--------|-------------|
| `sensor.homechat_status` | Server connection status |
| `sensor.homechat_channels` | Number of channels |

## Troubleshooting

### Integration Fails to Connect

```bash
# Test API from HA
curl -H "Authorization: Bearer YOUR_TOKEN" http://homechat:3000/api/v1/health
```

**Check:**
- HomeChat server is running
- Host/port are correct
- API token is valid and active
- Network allows connection

### Messages Not Appearing

1. Verify target room exists in HomeChat
2. Check API token permissions
3. Review HomeChat logs for errors
4. Test with basic message first

### Webhooks Not Working

1. Enable two-way communication in setup
2. Verify HomeChat can reach HA
3. Check webhook URL configuration
4. Review HA logs for webhook events

### Debug Logging

```yaml
logger:
  default: info
  logs:
    custom_components.homechat: debug
```

## API Token Setup

1. Open HomeChat admin panel (`/admin/integrations`)
2. Click "Generate API Token"
3. Name it "Home Assistant"
4. Copy the full token (shown once)
5. Use in integration configuration

## Related Documentation

- [HomeChat Server](https://github.com/kebabmane/homechat)
- [HomeChat Add-on](https://github.com/kebabmane/homechat-addon)
- [Integration Setup Guide](https://github.com/kebabmane/homechat/blob/main/docs/deployment/home-assistant.md)

## Support

- [GitHub Issues](https://github.com/kebabmane/homechat-integration/issues)
- [HomeChat Discussions](https://github.com/kebabmane/homechat/discussions)

## License

MIT License. See [LICENSE](LICENSE) for details.

[hacs-shield]: https://img.shields.io/badge/HACS-Custom-orange.svg
[hacs-url]: https://github.com/hacs/integration
[version-shield]: https://img.shields.io/github/v/release/kebabmane/homechat-integration
[version-url]: https://github.com/kebabmane/homechat-integration/releases
[license-shield]: https://img.shields.io/github/license/kebabmane/homechat-integration
[license-url]: https://github.com/kebabmane/homechat-integration/blob/main/LICENSE
