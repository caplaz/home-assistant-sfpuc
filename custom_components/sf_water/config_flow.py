"""Config flow for SF Water integration."""

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import CONF_PASSWORD, CONF_UPDATE_INTERVAL, CONF_USERNAME, DEFAULT_UPDATE_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class SFWaterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SF Water."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                # Validate credentials by attempting login
                from .coordinator import SFPUCScraper
                scraper = SFPUCScraper(user_input[CONF_USERNAME], user_input[CONF_PASSWORD])
                if scraper.login():
                    return self.async_create_entry(
                        title="SF Water",
                        data={
                            CONF_USERNAME: user_input[CONF_USERNAME],
                            CONF_PASSWORD: user_input[CONF_PASSWORD],
                        },
                        options={
                            CONF_UPDATE_INTERVAL: user_input.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
                        },
                    )
                else:
                    errors["base"] = "invalid_auth"
            except Exception as e:
                _LOGGER.error("Error during config flow: %s", e)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): vol.All(
                    vol.Coerce(int), vol.Range(min=15, max=1440)
                ),
            }),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return SFWaterOptionsFlowHandler(config_entry)


class SFWaterOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for SF Water."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=self.config_entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
                ): vol.All(vol.Coerce(int), vol.Range(min=15, max=1440)),
            }),
        )
