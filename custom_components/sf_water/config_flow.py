"""Config flow for SF Water integration."""

import asyncio
import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
import voluptuous as vol

from .const import CONF_PASSWORD, CONF_USERNAME, DOMAIN
from .coordinator import SFPUCScraper

_LOGGER = logging.getLogger(__name__)


class ConfigFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SF Water."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            _LOGGER.debug(
                "Attempting to validate SFPUC credentials for user: %s",
                user_input[CONF_USERNAME][:3] + "***",
            )
            try:
                # Validate credentials by attempting login (run in executor to avoid blocking)
                scraper = SFPUCScraper(
                    user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
                )
                _LOGGER.debug("Created scraper instance, attempting login...")
                loop = asyncio.get_event_loop()
                login_success = await loop.run_in_executor(None, scraper.login)

                if login_success:
                    _LOGGER.info(
                        "Successfully validated SFPUC credentials for user: %s",
                        user_input[CONF_USERNAME][:3] + "***",
                    )
                    return self.async_create_entry(
                        title="SF Water",
                        data={
                            CONF_USERNAME: user_input[CONF_USERNAME],
                            CONF_PASSWORD: user_input[CONF_PASSWORD],
                        },
                    )
                else:
                    _LOGGER.warning(
                        "SFPUC login failed for user: %s",
                        user_input[CONF_USERNAME][:3] + "***",
                    )
                    errors["base"] = "invalid_auth"
            except Exception as e:
                _LOGGER.error("Error during config flow validation: %s", e)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for SF Water."""

    def __init__(self):
        """Initialize options flow."""
        pass

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        # No configurable options - update interval is fixed for daily data
        return self.async_create_entry(title="", data={})
