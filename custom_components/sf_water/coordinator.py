"""Coordinator for SF Water integration."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any

from bs4 import BeautifulSoup
from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import (
    StatisticMeanType,
    async_add_external_statistics,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
import requests

from .const import CONF_PASSWORD, CONF_USERNAME, DEFAULT_UPDATE_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class SFPUCScraper:
    """SF PUC water usage data scraper."""

    def __init__(self, username: str, password: str) -> None:
        """Initialize the scraper."""
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
        """Login to SFPUC account."""
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
            if "MY_ACCOUNT_RSF.aspx" in response.url or "Welcome" in response.text:
                _LOGGER.info(
                    "SFPUC login successful for user: %s", self.username[:3] + "***"
                )
                return True
            else:
                _LOGGER.warning(
                    "SFPUC login failed - unexpected response. URL: %s", response.url
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
                usage_url = f"{self.base_url}/USE_MONTHLY.aspx"
                data_type = "Monthly+Use"
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
                                    # Format: MM/DD/YYYY HH:MM:SS
                                    timestamp = datetime.strptime(
                                        timestamp_str, "%m/%d/%Y %H:%M:%S"
                                    )
                                elif resolution == "daily":
                                    # Format: MM/DD/YYYY
                                    timestamp = datetime.strptime(
                                        timestamp_str, "%m/%d/%Y"
                                    )
                                elif resolution == "monthly":
                                    # Format: MM/YYYY
                                    timestamp = datetime.strptime(
                                        timestamp_str, "%m/%Y"
                                    )

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
        """Get today's water usage in gallons (legacy method for backward compatibility)."""
        today = datetime.now()
        data = self.get_usage_data(today, today, "hourly")
        if data:
            # Sum all hourly usage for the day
            return sum(item["usage"] for item in data)
        return None


class SFWaterCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """SF Water data update coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry[Any],
    ) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            logger=hass.data[DOMAIN]["logger"],
            name=DOMAIN,
            update_interval=timedelta(minutes=DEFAULT_UPDATE_INTERVAL),
        )
        self.config_entry = config_entry
        self.scraper = SFPUCScraper(
            config_entry.data[CONF_USERNAME],
            config_entry.data[CONF_PASSWORD],
        )
        self._last_backfill_date: datetime | None = None
        self._historical_data_fetched = False

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from SF PUC."""
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

            # Get current daily usage
            today = datetime.now()
            self.logger.debug("Fetching current daily usage data for %s", today.date())
            daily_data = await loop.run_in_executor(
                None, self.scraper.get_usage_data, today, today, "hourly"
            )

            if not daily_data:
                self.logger.error("Failed to retrieve current usage data")
                raise UpdateFailed("Failed to retrieve current usage data")

            # Sum hourly data for daily total
            daily_usage = sum(item["usage"] for item in daily_data)
            self.logger.debug(
                "Calculated daily usage: %.2f gallons from %d hourly readings",
                daily_usage,
                len(daily_data),
            )

            # Get latest hourly usage (most recent hour)
            hourly_usage = daily_data[-1]["usage"] if daily_data else 0
            self.logger.debug("Latest hourly usage: %.2f gallons", hourly_usage)

            # Get current monthly usage (sum of daily data this month)
            start_of_month = today.replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
            self.logger.debug(
                "Fetching monthly usage data from %s to %s",
                start_of_month.date(),
                today.date(),
            )
            monthly_data = await loop.run_in_executor(
                None, self.scraper.get_usage_data, start_of_month, today, "daily"
            )
            monthly_usage = (
                sum(item["usage"] for item in monthly_data) if monthly_data else 0
            )
            self.logger.debug(
                "Calculated monthly usage: %.2f gallons from %d daily readings",
                monthly_usage,
                len(monthly_data) if monthly_data else 0,
            )

            data = {
                "daily_usage": daily_usage,
                "hourly_usage": hourly_usage,
                "monthly_usage": monthly_usage,
                "last_updated": datetime.now(),
            }

            # Insert current statistics
            self.logger.debug("Inserting current statistics")
            await self._async_insert_statistics(daily_data)

            self.logger.info(
                "Data update completed successfully - Daily: %.2f, Hourly: %.2f, Monthly: %.2f",
                daily_usage,
                hourly_usage,
                monthly_usage,
            )
            return data

        except Exception as err:
            self.logger.error("Error updating SF Water data: %s", err)
            raise UpdateFailed(f"Error updating SF Water data: {err}") from err

    async def _async_fetch_historical_data(self) -> None:
        """Fetch historical data going back months/years on first run."""
        try:
            self.logger.info("Fetching historical water usage data...")

            # Fetch data at different resolutions
            # Start with monthly data for the past 2 years
            end_date = datetime.now()
            start_date = end_date - timedelta(days=730)  # 2 years

            loop = asyncio.get_event_loop()
            self.logger.debug(
                "Fetching monthly data from %s to %s",
                start_date.date(),
                end_date.date(),
            )

            # Fetch monthly data
            monthly_data = await loop.run_in_executor(
                None, self.scraper.get_usage_data, start_date, end_date, "monthly"
            )
            if monthly_data:
                await self._async_insert_statistics(monthly_data)
                self.logger.info("Fetched %d monthly data points", len(monthly_data))
            else:
                self.logger.warning("No monthly data retrieved")

            # Fetch daily data for the past 90 days (more detailed recent data)
            start_date = end_date - timedelta(days=90)
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
        """Backfill missing data with 30-day lookback window."""
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
        """Insert water usage statistics into Home Assistant."""
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

            # Group data by resolution
            hourly_data = []
            daily_data = []
            monthly_data = []

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
        """Insert statistics for a specific resolution."""
        try:
            self.logger.debug(
                "Inserting %d %s statistics", len(data_points), resolution
            )

            # Create statistic metadata based on resolution
            if resolution == "hourly":
                stat_id = f"{DOMAIN}:hourly_usage"
                name = "SF Water Hourly Usage"
                has_sum = True
                unit_class = "volume"
            elif resolution == "daily":
                stat_id = f"{DOMAIN}:daily_usage"
                name = "SF Water Daily Usage"
                has_sum = True
                unit_class = "volume"
            elif resolution == "monthly":
                stat_id = f"{DOMAIN}:monthly_usage"
                name = "SF Water Monthly Usage"
                has_sum = True
                unit_class = "volume"
            else:
                self.logger.error("Unknown resolution for statistics: %s", resolution)
                return

            metadata = StatisticMetaData(
                has_mean=False,
                has_sum=has_sum,
                mean_type=StatisticMeanType.NONE,
                name=name,
                source=DOMAIN,
                statistic_id=stat_id,
                unit_class=unit_class,
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
            async_add_external_statistics(self.hass, metadata, statistic_data)
            self.logger.debug("Successfully inserted %s statistics", resolution)

        except Exception as err:
            self.logger.warning("Failed to insert %s statistics: %s", resolution, err)

    async def _async_insert_legacy_statistics(self, daily_usage: float) -> None:
        """Insert legacy daily statistics (backward compatibility)."""
        try:
            # Create statistic metadata for daily water usage
            metadata = StatisticMetaData(
                has_mean=False,
                has_sum=True,
                mean_type=StatisticMeanType.NONE,
                name="SF Water Daily Usage",
                source=DOMAIN,
                statistic_id=f"{DOMAIN}:daily_usage",
                unit_class="volume",
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
            async_add_external_statistics(self.hass, metadata, statistic_data)

        except Exception as err:
            self.logger.warning(
                "Failed to insert legacy water usage statistics: %s", err
            )
