"""Tests for San Francisco Water Power Sewer coordinator."""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from homeassistant.helpers.update_coordinator import UpdateFailed
import pytest

from custom_components.sfpuc.const import DEFAULT_UPDATE_INTERVAL
from custom_components.sfpuc.coordinator import SFWaterCoordinator

from .common import MockConfigEntry


class TestSFWaterCoordinator:
    """Test the San Francisco Water Power Sewer coordinator functionality."""

    @pytest.fixture(autouse=True)
    def setup_method(self, hass):
        """Set up test fixtures."""
        self.hass = hass
        self.config_entry = MockConfigEntry()

    def test_coordinator_initialization(self, hass, config_entry):
        """Test coordinator initialization."""
        coordinator = SFWaterCoordinator(hass, config_entry)

        assert coordinator.config_entry == config_entry
        assert coordinator._last_backfill_date is None
        assert coordinator._historical_data_fetched is False
        assert coordinator.update_interval == timedelta(minutes=DEFAULT_UPDATE_INTERVAL)

    @patch("custom_components.sfpuc.coordinator.SFPUCScraper")
    @pytest.mark.asyncio
    async def test_update_data_success_first_run(
        self, mock_scraper_class, hass, config_entry
    ):
        """Test successful data update on first run."""
        # Mock the scraper
        mock_scraper = Mock()
        mock_scraper_class.return_value = mock_scraper
        mock_scraper.login.return_value = True

        coordinator = SFWaterCoordinator(hass, config_entry)

        # Mock statistics_during_period and async_add_external_statistics
        from unittest.mock import AsyncMock

        safe_account = (
            config_entry.data.get("username", "unknown").replace("-", "_").lower()
        )
        stat_id = f"sfpuc:{safe_account}_water_consumption"

        with (
            patch(
                "homeassistant.components.recorder.get_instance"
            ) as mock_get_instance,
            patch("custom_components.sfpuc.coordinator.async_add_external_statistics"),
            patch.object(
                coordinator, "_async_backfill_missing_data", return_value=None
            ),
            patch.object(
                coordinator, "_async_check_has_historical_data", return_value=False
            ),
            patch.object(coordinator, "_async_detect_billing_day", return_value=None),
        ):
            mock_recorder = Mock()
            mock_recorder.async_add_executor_job = AsyncMock(
                return_value={stat_id: [{"state": 95.0}, {"state": 45.0}]}
            )
            mock_get_instance.return_value = mock_recorder
            result = await coordinator._async_update_data()

        assert result["current_bill_usage"] == 140.0  # Sum of the states
        assert "last_updated" in result
        assert (
            coordinator._historical_data_fetched is False
        )  # Background task scheduled, not completed

        # No direct calls to get_usage_data in _async_update_data (backfill mocked)
        assert mock_scraper.get_usage_data.call_count == 0

    @patch("custom_components.sfpuc.coordinator.SFPUCScraper")
    @pytest.mark.asyncio
    async def test_update_data_login_failure(
        self, mock_scraper_class, hass, config_entry
    ):
        """Test data update with login failure."""
        mock_scraper = Mock()
        mock_scraper_class.return_value = mock_scraper
        mock_scraper.login.return_value = False

        coordinator = SFWaterCoordinator(hass, config_entry)

        with pytest.raises(UpdateFailed, match="Failed to login to SF PUC"):
            await coordinator._async_update_data()

    @patch("custom_components.sfpuc.coordinator.SFPUCScraper")
    @pytest.mark.asyncio
    async def test_update_data_no_current_data(
        self, mock_scraper_class, hass, config_entry
    ):
        """Test data update when no current data is available."""
        mock_scraper = Mock()
        mock_scraper_class.return_value = mock_scraper
        mock_scraper.login.return_value = True
        mock_scraper.get_usage_data.return_value = None

        coordinator = SFWaterCoordinator(hass, config_entry)

        # Mock statistics to return empty
        from unittest.mock import AsyncMock

        with (
            patch(
                "homeassistant.components.recorder.get_instance"
            ) as mock_get_instance,
            patch("custom_components.sfpuc.coordinator.async_add_external_statistics"),
            patch.object(
                coordinator, "_async_backfill_missing_data", return_value=None
            ),
            patch.object(
                coordinator, "_async_check_has_historical_data", return_value=False
            ),
            patch.object(coordinator, "_async_detect_billing_day", return_value=None),
        ):
            mock_recorder = Mock()
            mock_recorder.async_add_executor_job = AsyncMock(
                return_value={}
            )  # Empty stats
            mock_get_instance.return_value = mock_recorder
            result = await coordinator._async_update_data()

        assert result["current_bill_usage"] == 0.0
        assert "last_updated" in result

    @patch("custom_components.sfpuc.coordinator.SFPUCScraper")
    @pytest.mark.asyncio
    async def test_fetch_historical_data_success(
        self, mock_scraper_class, hass, config_entry
    ):
        """Test successful historical data fetching."""
        mock_scraper = Mock()
        mock_scraper_class.return_value = mock_scraper
        mock_scraper.get_usage_data.side_effect = [
            # Daily data
            [
                {
                    "timestamp": datetime(2023, 9, 15),
                    "usage": 150.0,
                    "resolution": "daily",
                }
            ],
            # Hourly data
            [
                {
                    "timestamp": datetime(2023, 9, 30, 15, 0),
                    "usage": 25.0,
                    "resolution": "hourly",
                }
            ],
        ]

        coordinator = SFWaterCoordinator(hass, config_entry)

        with patch(
            "custom_components.sfpuc.coordinator.async_add_external_statistics"
        ) as mock_add_stats:
            await coordinator._async_fetch_historical_data()

        # Verify historical data calls
        assert mock_scraper.get_usage_data.call_count == 4

        # Verify statistics were added
        assert mock_add_stats.call_count == 1

    @patch("custom_components.sfpuc.coordinator.SFPUCScraper")
    @patch("custom_components.sfpuc.coordinator._LOGGER")
    @pytest.mark.asyncio
    async def test_fetch_historical_data_failure(
        self, mock_logger, mock_scraper_class, hass, config_entry
    ):
        """Test historical data fetching with failures."""
        mock_scraper = Mock()
        mock_scraper_class.return_value = mock_scraper
        mock_scraper.get_usage_data.side_effect = Exception("Network error")

        coordinator = SFWaterCoordinator(hass, config_entry)

        # Should not raise exception, just log warning
        await coordinator._async_fetch_historical_data()

        # Verify logger was called
        mock_logger.warning.assert_called()

    @patch("custom_components.sfpuc.coordinator.SFPUCScraper")
    @pytest.mark.asyncio
    async def test_backfill_missing_data_first_run(
        self, mock_scraper_class, hass, config_entry
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
            # Hourly backfill data
            [
                {
                    "timestamp": datetime(2023, 9, 28, 10, 0),
                    "usage": 20.0,
                    "resolution": "hourly",
                }
            ],
        ]

        coordinator = SFWaterCoordinator(hass, config_entry)

        with patch(
            "custom_components.sfpuc.coordinator.async_add_external_statistics"
        ) as mock_add_stats:
            await coordinator._async_backfill_missing_data()

        # Should perform backfill on first run
        assert mock_scraper.get_usage_data.call_count == 3
        assert mock_add_stats.call_count == 1
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

        await coordinator._async_backfill_missing_data()

        # Should not perform backfill
        mock_scraper.get_usage_data.assert_not_called()

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

        with patch(
            "custom_components.sfpuc.coordinator.async_add_external_statistics"
        ) as mock_add_stats:
            await coordinator._async_insert_statistics(hourly_data)

        # Verify statistics were added
        mock_add_stats.assert_called_once()
        # Just verify the function was called with the right number of arguments
        call_args = mock_add_stats.call_args
        assert len(call_args[0]) == 3  # hass, metadata, statistics

    @pytest.mark.asyncio
    async def test_insert_statistics_daily_data(self, hass, config_entry):
        """Test inserting statistics for daily data."""
        coordinator = SFWaterCoordinator(hass, config_entry)

        daily_data = [
            {"timestamp": datetime(2023, 10, 1), "usage": 150.0, "resolution": "daily"},
        ]

        with patch(
            "custom_components.sfpuc.coordinator.async_add_external_statistics"
        ) as mock_add_stats:
            await coordinator._async_insert_statistics(daily_data)

        mock_add_stats.assert_called_once()
        call_args = mock_add_stats.call_args
        assert len(call_args[0]) == 3  # hass, metadata, statistics

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

        with patch(
            "custom_components.sfpuc.coordinator.async_add_external_statistics"
        ) as mock_add_stats:
            await coordinator._async_insert_statistics(monthly_data)

        mock_add_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_insert_statistics_legacy_float(self, hass, config_entry):
        """Test inserting statistics with legacy float format."""
        coordinator = SFWaterCoordinator(hass, config_entry)

        with patch(
            "custom_components.sfpuc.coordinator.async_add_external_statistics"
        ) as mock_add_stats:
            await coordinator._async_insert_statistics(150.0)

        mock_add_stats.assert_called_once()
        call_args = mock_add_stats.call_args
        assert len(call_args[0]) == 3  # hass, metadata, statistics

    @pytest.mark.asyncio
    async def test_insert_statistics_empty_data(self, hass, config_entry):
        """Test inserting statistics with empty data."""
        coordinator = SFWaterCoordinator(hass, config_entry)

        with patch(
            "custom_components.sfpuc.coordinator.async_add_external_statistics"
        ) as mock_add_stats:
            await coordinator._async_insert_statistics([])

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
            "custom_components.sfpuc.coordinator.async_add_external_statistics"
        ) as mock_add_stats:
            await coordinator._async_insert_resolution_statistics(
                data_points, "invalid"
            )

        mock_add_stats.assert_not_called()
