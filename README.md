# HomeChat Home Assistant Integration

A custom Home Assistant integration that connects Home Assistant to HomeChat, enabling two-way communication between your smart home and chat system.

## Features

- **Send notifications** from Home Assistant to HomeChat
- **Two-way communication** via webhooks and bot integration
- **Multiple message types** (notifications, alerts, automations, device updates)
- **Flexible targeting** (send to specific rooms or users)
- **Rich formatting** with priority indicators and timestamps
- **Bot commands** for interactive communication

## Installation

### Manual Installation

1. Copy the `custom_components/homechat` directory to your Home Assistant `custom_components` folder:
   ```
   <ha_config>/custom_components/homechat/
   ```

2. Restart Home Assistant

3. Go to **Settings** > **Devices & Services** > **Add Integration**

4. Search for "HomeChat" and click to configure

### HACS Installation

1. Add this repository to HACS as a custom repository
2. Install the HomeChat integration through HACS
3. Restart Home Assistant
4. Configure the integration via the UI

## Configuration

### Prerequisites

1. **HomeChat Server**: Running HomeChat addon or standalone instance
2. **API Token**: Generate an API token in HomeChat (requires admin access)
3. **Network Access**: Home Assistant must be able to reach HomeChat server

### Setup Steps

1. **Add Integration**:
   - Go to Settings > Devices & Services > Add Integration
   - Search for "HomeChat"
   - Enter your HomeChat server details

2. **Server Configuration**:
   - **Host**: HomeChat server hostname or IP
   - **Port**: HomeChat port (default: 3000)
   - **SSL**: Enable if using HTTPS
   - **API Token**: Your generated API token

3. **Bot Configuration**:
   - **Bot Username**: Name for Home Assistant bot in HomeChat
   - **Enable Two-way Communication**: Allows HomeChat to send messages back

## Usage

### Sending Notifications

Use the `notify.homechat` service to send messages:

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

### Service Calls

#### `homechat.send_message`
Send a basic message to HomeChat:

```yaml
service: homechat.send_message
data:
  message: "Kitchen light turned on"
  room_id: "home-automation"
  title: "Device Update"
```

#### `homechat.send_notification`
Send a formatted notification:

```yaml
service: homechat.send_notification
data:
  message: "Garage door has been open for 30 minutes"
  title: "Reminder"
  priority: "normal"
  room_id: "general"
```

#### `homechat.create_bot`
Create a new bot in HomeChat:

```yaml
service: homechat.create_bot
data:
  name: "weather_bot"
  description: "Provides weather updates"
  webhook_id: "weather-webhook-123"
```

### Automation Examples

#### Motion Detection Alert
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

#### Device Offline Notification
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

#### Daily Summary
```yaml
automation:
  - alias: "Daily Summary"
    trigger:
      platform: time
      at: "22:00:00"
    action:
      service: homechat.send_message
      data:
        message: >
          📊 **Daily Summary**
          • Lights: {{ states.light | selectattr('state', 'eq', 'on') | list | length }} on
          • Sensors: {{ states.binary_sensor | selectattr('state', 'eq', 'on') | list | length }} active
          • Temperature: {{ states('sensor.living_room_temperature') }}°C
        title: "End of Day Report"
        room_id: "daily-reports"
```

### Two-Way Communication

When two-way communication is enabled, HomeChat can send messages back to Home Assistant via webhooks.

#### Webhook Events

The integration fires these events that can be used in automations:

- `homechat_message_received`: Any message from HomeChat
- `homechat_bot_message`: Bot-specific messages

#### Event Automation Example
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
      service: light.turn_off
      target:
        entity_id: all
```

### Message Types and Formatting

The integration supports different message types with automatic formatting:

#### Priority Levels
- **urgent**: 🚨 **URGENT** prefix
- **high**: ⚠️ **HIGH PRIORITY** prefix  
- **normal**: Standard formatting
- **low**: ℹ️ prefix

#### Message Types
- **notification**: 🏠 prefix with title
- **alert**: 🔔 **ALERT** prefix
- **automation**: 🤖 **Automation** prefix
- **device**: 📱 device name prefix
- **security**: 🔒 **Security** prefix

## Troubleshooting

### Common Issues

**Integration fails to connect**
- Verify HomeChat server is running and accessible
- Check host, port, and SSL settings
- Ensure API token is valid

**Messages not appearing in HomeChat**
- Check that the target room exists or can be auto-created
- Verify API token has necessary permissions
- Check Home Assistant logs for errors

**Webhooks not working**
- Ensure two-way communication is enabled
- Check that HomeChat can reach Home Assistant
- Verify webhook ID is properly configured

### Debug Logging

Enable debug logging in `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.homechat: debug
```

### API Token Setup

1. In HomeChat, go to Admin Settings
2. Generate a new API token
3. Copy the token and use it in Home Assistant integration setup
4. Ensure the admin user has necessary permissions

## Development

### Local Development Setup

1. Clone this repository
2. Copy to Home Assistant custom_components directory
3. Configure HomeChat with API endpoints
4. Set up development environment with proper logging

### Testing

Test the integration using Home Assistant's developer tools:

1. Go to Developer Tools > Services
2. Test `homechat.send_message` and `notify.homechat` services
3. Check logs for any errors

## Support

For issues and feature requests:
- Check the [GitHub repository](https://github.com/your-username/homechat-integration)
- Review Home Assistant logs for error details
- Ensure HomeChat server is compatible with the integration

## License

This project is licensed under the MIT License.