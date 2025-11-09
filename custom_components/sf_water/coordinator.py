"""Coordinator for SF Water integration."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any

from bs4 import BeautifulSoup
from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import async_add_external_statistics
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
import requests

from .const import CONF_PASSWORD, CONF_UPDATE_INTERVAL, CONF_USERNAME, DOMAIN


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
            # GET the login page to extract ViewState
            login_url = f"{self.base_url}/"
            response = self.session.get(login_url)
            soup = BeautifulSoup(response.content, "html.parser")

            # Extract hidden form fields
            viewstate = soup.find("input", {"name": "__VIEWSTATE"})
            eventvalidation = soup.find("input", {"name": "__EVENTVALIDATION"})
            viewstate_generator = soup.find("input", {"name": "__VIEWSTATEGENERATOR"})

            if not viewstate or not eventvalidation:
                return False

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
            response = self.session.post(
                login_url, data=login_data, allow_redirects=True
            )

            # Check if login successful
            if "MY_ACCOUNT_RSF.aspx" in response.url or "Welcome" in response.text:
                return True
            else:
                return False

        except Exception:
            return False

    def get_daily_usage(self) -> float | None:
        """Get today's water usage in gallons."""
        try:
            # Navigate to hourly usage page
            usage_url = f"{self.base_url}/USE_HOURLY.aspx"
            response = self.session.get(usage_url)
            soup = BeautifulSoup(response.content, "html.parser")

            # Extract form tokens
            tokens = {}
            form = soup.find("form")
            if form:
                for inp in form.find_all("input"):
                    name = inp.get("name")
                    if name:
                        tokens[name] = inp.get("value", "")

            # Set download parameters for today's usage
            today = datetime.now().strftime("%m/%d/%Y")
            tokens.update(
                {
                    "img_EXCEL_DOWNLOAD_IMAGE.x": "8",
                    "img_EXCEL_DOWNLOAD_IMAGE.y": "13",
                    "tb_DAILY_USE": "Hourly+Use",
                    "SD": today,
                    "dl_UOM": "GALLONS",
                }
            )

            # POST to trigger download
            download_url = f"{self.base_url}/USE_HOURLY.aspx"
            response = self.session.post(
                download_url, data=tokens, allow_redirects=True
            )

            if "TRANSACTIONS_EXCEL_DOWNLOAD.aspx" in response.url:
                # Parse the Excel data
                content = response.content.decode("utf-8", errors="ignore")
                lines = content.split("\n")

                total_usage = 0.0
                for line in lines[1:]:  # Skip header
                    if line.strip():
                        parts = line.split("\t")
                        if len(parts) >= 2:
                            try:
                                usage = float(parts[1])
                                total_usage += usage
                            except (ValueError, IndexError):
                                continue

                return total_usage
            else:
                return None

        except Exception:
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
            update_interval=timedelta(
                minutes=config_entry.options.get(CONF_UPDATE_INTERVAL, 60)
            ),
        )
        self.config_entry = config_entry
        self.scraper = SFPUCScraper(
            config_entry.data[CONF_USERNAME],
            config_entry.data[CONF_PASSWORD],
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from SF PUC."""
        try:
            # Login (run in executor since it's blocking)
            loop = asyncio.get_event_loop()
            login_success = await loop.run_in_executor(None, self.scraper.login)

            if not login_success:
                raise UpdateFailed("Failed to login to SF PUC")

            # Get daily usage (run in executor since it's blocking)
            daily_usage = await loop.run_in_executor(None, self.scraper.get_daily_usage)

            if daily_usage is None:
                raise UpdateFailed("Failed to retrieve usage data")

            data = {
                "daily_usage": daily_usage,
                "last_updated": datetime.now(),
            }

            # Insert statistics for Energy dashboard (like OPOWER)
            await self._async_insert_statistics(daily_usage)

            return data

        except Exception as err:
            raise UpdateFailed(f"Error updating SF Water data: {err}") from err

    async def _async_insert_statistics(self, daily_usage: float) -> None:
        """Insert water usage statistics into Home Assistant (like OPOWER)."""
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
            self.logger.warning("Failed to insert water usage statistics: %s", err)
