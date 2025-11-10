"""Test fixtures and utilities."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest


@pytest.fixture
def config_entry():
    """Create a mock config entry."""
    from .common import MockConfigEntry

    return MockConfigEntry()


@pytest.fixture
def mock_scraper():
    """Create a mock SFPUC scraper."""
    with patch("custom_components.sfpuc.coordinator.SFPUCScraper") as mock:
        scraper = Mock()
        mock.return_value = scraper
        scraper.login.return_value = True
        scraper.get_usage_data.return_value = [
            {
                "timestamp": datetime(2023, 10, 1, 10, 0),
                "usage": 50.0,
                "resolution": "hourly",
            }
        ]
        yield scraper


@pytest.fixture
def mock_coordinator(hass, config_entry, mock_scraper):
    """Create a mock coordinator."""
    with patch("custom_components.sfpuc.coordinator.SFWaterCoordinator") as mock:
        coordinator = Mock()
        mock.return_value = coordinator
        coordinator.config_entry = config_entry
        coordinator.data = {
            "daily_usage": 150.0,
            "hourly_usage": 25.0,
            "monthly_usage": 1200.0,
        }
        coordinator.async_config_entry_first_refresh = AsyncMock()
        yield coordinator


@pytest.fixture(autouse=True)
def setup_hass_data(hass):
    """Set up Home Assistant data structure for the integration."""
    from homeassistant.components.recorder import DATA_INSTANCE

    from custom_components.sfpuc.const import DOMAIN

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    if "logger" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["logger"] = Mock()

    # Mock recorder instance availability for statistics insertion
    if DATA_INSTANCE not in hass.data:
        hass.data[DATA_INSTANCE] = Mock()
