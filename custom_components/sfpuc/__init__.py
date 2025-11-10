"""San Francisco Water Power Sewer integration for Home Assistant.

This integration connects to SFPUC (San Francisco Public Utilities Commission)
to monitor water usage data from your account.

The integration provides:
- Sensor entity with daily water usage in gallons
- Historical data storage in Home Assistant database
- Automatic data fetching from SFPUC portal
- Support for multiple languages (English, Spanish)
- Integration with Home Assistant Energy dashboard

Author: caplaz
License: MIT
"""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import SFWaterCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up San Francisco Water Power Sewer from a config entry."""
    _LOGGER.info("Setting up San Francisco Water Power Sewer integration")
    _LOGGER.debug(
        "Config entry data: %s",
        {
            k: "***" if k in ["username", "password"] else v
            for k, v in entry.data.items()
        },
    )

    # Create coordinator for managing updates
    _LOGGER.debug("Creating SFWaterCoordinator")
    coordinator = SFWaterCoordinator(hass, entry)
    _LOGGER.debug("Coordinator created, performing first refresh")
    await coordinator.async_config_entry_first_refresh()
    _LOGGER.info("Coordinator initialized successfully")

    # Store coordinator in entry runtime data
    entry.runtime_data = coordinator
    _LOGGER.debug("Coordinator stored in entry runtime data")

    # Set up platforms
    _LOGGER.debug("Forwarding setup to sensor platform")
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.info("San Francisco Water Power Sewer integration setup completed")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
