"""Repairs platform for San Francisco Water Power Sewer integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.repairs import RepairsFlow  # type: ignore[attr-defined]
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
import voluptuous as vol

from .const import CONF_PASSWORD, DOMAIN

_LOGGER = __import__("logging").getLogger(__name__)


async def async_create_fix_flow(
    hass: HomeAssistant, issue_id: str, data: dict[str, Any] | None
) -> RepairsFlow:
    """Create a repairs flow for the given issue.

    This is called by Home Assistant when a user initiates a repair
    for an issue created by this integration. Note: The RepairsFlowManager
    automatically sets flow.issue_id and flow.data after this function returns.
    """
    _LOGGER.debug("Creating fix flow for issue %s with data: %s", issue_id, data)
    if issue_id == "invalid_credentials":
        return SFWaterCredentialsRepair()

    raise ValueError(f"Unknown issue: {issue_id}")


class SFWaterCredentialsRepair(RepairsFlow):
    """Handler for credential issue repairs."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the first step of the repair flow."""
        return await self.async_step_confirm_repair()

    async def async_step_confirm_repair(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the confirm step of the repair flow."""
        # Get the config entry from self.data (set by RepairsFlowManager)
        config_entry_id = self.data.get("entry_id") if self.data else None
        config_entry = None

        if config_entry_id:
            for entry in self.hass.config_entries.async_entries(DOMAIN):
                if entry.entry_id == config_entry_id:
                    config_entry = entry
                    break

        if user_input is not None and config_entry:
            # Update the config entry with new password (username stays the same)
            self.hass.config_entries.async_update_entry(
                config_entry,
                data={
                    **config_entry.data,
                    CONF_PASSWORD: user_input.get(CONF_PASSWORD),
                },
            )
            # Reload the config entry
            await self.hass.config_entries.async_reload(config_entry.entry_id)

            return self.async_abort(reason="credential_updated")

        # Get account from self.data (automatically populated by RepairsFlowManager)
        account = "unknown"
        if self.data:
            account = self.data.get("account", "unknown")
        _LOGGER.debug("Showing repair form with account from self.data: %s", account)

        return self.async_show_form(
            step_id="confirm_repair",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            description_placeholders={
                "account": account,
            },
        )
