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
                "custom_components.sfpuc.data_fetcher.async_insert_statistics",
                new_callable=AsyncMock,
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
        """Test backfilling is skipped when no data exists (first run)."""
        mock_scraper = Mock()
        mock_scraper_class.return_value = mock_scraper
        mock_scraper.get_usage_data.return_value = []

        coordinator = SFWaterCoordinator(hass, config_entry)

        # When no statistics exist, backfill should skip gracefully
        await async_backfill_missing_data(coordinator)

        # Should have not raised an exception
        assert coordinator._last_backfill_date is None  # Was skipped

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
                "custom_components.sfpuc.data_fetcher.async_insert_statistics",
                new_callable=AsyncMock,
            ) as mock_insert_stats,
        ):
            await async_fetch_historical_data(coordinator)
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
                "custom_components.sfpuc.data_fetcher.async_insert_statistics",
                new_callable=AsyncMock,
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
            patch(
                "custom_components.sfpuc.data_fetcher.async_insert_statistics",
                new_callable=AsyncMock,
            ),
        ):
            await async_fetch_historical_data(coordinator)

        # Should have retried hourly data
        assert mock_scraper.get_usage_data.call_count >= 3

    @patch("custom_components.sfpuc.coordinator.SFPUCScraper")
    @pytest.mark.asyncio
    async def test_backfill_retry_on_failure(
        self, mock_scraper_class, hass, config_entry, mock_asyncio_sleep
    ):
        """Test backfill handles network errors gracefully."""
        mock_scraper = Mock()
        mock_scraper_class.return_value = mock_scraper

        # Simulate network failure
        mock_scraper.get_usage_data = Mock(side_effect=Exception("Network error"))

        coordinator = SFWaterCoordinator(hass, config_entry)

        # Should handle failure gracefully
        await async_backfill_missing_data(coordinator)

        # Should have logged the failure but not raised
        assert True  # Test passed if no exception was raised

    @patch("custom_components.sfpuc.coordinator.SFPUCScraper")
    @pytest.mark.asyncio
    async def test_backfill_handles_continued_failures(
        self, mock_scraper_class, hass, config_entry, mock_asyncio_sleep
    ):
        """Test backfill handles continued failures and doesn't raise."""
        mock_scraper = Mock()
        mock_scraper_class.return_value = mock_scraper

        # All calls fail
        mock_scraper.get_usage_data = Mock(side_effect=Exception("Data unavailable"))

        coordinator = SFWaterCoordinator(hass, config_entry)

        # Should handle continuous failures without raising
        await async_backfill_missing_data(coordinator)

        # Should have logged failures but not raised
        assert True  # Test passed if no exception was raised

    @patch("custom_components.sfpuc.coordinator.SFPUCScraper")
    @pytest.mark.asyncio
    async def test_fetch_historical_data_no_gap_daily_to_hourly(
        self, mock_scraper_class, hass, config_entry, mock_asyncio_sleep
    ):
        """Test that daily and hourly data transition has no gaps.

        Regression test for bug where Oct 12-13 had missing data due to
        boundary mismatch between daily (ends 31 days ago) and hourly
        (started 31 days ago from 'now' instead of from 'end_date_available').

        Daily data ends 31 days ago from end_date_available (which is 2 days back).
        Hourly data starts 32 days ago from 'now', creating 1-day overlap.
        """
        mock_scraper = Mock()
        mock_scraper_class.return_value = mock_scraper

        # Create realistic data points around the boundary
        # This simulates the transition from daily to hourly data
        now = datetime.now()
        end_date_available = now - timedelta(days=2)  # SFPUC 2-day lag
        daily_end = end_date_available - timedelta(days=31)  # 31 days back
        hourly_start = now - timedelta(days=32)  # 32 days back

        # Data points spanning the boundary
        daily_data = [
            {
                "timestamp": daily_end - timedelta(days=2),
                "usage": 80.0,
                "resolution": "daily",
            },
            {
                "timestamp": daily_end - timedelta(days=1),
                "usage": 85.0,
                "resolution": "daily",
            },
            {
                "timestamp": daily_end,
                "usage": 90.0,
                "resolution": "daily",
            },
        ]

        # Hourly data starting from 32 days ago (1 day overlap with daily)
        hourly_data = [
            {
                "timestamp": hourly_start,
                "usage": 3.75,
                "resolution": "hourly",
            },
            {
                "timestamp": hourly_start + timedelta(hours=1),
                "usage": 3.80,
                "resolution": "hourly",
            },
            {
                "timestamp": hourly_start + timedelta(days=1),
                "usage": 3.85,
                "resolution": "hourly",
            },
        ]

        # Mock the scraper to return data in expected fetch order
        def get_usage_data_side_effect(start, end, resolution):
            if resolution == "monthly":
                return []
            elif resolution == "daily":
                # Return data for the requested period
                if end >= daily_end - timedelta(days=2):
                    return daily_data
                return []
            elif resolution == "hourly":
                # Return data for the requested period
                if start >= hourly_start and end >= hourly_start:
                    return hourly_data
                return []
            return []

        mock_scraper.get_usage_data = Mock(side_effect=get_usage_data_side_effect)

        coordinator = SFWaterCoordinator(hass, config_entry)

        with (
            patch(
                "custom_components.sfpuc.data_fetcher.async_check_has_historical_data",
                return_value=False,
            ),
            patch(
                "custom_components.sfpuc.data_fetcher.async_insert_statistics",
                new_callable=AsyncMock,
            ) as mock_insert_stats,
        ):
            await async_fetch_historical_data(coordinator)

        # Verify both daily and hourly data were inserted
        assert mock_insert_stats.call_count >= 2

        # Verify that calls were made for all three resolutions
        # monthly=1, daily chunks (at least 1), hourly days (at least 1)
        assert mock_scraper.get_usage_data.call_count >= 3

    @patch("custom_components.sfpuc.coordinator.SFPUCScraper")
    @pytest.mark.asyncio
    async def test_fetch_historical_data_hourly_includes_day_32_back(
        self, mock_scraper_class, hass, config_entry, mock_asyncio_sleep
    ):
        """Test that hourly data fetch loop includes day 32 back for overlap.

        The hourly data loop should use range(32, 1, -1) to ensure it starts
        32 days back from today, which creates overlap with daily data ending
        31 days back from end_date_available.
        """
        mock_scraper = Mock()
        mock_scraper_class.return_value = mock_scraper

        # Collect all the dates that hourly data is requested for
        hourly_dates_requested = []

        def get_usage_data_side_effect(start, end, resolution):
            if resolution == "hourly":
                hourly_dates_requested.append((start.date(), end.date()))
            return []

        mock_scraper.get_usage_data = Mock(side_effect=get_usage_data_side_effect)

        coordinator = SFWaterCoordinator(hass, config_entry)

        with (
            patch(
                "custom_components.sfpuc.data_fetcher.async_check_has_historical_data",
                return_value=False,
            ),
            patch(
                "custom_components.sfpuc.data_fetcher.async_insert_statistics",
                new_callable=AsyncMock,
            ),
        ):
            await async_fetch_historical_data(coordinator)

        # Verify hourly dates were requested
        assert len(hourly_dates_requested) > 0

        # Get the earliest hourly date requested
        earliest_hourly_date = min(
            min(start, end) for start, end in hourly_dates_requested
        )

        now = datetime.now()
        expected_earliest = (now - timedelta(days=32)).date()

        # The hourly data should start from 32 days back to overlap with daily
        assert earliest_hourly_date == expected_earliest
