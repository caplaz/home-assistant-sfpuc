"""SF Water integration for Home Assistant.

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

from .const import DOMAIN
from .coordinator import SFWaterCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SF Water from a config entry."""
    _LOGGER.info("Setting up SF Water integration")

    # Create coordinator for managing updates
    coordinator = SFWaterCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator in entry runtime data (like OPOWER)
    entry.runtime_data = coordinator

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
