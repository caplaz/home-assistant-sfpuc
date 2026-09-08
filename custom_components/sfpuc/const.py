"""Constants for the San Francisco Water Power Sewer integration."""

DOMAIN = "sfpuc"

# Configuration options
CONF_USERNAME = "username"
CONF_PASSWORD = "password"  # nosec B105

# Default configuration values
DEFAULT_UPDATE_INTERVAL = 720  # minutes (12 hours - fixed for daily data)

# SFPUC publishes meter readings a couple of days in arrears, so even a
# perfectly healthy integration is always this far behind.
EXPECTED_DATA_LAG_DAYS = 2
# Warn once the newest reading is older than this. Anything beyond the
# normal lag plus a margin means collection has stopped.
MAX_EXPECTED_DATA_LAG_DAYS = 4

# Sensor data keys
KEY_DAILY_USAGE = "daily_usage"
KEY_LAST_UPDATED = "last_updated"

# Sensor types configuration
SENSOR_TYPES = {
    "daily_usage": {
        "name": "Daily Water Usage",
        "unit": "gal",
        "icon": "mdi:water",
        "device_class": "water",
    },
}
