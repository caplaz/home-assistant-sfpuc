"""Data fetching utilities for SFPUC coordinator."""

import asyncio
from datetime import datetime, timedelta

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import statistics_during_period
from homeassistant.util import dt as dt_util

from .const import CONF_USERNAME, DOMAIN
from .statistics_handler import async_insert_statistics


async def async_check_has_historical_data(coordinator) -> bool:
    """Check if we already have sufficient historical data in the database.

    Returns True if we have daily statistics going back at least 1 year.
    This prevents re-fetching 2 years of data on every HA restart.
    """
    try:
        # Check for daily statistics from 1 year ago
        one_year_ago = datetime.now() - timedelta(days=365)
        safe_account = (
            coordinator.config_entry.data.get(CONF_USERNAME, "unknown")
            .replace("-", "_")
            .lower()
        )
        stat_id = f"{DOMAIN}:{safe_account}_water_consumption"

        stats = await get_instance(coordinator.hass).async_add_executor_job(
            statistics_during_period,
            coordinator.hass,
            dt_util.as_utc(one_year_ago),
            None,  # end_time (None = now)
            {stat_id},
            "hour",  # period
            None,  # units
            {"sum"},  # types
        )

        # If we have statistics going back at least 1 year, consider historical data fetched
        if stat_id in stats and len(stats[stat_id]) > 300:  # ~300 days minimum
            coordinator.logger.info(
                "Found %d existing daily statistics records - skipping historical data fetch",
                len(stats[stat_id]),
            )
            return True

        coordinator.logger.debug("No sufficient historical data found in database")
        return False

    except Exception as err:
        coordinator.logger.warning("Error checking for historical data: %s", err)
        return False


async def async_fetch_historical_data(coordinator) -> None:
    """Fetch historical data going back months/years on first run.

    Populates recorder statistics with:
    - Monthly billed usage data for the past 2 years (billing cycle data)
    - Daily usage data for the past 2 years (comprehensive historical data)
    - Hourly usage data for the past 30 days (most detailed recent data)

    Monthly data represents actual billing periods (typically 25th-25th)
    and provides valuable year-over-year comparison data.

    Logs warnings if data retrieval fails but does not raise exceptions
    to avoid blocking the initial coordinator setup.

    NOTE: This method is now scheduled to run in the background after
    initial setup to avoid blocking Home Assistant startup.
    """
    try:
        coordinator.logger.info("Background historical fetch started...")

        # Fetch data strategy for first sync (oldest to newest):
        # 1. Daily data from 2 years ago to 30 days ago (historical baseline)
        # 2. Hourly data from 30 days ago to 2 days ago (fills gap to most recent)
        # Regular updates will only fetch new hourly data incrementally
        # This approach builds cumulative sum naturally in chronological order
        end_date = datetime.now()
        # SFPUC has ~2 day data lag - don't fetch today or yesterday
        end_date_available = end_date - timedelta(days=2)
        loop = asyncio.get_event_loop()

        # Fetch monthly billed usage data - all available history
        coordinator.logger.info("Fetching monthly billed usage data...")
        try:
            # SFPUC typically has 2+ years of billing history
            start_date = end_date - timedelta(days=730)  # 2 years back
            monthly_data = await loop.run_in_executor(
                None,
                coordinator.scraper.get_usage_data,
                start_date,
                end_date,
                "monthly",
            )
            if monthly_data:
                await async_insert_statistics(coordinator, monthly_data)
                coordinator.logger.info(
                    "Fetched %d monthly billing data points", len(monthly_data)
                )
            else:
                coordinator.logger.warning("No monthly billing data retrieved")
        except Exception as err:
            coordinator.logger.warning("Failed to fetch monthly billing data: %s", err)

        # Fetch daily data for the past 2 years (comprehensive historical data)
        # SFPUC limits daily data downloads to ~7-10 days, so we fetch in chunks
        # Fetch from 2 years ago to 30 days ago (stops before hourly data period)
        coordinator.logger.info(
            "Fetching daily data in chunks (2 years to 30 days ago)..."
        )
        try:
            all_daily_data = []
            chunk_days = 3  # Fetch 3 days at a time to reduce load
            start_date_2yr = end_date_available - timedelta(
                days=730
            )  # 2 years back from last available
            end_date_daily = end_date_available - timedelta(days=30)  # Stop 30 days ago
            current_start = start_date_2yr

            while current_start < end_date_daily:
                chunk_end = min(
                    current_start + timedelta(days=chunk_days), end_date_daily
                )
                coordinator.logger.debug(
                    "Fetching daily chunk from %s to %s",
                    current_start.date(),
                    chunk_end.date(),
                )

                # Retry logic for network errors
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        chunk_data = await loop.run_in_executor(
                            None,
                            coordinator.scraper.get_usage_data,
                            current_start,
                            chunk_end,
                            "daily",
                        )
                        break  # Success, exit retry loop
                    except Exception as err:
                        if attempt < max_retries - 1:
                            coordinator.logger.warning(
                                "Failed to fetch daily chunk (attempt %d/%d): %s, retrying...",
                                attempt + 1,
                                max_retries,
                                err,
                            )
                            await asyncio.sleep(2**attempt)  # Exponential backoff
                        else:
                            coordinator.logger.error(
                                "Failed to fetch daily chunk after %d attempts: %s",
                                max_retries,
                                err,
                            )
                            raise  # Re-raise to stop fetching

                if chunk_data:
                    all_daily_data.extend(chunk_data)
                    coordinator.logger.debug(
                        "Chunk returned %d data points", len(chunk_data)
                    )

                current_start = chunk_end + timedelta(days=1)
                # Small delay to avoid overwhelming the server
                await asyncio.sleep(1.0)

            if all_daily_data:
                await async_insert_statistics(coordinator, all_daily_data)
                coordinator.logger.info(
                    "Fetched %d daily data points total", len(all_daily_data)
                )
            else:
                coordinator.logger.warning("No daily data retrieved")
        except Exception as err:
            coordinator.logger.warning("Failed to fetch daily data: %s", err)

        # Fetch hourly data for the past 30 days (most detailed recent data)
        # This fills in the gap between daily data (ends 30 days ago) and most recent available
        # Fetches day-by-day to append after daily data in cumulative sum
        # Stops 2 days before today due to SFPUC data lag
        coordinator.logger.info("Fetching hourly data for last 30 days...")
        try:
            all_hourly_data = []
            # Fetch from 30 days ago to 2 days ago (respecting SFPUC data lag)
            days_back = 30

            for days_offset in range(
                days_back, 2, -1  # Start from 30 days ago, stop at 2 days ago
            ):  # Stop at 2 days ago (SFPUC data lag)
                fetch_date = end_date - timedelta(days=days_offset)
                coordinator.logger.debug(
                    "Fetching hourly data for %s",
                    fetch_date.date(),
                )

                # Retry logic for network errors
                max_retries = 3
                hourly_chunk = None
                for attempt in range(max_retries):
                    try:
                        # Fetch one day at a time for hourly data
                        hourly_chunk = await loop.run_in_executor(
                            None,
                            coordinator.scraper.get_usage_data,
                            fetch_date,
                            fetch_date,  # Same day for start and end
                            "hourly",
                        )
                        break  # Success
                    except Exception as err:
                        if attempt < max_retries - 1:
                            coordinator.logger.warning(
                                "Failed to fetch hourly data for %s (attempt %d/%d): %s, retrying...",
                                fetch_date.date(),
                                attempt + 1,
                                max_retries,
                                err,
                            )
                            await asyncio.sleep(2**attempt)  # Exponential backoff
                        else:
                            coordinator.logger.error(
                                "Failed to fetch hourly data for %s after %d attempts: %s",
                                fetch_date.date(),
                                max_retries,
                                err,
                            )
                            # Continue to next day instead of stopping

                if hourly_chunk:
                    all_hourly_data.extend(hourly_chunk)
                    coordinator.logger.debug(
                        "Fetched %d hourly data points for %s",
                        len(hourly_chunk),
                        fetch_date.date(),
                    )

                # Small delay to avoid overwhelming the server
                await asyncio.sleep(0.5)

            if all_hourly_data:
                await async_insert_statistics(coordinator, all_hourly_data)
                coordinator.logger.info(
                    "Fetched %d hourly data points total for past 30 days",
                    len(all_hourly_data),
                )
            else:
                coordinator.logger.warning("No hourly data retrieved")
        except Exception as err:
            coordinator.logger.warning("Failed to fetch hourly data: %s", err)

    except Exception as err:
        coordinator.logger.warning("Failed to fetch historical data: %s", err)


async def async_background_historical_fetch(coordinator) -> None:
    """Fetch historical data in background after startup.

    This method runs the historical data fetch process in the background
    to avoid blocking Home Assistant startup. It waits 30 seconds after
    startup before beginning to allow HA to fully initialize.
    """
    try:
        # Wait 30 seconds to let Home Assistant fully start
        await asyncio.sleep(30)

        coordinator.logger.info("Starting background historical data fetch...")
        await async_fetch_historical_data(coordinator)
        coordinator._historical_data_fetched = True
        # Set backfill date to now to avoid re-fetching the same data
        coordinator._last_backfill_date = datetime.now()
        coordinator.logger.info(
            "Background historical data fetch completed successfully"
        )
    except Exception as err:
        coordinator.logger.warning("Background historical data fetch failed: %s", err)
        # Don't set _historical_data_fetched to True so we retry on next coordinator update


async def async_backfill_missing_data(coordinator) -> None:
    """Fetch only new hourly data since last update.

    Regular update strategy (runs every 12 hours):
    1. Find the latest statistic timestamp in the database
    2. Fetch only NEW hourly data from that timestamp to 2 days ago (SFPUC data lag)
    3. Insert new data points (cumulative sum continues from last value)

    This avoids re-fetching historical data and only appends the latest usage.
    Respects SFPUC's 2-day data lag.
    Throttled to run at most once per 12 hours.

    Logs warnings if fetch fails but does not raise exceptions.
    """
    try:
        now = datetime.now()
        # SFPUC has ~2 day data lag
        end_date_available = now - timedelta(days=2)

        # Check if we need to update (run every 12 hours)
        if coordinator._last_backfill_date and (
            now - coordinator._last_backfill_date
        ) < timedelta(hours=12):
            return

        coordinator.logger.debug("Fetching new hourly data since last update...")

        # Get the latest statistic timestamp from database
        from homeassistant.components.recorder.statistics import get_last_statistics

        safe_account = (
            coordinator.config_entry.data.get(CONF_USERNAME, "unknown")
            .replace("-", "_")
            .lower()
        )
        stat_id = f"{DOMAIN}:{safe_account}_water_consumption"

        last_stat = await get_instance(coordinator.hass).async_add_executor_job(
            get_last_statistics, coordinator.hass, 1, stat_id, True, set()
        )

        # Determine start date for fetch
        if last_stat and stat_id in last_stat:
            last_timestamp = last_stat[stat_id][0]["start"]
            # Convert timestamp to datetime and add 1 hour to avoid duplicate
            from datetime import datetime as dt

            start_date = dt.fromtimestamp(last_timestamp) + timedelta(hours=1)
            coordinator.logger.debug(
                "Latest statistic: %s, fetching data since then",
                dt.fromtimestamp(last_timestamp),
            )
        else:
            # No existing data - skip backfill on first sync
            # The background historical fetch will handle initial data population
            coordinator.logger.debug(
                "No existing statistics, skipping backfill (handled by background fetch)"
            )
            return

        loop = asyncio.get_event_loop()

        # Fetch only NEW hourly data since last statistic (up to 2 days ago)
        coordinator.logger.info(
            f"Fetching new hourly data from {start_date.date()} to {end_date_available.date()}..."
        )
        try:
            # Fetch hourly data from start_date to end_date_available, one day at a time
            hourly_data_all = []
            current_date = start_date

            while current_date.date() <= end_date_available.date():
                fetch_date = current_date

                # Retry logic for network errors
                max_retries = 3
                hourly_chunk = None
                for attempt in range(max_retries):
                    try:
                        hourly_chunk = await loop.run_in_executor(
                            None,
                            coordinator.scraper.get_usage_data,
                            fetch_date,
                            fetch_date,  # Same day for start and end
                            "hourly",
                        )
                        break  # Success
                    except Exception as err:
                        if attempt < max_retries - 1:
                            coordinator.logger.warning(
                                "Failed to fetch hourly data for %s (attempt %d/%d): %s, retrying...",
                                fetch_date.date(),
                                attempt + 1,
                                max_retries,
                                err,
                            )
                            await asyncio.sleep(2**attempt)
                        else:
                            coordinator.logger.error(
                                "Failed to fetch hourly data for %s after %d attempts: %s",
                                fetch_date.date(),
                                max_retries,
                                err,
                            )

                if hourly_chunk:
                    hourly_data_all.extend(hourly_chunk)

                # Move to next day
                current_date += timedelta(days=1)
                await asyncio.sleep(0.5)  # Small delay

            if hourly_data_all:
                await async_insert_statistics(coordinator, hourly_data_all)
                coordinator.logger.info(
                    "Fetched %d new hourly data points", len(hourly_data_all)
                )
            else:
                coordinator.logger.debug("No new hourly data found")
        except Exception as err:
            coordinator.logger.warning("Failed to fetch new hourly data: %s", err)

        coordinator._last_backfill_date = now

    except Exception as err:
        coordinator.logger.warning("Failed to update with new data: %s", err)
