"""Statistics handling utilities for SFPUC coordinator."""

from typing import Any
import zoneinfo

from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import async_add_external_statistics
from homeassistant.components.recorder.util import DATA_INSTANCE
from homeassistant.const import VOLUME, UnitOfVolume
from homeassistant.util import dt as dt_util

from .const import CONF_USERNAME, DOMAIN


async def async_insert_statistics(
    coordinator, usage_data: float | list[dict[str, Any]]
) -> None:
    """Insert water usage statistics into Home Assistant.

    Handles both legacy (float) and new (list) data formats.
    Groups data points by resolution and delegates to appropriate
    resolution-specific insertion methods.

    Args:
        usage_data: Either a float representing daily usage (legacy format)
                   or a list of dictionaries containing 'timestamp', 'usage',
                   and 'resolution' keys.

    Logs warnings if insertion fails but does not raise exceptions.
    """
    try:
        if isinstance(usage_data, (int, float)):
            # Legacy format: single daily usage value
            coordinator.logger.debug(
                "Inserting legacy statistics format: %.2f", usage_data
            )
            await async_insert_legacy_statistics(coordinator, usage_data)
            return

        # New format: list of data points
        if not usage_data:
            coordinator.logger.debug("No usage data to insert")
            return

        coordinator.logger.debug(
            "Processing %d data points for statistics insertion", len(usage_data)
        )

        # Group data by resolution (skip monthly data)
        hourly_data = []
        daily_data = []
        monthly_data = []  # Enabled - billing cycles are now supported

        for item in usage_data:
            resolution = item.get("resolution", "daily")
            if resolution == "hourly":
                hourly_data.append(item)
            elif resolution == "daily":
                daily_data.append(item)
            elif resolution == "monthly":
                monthly_data.append(item)

        coordinator.logger.debug(
            "Grouped data - Hourly: %d, Daily: %d, Monthly: %d",
            len(hourly_data),
            len(daily_data),
            len(monthly_data),
        )

        # Insert statistics for each resolution
        if hourly_data:
            await async_insert_resolution_statistics(coordinator, hourly_data, "hourly")
        if daily_data:
            await async_insert_resolution_statistics(coordinator, daily_data, "daily")
        if monthly_data:
            await async_insert_resolution_statistics(
                coordinator, monthly_data, "monthly"
            )

    except Exception as err:
        coordinator.logger.warning("Failed to insert water usage statistics: %s", err)


async def async_insert_resolution_statistics(
    coordinator, data_points: list[dict[str, Any]], resolution: str
) -> None:
    """Insert statistics for a specific resolution.

    Creates StatisticMetaData and StatisticData objects and adds them
    to Home Assistant's recorder component. Handles timezone conversion
    for San Francisco (America/Los_Angeles).

    Args:
        data_points: List of dictionaries with 'timestamp' and 'usage' keys.
                    Timestamps should be timezone-naive (assumed local to SF).
        resolution: Data resolution - 'hourly' or 'daily'. Determines statistic ID
                   and metadata.

    Logs warnings if insertion fails but does not raise exceptions.
    """
    try:
        coordinator.logger.debug(
            "Inserting %d %s statistics", len(data_points), resolution
        )

        # Sort data points by timestamp to ensure correct cumulative sum calculation
        data_points = sorted(data_points, key=lambda x: x["timestamp"])

        # Deduplicate by timestamp (keep last occurrence to get most recent data)
        seen_timestamps = {}
        for point in data_points:
            timestamp_key = point["timestamp"]
            seen_timestamps[timestamp_key] = point

        # Convert back to list, maintaining sorted order
        data_points = list(seen_timestamps.values())
        data_points.sort(key=lambda x: x["timestamp"])

        coordinator.logger.debug(
            "After deduplication: %d %s statistics", len(data_points), resolution
        )

        # Create statistic metadata based on resolution
        # Use SINGLE statistic ID for all resolutions
        # This consolidates hourly, daily, and monthly data into one statistic
        account_number = coordinator.config_entry.data.get(CONF_USERNAME, "default")
        # Sanitize account number (lowercase, replace special chars)
        safe_account = account_number.lower().replace("-", "_").replace(" ", "_")

        # Single unified statistic for all water consumption data
        stat_id = f"{DOMAIN}:{safe_account}_water_consumption"
        name = "San Francisco Water Power Sewer"
        has_sum = True

        metadata = StatisticMetaData(
            has_mean=False,
            has_sum=has_sum,
            mean_type=StatisticMeanType.NONE,
            name=name,
            source=DOMAIN,
            statistic_id=stat_id,
            unit_class=VOLUME,
            unit_of_measurement=UnitOfVolume.GALLONS.value,
        )

        # Create statistic data points
        statistic_data = []
        cumulative_sum = 0.0  # Track cumulative sum for Energy Dashboard

        for point in data_points:
            timestamp = point["timestamp"]
            usage = point["usage"]

            # Adjust timestamp based on resolution
            if resolution == "hourly":
                start_time = timestamp
            elif resolution == "daily":
                start_time = timestamp.replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
            elif resolution == "monthly":
                start_time = timestamp.replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0
                )

            # Convert naive timestamp to timezone-aware UTC (HA stores statistics in UTC)
            if start_time.tzinfo is None:
                # Treat naive timestamp as San Francisco local time
                # Localize to SF timezone, then convert to UTC
                sf_timezone = zoneinfo.ZoneInfo("America/Los_Angeles")
                # Create a new aware datetime by interpreting the naive time as SF local time
                start_time_aware = start_time.replace(tzinfo=sf_timezone)
                # Convert to UTC
                start_time = dt_util.as_utc(start_time_aware)
            else:
                # Already timezone-aware, convert to UTC
                start_time = dt_util.as_utc(start_time)

            # Accumulate sum for Energy Dashboard compatibility
            cumulative_sum += usage

            statistic_data.append(
                StatisticData(
                    start=start_time,
                    state=usage,  # Individual period usage
                    sum=cumulative_sum,  # Cumulative total for Energy Dashboard
                )
            )

        # Insert statistics into Home Assistant recorder
        coordinator.logger.debug(
            "Adding %d %s statistics to recorder", len(statistic_data), resolution
        )

        # Check if recorder is available before inserting statistics
        if DATA_INSTANCE not in coordinator.hass.data:
            coordinator.logger.warning(
                "Recorder not available, skipping %s statistics insertion",
                resolution,
            )
            return

        async_add_external_statistics(coordinator.hass, metadata, statistic_data)
        coordinator.logger.debug("Successfully inserted %s statistics", resolution)

    except Exception as err:
        coordinator.logger.warning(
            "Failed to insert %s statistics for account %s: %s",
            resolution,
            coordinator.config_entry.data.get(CONF_USERNAME, "unknown")[:3] + "***",
            err,
        )


async def async_insert_legacy_statistics(coordinator, daily_usage: float) -> None:
    """Insert legacy daily statistics (backward compatibility).

    Creates a single daily statistic data point for the current day.
    Used when legacy data format (float) is provided to async_insert_statistics.

    Args:
        daily_usage: Total water usage for the day in gallons.

    Logs warnings if insertion fails but does not raise exceptions.
    """
    try:
        # Create statistic metadata for daily water usage
        # Use unified statistic ID (same as all other resolutions)
        account_number = coordinator.config_entry.data.get(CONF_USERNAME, "default")
        # Sanitize account number (lowercase, replace special chars)
        safe_account = account_number.lower().replace("-", "_").replace(" ", "_")
        metadata = StatisticMetaData(
            has_mean=False,
            has_sum=True,
            mean_type=StatisticMeanType.NONE,
            name="San Francisco Water Power Sewer",
            source=DOMAIN,
            statistic_id=f"{DOMAIN}:{safe_account}_water_consumption",
            unit_class=VOLUME,
            unit_of_measurement=UnitOfVolume.GALLONS,
        )

        # Get current date for the statistic
        now = dt_util.now()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Create statistic data point
        statistic_data = [
            StatisticData(
                start=start_of_day,
                state=daily_usage,
                sum=daily_usage,
            )
        ]

        # Insert statistics into Home Assistant recorder

        # Check if recorder is available before inserting statistics
        if DATA_INSTANCE not in coordinator.hass.data:
            coordinator.logger.warning(
                "Recorder not available, skipping legacy statistics insertion"
            )
            return

        async_add_external_statistics(coordinator.hass, metadata, statistic_data)

    except Exception as err:
        coordinator.logger.warning(
            "Failed to insert legacy water usage statistics for account %s: %s",
            coordinator.config_entry.data.get(CONF_USERNAME, "unknown")[:3] + "***",
            err,
        )
