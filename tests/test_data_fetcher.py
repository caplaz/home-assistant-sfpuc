"""Tests for SFPUC data fetching operations."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from custom_components.sfpuc.coordinator import SFWaterCoordinator
from custom_components.sfpuc.data_fetcher import (
    async_backfill_missing_data,
    async_fetch_historical_data,
)

from .common import MockConfigEntry


@pytest.fixture
def mock_asyncio_sleep():
    """Mock asyncio.sleep to prevent test hangs."""
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        yield mock_sleep


class TestDataFetcher:
    """Test the SFPUC data fetching functionality."""

    @pytest.fixture(autouse=True)
    def setup_method(self, hass):
        """Set up test fixtures."""
        self.hass = hass
        self.config_entry = MockConfigEntry()
        # Add recorder instance to hass.data for statistics insertion
        from homeassistant.components.recorder.util import DATA_INSTANCE

        if DATA_INSTANCE not in hass.data:
            hass.data[DATA_INSTANCE] = Mock()

    @pytest.fixture(autouse=True)
    def mock_coordinator_timer(self):
        """Mock coordinator timer and background tasks to prevent lingering timers."""
        with (
            patch("asyncio.AbstractEventLoop.call_later", return_value=None),
            patch(
                "custom_components.sfpuc.data_fetcher.async_background_historical_fetch",
                return_value=None,
            ),
        ):
            yield

    @patch("custom_components.sfpuc.coordinator.SFPUCScraper")
    @pytest.mark.asyncio
    async def test_fetch_historical_data_success(
        self, mock_scraper_class, hass, config_entry, mock_asyncio_sleep
    ):
        """Test successful historical data fetching."""
        mock_scraper = Mock()
        mock_scraper_class.return_value = mock_scraper
        mock_scraper.get_usage_data = Mock(
            side_effect=[
                # Monthly data
                [
                    {
                        "timestamp": datetime(2023, 9, 15),
                        "usage": 150.0,
                        "resolution": "monthly",
                    }
                ],
                # Daily data - empty to end loop
                [],
                # Hourly data - empty to end loop
                [],
            ]
        )

        coordinator = SFWaterCoordinator(hass, config_entry)

        with (
            patch(
                "custom_components.sfpuc.data_fetcher.async_check_has_historical_data",
                return_value=False,
            ),
            patch(
                "custom_components.sfpuc.data_fetcher.async_insert_statistics"
            ) as mock_insert_stats,
        ):
            await async_fetch_historical_data(coordinator)

        assert mock_insert_stats.call_count >= 1

    @patch("custom_components.sfpuc.coordinator.SFPUCScraper")
    @patch("custom_components.sfpuc.coordinator._LOGGER")
    @pytest.mark.asyncio
    async def test_fetch_historical_data_failure(
        self, mock_logger, mock_scraper_class, hass, config_entry, mock_asyncio_sleep
    ):
        """Test historical data fetching with failures."""
        mock_scraper = Mock()
        mock_scraper_class.return_value = mock_scraper
        mock_scraper.get_usage_data.side_effect = Exception("Network error")

        coordinator = SFWaterCoordinator(hass, config_entry)

        # Should not raise exception, just log warning
        await async_fetch_historical_data(coordinator)

        # Verify logger was called
        mock_logger.warning.assert_called()

    @patch("custom_components.sfpuc.coordinator.SFPUCScraper")
    @pytest.mark.asyncio
    async def test_backfill_missing_data_first_run(
        self, mock_scraper_class, hass, config_entry, mock_asyncio_sleep
    ):
        """Test backfilling on first run."""
        mock_scraper = Mock()
        mock_scraper_class.return_value = mock_scraper
        mock_scraper.get_usage_data.side_effect = [
            # Daily backfill data
            [
                {
                    "timestamp": datetime(2023, 9, 25),
                    "usage": 140.0,
                    "resolution": "daily",
                }
            ],
            # Hourly data - empty to end loop
            [],
        ]

        coordinator = SFWaterCoordinator(hass, config_entry)

        with patch(
            "custom_components.sfpuc.data_fetcher.async_insert_statistics"
        ) as mock_insert_stats:
            await async_backfill_missing_data(coordinator)

        assert mock_insert_stats.call_count >= 1
        assert coordinator._last_backfill_date is not None

    @patch("custom_components.sfpuc.coordinator.SFPUCScraper")
    @pytest.mark.asyncio
    async def test_backfill_missing_data_recent_run(
        self, mock_scraper_class, hass, config_entry
    ):
        """Test backfilling is skipped when recently run."""
        mock_scraper = Mock()
        mock_scraper_class.return_value = mock_scraper

        coordinator = SFWaterCoordinator(hass, config_entry)
        # Set last backfill to recent time
        coordinator._last_backfill_date = datetime.now() - timedelta(hours=1)

        await async_backfill_missing_data(coordinator)

        # Should not perform backfill
        mock_scraper.get_usage_data.assert_not_called()

    @patch("custom_components.sfpuc.coordinator.SFPUCScraper")
    @pytest.mark.asyncio
    async def test_fetch_historical_data_daily_retry_on_failure(
        self, mock_scraper_class, hass, config_entry, mock_asyncio_sleep
    ):
        """Test retry logic for daily data fetching with transient failures."""
        mock_scraper = Mock()
        mock_scraper_class.return_value = mock_scraper

        # First call fails, second succeeds (simulating transient failure)
        mock_scraper.get_usage_data = Mock(
            side_effect=[
                # Monthly data
                [
                    {
                        "timestamp": datetime(2023, 9, 15),
                        "usage": 150.0,
                        "resolution": "monthly",
                    }
                ],
                # Daily data - 1st attempt fails, 2nd succeeds
                Exception("Network error"),
                [
                    {
                        "timestamp": datetime(2023, 9, 25),
                        "usage": 140.0,
                        "resolution": "daily",
                    }
                ],
                # Hourly data
                [],
            ]
        )

        coordinator = SFWaterCoordinator(hass, config_entry)

        with (
            patch(
                "custom_components.sfpuc.data_fetcher.async_check_has_historical_data",
                return_value=False,
            ),
            patch(
                "custom_components.sfpuc.data_fetcher.async_insert_statistics"
            ) as mock_insert_stats,
        ):
            await async_fetch_historical_data(coordinator)

        # Should retry and eventually succeed
        assert mock_insert_stats.call_count >= 1
        assert mock_scraper.get_usage_data.call_count >= 3

    @patch("custom_components.sfpuc.coordinator.SFPUCScraper")
    @pytest.mark.asyncio
    async def test_fetch_historical_data_hourly_retry_on_failure(
        self, mock_scraper_class, hass, config_entry, mock_asyncio_sleep
    ):
        """Test retry logic for hourly data fetching with transient failures."""
        mock_scraper = Mock()
        mock_scraper_class.return_value = mock_scraper

        # Monthly and daily succeed, hourly fails then succeeds
        mock_scraper.get_usage_data = Mock(
            side_effect=[
                # Monthly data
                [
                    {
                        "timestamp": datetime(2023, 9, 15),
                        "usage": 150.0,
                        "resolution": "monthly",
                    }
                ],
                # Daily data
                [],
                # Hourly data - 1st attempt fails
                Exception("Timeout"),
                # Hourly data - 2nd attempt succeeds
                [
                    {
                        "timestamp": datetime(2023, 9, 30, 15, 0),
                        "usage": 25.0,
                        "resolution": "hourly",
                    }
                ],
            ]
        )

        coordinator = SFWaterCoordinator(hass, config_entry)

        with (
            patch(
                "custom_components.sfpuc.data_fetcher.async_check_has_historical_data",
                return_value=False,
            ),
            patch("custom_components.sfpuc.data_fetcher.async_insert_statistics"),
        ):
            await async_fetch_historical_data(coordinator)

        # Should have retried hourly data
        assert mock_scraper.get_usage_data.call_count >= 3

    @patch("custom_components.sfpuc.coordinator.SFPUCScraper")
    @pytest.mark.asyncio
    async def test_backfill_retry_on_failure(
        self, mock_scraper_class, hass, config_entry, mock_asyncio_sleep
    ):
        """Test retry logic for backfill data fetching."""
        mock_scraper = Mock()
        mock_scraper_class.return_value = mock_scraper

        # First call fails, second succeeds
        mock_scraper.get_usage_data = Mock(
            side_effect=[
                Exception("Network error"),
                [
                    {
                        "timestamp": datetime(2023, 9, 25),
                        "usage": 140.0,
                        "resolution": "daily",
                    }
                ],
                [],
            ]
        )

        coordinator = SFWaterCoordinator(hass, config_entry)

        with patch(
            "custom_components.sfpuc.data_fetcher.async_insert_statistics"
        ) as mock_insert_stats:
            await async_backfill_missing_data(coordinator)

        # Should retry and eventually succeed
        assert mock_insert_stats.call_count >= 1
        assert mock_scraper.get_usage_data.call_count >= 2

    @patch("custom_components.sfpuc.coordinator.SFPUCScraper")
    @pytest.mark.asyncio
    async def test_backfill_handles_continued_failures(
        self, mock_scraper_class, hass, config_entry, mock_asyncio_sleep
    ):
        """Test backfill continues after max retries exhausted for hourly data."""
        mock_scraper = Mock()
        mock_scraper_class.return_value = mock_scraper

        # All daily calls succeed, hourly continuously fails

        def side_effect(*args, **kwargs):
            resolution = args[2] if len(args) > 2 else kwargs.get("resolution")
            if resolution == "daily":
                return [
                    {
                        "timestamp": datetime(2023, 9, 25),
                        "usage": 140.0,
                        "resolution": "daily",
                    }
                ]
            elif resolution == "hourly":
                # Always fail for hourly
                raise Exception("Hourly data unavailable")
            return []

        mock_scraper.get_usage_data = Mock(side_effect=side_effect)

        coordinator = SFWaterCoordinator(hass, config_entry)

        with patch(
            "custom_components.sfpuc.data_fetcher.async_insert_statistics"
        ) as mock_insert_stats:
            # Should not raise exception even if hourly fails repeatedly
            await async_backfill_missing_data(coordinator)

        # Should have still inserted daily data
        assert mock_insert_stats.call_count >= 1
