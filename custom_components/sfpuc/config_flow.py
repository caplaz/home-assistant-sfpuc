"""Config flow for SFPUC integration."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_FLO_USERNAME,
    CONF_FLO_PASSWORD,
)


class SFPUCConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SFPUC."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Validate SFPUC credentials
            try:
                # Add validation logic here
                pass
            except Exception:
                errors["base"] = "auth"

            # Validate Flo credentials if provided
            if user_input.get(CONF_FLO_USERNAME) and user_input.get(CONF_FLO_PASSWORD):
                try:
                    # Add Flo validation logic here
                    pass
                except Exception:
                    errors["base"] = "flo_auth"

            if not errors:
                return self.async_create_entry(
                    title="SFPUC",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Optional(CONF_FLO_USERNAME): str,
                    vol.Optional(CONF_FLO_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return SFPUCOptionsFlow(config_entry)


class SFPUCOptionsFlow(config_entries.OptionsFlow):
    """Handle options."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_FLO_USERNAME,
                        default=self.config_entry.data.get(CONF_FLO_USERNAME, ""),
                    ): str,
                    vol.Optional(
                        CONF_FLO_PASSWORD,
                        default=self.config_entry.data.get(CONF_FLO_PASSWORD, ""),
                    ): str,
                }
            ),
        )