# Changelog

## 1.1.0 (2026-11-04)

### New Features & Improvements

- **Data Staleness Visibility**: Expose `data_through` and `data_age_days` attributes on the primary sensor, making collection health transparent in the UI and usable in automations (#9, PR #11)
- **Coordinator Warning on Stale Data**: Log a warning when data age exceeds 4 days (normal 2-day SFPUC lag plus margin), identifying broken collection early (#9, PR #11)

### Bug Fixes

- **Authentication Validation**: Fix false-positive login success when credentials are rejected by checking authoritative landing URLs rather than page text matching "Account" (PR #8)
- **Hourly Fetch Circuit Breaker**: Abort day-by-day historical backfill after 3 consecutive failures to prevent hammering the SFPUC portal with ~93 failed requests per cycle during session or network outages (#10, PR #12)
- **Home Assistant 2026.11 Compatibility**: Specify `unit_class=VolumeConverter.UNIT_CLASS` when creating external statistics to resolve deprecation warnings and ensure compatibility with Home Assistant 2026.11+ (#4, PR #5)

### Contributors

A special thank you to our community contributors for this release:
- @pleasantone for identifying the login false-positive and staleness issues, and contributing PR #8, PR #11, and PR #12
- @joyjit for contributing the Home Assistant 2026.11 `unit_class` compatibility fix in PR #5
- @simX for testing, issue reports, and troubleshooting feedback (#4, #6, #7, #9)

## 1.0.5 (2026-01-30)

### Improvements

- Enhance config flow with detailed data field descriptions for better user guidance
- Improve user onboarding experience with clear field explanations in setup flow
- Add comprehensive data descriptions for username and password fields
- Maintain bilingual support (English/Spanish) for all new field descriptions

### Bug Fixes

- Resolve hassfest translation validation errors by removing invalid description_placeholders
- Fix MyPy type errors by removing invalid unit_class parameters from statistics handler
- Ensure all translation files pass Home Assistant validation requirements

## 1.0.4 (2025-11-24)

### Bug Fixes

- Add 30-second timeout to all HTTP requests to prevent hanging connections
- Implement retry logic with exponential backoff for network failures
- Improve error handling for connection timeouts and network errors

### Improvements

- Refactor repairs flow to use RepairsFlowManager's automatic data injection
- Simplify credential repair to password-only update (username stays unchanged)
- Move repair flow translations to proper `issues.invalid_credentials.fix_flow` location
- Clean up duplicate/unused repair translation steps

### Documentation

- Update README.md for official HACS integration status
- Simplify HACS installation instructions (no longer requires custom repository)
- Update HACS badge to reflect default integration status

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
