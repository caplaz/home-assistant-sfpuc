# San Francisco Water Power Sewer - Development Setup

This directory contains a Docker-based development environment for testing the San Francisco Water Power Sewer Home Assistant integration.

## Prerequisites

- Docker and Docker Compose installed
- Git

## Quick Start

1. **Clone and setup the project:**

   ```bash
   git clone https://github.com/caplaz/hass-sfpuc.git
   cd hass-sfpuc
   ```

2. **Start the development environment:**

   ```bash
   docker-compose up -d
   ```

3. **Access Home Assistant:**

   - Open your browser to `http://localhost:8123`
   - Complete the initial setup wizard
   - The integration will be automatically available

4. **Monitor logs:**
   ```bash
   docker-compose logs -f homeassistant
   ```

## Development Workflow

### Making Code Changes

1. Edit the integration code in `custom_components/sfpuc/`
2. Restart Home Assistant to reload the integration:
   ```bash
   docker-compose restart homeassistant
   ```
3. Check the logs for any errors:
   ```bash
   docker-compose logs homeassistant
   ```

### Testing the Integration

#### Adding the Integration

1. In Home Assistant, go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "San Francisco Water Power Sewer" in the integration list
4. Click on "San Francisco Water Power Sewer" and follow the setup wizard
5. Enter your SFPUC credentials when prompted

#### Checking Integration Status

- Go to **Settings** → **Devices & Services**
- Find "San Francisco Water Power Sewer" in the list
- Click on it to see sensor status and configuration

#### Viewing Sensor Data

- Go to **Settings** → **Dashboards**
- Create a new dashboard or edit existing one
- Add a sensor card for "San Francisco Water Power Sewer Daily Usage"

### Development Environment Features

The development environment includes sample sensors that provide realistic water usage data:

- **San Francisco Water Power Sewer Daily Usage**: Shows current day's water consumption in gallons
- **Historical Data**: Simulated historical usage data for testing trends
- **Real-time Updates**: Data updates every 5 minutes for development testing

### Debugging

#### Enable Debug Logging

Add this to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.sfpuc: debug
```

#### Common Issues

1. **Integration not loading**: Check that `custom_components/sfpuc/` is properly mounted
2. **Login failures**: Verify SFPUC credentials are correct
3. **No data**: Check SFPUC portal availability and credentials
4. **Permission errors**: Ensure proper file permissions in the container

### Code Structure

```
custom_components/sfpuc/
├── __init__.py              # Integration initialization
├── config_flow.py           # Configuration flow for setup
├── const.py                 # Constants and configuration keys
├── manifest.json            # Integration manifest
├── sensor.py                # Sensor entity implementation
├── strings.json             # UI strings for configuration
├── version.py               # Version information
├── translations/            # Localized strings
│   ├── en.json             # English translations
│   └── es.json             # Spanish translations
├── coordinator.py           # Data coordinator with SFPUC scraper implementation
```

### Testing with Real Data

For testing with real SFPUC data:

1. Ensure you have valid SFPUC credentials
2. Configure the integration with real credentials
3. Monitor logs for any authentication or parsing issues
4. Test data updates and historical data retrieval

### Testing with Mock Data

For development without real SFPUC access:

1. Modify `coordinator.py` SFPUCScraper class to return mock data
2. Comment out real login/download code
3. Use static test data for development
4. Test UI and data flow without external dependencies

### Performance Testing

To test performance with large datasets:

1. Modify scraper to return large historical datasets
2. Monitor memory usage and response times
3. Test data processing and storage efficiency
4. Validate sensor update performance

### Security Testing

- Verify credentials are not logged in plain text
- Check HTTPS usage for all SFPUC communications
- Validate input sanitization
- Test error handling without exposing sensitive data

## Docker Environment Details

### Container Configuration

- **Home Assistant**: Latest stable version
- **Python**: 3.11+
- **Base Image**: Official Home Assistant Docker image
- **Volumes**: Persistent configuration and custom components

### Environment Variables

```bash
# Set in docker-compose.yml
TZ=America/Los_Angeles
```

### Network Configuration

- **Port**: 8123 (Home Assistant web interface)
- **Network**: Bridge network for container isolation

## Contributing

### Development Standards

- Follow PEP 8 coding standards
- Add type hints to all functions
- Write comprehensive unit tests
- Update documentation for changes

### Pull Request Process

1. Test changes in development environment
2. Run all automated tests
3. Update documentation if needed
4. Create pull request with detailed description

## Troubleshooting

### Container Issues

```bash
# Stop all containers
docker-compose down

# Rebuild containers
docker-compose build --no-cache

# Start fresh
docker-compose up -d
```

### Integration Issues

1. **Restart Home Assistant**:

   ```bash
   docker-compose restart homeassistant
   ```

2. **Check logs**:

   ```bash
   docker-compose logs homeassistant
   ```

3. **Reinstall integration**:
   - Remove integration from Home Assistant
   - Restart container
   - Re-add integration

### Data Issues

1. **Clear stored data**: Remove integration and re-add
2. **Check SFPUC portal**: Verify manual access works
3. **Network connectivity**: Test internet connection from container

## Advanced Development

### Custom Testing Scenarios

Create custom test scenarios by modifying the scraper to return specific data patterns for testing edge cases.

### Performance Profiling

Use Python profiling tools to identify performance bottlenecks in data processing and sensor updates.

### Memory Leak Testing

Monitor memory usage over extended periods to detect potential memory leaks in long-running scenarios.
