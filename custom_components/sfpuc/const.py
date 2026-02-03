"""Constants for the SFPUC integration."""
DOMAIN = "sfpuc"

CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_FLO_USERNAME = "flo_username"
CONF_FLO_PASSWORD = "flo_password"

# SFPUC cost tiers (2023 rates)
TIER_1_LIMIT = 10  # ccf
TIER_2_LIMIT = 20  # ccf
TIER_1_RATE = 2.54  # $/ccf
TIER_2_RATE = 3.50  # $/ccf
TIER_3_RATE = 6.27  # $/ccf

# Sensors
SENSOR_USAGE = "usage"
SENSOR_COST = "cost"

# Update interval
UPDATE_INTERVAL = 12  # hours