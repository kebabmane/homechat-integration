# Contributing to HomeChat Integration

Thank you for your interest in contributing to the HomeChat Home Assistant Integration!

## Development Setup

### Prerequisites

- Python 3.11+
- Home Assistant development environment
- HomeChat server (for testing)

### Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/kebabmane/homechat-integration.git
   cd homechat-integration
   ```

2. **Copy to Home Assistant**

   ```bash
   cp -r custom_components/homechat /path/to/ha/config/custom_components/
   ```

3. **Enable debug logging**

   ```yaml
   # configuration.yaml
   logger:
     default: info
     logs:
       custom_components.homechat: debug
   ```

4. **Restart Home Assistant**

## Code Structure

```
custom_components/homechat/
├── __init__.py       # Integration setup, API client
├── config_flow.py    # Configuration UI
├── coordinator.py    # Data update coordinator
├── const.py          # Constants
├── sensor.py         # Sensor entities
├── notify.py         # Notification platform
├── conversation.py   # Voice/conversation agent
├── diagnostics.py    # Diagnostics support
├── exceptions.py     # Custom exceptions
├── services.yaml     # Service definitions
├── manifest.json     # Integration metadata
├── strings.json      # UI strings
└── translations/     # Localization
```

## Making Changes

### Code Style

- Follow Home Assistant coding standards
- Use async/await for all I/O operations
- Type hints required for all functions
- Docstrings for public methods

### Testing

```bash
# Test in development mode
hass -c /path/to/config --debug
```

### Service Changes

When adding or modifying services:

1. Update `services.yaml` with schema
2. Add handler in `__init__.py`
3. Update `strings.json` for UI
4. Update translations

### Configuration Flow Changes

1. Modify `config_flow.py`
2. Update `strings.json`
3. Test all configuration paths

## Pull Request Process

1. **Create a branch**

   ```bash
   git checkout -b feature/your-feature
   ```

2. **Make changes**

   - Follow code style guidelines
   - Add/update documentation
   - Test thoroughly

3. **Commit**

   ```bash
   git commit -m "Add feature: description"
   ```

4. **Push and create PR**

   ```bash
   git push origin feature/your-feature
   ```

## Commit Messages

Use clear, descriptive messages:

- `Add: new service for channel management`
- `Fix: webhook signature verification`
- `Update: improve error messages`
- `Docs: add service examples`

## Testing Checklist

Before submitting:

- [ ] Integration loads without errors
- [ ] Configuration flow works
- [ ] All services function correctly
- [ ] Sensors update properly
- [ ] Webhook events fire correctly
- [ ] Error handling is appropriate
- [ ] Debug logging is helpful

## Questions?

- [GitHub Issues](https://github.com/kebabmane/homechat-integration/issues)
- [HomeChat Discussions](https://github.com/kebabmane/homechat/discussions)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
