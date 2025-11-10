# San Francisco Water Power Sewer for Home Assistant

[![hacs][hacsbadge]][hacs]
[![GitHub Release][releases-shield]][releases]
[![CI][ci-shield]][ci]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

A Home Assistant custom integration for monitoring San Francisco water usage from SFPUC (San Francisco Public Utilities Commission). This integration connects to your SFPUC account to fetch historical water usage data and provides it as sensors in Home Assistant.

![San Francisco Water Power Sewer][logo]

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

2. **Historical Data Fetching** �

   - **Initial Setup**: Downloads 2 years of monthly data, 90 days of daily data, 30 days of hourly data
   - **Multiple Resolutions**: Fetches data at hourly, daily, and monthly intervals
   - **Backfilling**: Automatically fills missing data with 30-day lookback window
   - **Incremental Updates**: Adds new data points as they become available

3. **Data Processing** ⚙️

   - Converts raw SFPUC Excel data into structured Home Assistant sensor format
   - Applies proper device classes and state classes for each resolution
   - Calculates cumulative usage for accurate tracking across all time periods

4. **Statistics Insertion** 📈

   - Inserts usage data into Home Assistant's recorder database at multiple resolutions
   - Creates separate statistics streams for hourly, daily, and monthly data
   - Enables comprehensive historical analysis and Energy dashboard integration
   - Supports long-term usage trends and comparative analysis

5. **Sensor Updates** 🔄
   - Updates sensors with latest data from each resolution
   - Provides real-time data to dashboards and automations
   - Maintains data availability and handles connection issues

### Energy Dashboard Integration

This integration enables comprehensive water usage tracking in Home Assistant's Energy dashboard:

- **Multi-Resolution Data**: Hourly, daily, and monthly usage statistics
- **Historical Data**: Past usage data going back months/years
- **Backfilling**: Automatic gap-filling for missing data points
- **Statistics**: Proper statistics metadata for dashboard calculations
- **Cost Tracking**: Foundation for future cost calculation features
- **Comparative Analysis**: Track usage patterns across different time scales

### Update Cycle

- **Frequency**: Fixed 12-hour intervals (appropriate for daily water usage data)
- **Historical Fetching**: Comprehensive data download on first setup
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
3. **Search and Install**:
   - Search for "San Francisco Water Power Sewer" in HACS
   - Click on it and select "Download"
   - Choose the latest version
4. **Restart Home Assistant**: Required for the integration to load

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

The integration creates multiple sensors for different time resolutions:

- **San Francisco Water Power Sewer Daily Usage** (`sensor.sfpuc_daily_usage`)

  - **State**: Daily water usage in gallons
  - **Device Class**: `water`
  - **State Class**: `total_increasing`
  - **Unit**: `gal` (gallons)
  - **Update**: Every 12 hours

- **San Francisco Water Power Sewer Hourly Usage** (`sensor.sfpuc_hourly_usage`)

  - **State**: Most recent hourly water usage in gallons
  - **Device Class**: `water`
  - **State Class**: `total_increasing`
  - **Unit**: `gal` (gallons)
  - **Update**: Every 12 hours

- **San Francisco Water Power Sewer Monthly Usage** (`sensor.sfpuc_monthly_usage`)
  - **State**: Current month-to-date water usage in gallons
  - **Device Class**: `water`
  - **State Class**: `total_increasing`
  - **Unit**: `gal` (gallons)
  - **Update**: Every 12 hours

### Dashboard Integration

#### Add to Energy Dashboard

The integration enables water usage monitoring in the Energy dashboard:

1. **Navigate to Energy Dashboard**: Settings → Dashboards → Energy
2. **Add Water Consumption**:
   - Click "Add Consumption" (water usage is consumption)
   - Select `sensor.sfpuc_daily_usage`
   - Configure display preferences
3. **View Historical Data**: The dashboard will show water usage trends over time
4. **Statistics Integration**: Historical data is automatically stored for long-term analysis

#### Add Sensor Card

For detailed monitoring, add a sensor card to your dashboard:

1. **Add Card**: Dashboard → Add Card → Sensor
2. **Select Sensor**: Choose `sensor.sfpuc_daily_usage`
3. **Customize**: Set display options, icons, and graph preferences
4. **Historical View**: Enable graph to see usage patterns

### Data Storage & Privacy

- **Local Storage**: All data stored in Home Assistant's local database
- **No External Dependencies**: Data processing happens entirely locally
- **Historical Preservation**: Full usage history maintained for analysis
- **Secure Credentials**: SFPUC credentials encrypted and stored securely
- **Statistics**: Data inserted into Home Assistant recorder for Energy dashboard

## Troubleshooting

### Common Issues

#### Authentication Failed

- **Cause**: Invalid username/password or SFPUC portal changes
- **Solution**: Verify your SFPUC credentials and try reconfiguring the integration

#### No Data Updates

- **Cause**: SFPUC portal issues or network connectivity
- **Solution**: Check SFPUC website manually and verify internet connection

#### Sensor Unavailable

- **Cause**: Integration unable to fetch data
- **Solution**: Check Home Assistant logs for error messages

### Debug Logging

Enable debug logging to troubleshoot issues:

```yaml
logger:
  logs:
    custom_components.sfpuc: debug
```

## Technical Details

### Architecture Overview

The integration follows Home Assistant best practices with a modern architecture:

- **Coordinator Pattern**: Manages data fetching and updates
- **Entity Descriptions**: Modern sensor implementation with descriptions
- **Statistics Integration**: Inserts data into Home Assistant recorder
- **Config Flow**: User-friendly setup and configuration
- **Error Handling**: Graceful failure recovery and logging

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

## Support

- **Issues**: [GitHub Issues](https://github.com/caplaz/hass-sfpuc/issues)
- **Discussions**: [GitHub Discussions](https://github.com/caplaz/hass-sfpuc/discussions)
- **Documentation**: [Full Documentation](https://github.com/caplaz/hass-sfpuc/wiki)

## Credits

- **Author**: caplaz
- **Inspired by**: Other utility monitoring integrations
- **SFPUC**: San Francisco Public Utilities Commission for providing water service data

---

## ⚠️ Important Disclaimer

**This project is not affiliated with or endorsed by the San Francisco Public Utilities Commission (SFPUC) or https://www.sfpuc.gov.**

This is an unofficial, community-maintained integration that scrapes data from the SFPUC website. As such:

- **It can break at any time** due to changes in SFPUC's website structure, authentication methods, or data formats
- **Use at your own risk** - the integration may stop working without notice
- **No guarantees** of functionality, accuracy, or continued operation
- **Not responsible for any issues** that may arise from using this integration
- **Please use responsibly** and in accordance with SFPUC's terms of service

If the integration stops working, please check the [GitHub Issues](https://github.com/caplaz/hass-sfpuc/issues) for updates or create a new issue.
