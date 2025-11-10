"""Config flow for San Francisco Water Power Sewer integration."""

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
    """Handle a config flow for San Francisco Water Power Sewer.

    Manages the initial setup flow for adding the integration to Home Assistant.
    Validates SFPUC account credentials by attempting login before creating the config entry.
    """

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step.

        Prompts user for SFPUC account username and password, validates them
        by attempting login, and creates a config entry if successful.

        Args:
            user_input: Dictionary containing CONF_USERNAME and CONF_PASSWORD
                       provided by the user. None on initial call.

        Returns:
            ConfigFlowResult containing either a form for user input or
            a created config entry.
        """
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
                        title="San Francisco Water Power Sewer",
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
        """Create the options flow.

        Args:
            config_entry: The config entry for which options are being managed.

        Returns:
            An OptionsFlowHandler instance for managing integration options.
        """
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for San Francisco Water Power Sewer.

    Manages credential updates after the integration has been added to Home Assistant.
    Allows users to change their SFPUC account credentials.
    """

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options.

        Prompts user for updated SFPUC credentials, validates them by
        attempting login, and updates the config entry if successful.

        Args:
            user_input: Dictionary containing CONF_USERNAME and CONF_PASSWORD
                       provided by the user. None on initial call.

        Returns:
            ConfigFlowResult containing either a form for user input or
            a created options entry.
        """
        if user_input is not None:
            # Validate new credentials
            errors = {}
            try:
                _LOGGER.debug(
                    "Attempting to validate new SFPUC credentials for user: %s",
                    user_input[CONF_USERNAME][:3] + "***",
                )

                # Validate credentials by attempting login
                scraper = SFPUCScraper(
                    user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
                )
                _LOGGER.debug("Created scraper instance, attempting login...")
                loop = asyncio.get_event_loop()
                login_success = await loop.run_in_executor(None, scraper.login)

                if login_success:
                    _LOGGER.info(
                        "Successfully validated new SFPUC credentials for user: %s",
                        user_input[CONF_USERNAME][:3] + "***",
                    )
                    # Update the config entry data with new credentials
                    self.hass.config_entries.async_update_entry(
                        self.config_entry,
                        data={
                            CONF_USERNAME: user_input[CONF_USERNAME],
                            CONF_PASSWORD: user_input[CONF_PASSWORD],
                        },
                    )
                    return self.async_create_entry(title="", data={})
                else:
                    _LOGGER.warning(
                        "SFPUC login failed for user: %s",
                        user_input[CONF_USERNAME][:3] + "***",
                    )
                    errors["base"] = "invalid_auth"
            except Exception as e:
                _LOGGER.error("Error during options flow validation: %s", e)
                errors["base"] = "unknown"

            if errors:
                return self.async_show_form(
                    step_id="init",
                    data_schema=self._get_options_schema(),
                    errors=errors,
                )

        return self.async_show_form(
            step_id="init",
            data_schema=self._get_options_schema(),
        )

    def _get_options_schema(self):
        """Get the options schema.

        Returns a Voluptuous schema for the options form, with the current
        username pre-filled as the default value.

        Returns:
            Voluptuous Schema for credential input.
        """
        current_username = self.config_entry.data.get(CONF_USERNAME, "")

        return vol.Schema(
            {
                vol.Required(CONF_USERNAME, default=current_username): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )
