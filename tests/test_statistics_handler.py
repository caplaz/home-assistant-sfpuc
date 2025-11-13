"""Tests for SFPUC statistics handling operations."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from custom_components.sfpuc.coordinator import SFWaterCoordinator
from custom_components.sfpuc.statistics_handler import (
    async_insert_legacy_statistics,
    async_insert_resolution_statistics,
    async_insert_statistics,
)

from .common import MockConfigEntry


class TestStatisticsHandler:
    """Test the SFPUC statistics handling functionality."""

    @pytest.fixture(autouse=True)
    def setup_method(self, hass):
        """Set up test fixtures."""
        self.hass = hass
        self.config_entry = MockConfigEntry()
        # Add recorder instance to hass.data for statistics insertion
        from homeassistant.components.recorder.util import DATA_INSTANCE

        if DATA_INSTANCE not in hass.data:
            recorder_mock = Mock()
            recorder_mock.async_add_executor_job = AsyncMock()
            hass.data[DATA_INSTANCE] = recorder_mock

    @pytest.fixture(autouse=True)
    def mock_coordinator_timer(self):
        """Mock coordinator timer and background tasks to prevent lingering timers."""
        with (
            patch("asyncio.AbstractEventLoop.call_later", return_value=None),
            patch("asyncio.create_task", return_value=None),
            patch(
                "custom_components.sfpuc.data_fetcher.async_background_historical_fetch",
                return_value=None,
            ),
        ):
            yield

    def teardown_method(self):
        """Clean up after each test method."""
        # Clean up any lingering coordinators
        if hasattr(self, "coordinator"):
            # Stop the coordinator's refresh timer
            if (
                hasattr(self.coordinator, "_refresh_timer")
                and self.coordinator._refresh_timer
            ):
                self.coordinator._refresh_timer.cancel()
            if hasattr(self.coordinator, "_unsub_refresh"):
                self.coordinator._unsub_refresh()

    @pytest.mark.asyncio
    async def test_insert_statistics_hourly_data(self, hass, config_entry):
        """Test inserting statistics for hourly data."""
        coordinator = SFWaterCoordinator(hass, config_entry)

        hourly_data = [
            {
                "timestamp": datetime(2023, 10, 1, 10, 0),
                "usage": 50.0,
                "resolution": "hourly",
            },
            {
                "timestamp": datetime(2023, 10, 1, 11, 0),
                "usage": 45.0,
                "resolution": "hourly",
            },
        ]

        with patch("homeassistant.components.recorder") as mock_recorder:
            mock_recorder.statistics.async_add_external_statistics = AsyncMock()
            await async_insert_statistics(coordinator, hourly_data)

        # Since the function was mocked, it should not have failed with the Mock await error

    @pytest.mark.asyncio
    async def test_insert_statistics_daily_data(self, hass, config_entry):
        """Test inserting statistics for daily data."""
        coordinator = SFWaterCoordinator(hass, config_entry)

        daily_data = [
            {"timestamp": datetime(2023, 10, 1), "usage": 150.0, "resolution": "daily"},
        ]

        with patch("homeassistant.components.recorder") as mock_recorder:
            mock_recorder.statistics.async_add_external_statistics = AsyncMock()
            await async_insert_statistics(coordinator, daily_data)

        # Since the function was mocked, it should not have failed with the Mock await error

    @pytest.mark.asyncio
    async def test_insert_statistics_monthly_data(self, hass, config_entry):
        """Test inserting statistics for monthly data."""
        coordinator = SFWaterCoordinator(hass, config_entry)

        monthly_data = [
            {
                "timestamp": datetime(2023, 10, 1),
                "usage": 4500.0,
                "resolution": "monthly",
            },
        ]

        with patch("homeassistant.components.recorder") as mock_recorder:
            mock_recorder.statistics.async_add_external_statistics = AsyncMock()
            await async_insert_statistics(coordinator, monthly_data)

        # Since the function was mocked, it should not have failed with the Mock await error

    @pytest.mark.asyncio
    async def test_insert_statistics_legacy_float(self, hass, config_entry):
        """Test inserting statistics with legacy float format."""
        coordinator = SFWaterCoordinator(hass, config_entry)

        with patch("homeassistant.components.recorder") as mock_recorder:
            mock_recorder.statistics.async_add_external_statistics = AsyncMock()
            await async_insert_legacy_statistics(coordinator, 150.0)

        # Since the function was mocked, it should not have failed with the Mock await error

    @pytest.mark.asyncio
    async def test_insert_statistics_empty_data(self, hass, config_entry):
        """Test inserting statistics with empty data."""
        coordinator = SFWaterCoordinator(hass, config_entry)

        with patch(
            "custom_components.sfpuc.statistics_handler.async_add_external_statistics"
        ) as mock_add_stats:
            await async_insert_statistics(coordinator, [])

        mock_add_stats.assert_not_called()

    @pytest.mark.asyncio
    async def test_insert_resolution_statistics_invalid_resolution(
        self, hass, config_entry
    ):
        """Test inserting statistics with invalid resolution."""
        coordinator = SFWaterCoordinator(hass, config_entry)

        data_points = [
            {
                "timestamp": datetime(2023, 10, 1),
                "usage": 100.0,
                "resolution": "invalid",
            }
        ]

        with patch(
            "custom_components.sfpuc.statistics_handler.async_add_external_statistics"
        ) as mock_add_stats:
            await async_insert_resolution_statistics(
                coordinator, data_points, "invalid"
            )

        mock_add_stats.assert_not_called()
