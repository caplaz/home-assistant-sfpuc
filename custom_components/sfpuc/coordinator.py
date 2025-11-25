"""Coordinator for San Francisco Water Power Sewer integration."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import CONF_PASSWORD, CONF_USERNAME, DEFAULT_UPDATE_INTERVAL, DOMAIN
from .data_fetcher import (
    async_backfill_missing_data,
    async_background_historical_fetch,
    async_check_has_historical_data,
)
from .scraper import SFPUCScraper
from .utils import async_detect_billing_day, calculate_billing_period

_LOGGER = logging.getLogger(__name__)


class SFWaterCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """San Francisco Water Power Sewer data update coordinator.

    Manages periodic data fetching from SFPUC portal and caching via
    DataUpdateCoordinator pattern. Handles statistics insertion into
    Home Assistant's recorder component for historical tracking and
    statistics card integration.
    """

    config_entry: ConfigEntry[Any]

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry[Any],
    ) -> None:
        """Initialize coordinator.

        Args:
            hass: Home Assistant instance.
            config_entry: The config entry for this integration.
        """
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=DEFAULT_UPDATE_INTERVAL),
        )

        # Add dummy listener to ensure coordinator updates continue
        # even when all sensors are disabled
        @callback
        def _dummy_listener() -> None:
            """Dummy listener to keep coordinator alive for statistics insertion."""
            pass

        self.async_add_listener(_dummy_listener)
        self.logger.debug("Registered dummy listener to maintain statistics updates")

        self.config_entry = config_entry
        self.scraper = SFPUCScraper(
            config_entry.data[CONF_USERNAME],
            config_entry.data[CONF_PASSWORD],
        )
        self._last_backfill_date: datetime | None = None
        self._historical_data_fetched = False
        self._checked_for_historical_data = False
        self._billing_day: int | None = None  # Detected billing day from monthly data

    def update_credentials(self, username: str, password: str) -> None:
        """Update the scraper credentials.

        Args:
            username: New SFPUC account username/account number.
            password: New SFPUC account password.
        """
        self.logger.info(
            "Updating SFPUC credentials for user: %s", username[:3] + "***"
        )
        self.scraper = SFPUCScraper(username, password)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from SF PUC.

        This method:
        1. Authenticates with the SFPUC portal
        2. Fetches historical data on first run
        3. Performs data backfilling for the past 30 days
        4. Calculates current billing period usage (from 25th to today)
        5. Inserts statistics into Home Assistant recorder
        6. Returns current billing period usage for the sensor

        Returns:
            Dictionary containing current usage data with keys:
            - current_bill_usage: Cumulative usage for current billing period in gallons
            - last_updated: Timestamp of the update

        Raises:
            UpdateFailed: If authentication fails or data retrieval encounters errors.
        """
        try:
            self.logger.debug("Starting data update cycle")

            # Login (run in executor since it's blocking)
            loop = asyncio.get_event_loop()
            self.logger.debug("Attempting SFPUC login")
            login_success = await loop.run_in_executor(None, self.scraper.login)

            if not login_success:
                self.logger.error("Failed to login to SF PUC - aborting update")
                # Create an issue for invalid credentials
                from homeassistant.helpers.issue_registry import (
                    IssueSeverity,
                    async_create_issue,
                )

                async_create_issue(
                    self.hass,
                    DOMAIN,
                    "invalid_credentials",
                    is_fixable=True,
                    severity=IssueSeverity.ERROR,
                    translation_key="invalid_credentials",
                    translation_placeholders={
                        "account": self.config_entry.data.get("username", "unknown"),
                    },
                    data={
                        "entry_id": self.config_entry.entry_id,
                        "account": self.config_entry.data.get("username", "unknown"),
                    },
                )
                raise UpdateFailed(
                    "Failed to login to SF PUC - credentials may be invalid"
                )

            # Login successful - delete any existing invalid_credentials issue
            from homeassistant.helpers.issue_registry import async_delete_issue

            async_delete_issue(self.hass, DOMAIN, "invalid_credentials")

            self.logger.debug("Login successful, proceeding with data fetch")

            # Check if we need to fetch historical data
            # Only check once per HA session to avoid repeated database queries
            if not self._checked_for_historical_data:
                has_historical = await async_check_has_historical_data(self)
                self._checked_for_historical_data = True
                if has_historical:
                    self._historical_data_fetched = True
                    self.logger.info(
                        "Historical data already present in database - skipping fetch"
                    )

            # Schedule historical data fetch on first run (if not already in database)
            # Run in background to avoid blocking startup
            if not self._historical_data_fetched:
                self.logger.info("Scheduling historical data fetch in background...")
                asyncio.create_task(async_background_historical_fetch(self))

            # Detect billing day from monthly data (if not already detected)
            if self._billing_day is None:
                try:
                    await async_detect_billing_day(self)
                except Exception as err:
                    self.logger.warning(
                        "Failed to detect billing day, will use default: %s", err
                    )

            # Perform backfilling if needed (30-day lookback)
            # Skip if we just did a historical fetch to avoid duplicate/overlapping data
            try:
                await async_backfill_missing_data(self)
            except Exception as err:
                self.logger.warning(
                    "Data backfilling failed, continuing with available data: %s", err
                )

            # Calculate billing period dates (SFPUC bills ~25th of each month)
            bill_start, bill_end = calculate_billing_period(self)
            self.logger.debug(
                "Current billing period: %s to %s",
                bill_start.date(),
                bill_end.date(),
            )

            # Use statistics data to get current billing period usage
            # This provides real-time updates from already-inserted hourly/daily data
            from homeassistant.components.recorder import get_instance
            from homeassistant.components.recorder.statistics import (
                statistics_during_period,
            )

            self.logger.debug(
                "Calculating current billing period usage from statistics (%s to %s)",
                bill_start.date(),
                datetime.now().date(),
            )

            # Get hourly statistics for the current billing period
            safe_account = (
                self.config_entry.data.get(CONF_USERNAME, "unknown")
                .replace("-", "_")
                .lower()
            )
            stat_id = f"{DOMAIN}:{safe_account}_water_consumption"

            try:
                # Fetch hourly statistics from bill_start to now
                # We query with period="hour" since we store hourly granularity data
                stats = await get_instance(self.hass).async_add_executor_job(
                    statistics_during_period,
                    self.hass,
                    dt_util.as_utc(bill_start),
                    dt_util.as_utc(datetime.now()),
                    {stat_id},
                    "hour",
                    None,
                    {"state"},
                )

                if stats and stat_id in stats:
                    # Sum all hourly usage values in the billing period
                    current_bill_usage = sum(
                        float(stat.get("state", 0) or 0) for stat in stats[stat_id]
                    )
                    self.logger.debug(
                        "Calculated current billing period usage from statistics: %.2f gallons from %d hourly records",
                        current_bill_usage,
                        len(stats[stat_id]),
                    )
                else:
                    self.logger.warning(
                        "No statistics found for current billing period"
                    )
                    current_bill_usage = 0

            except Exception as err:
                self.logger.error("Failed to calculate usage from statistics: %s", err)
                current_bill_usage = 0

            # Return simplified data for the single sensor
            data = {
                "current_bill_usage": current_bill_usage,
                "last_updated": datetime.now(),
            }

            self.logger.info(
                "Data update completed successfully - Current billing period usage: %.2f gallons",
                current_bill_usage,
            )
            return data

        except UpdateFailed:
            # Re-raise UpdateFailed exceptions as-is
            raise
        except Exception as err:
            self.logger.error(
                "Unexpected error updating San Francisco Water Power Sewer data: %s",
                err,
            )
            raise UpdateFailed(
                f"Unexpected error updating San Francisco Water Power Sewer data: {err}"
            ) from err

    async def _insert_statistics(self) -> None:
        """Insert statistics into Home Assistant.

        This method is called during every coordinator update cycle to register
        our domain as the statistics provider, which prevents Home Assistant's
        recorder from automatically creating statistics for our sensors.

        We query for existing statistics to register our interaction with the
        statistics system.
        """
        try:
            from homeassistant.components.recorder import get_instance
            from homeassistant.components.recorder.statistics import (
                get_last_statistics,
            )

            # Get our statistic ID
            safe_account = (
                self.config_entry.data.get(CONF_USERNAME, "unknown")
                .replace("-", "_")
                .lower()
            )
            stat_id = f"{DOMAIN}:{safe_account}_water_consumption"

            # Query for existing statistics - this registers our domain as managing
            # its own statistics, preventing the recorder from auto-creating them
            await get_instance(self.hass).async_add_executor_job(
                get_last_statistics,
                self.hass,
                1,  # num_stats
                stat_id,
                True,  # convert_units
                set(),  # types
            )

            self.logger.debug("Statistics ownership registered for %s", stat_id)

        except Exception as err:
            self.logger.warning("Error in statistics registration: %s", err)
