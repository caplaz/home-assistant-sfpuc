# San Francisco Water Power Sewer for Home Assistant

[![hacs][hacsbadge]][hacs]
[![GitHub Release][releases-shield]][releases]
[![CI][ci-shield]][ci]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

A Home Assistant custom integration for monitoring San Francisco water usage from SFPUC (San Francisco Public Utilities Commission). This integration connects to your SFPUC account to fetch historical water usage data and provides it as sensors in Home Assistant.

![San Francisco Water Power Sewer][logo]

## ⚠️ Important Disclaimer

**This project is not affiliated with or endorsed by the San Francisco Public Utilities Commission (SFPUC) or https://www.sfpuc.gov.**

This is an unofficial, community-maintained integration that scrapes data from the SFPUC website. As such:

- **It can break at any time** due to changes in SFPUC's website structure, authentication methods, or data formats
- **Use at your own risk** - the integration may stop working without notice
- **No guarantees** of functionality, accuracy, or continued operation
- **Not responsible for any issues** that may arise from using this integration
- **Please use responsibly** and in accordance with SFPUC's terms of service

If the integration stops working, please check the [GitHub Issues](https://github.com/caplaz/hass-sfpuc/issues) for updates or create a new issue.

## How It Works

### Data Flow Overview

The San Francisco Water Power Sewer integration provides comprehensive historical utility data for the Home Assistant Energy dashboard, with multiple data resolutions.

```
SFPUC Portal → Integration → Home Assistant → Energy Dashboard
      ↓              ↓              ↓              ↓
   Login/Auth    Scrape Data    Store Data    Visualize Usage
   Historical    Multiple       Statistics     Trends &
   Data          Resolutions    Database       Analytics
```

### Step-by-Step Process

1. **Authentication** 🔐

   - Integration logs into your SFPUC account using provided credentials
   - Maintains secure session for data access
   - Handles authentication errors gracefully

2. **Historical Data Fetching** 📊

   - **Initial Setup**: Downloads 2 years of monthly data, 90 days of daily data, 30 days of hourly data
   - **Multiple Resolutions**: Fetches data at hourly, daily, and monthly intervals
   - **Backfilling**: Automatically fills missing data with 30-day lookback window
   - **Incremental Updates**: Adds new data points as they become available
   - **Smart Optimization**: Skips historical fetch on subsequent restarts if data exists

3. **Data Processing** ⚙️

   - Converts raw SFPUC Excel data into structured Home Assistant sensor format
   - Applies proper device classes and state classes for each resolution
   - Calculates cumulative usage for accurate tracking across all time periods

4. **Statistics Insertion** 📈

   - Inserts usage data into Home Assistant's recorder database at multiple resolutions
   - Creates consolidated statistics streams for comprehensive historical analysis
   - Enables Energy dashboard integration with proper cumulative sum calculations
   - Supports long-term usage trends and comparative analysis

5. **Sensor Updates** 🔄
   - Updates sensors with latest data from each resolution
   - Provides real-time data to dashboards and automations
   - Maintains data availability and handles connection issues

6. **Credential Management** 🔐
   - Automatic detection of credential expiration
   - Home Assistant repair notifications when credentials fail
   - Easy fix flow for updating credentials
   - Automatic integration reload on successful update

### Energy Dashboard Integration

This integration enables comprehensive water usage tracking in Home Assistant's Energy dashboard:

- **Multi-Resolution Data**: Hourly, daily, and monthly usage statistics
- **Historical Data**: Past usage data going back months/years
- **Backfilling**: Automatic gap-filling for missing data points
- **Statistics**: Proper statistics metadata for dashboard calculations
- **Cost Tracking**: Foundation for future cost calculation features
- **Comparative Analysis**: Track usage patterns across different time scales

### Credential Management

The integration monitors your SFPUC credentials and automatically alerts you when they need to be updated:

- **Automatic Detection**: Detects login failures and credential issues
- **Repair Notifications**: Shows notifications in Home Assistant UI
- **Easy Fix Flow**: Two-step repair process with credential update form
- **Automatic Testing**: Tests new credentials before saving
- **Auto-reload**: Integration automatically reloads after credential update

### Update Cycle

- **Frequency**: Fixed 12-hour intervals (appropriate for daily water usage data)
- **Historical Fetching**: Comprehensive data download on first setup only
- **Backfilling**: 30-day lookback window for missing data (runs periodically)
- **Pattern**: Follows Home Assistant utility integration best practices
- **Trigger**: Time-based coordinator updates with intelligent backfilling
- **Scope**: Fetches current data plus fills historical gaps
- **Storage**: All data stored locally in Home Assistant database with multiple resolutions

## Installation

### Method 1: HACS (Recommended)

HACS (Home Assistant Community Store) is the easiest way to install and manage custom integrations.

#### Prerequisites

- [HACS](https://hacs.xyz/) must be installed in your Home Assistant instance
- Home Assistant version 2023.1.0 or higher
- Valid SFPUC account credentials

#### Installation Steps

1. **Open HACS**: Go to HACS in your Home Assistant sidebar
2. **Navigate to Integrations**: Click on "Integrations"
3. **Add Custom Repository**:
   - Click the three dots menu (⋮) in the top right
   - Select "Custom repositories"
   - Add repository: `https://github.com/caplaz/hass-sfpuc`
   - Category: `Integration`
   - Click "Add"
4. **Search and Install**:
   - Search for "San Francisco Water Power Sewer" in HACS
   - Click on it and select "Download"
   - Choose the latest version
5. **Restart Home Assistant**: Required for the integration to load

### Method 2: Manual Installation

#### Prerequisites

- Home Assistant version 2023.1.0 or higher
- Valid SFPUC account credentials

#### Installation Steps

1. **Download the Integration**:

   ```bash
   wget https://github.com/caplaz/hass-sfpuc/archive/refs/tags/v1.0.0.zip
   unzip v1.0.0.zip
   ```

2. **Copy Files**:

   ```bash
   cp -r hass-sfpuc-1.0.0/custom_components/sfpuc /config/custom_components/
   ```

3. **Restart Home Assistant**:
   - Go to Settings → System → Restart
   - Wait for Home Assistant to restart

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a list of changes and version history.

## Configuration

### Initial Setup

1. **Add Integration**: Go to Settings → Devices & Services → Add Integration
2. **Search**: Type "San Francisco Water Power Sewer" in the search box
3. **Select**: Click on "San Francisco Water Power Sewer" from the results
4. **Configure**:
   - **SFPUC Username**: Your SFPUC account username (typically account number or email)
   - **SFPUC Password**: Your SFPUC portal password
5. **Submit**: The integration will test your credentials and create the sensor

### Usage

### Sensors Created

The integration creates a single primary sensor that displays current billing period water usage:

- **San Francisco Water Power Sewer** (`sensor.sfpuc_water_account_{account}_current_bill_water_usage_to_date`)

  - **State**: Current billing period cumulative water usage in gallons (from last bill date to today)
  - **Device Class**: `water`
  - **State Class**: None (statistics-only approach)
  - **Unit**: `gal` (gallons)
  - **Update**: Every 12 hours
  - **Statistics**: Links to underlying `sfpuc:{account}_water_consumption` statistics for historical data

### Historical Data Access

Historical water usage data is stored in Home Assistant statistics, not in sensor state history:

- **Statistics ID**: `sfpuc:{account}_water_consumption`
- **Data Resolutions**: Hourly, daily, and monthly statistics
- **Time Range**: Up to 2+ years of historical data
- **Access Methods**:
  - Energy Dashboard (recommended)
  - Developer Tools → Statistics
  - Custom dashboard cards (ApexCharts, etc.)
  - History graphs (statistics mode)

### Dashboard Integration

#### Add to Energy Dashboard

The integration enables water usage monitoring in the Energy dashboard:

1. **Navigate to Energy Dashboard**: Settings → Dashboards → Energy
2. **Add Water Consumption**:
   - Click "Add Consumption" (water usage is consumption)
   - Select `sensor.sfpuc_water_account_{account}_current_bill_water_usage_to_date`
   - Configure display preferences
3. **View Historical Data**: The dashboard will show water usage trends over time using underlying statistics
4. **Statistics Integration**: Historical data is automatically stored for long-term analysis

#### Add Sensor Card

For detailed monitoring, add a sensor card to your dashboard:

1. **Add Card**: Dashboard → Add Card → Sensor
2. **Select Sensor**: Choose `sensor.sfpuc_water_account_{account}_current_bill_water_usage_to_date`
3. **Customize**: Set display options, icons, and graph preferences
4. **Historical View**: Enable graph to see usage patterns

#### View Historical Statistics

To view detailed historical data beyond the Energy Dashboard:

1. **Developer Tools**: Go to Developer Tools → Statistics
2. **Find Statistics**: Search for `sfpuc:{account}_water_consumption`
3. **View Data**: Browse hourly, daily, and monthly usage statistics
4. **Custom Cards**: Use statistics in custom dashboard cards for advanced visualizations

### Data Storage & Privacy

- **Local Storage**: All data stored in Home Assistant's local database
- **Statistics Storage**: Historical data stored in recorder statistics, not sensor state history
- **No External Dependencies**: Data processing happens entirely locally
- **Historical Preservation**: Full usage history maintained for analysis
- **Secure Credentials**: SFPUC credentials encrypted and stored securely
- **Statistics Access**: Historical data available through Developer Tools → Statistics

## Troubleshooting

### Common Issues

#### Authentication Failed

- **Cause**: Invalid username/password or SFPUC portal changes
- **Solution**: Verify your SFPUC credentials and try reconfiguring the integration

#### No Data in Energy Dashboard

- **Cause**: Statistics sum values were missing (fixed in v1.0.0+)
- **Solution**: Clear existing statistics and restart Home Assistant to re-insert data with proper sums

#### No Historical Data Visible

- **Cause**: Historical data is stored in statistics, not sensor history
- **Solution**: Use Developer Tools → Statistics or Energy Dashboard to view historical data

#### Sensor Unavailable

- **Cause**: Integration unable to fetch data
- **Solution**: Check Home Assistant logs for error messages

#### Slow Startup

- **Cause**: Historical data fetching on first setup
- **Solution**: This is normal for the first run; subsequent restarts will be faster

### Debug Logging

Enable debug logging to troubleshoot issues:

```yaml
logger:
  logs:
    custom_components.sfpuc: debug
```

## Technical Details

### Architecture Overview

The integration follows Home Assistant best practices with a modern statistics-first architecture:

- **Coordinator Pattern**: Manages data fetching and updates with dummy listener for reliability
- **Statistics-First Approach**: Historical data stored in recorder statistics, sensor shows current billing period
- **Single Sensor Entity**: One primary sensor per account displaying cumulative billing period usage
- **Multi-Resolution Statistics**: Hourly, daily, and monthly data stored in consolidated statistics streams
- **Smart Historical Fetching**: Downloads comprehensive data on first setup, skips on subsequent restarts
- **Config Flow**: User-friendly setup and configuration
- **Error Handling**: Graceful failure recovery and logging

### Recent Improvements

#### v1.0.0+ (Latest)

- **✅ Single Sensor Architecture**: Consolidated to one primary sensor per account
- **✅ Statistics Sum Fix**: Fixed cumulative sum calculations for proper Energy Dashboard display
- **✅ Timezone Bug Fix**: Corrected timestamp handling for San Francisco local time
- **✅ Startup Optimization**: Deferred historical data fetching to background, preventing slow startups
- **✅ Smart Re-fetch Prevention**: Checks for existing data to avoid redundant downloads on restart
- **✅ Monthly Historical Data**: Enabled billing cycle data for comprehensive historical analysis
- **✅ Type Safety**: Fixed mypy type errors and improved code quality

### Requirements

- **Python Packages**:
  - `requests>=2.25.1`
  - `beautifulsoup4>=4.9.3`
  - `voluptuous>=0.13.1`

### Supported Languages

- English (en)
- Spanish (es)

### API Usage

- Connects to SFPUC portal using secure HTTPS
- Downloads Excel files containing usage data
- Parses data locally without external API calls
- Respects SFPUC's terms of service and rate limits

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/caplaz/hass-sfpuc.git
   cd hass-sfpuc
   ```

2. Install development dependencies:

   ```bash
   pip install -r requirements-dev.txt
   ```

3. Run tests:
   ```bash
   python -m pytest
   ```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<!-- Badges -->

[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/caplaz/hass-sfpuc.svg?style=for-the-badge
[releases]: https://github.com/caplaz/hass-sfpuc/releases
[ci-shield]: https://img.shields.io/github/actions/workflow/status/caplaz/hass-sfpuc/ci.yml?style=for-the-badge
[ci]: https://github.com/caplaz/hass-sfpuc/actions/workflows/ci.yml
[commits-shield]: https://img.shields.io/github/commit-activity/m/caplaz/hass-sfpuc?style=for-the-badge
[commits]: https://github.com/caplaz/hass-sfpuc/commits/main
[license-shield]: https://img.shields.io/github/license/caplaz/hass-sfpuc.svg?style=for-the-badge
[logo]: https://www.sfpuc.gov/themes/custom/sfwater/img/scm_logo.svg
