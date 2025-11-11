"""Utility functions for SFPUC coordinator."""

from collections import Counter
from datetime import datetime, timedelta

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import statistics_during_period
from homeassistant.util import dt as dt_util

from .const import CONF_USERNAME, DOMAIN


def calculate_billing_period(coordinator) -> tuple[datetime, datetime]:
    """Calculate current SFPUC billing period dates.

    Uses billing day detected from monthly data, or defaults to 25th.

    Returns:
        Tuple of (bill_start_date, bill_end_date)
    """
    # Use detected billing day (will be set during first data fetch)
    # Default to 25 if not yet detected
    billing_day = (
        coordinator._billing_day if coordinator._billing_day is not None else 25
    )

    today = datetime.now()
    current_month_bill_date = today.replace(
        day=billing_day, hour=0, minute=0, second=0, microsecond=0
    )

    if today.day < billing_day:
        # Haven't hit this month's bill date yet
        # Period started last month's billing day
        if today.month == 1:
            bill_start = current_month_bill_date.replace(year=today.year - 1, month=12)
        else:
            bill_start = current_month_bill_date.replace(month=today.month - 1)
        bill_end = current_month_bill_date
    else:
        # Past this month's bill date
        # Period started this month's billing day
        bill_start = current_month_bill_date
        if today.month == 12:
            bill_end = current_month_bill_date.replace(year=today.year + 1, month=1)
        else:
            bill_end = current_month_bill_date.replace(month=today.month + 1)

    return bill_start, bill_end


async def async_detect_billing_day(coordinator) -> int:
    """Detect billing day from monthly statistics.

    Analyzes monthly billing data to determine the billing cycle day.
    Falls back to default of 25th if detection fails.

    Returns:
        Billing day of month (1-31)
    """
    if coordinator._billing_day is not None:
        return coordinator._billing_day

    try:
        # Query monthly statistics to detect billing pattern
        safe_account = (
            coordinator.config_entry.data.get(CONF_USERNAME, "unknown")
            .replace("-", "_")
            .lower()
        )
        stat_id = f"{DOMAIN}:{safe_account}_water_consumption"

        # Get last 3 months of billing data
        three_months_ago = datetime.now() - timedelta(days=90)
        stats = await get_instance(coordinator.hass).async_add_executor_job(
            statistics_during_period,
            coordinator.hass,
            dt_util.as_utc(three_months_ago),
            None,  # end_time (None = now)
            {stat_id},
            "month",
            None,
            {"state"},
        )

        if stats and stat_id in stats and len(stats[stat_id]) >= 2:
            # Extract days from monthly billing timestamps
            billing_days: list[int] = []
            for stat in stats[stat_id]:
                start_time = stat.get("start")
                if start_time and isinstance(start_time, datetime):
                    # Convert to local timezone for accurate day extraction
                    local_time = dt_util.as_local(start_time)
                    billing_days.append(local_time.day)

            # Use the most common billing day
            if billing_days:
                most_common = Counter(billing_days).most_common(1)[0][0]
                coordinator._billing_day = most_common
                coordinator.logger.info(
                    "Detected billing day: %d (from %d monthly records)",
                    coordinator._billing_day,
                    len(billing_days),
                )
                return coordinator._billing_day

        # Fallback to default
        coordinator._billing_day = 25
        coordinator.logger.info("Using default billing day: 25")
        return coordinator._billing_day

    except Exception as err:
        coordinator.logger.warning(
            "Failed to detect billing day, using default 25: %s", err
        )
        coordinator._billing_day = 25
        return coordinator._billing_day
