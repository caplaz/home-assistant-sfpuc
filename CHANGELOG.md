# Changelog

## 1.0.4 (2025-11-24)

### Bug Fixes

- Add 30-second timeout to all HTTP requests to prevent hanging connections
- Implement retry logic with exponential backoff for network failures
- Improve error handling for connection timeouts and network errors

## 1.0.3 (2025-11-19)

### Bug Fixes

- Add country restriction to US in hacs.json
- Remove invalid filename field from hacs.json

## 1.0.2 (2025-11-18)

### Bug Fixes

- Fix repair dialog "Handler does not support user" error
- Correct repair flow step naming from `repair_confirm` to `confirm_repair`
- Update repair flow method from `async_step_confirm` to `async_step_confirm_repair`

### Improvements

- Add backward compatibility for repair flow translations
- Update all repair flow tests to match new step naming convention
- Remove unnecessary `last_step` parameter from repair form

## 1.0.1 (2025-11-16)

### Enhancements

- Add comprehensive translation strings for repair flow dialog
- Improve repair framework with proper form step indicators

### Improvements

- Add translation strings for repair flow (English and Spanish)
- Include field labels and descriptions for username/password inputs in repair flow
- Add last_step indicator to repair form for proper step completion

### Testing

- Add comprehensive tests for repair issue creation on authentication failure
- Add tests for automatic issue cleanup on successful login
- Verify issue_id and is_fixable parameters are set correctly
- Enhanced coordinator test coverage for repair workflow

## 1.0.0 (2025-11-13)

### Features

- **SFPUC Water Usage Integration**: Monitor San Francisco Public Utilities Commission water usage
- **Historical Data Fetching**: Downloads historical water usage data going back months/years on initial setup
- **Multiple Data Resolutions**: Fetches data at hourly, daily, and monthly intervals
- **Automatic Backfilling**: 30-day lookback window to fill missing data gaps
- **Multi-Resolution Sensors**: Daily, hourly, and monthly usage sensors for comprehensive monitoring
- **SFPUC Portal Integration**: Secure authentication and data scraping from SFPUC portal
- **Energy Dashboard Support**: Automatic statistics insertion for Home Assistant Energy dashboard with multiple resolutions
- **Configuration Flow**: User-friendly setup through Home Assistant UI
- **Multi-language Support**: English and Spanish translations
- **Repairs Framework**: Automatic issue detection and credential repair flow for expired credentials
  - Users notified when credentials become invalid
  - Easy fix flow with credential update form
  - Two-step repair: notification → confirmation
  - Automatic integration reload on successful credential update

### Technical Details

- **Home Assistant 2023.1+**: Compatible with modern Home Assistant installations
- **HACS Compatible**: Proper manifest structure for Home Assistant Community Store
- **Security First**: Secure credential storage and HTTPS-only communications
- **Code Quality**: Comprehensive pre-commit hooks (black, isort, flake8, mypy, bandit, codespell, yamllint)
- **Modular Architecture**: Clean separation between coordinator, sensor, and configuration components
- **Type Safety**: Full type annotations and mypy compliance
- **Intelligent Backfilling**: Periodic checks for missing data with configurable lookback window
- **Resolution-Based Storage**: Proper statistics metadata for each time resolution
- **Enhanced Coordinator**: Historical data fetching on first run with incremental updates
- **Update Frequency**: Fixed 12-hour intervals for daily water usage data (following Home Assistant utility integration patterns)
- **CONFIG_SCHEMA**: Proper config schema for Home Assistant validation compliance

### Requirements

- **Python Dependencies**: requests>=2.25.1, beautifulsoup4>=4.9.3, voluptuous>=0.13.1
- **Home Assistant**: 2023.1.0 or later
- **SFPUC Account**: Valid SFPUC water service account credentials
