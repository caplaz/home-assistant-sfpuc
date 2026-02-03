"""Coordinator for SFPUC integration."""
from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, UPDATE_INTERVAL
from .utils import calculate_water_cost

_LOGGER = logging.getLogger(__name__)


class SFPUCCoordinator(DataUpdateCoordinator):
    """SFPUC data coordinator."""

    def __init__(self, hass: HomeAssistant, config_entry) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=UPDATE_INTERVAL),
        )
        self.config_entry = config_entry

    async def _async_update_data(self):
        """Fetch data from SFPUC and Flo."""
        data = {}

        # Try Flo first for real-time usage
        flo_usage = await self._fetch_flo_usage()
        if flo_usage is not None:
            data["usage"] = flo_usage
            data["cost"] = calculate_water_cost(flo_usage)
        else:
            # Fallback to SFPUC statistics
            sfpuc_usage = await self._fetch_sfpuc_usage()
            if sfpuc_usage is not None:
                data["usage"] = sfpuc_usage
                data["cost"] = calculate_water_cost(sfpuc_usage)

        return data

    async def _fetch_flo_usage(self):
        """Fetch water usage from Flo API."""
        flo_username = self.config_entry.data.get("flo_username")
        flo_password = self.config_entry.data.get("flo_password")

        if not flo_username or not flo_password:
            return None

        try:
            # Placeholder for Flo API integration
            # In real implementation, use pyflowater library
            # from pyflowater import FloClient
            # client = FloClient(flo_username, flo_password)
            # usage = await client.get_current_usage()
            # return usage
            _LOGGER.info("Flo integration placeholder - returning mock data")
            return 15.5  # Mock usage in ccf
        except Exception as err:
            _LOGGER.error("Error fetching Flo data: %s", err)
            return None

    async def _fetch_sfpuc_usage(self):
        """Fetch water usage from SFPUC."""
        username = self.config_entry.data["username"]
        password = self.config_entry.data["password"]

        try:
            # Placeholder for SFPUC API integration
            # In real implementation, use existing SFPUC scraping logic
            _LOGGER.info("SFPUC integration placeholder - returning mock data")
            return 12.3  # Mock usage in ccf
        except Exception as err:
            _LOGGER.error("Error fetching SFPUC data: %s", err)
            return None