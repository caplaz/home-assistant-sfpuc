# SF Water for Home Assistant

[![hacs][hacsbadge]][hacs]
[![GitHub Release][releases-shield]][releases]
[![CI][ci-shield]][ci]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

A Home Assistant custom integration for monitoring San Francisco water usage from SFPUC (San Francisco Public Utilities Commission). This integration connects to your SFPUC account to fetch historical water usage data and provides it as sensors in Home Assistant.

![SF Water][logo]

## How It Works

### Data Flow Overview

The SF Water integration provides historical utility data for the Home Assistant Energy dashboard, following modern smart home integration patterns.

```
SFPUC Portal → Integration → Home Assistant → Energy Dashboard
      ↓              ↓              ↓              ↓
   Login/Auth    Scrape Data    Store Data    Visualize Usage
```

### Step-by-Step Process

1. **Authentication** 🔐

   - Integration logs into your SFPUC account using provided credentials
   - Maintains secure session for data access
   - Handles authentication errors gracefully

2. **Data Fetching** 📊

   - Connects to SFPUC's hourly usage page
   - Downloads Excel files containing water usage data
   - Parses data locally on your Home Assistant instance
   - Extracts daily water consumption in gallons

3. **Data Processing** ⚙️

   - Converts raw SFPUC data into Home Assistant sensor format
   - Applies proper device class (`water`) and state class (`total_increasing`)
   - Calculates cumulative usage for accurate tracking

4. **Statistics Insertion** 📈

   - Inserts usage data into Home Assistant's recorder database
   - Creates historical statistics for Energy dashboard integration
   - Enables long-term usage analysis and trends

5. **Sensor Updates** 🔄
   - Updates sensor state with latest daily usage
   - Provides real-time data to dashboards and automations
   - Maintains data availability and handles connection issues

### Energy Dashboard Integration

This integration enables water usage tracking in Home Assistant's Energy dashboard:

- **Historical Data**: Past usage data is stored and accessible
- **Statistics**: Proper statistics metadata for dashboard calculations
- **Cost Tracking**: Foundation for future cost calculation features
- **Comparative Analysis**: Track usage patterns over time

### Update Cycle

- **Frequency**: Configurable (15-1440 minutes, default 60 minutes)
- **Trigger**: Time-based coordinator updates
- **Scope**: Fetches current daily usage (historical data via statistics)
- **Storage**: All data stored locally in Home Assistant database

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
   - Search for "SF Water" in HACS
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
   cp -r hass-sfpuc-1.0.0/custom_components/sf_water /config/custom_components/
   ```

3. **Restart Home Assistant**:
   - Go to Settings → System → Restart
   - Wait for Home Assistant to restart

## Configuration

### Initial Setup

1. **Add Integration**: Go to Settings → Devices & Services → Add Integration
2. **Search**: Type "SF Water" in the search box
3. **Select**: Click on "SF Water" from the results
4. **Configure**:
   - **SFPUC Username**: Your SFPUC account username (typically account number or email)
   - **SFPUC Password**: Your SFPUC portal password
   - **Update Interval**: How often to fetch data (15-1440 minutes, default 60)
5. **Submit**: The integration will test your credentials and create the sensor

### Configuration Options

After setup, you can modify settings by:

1. Going to Settings → Devices & Services
2. Finding "SF Water" in your integrations list
3. Clicking "Configure" to change the update interval

## Usage

### Sensors Created

The integration creates one main sensor:

- **SF Water Daily Usage** (`sensor.sf_water_daily_usage`)
  - **State**: Daily water usage in gallons
  - **Device Class**: `water`
  - **State Class**: `total_increasing`
  - **Unit**: `gal` (gallons)

### Dashboard Integration

#### Add to Energy Dashboard

The integration enables water usage monitoring in the Energy dashboard:

1. **Navigate to Energy Dashboard**: Settings → Dashboards → Energy
2. **Add Water Consumption**:
   - Click "Add Consumption" (water usage is consumption)
   - Select `sensor.sf_water_daily_usage`
   - Configure display preferences
3. **View Historical Data**: The dashboard will show water usage trends over time
4. **Statistics Integration**: Historical data is automatically stored for long-term analysis

#### Add Sensor Card

For detailed monitoring, add a sensor card to your dashboard:

1. **Add Card**: Dashboard → Add Card → Sensor
2. **Select Sensor**: Choose `sensor.sf_water_daily_usage`
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
    custom_components.sf_water: debug
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

_This integration is not officially affiliated with or endorsed by the San Francisco Public Utilities Commission (SFPUC). Use at your own risk and in accordance with SFPUC's terms of service._
