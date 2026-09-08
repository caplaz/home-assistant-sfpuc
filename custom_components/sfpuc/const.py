"""Constants for the San Francisco Water Power Sewer integration."""

DOMAIN = "sfpuc"

# Configuration options
CONF_USERNAME = "username"
CONF_PASSWORD = "password"  # nosec B105

# Default configuration values
DEFAULT_UPDATE_INTERVAL = 720  # minutes (12 hours - fixed for daily data)

# Give up on a day-by-day fetch once this many consecutive days fail. A
# broken session fails every remaining day in the window, so continuing
# only hammers the portal with requests that cannot succeed.
MAX_CONSECUTIVE_FETCH_FAILURES = 3

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
