"""Coordinator for San Francisco Water Power Sewer integration."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any

from bs4 import BeautifulSoup
from homeassistant.components.recorder import (
    DATA_INSTANCE,
)
from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
import requests

from .const import CONF_PASSWORD, CONF_USERNAME, DEFAULT_UPDATE_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class SFPUCScraper:
    """SF PUC water usage data scraper.

    This class handles web scraping of water usage data from the SFPUC
    (San Francisco Public Utilities Commission) online portal at
    myaccount-water.sfpuc.org. It manages authentication, form submission,
    and parsing of downloaded usage data in various resolutions.
    """

    def __init__(self, username: str, password: str) -> None:
        """Initialize the scraper.

        Args:
            username: SFPUC account username/account number.
            password: SFPUC account password.
        """
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.base_url = "https://myaccount-water.sfpuc.org"

        # Mimic a real browser
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )

    def login(self) -> bool:
        """Authenticate with SFPUC portal.

        Performs ASP.NET authentication with the SFPUC portal by:
        1. Fetching the login page to extract ASP.NET view state and event validation tokens
        2. Submitting credentials via POST with the extracted tokens
        3. Analyzing response for success/failure indicators

        Returns:
            True if login was successful, False otherwise.
        """
        try:
            _LOGGER.debug(
                "Starting SFPUC login process for user: %s", self.username[:3] + "***"
            )

            # GET the login page to extract ViewState
            login_url = f"{self.base_url}/"
            _LOGGER.debug("Fetching login page: %s", login_url)
            response = self.session.get(login_url)
            _LOGGER.debug("Login page response status: %s", response.status_code)

            soup = BeautifulSoup(response.content, "html.parser")

            # Extract hidden form fields
            viewstate = soup.find("input", {"name": "__VIEWSTATE"})
            eventvalidation = soup.find("input", {"name": "__EVENTVALIDATION"})
            viewstate_generator = soup.find("input", {"name": "__VIEWSTATEGENERATOR"})

            if not viewstate or not eventvalidation:
                _LOGGER.warning("Failed to extract form tokens from login page")
                return False

            _LOGGER.debug("Successfully extracted form tokens")

            # Login form data
            login_data = {
                "__EVENTTARGET": "",
                "__EVENTARGUMENT": "",
                "__VIEWSTATE": viewstate["value"],
                "__VIEWSTATEGENERATOR": (
                    viewstate_generator["value"] if viewstate_generator else ""
                ),
                "__SCROLLPOSITIONX": "0",
                "__SCROLLPOSITIONY": "0",
                "__EVENTVALIDATION": eventvalidation["value"],
                "tb_USER_ID": self.username,
                "tb_USER_PSWD": self.password,
                "cb_REMEMBER_ME": "on",
                "btn_SIGN_IN_BUTTON": "Sign+in",
            }

            # Submit login
            _LOGGER.debug("Submitting login form")
            response = self.session.post(
                login_url, data=login_data, allow_redirects=True
            )
            _LOGGER.debug(
                "Login response status: %s, URL: %s", response.status_code, response.url
            )

            # Check if login successful
            # Look for indicators of successful login vs failure
            if response.status_code == 200:
                # Check for common success indicators
                success_indicators = [
                    "MY_ACCOUNT_RSF.aspx" in response.url,
                    "Welcome" in response.text,
                    "Dashboard" in response.text,
                    "Account" in response.text,
                    "Usage" in response.text,
                    "Logout" in response.text,
                ]

                # Check for failure indicators
                failure_indicators = [
                    "Invalid" in response.text and "password" in response.text.lower(),
                    "Login failed" in response.text,
                    "Authentication failed" in response.text,
                    "Error" in response.text and "login" in response.text.lower(),
                    "Please try again" in response.text,
                    response.url.endswith("/"),  # Still on login page
                ]

                success_score = sum(success_indicators)
                failure_score = sum(failure_indicators)

                _LOGGER.debug(
                    "Login analysis - Success indicators: %d, Failure indicators: %d",
                    success_score,
                    failure_score,
                )
                _LOGGER.debug("Response URL: %s", response.url)
                _LOGGER.debug(
                    "Response contains 'Welcome': %s", "Welcome" in response.text
                )
                _LOGGER.debug(
                    "Response contains 'Invalid': %s", "Invalid" in response.text
                )

                if success_score > 0 and failure_score == 0:
                    _LOGGER.info(
                        "SFPUC login successful for user: %s", self.username[:3] + "***"
                    )
                    return True
                else:
                    _LOGGER.warning(
                        "SFPUC login failed - success_score: %d, failure_score: %d",
                        success_score,
                        failure_score,
                    )
                    return False
            else:
                _LOGGER.warning(
                    "SFPUC login failed with status code: %s", response.status_code
                )
                return False

        except Exception as e:
            _LOGGER.error("Exception during SFPUC login: %s", e)
            return False

    def get_usage_data(
        self,
        start_date: datetime,
        end_date: datetime | None = None,
        resolution: str = "hourly",
    ) -> list[dict[str, Any]] | None:
        """Get water usage data for the specified date range and resolution.

        Args:
            start_date: Start date for data retrieval
            end_date: End date for data retrieval (defaults to start_date)
            resolution: Data resolution - "hourly", "daily", or "monthly"

        Returns:
            List of usage data points with timestamps and values
        """
        if end_date is None:
            end_date = start_date

        try:
            _LOGGER.debug(
                "Fetching %s usage data from %s to %s",
                resolution,
                start_date.date(),
                end_date.date(),
            )

            # Navigate to appropriate usage page based on resolution
            if resolution == "hourly":
                usage_url = f"{self.base_url}/USE_HOURLY.aspx"
                data_type = "Hourly+Use"
            elif resolution == "daily":
                usage_url = f"{self.base_url}/USE_DAILY.aspx"
                data_type = "Daily+Use"
            elif resolution == "monthly":
                # Use the billed usage page for monthly data
                usage_url = f"{self.base_url}/USE_BILLED.aspx"
                data_type = "Billed+Use"
            else:
                _LOGGER.error("Invalid resolution specified: %s", resolution)
                return None

            _LOGGER.debug("Navigating to usage page: %s", usage_url)
            response = self.session.get(usage_url)
            _LOGGER.debug("Usage page response status: %s", response.status_code)

            soup = BeautifulSoup(response.content, "html.parser")

            # Extract form tokens
            tokens = {}
            form = soup.find("form")
            if form:
                for inp in form.find_all("input"):
                    name = inp.get("name")
                    if name:
                        tokens[name] = inp.get("value", "")

            _LOGGER.debug("Extracted %d form tokens", len(tokens))

            # Set download parameters
            tokens.update(
                {
                    "img_EXCEL_DOWNLOAD_IMAGE.x": "8",
                    "img_EXCEL_DOWNLOAD_IMAGE.y": "13",
                    "tb_DAILY_USE": data_type,
                    "SD": start_date.strftime("%m/%d/%Y"),
                    "ED": end_date.strftime("%m/%d/%Y"),
                    "dl_UOM": "GALLONS",
                }
            )

            # POST to trigger download
            if resolution == "monthly":
                download_url = f"{self.base_url}/USE_BILLED.aspx"
            else:
                download_url = f"{self.base_url}/USE_{resolution.upper()}.aspx"
            _LOGGER.debug("Triggering Excel download from: %s", download_url)
            response = self.session.post(
                download_url, data=tokens, allow_redirects=True
            )
            _LOGGER.debug(
                "Download response status: %s, URL: %s",
                response.status_code,
                response.url,
            )

            if "TRANSACTIONS_EXCEL_DOWNLOAD.aspx" in response.url:
                # Parse the Excel data
                content = response.content.decode("utf-8", errors="ignore")
                lines = content.split("\n")
                _LOGGER.debug("Downloaded content has %d lines", len(lines))

                usage_data = []
                for line in lines[1:]:  # Skip header
                    if line.strip():
                        parts = line.split("\t")
                        if len(parts) >= 2:
                            try:
                                # Parse timestamp and usage
                                timestamp_str = parts[0].strip()
                                usage = float(parts[1])

                                # Parse timestamp based on resolution
                                if resolution == "hourly":
                                    # Try multiple formats for hourly data
                                    timestamp = None
                                    # First try full datetime format (for tests)
                                    try:
                                        timestamp = datetime.strptime(
                                            timestamp_str, "%m/%d/%Y %H:%M:%S"
                                        )
                                    except ValueError:
                                        pass

                                    # If that fails, try AM/PM format without date (real SFPUC format)
                                    if timestamp is None:
                                        try:
                                            # Handle AM/PM format like "12 AM", "1 PM"
                                            if timestamp_str.upper().endswith(
                                                " AM"
                                            ) or timestamp_str.upper().endswith(" PM"):
                                                hour_str = timestamp_str.split()[0]
                                                am_pm = timestamp_str.split()[1].upper()
                                                hour = int(hour_str)
                                                if am_pm == "PM" and hour != 12:
                                                    hour += 12
                                                elif am_pm == "AM" and hour == 12:
                                                    hour = 0
                                                # Use current date for the timestamp
                                                current_date = datetime.now().date()
                                                timestamp = datetime.combine(
                                                    current_date,
                                                    datetime.min.time().replace(
                                                        hour=hour
                                                    ),
                                                )
                                        except (ValueError, IndexError):
                                            pass

                                    if timestamp is None:
                                        _LOGGER.debug(
                                            "Failed to parse hourly timestamp: %s",
                                            timestamp_str,
                                        )
                                        continue

                                elif resolution == "daily":
                                    # Try multiple formats for daily data
                                    timestamp = None
                                    # First try full date format (for tests)
                                    try:
                                        timestamp = datetime.strptime(
                                            timestamp_str, "%m/%d/%Y"
                                        )
                                    except ValueError:
                                        pass

                                    # If that fails, try MM/DD format without year (real SFPUC format)
                                    if timestamp is None:
                                        try:
                                            month, day = map(
                                                int, timestamp_str.split("/")
                                            )
                                            current_year = datetime.now().year
                                            timestamp = datetime(
                                                current_year, month, day
                                            )
                                        except (ValueError, IndexError):
                                            pass

                                    if timestamp is None:
                                        _LOGGER.debug(
                                            "Failed to parse daily timestamp: %s",
                                            timestamp_str,
                                        )
                                        continue

                                elif resolution == "monthly":
                                    # Try multiple formats for monthly data
                                    timestamp = None
                                    # First try MM/YYYY format (for tests)
                                    try:
                                        timestamp = datetime.strptime(
                                            timestamp_str, "%m/%Y"
                                        )
                                    except ValueError:
                                        pass

                                    # If that fails, try "Mon YY" format (real SFPUC format like "Dec 23")
                                    if timestamp is None:
                                        try:
                                            # Parse "Dec 23" format - month abbreviation and 2-digit year
                                            month_name, year_str = timestamp_str.split()
                                            # Convert month name to number
                                            month = datetime.strptime(
                                                month_name, "%b"
                                            ).month
                                            # Convert 2-digit year to 4-digit (assuming 2000s)
                                            year = 2000 + int(year_str)
                                            timestamp = datetime(year, month, 1)
                                        except (ValueError, IndexError):
                                            pass

                                    if timestamp is None:
                                        _LOGGER.debug(
                                            "Failed to parse monthly timestamp: %s",
                                            timestamp_str,
                                        )
                                        continue

                                usage_data.append(
                                    {
                                        "timestamp": timestamp,
                                        "usage": usage,
                                        "resolution": resolution,
                                    }
                                )
                            except (ValueError, IndexError) as e:
                                _LOGGER.debug(
                                    "Failed to parse line: %s, error: %s",
                                    line.strip(),
                                    e,
                                )
                                continue

                _LOGGER.info(
                    "Successfully parsed %d %s data points", len(usage_data), resolution
                )
                return usage_data
            else:
                _LOGGER.warning("Download failed - unexpected URL: %s", response.url)
                return None

        except Exception as e:
            _LOGGER.error("Exception during data retrieval: %s", e)
            return None

    def get_daily_usage(self) -> float | None:
        """Get today's water usage in gallons (legacy method for backward compatibility).

        Convenience method that aggregates hourly usage data for the current day.

        Returns:
            Total water usage for today in gallons, or None if data retrieval fails.
        """
        today = datetime.now()
        data = self.get_usage_data(today, today, "hourly")
        if data:
            # Sum all hourly usage for the day
            return sum(item["usage"] for item in data)
        return None


class SFWaterCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """San Francisco Water Power Sewer data update coordinator.

    Manages periodic data fetching from SFPUC portal and caching via
    DataUpdateCoordinator pattern. Handles statistics insertion into
    Home Assistant's recorder component for historical tracking and
    statistics card integration.
    """

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

    def _calculate_billing_period(self) -> tuple[datetime, datetime]:
        """Calculate current SFPUC billing period dates.

        SFPUC typically bills on the 25th of each month based on sample data.
        This could be made dynamic by parsing billing dates from monthly data.

        Returns:
            Tuple of (bill_start_date, bill_end_date)
        """
        # TODO: Make billing day dynamic by parsing from monthly billing data
        # For now, use 25th as observed in sample data (May 25, Jun 25, Jul 25)
        billing_day = 25

        today = datetime.now()
        current_month_bill_date = today.replace(
            day=billing_day, hour=0, minute=0, second=0, microsecond=0
        )

        if today.day < billing_day:
            # Haven't hit this month's bill date yet
            # Period started last month's billing day
            if today.month == 1:
                bill_start = current_month_bill_date.replace(
                    year=today.year - 1, month=12
                )
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
                raise UpdateFailed("Failed to login to SF PUC")

            self.logger.debug("Login successful, proceeding with data fetch")

            # Fetch historical data on first run
            if not self._historical_data_fetched:
                self.logger.debug("First run - fetching historical data")
                await self._async_fetch_historical_data()
                self._historical_data_fetched = True

            # Perform backfilling if needed (30-day lookback)
            await self._async_backfill_missing_data()

            # Calculate billing period dates (SFPUC bills ~25th of each month)
            bill_start, bill_end = self._calculate_billing_period()
            self.logger.debug(
                "Current billing period: %s to %s",
                bill_start.date(),
                bill_end.date(),
            )

            # Fetch usage for current billing period (accumulated since last bill date)
            self.logger.debug(
                "Fetching current billing period usage data from %s to %s",
                bill_start.date(),
                datetime.now().date(),
            )
            period_data = await loop.run_in_executor(
                None, self.scraper.get_usage_data, bill_start, datetime.now(), "daily"
            )
            current_bill_usage = (
                sum(item["usage"] for item in period_data) if period_data else 0
            )
            self.logger.debug(
                "Calculated current billing period usage: %.2f gallons from %d daily readings",
                current_bill_usage,
                len(period_data) if period_data else 0,
            )

            # Return simplified data for the single sensor
            data = {
                "current_bill_usage": current_bill_usage,
                "last_updated": datetime.now(),
            }

            # Insert current statistics (daily data for the current period)
            if period_data:
                self.logger.debug("Inserting current period statistics")
                await self._async_insert_statistics(period_data)

            self.logger.info(
                "Data update completed successfully - Current billing period usage: %.2f gallons",
                current_bill_usage,
            )
            return data

        except Exception as err:
            self.logger.error(
                "Error updating San Francisco Water Power Sewer data: %s", err
            )
            raise UpdateFailed(
                f"Error updating San Francisco Water Power Sewer data: {err}"
            ) from err

    async def _async_fetch_historical_data(self) -> None:
        """Fetch historical data going back months/years on first run.

        Populates recorder statistics with:
        - Daily usage data for the past 2 years
        - Hourly usage data for the past 30 days

        Note: Monthly billing cycle data is skipped as SFPUC billing cycles
        do not align with calendar months (typically 25th-25th).

        Logs warnings if data retrieval fails but does not raise exceptions
        to avoid blocking the initial coordinator setup.
        """
        try:
            self.logger.info("Fetching historical water usage data...")

            # Fetch data at different resolutions
            end_date = datetime.now()
            loop = asyncio.get_event_loop()

            # Skip monthly data fetching - SFPUC provides billing cycle data (25th-25th)
            # which doesn't align with calendar months and may be confusing for users
            self.logger.info(
                "Skipping monthly historical data fetch - using daily data for historical trends"
            )

            # Fetch daily data for the past 2 years (comprehensive historical data)
            start_date = end_date - timedelta(days=730)
            self.logger.debug(
                "Fetching daily data from %s to %s", start_date.date(), end_date.date()
            )
            daily_data = await loop.run_in_executor(
                None, self.scraper.get_usage_data, start_date, end_date, "daily"
            )
            if daily_data:
                await self._async_insert_statistics(daily_data)
                self.logger.info("Fetched %d daily data points", len(daily_data))
            else:
                self.logger.warning("No daily data retrieved")

            # Fetch hourly data for the past 30 days (most detailed recent data)
            start_date = end_date - timedelta(days=30)
            self.logger.debug(
                "Fetching hourly data from %s to %s", start_date.date(), end_date.date()
            )
            hourly_data = await loop.run_in_executor(
                None, self.scraper.get_usage_data, start_date, end_date, "hourly"
            )
            if hourly_data:
                await self._async_insert_statistics(hourly_data)
                self.logger.info("Fetched %d hourly data points", len(hourly_data))
            else:
                self.logger.warning("No hourly data retrieved")

        except Exception as err:
            self.logger.warning("Failed to fetch historical data: %s", err)

    async def _async_backfill_missing_data(self) -> None:
        """Backfill missing data with 30-day lookback window.

        Runs daily to ensure complete historical data in recorder by:
        1. Checking for missing daily data in the past 30 days
        2. Checking for missing hourly data in the past 7 days
        3. Inserting any missing data points into statistics

        Throttled to run at most once per 24 hours to avoid excessive
        API calls to SFPUC portal.

        Logs warnings if backfilling fails but does not raise exceptions.
        """
        try:
            now = datetime.now()

            # Check if we need to backfill (run this less frequently)
            if self._last_backfill_date and (
                now - self._last_backfill_date
            ) < timedelta(hours=24):
                return

            self.logger.debug("Checking for missing data to backfill...")

            # Look back 30 days for any missing data
            lookback_date = now - timedelta(days=30)

            loop = asyncio.get_event_loop()

            # Check for missing daily data in the lookback period
            daily_data = await loop.run_in_executor(
                None, self.scraper.get_usage_data, lookback_date, now, "daily"
            )
            if daily_data:
                await self._async_insert_statistics(daily_data)
                self.logger.debug("Backfilled %d daily data points", len(daily_data))

            # Check for missing hourly data in the recent past (last 7 days)
            recent_start = now - timedelta(days=7)
            hourly_data = await loop.run_in_executor(
                None, self.scraper.get_usage_data, recent_start, now, "hourly"
            )
            if hourly_data:
                await self._async_insert_statistics(hourly_data)
                self.logger.debug("Backfilled %d hourly data points", len(hourly_data))

            self._last_backfill_date = now

        except Exception as err:
            self.logger.warning("Failed to backfill missing data: %s", err)

    async def _async_insert_statistics(
        self, usage_data: float | list[dict[str, Any]]
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
                self.logger.debug(
                    "Inserting legacy statistics format: %.2f", usage_data
                )
                await self._async_insert_legacy_statistics(usage_data)
                return

            # New format: list of data points
            if not usage_data:
                self.logger.debug("No usage data to insert")
                return

            self.logger.debug(
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

            self.logger.debug(
                "Grouped data - Hourly: %d, Daily: %d, Monthly: %d",
                len(hourly_data),
                len(daily_data),
                len(monthly_data),
            )

            # Insert statistics for each resolution
            if hourly_data:
                await self._async_insert_resolution_statistics(hourly_data, "hourly")
            if daily_data:
                await self._async_insert_resolution_statistics(daily_data, "daily")
            if monthly_data:
                await self._async_insert_resolution_statistics(monthly_data, "monthly")

        except Exception as err:
            self.logger.warning("Failed to insert water usage statistics: %s", err)

    async def _async_insert_resolution_statistics(
        self, data_points: list[dict[str, Any]], resolution: str
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
            self.logger.debug(
                "Inserting %d %s statistics", len(data_points), resolution
            )

            # Create statistic metadata based on resolution
            if resolution == "hourly":
                # Include account number in statistic ID for multi-account support
                account_number = self.config_entry.data.get(CONF_USERNAME, "default")
                # Sanitize account number (lowercase, replace special chars)
                safe_account = (
                    account_number.lower().replace("-", "_").replace(" ", "_")
                )
                stat_id = f"{DOMAIN}:{safe_account}_water_hourly_consumption"
                name = "San Francisco Water Power Sewer Hourly Usage"
                has_sum = True
            elif resolution == "daily":
                # Include account number in statistic ID for multi-account support
                account_number = self.config_entry.data.get(CONF_USERNAME, "default")
                # Sanitize account number (lowercase, replace special chars)
                safe_account = (
                    account_number.lower().replace("-", "_").replace(" ", "_")
                )
                stat_id = f"{DOMAIN}:{safe_account}_water_daily_consumption"
                name = "San Francisco Water Power Sewer Daily Usage"
                has_sum = True
            elif resolution == "monthly":
                # Include account number in statistic ID for multi-account support
                account_number = self.config_entry.data.get(CONF_USERNAME, "default")
                # Sanitize account number (lowercase, replace special chars)
                safe_account = (
                    account_number.lower().replace("-", "_").replace(" ", "_")
                )
                stat_id = f"{DOMAIN}:{safe_account}_water_monthly_consumption"
                name = "San Francisco Water Power Sewer Monthly Usage"
                has_sum = True
            else:
                self.logger.error("Unknown resolution for statistics: %s", resolution)
                return

            metadata = StatisticMetaData(  # type: ignore[typeddict-item]
                has_mean=False,
                has_sum=has_sum,
                mean_type=StatisticMeanType.NONE,
                name=name,
                source=DOMAIN,
                statistic_id=stat_id,
                unit_of_measurement=UnitOfVolume.GALLONS,
            )

            # Create statistic data points
            statistic_data = []
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

                # Convert naive timestamp to timezone-aware (assume PST/PDT for SF)
                if start_time.tzinfo is None:
                    # Use America/Los_Angeles timezone for San Francisco
                    sf_timezone = dt_util.get_time_zone("America/Los_Angeles")
                    start_time = start_time.replace(tzinfo=sf_timezone)

                statistic_data.append(
                    StatisticData(
                        start=start_time,
                        state=usage,
                        sum=usage,
                    )
                )

            # Insert statistics into Home Assistant recorder
            self.logger.debug(
                "Adding %d %s statistics to recorder", len(statistic_data), resolution
            )

            # Check if recorder is available before inserting statistics
            if DATA_INSTANCE not in self.hass.data:
                self.logger.warning(
                    "Recorder not available, skipping %s statistics insertion",
                    resolution,
                )
                return

            async_add_external_statistics(self.hass, metadata, statistic_data)
            self.logger.debug("Successfully inserted %s statistics", resolution)

        except Exception as err:
            self.logger.warning("Failed to insert %s statistics: %s", resolution, err)

    async def _async_insert_legacy_statistics(self, daily_usage: float) -> None:
        """Insert legacy daily statistics (backward compatibility).

        Creates a single daily statistic data point for the current day.
        Used when legacy data format (float) is provided to _async_insert_statistics.

        Args:
            daily_usage: Total water usage for the day in gallons.

        Logs warnings if insertion fails but does not raise exceptions.
        """
        try:
            # Create statistic metadata for daily water usage
            # Include account number in statistic ID for multi-account support
            account_number = self.config_entry.data.get(CONF_USERNAME, "default")
            # Sanitize account number (lowercase, replace special chars)
            safe_account = account_number.lower().replace("-", "_").replace(" ", "_")
            metadata = StatisticMetaData(  # type: ignore[typeddict-item]
                has_mean=False,
                has_sum=True,
                mean_type=StatisticMeanType.NONE,
                name="San Francisco Water Power Sewer Daily Usage",
                source=DOMAIN,
                statistic_id=f"{DOMAIN}:{safe_account}_water_daily_consumption",
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
            if DATA_INSTANCE not in self.hass.data:
                self.logger.warning(
                    "Recorder not available, skipping legacy statistics insertion"
                )
                return

            async_add_external_statistics(self.hass, metadata, statistic_data)

        except Exception as err:
            self.logger.warning(
                "Failed to insert legacy water usage statistics: %s", err
            )
