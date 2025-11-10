# Installation Guide - San Francisco Water Power Sewer

This guide provides detailed step-by-step instructions for installing and configuring the San Francisco Water Power Sewer integration in Home Assistant.

## Prerequisites

Before starting, ensure you have:

- Home Assistant 2023.1.0 or higher
- Admin access to Home Assistant
- Valid SFPUC account credentials (username and password)
- Internet connection for data fetching

## Installation Methods

### Method 1: HACS Installation (Recommended)

HACS (Home Assistant Community Store) is the easiest and most reliable way to install custom integrations.

#### Step 1: Install HACS (if not already installed)

1. Follow the [HACS installation guide](https://hacs.xyz/docs/setup/download)
2. Restart Home Assistant
3. Configure HACS through the integration setup

#### Step 2: Install the Integration

1. **Open HACS**:

   - Go to your Home Assistant sidebar
   - Click on "HACS"

2. **Navigate to Integrations**:

   - Click on "Integrations" tab
   - This shows all available integrations

3. **Search and Install**:

   - Use the search box to find "San Francisco Water Power Sewer"
   - Click on the integration when it appears
   - Click "Download" button
   - Select "Download" in the confirmation dialog
   - Choose the latest version (recommended)

4. **Installation Complete**:
   - You'll see a success message
   - The integration files are now downloaded

#### Step 3: Restart Home Assistant

**Important**: You must restart Home Assistant for the integration to be recognized.

- Go to **Settings** → **System** → **Restart**
- Wait for Home Assistant to fully restart (this may take a few minutes)

### Method 2: Manual Installation

If you prefer manual installation or HACS is not available:

#### Step 1: Download the Integration

Choose one of the following methods:

**Option A: Download from GitHub Releases (Recommended)**

1. Go to [GitHub Releases](https://github.com/caplaz/hass-sfpuc/releases)
2. Download the latest release ZIP file
3. Extract the ZIP file to a temporary location

**Option B: Clone from GitHub**

```bash
# Clone the repository
git clone https://github.com/caplaz/hass-sfpuc.git
cd hass-sfpuc
```

#### Step 2: Copy Files to Home Assistant

```bash
# Copy the integration files
cp -r custom_components/sfpuc /config/custom_components/

# Verify the files were copied
ls -la /config/custom_components/sfpuc/
```

You should see these files:

```
total 64
drwxr-xr-x 2 homeassistant homeassistant  4096 Nov  9 12:00 .
drwxr-xr-x 3 homeassistant homeassistant  4096 Nov  9 12:00 ..
-rw-r--r-- 1 homeassistant homeassistant   847 Nov  9 12:00 __init__.py
-rw-r--r-- 1 homeassistant homeassistant  2655 Nov  9 12:00 config_flow.py
-rw-r--r-- 1 homeassistant homeassistant   745 Nov  9 12:00 const.py
-rw-r--r-- 1 homeassistant homeassistant  1034 Nov  9 12:00 manifest.json
-rw-r--r-- 1 homeassistant homeassistant  2480 Nov  9 12:00 sensor.py
-rw-r--r-- 1 homeassistant homeassistant   123 Nov  9 12:00 version.py
drwxr-xr-x 2 homeassistant homeassistant  4096 Nov  9 12:00 translations
```

#### Step 3: Set Proper Permissions

```bash
# Set ownership to homeassistant user
chown -R homeassistant:homeassistant /config/custom_components/sfpuc/

# Set proper permissions
chmod -R 644 /config/custom_components/sfpuc/
chmod 755 /config/custom_components/sfpuc/
```

#### Step 4: Restart Home Assistant

**Important**: You must restart Home Assistant for the integration to be recognized.

- Go to **Settings** → **System** → **Restart**
- Wait for Home Assistant to fully restart (this may take a few minutes)

## Configuration

### Initial Setup

1. **Access Integration Setup**:

   - Go to **Settings** → **Devices & Services**
   - Click **"Add Integration"** button

2. **Find San Francisco Water Power Sewer**:

   - Type "San Francisco Water Power Sewer" in the search box
   - Click on "San Francisco Water Power Sewer" when it appears

3. **Enter Credentials**:

   - **SFPUC Username**: Your SFPUC account username (account number or email)
   - **SFPUC Password**: Your SFPUC portal password
   - **Update Interval**: How often to fetch data (15-1440 minutes, default 60)

4. **Complete Setup**:
   - Click "Submit"
   - The integration will test your credentials
   - If successful, the sensor will be created

### Configuration Options

After initial setup, you can modify settings:

1. Go to **Settings** → **Devices & Services**
2. Find "San Francisco Water Power Sewer" in your integrations list
3. Click **"Configure"** to change the update interval

## Verification

### Check Installation

After restart, verify the integration is loaded:

1. Go to **Settings** → **Devices & Services**
2. Look for "San Francisco Water Power Sewer" in the integrations list
3. Status should show "Configured" with 1 device

### Check Sensors

The integration creates one sensor:

- **San Francisco Water Power Sewer Daily Usage** (`sensor.sfpuc_daily_usage`)
  - Should show current daily usage in gallons
  - Device class: water
  - State class: total_increasing

### Check Logs

If issues occur, check the logs:

1. Go to **Settings** → **System** → **Logs**
2. Look for entries from `custom_components.sfpuc`
3. Enable debug logging if needed:

```yaml
# Add to configuration.yaml
logger:
  logs:
    custom_components.sfpuc: debug
```

## Troubleshooting

### Common Installation Issues

#### Integration Not Appearing

**Symptoms**: San Francisco Water Power Sewer doesn't show up in the integrations list

**Solutions**:

1. Ensure Home Assistant restarted completely
2. Check file permissions are correct
3. Verify files are in the right location: `/config/custom_components/sfpuc/`
4. Check logs for import errors

#### Authentication Failed

**Symptoms**: Setup fails with "Invalid username or password"

**Solutions**:

1. Verify your SFPUC credentials on the SFPUC website
2. Check for typos in username/password
3. Ensure your SFPUC account is active
4. Try resetting your SFPUC password if needed

#### No Sensor Data

**Symptoms**: Sensor exists but shows "unavailable" or no data

**Solutions**:

1. Check SFPUC website is accessible
2. Verify internet connection
3. Check Home Assistant logs for errors
4. Try reconfiguring the integration

### Advanced Troubleshooting

#### Manual Testing

You can test the integration manually:

```bash
# SSH into Home Assistant
docker exec -it homeassistant bash

# Test Python imports
python3 -c "import custom_components.sfpuc; print('Import successful')"

# Check file structure
ls -la /config/custom_components/sfpuc/
```

#### Debug Mode

Enable detailed logging:

```yaml
# Add to configuration.yaml
logger:
  default: info
  logs:
    custom_components.sfpuc: debug
    homeassistant.components.sensor: debug
```

## Updating

### HACS Updates

If installed via HACS:

1. Go to HACS → Integrations
2. Find "San Francisco Water Power Sewer"
3. Click "Update" if available
4. Restart Home Assistant

### Manual Updates

For manual installations:

1. Download the new version
2. Replace the files in `/config/custom_components/sfpuc/`
3. Restart Home Assistant

## Uninstallation

To remove the integration:

1. Go to **Settings** → **Devices & Services**
2. Find "San Francisco Water Power Sewer" and click it
3. Click **"Delete"** at the bottom
4. Confirm deletion
5. Remove the files: `rm -rf /config/custom_components/sfpuc/`
6. Restart Home Assistant

## Support

If you encounter issues:

1. Check the [troubleshooting section](#troubleshooting) above
2. Review the [GitHub Issues](https://github.com/caplaz/hass-sfpuc/issues)
3. Create a new issue with:
   - Home Assistant version
   - Integration version
   - Error logs
   - Steps to reproduce

## Next Steps

After successful installation:

1. [Configure the Energy Dashboard](https://www.home-assistant.io/docs/energy/)
2. Create automations for water usage alerts
3. Add the sensor to your dashboards
4. Explore historical data in the Energy panel

---

_This integration is not officially affiliated with or endorsed by the San Francisco Public Utilities Commission (SFPUC). Use at your own risk and in accordance with SFPUC's terms of service._
