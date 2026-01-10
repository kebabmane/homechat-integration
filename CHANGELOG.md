# Changelog

All notable changes to the HomeChat Home Assistant Integration are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2025-01-10

### Added
- Image attachment support for `send_message` service
- HA Core 2026 compatibility fixes
- Comprehensive quality improvements

### Fixed
- Bot creation API handling
- Notify data handling edge cases

## [1.1.0] - 2025-01-09

### Added
- Zeroconf/mDNS auto-discovery support
- Dynamic channel target selection
- Improved error handling

### Fixed
- Critical bug fixes for webhook handling
- API response parsing improvements

## [1.0.1] - 2025-01-08

### Added
- HACS configuration file
- Additional service parameters

### Fixed
- Configuration flow validation
- Token authentication edge cases

## [1.0.0] - 2025-01-07

### Added

#### Core Features
- `notify.homechat` notification service
- `homechat.send_message` service
- `homechat.send_notification` service
- `homechat.create_bot` service
- `homechat.send_dm` direct message service
- `homechat.list_channels` service
- `homechat.join_channel` and `leave_channel` services
- `homechat.search` service

#### Integration Features
- Bearer token API authentication
- Webhook-based two-way communication
- HMAC-SHA256 signature verification
- Configurable bot username
- SSL/TLS support

#### Entities
- Server status sensor
- Channel count sensor
- Device grouping under "HomeChat Server"

#### Events
- `homechat_message_received` for all messages
- `homechat_bot_message` for bot-specific messages

#### Configuration
- UI-based configuration flow
- Zeroconf auto-discovery
- Reconfiguration support
- Connection testing

### Technical Details
- Home Assistant 2024.1.0+ required
- Python 3.11+ compatibility
- Async/await patterns throughout
- Comprehensive error handling
