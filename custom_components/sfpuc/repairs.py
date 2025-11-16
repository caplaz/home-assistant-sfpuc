"""Repairs platform for San Francisco Water Power Sewer integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.repairs import RepairsFlow  # type: ignore[attr-defined]
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
import voluptuous as vol

from .const import DOMAIN

_LOGGER = __import__("logging").getLogger(__name__)


async def async_create_fix_flow(
    hass: HomeAssistant, issue_id: str, data: dict[str, Any]
) -> RepairsFlow:
    """Create a repairs flow for the given issue.

    This is called by Home Assistant when a user initiates a repair
    for an issue created by this integration.
    """
    if issue_id == "invalid_credentials":
        flow = SFWaterCredentialsRepair()
        flow.hass = hass
        flow.context = {  # type: ignore[assignment,typeddict-unknown-key]
            "entry_id": data.get("entry_id"),
            "account": data.get("account", "unknown"),
            "source": "repairs",
        }
        return flow

    raise ValueError(f"Unknown issue: {issue_id}")


class SFWaterCredentialsRepair(RepairsFlow):
    """Handler for credential issue repairs."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the first step of the repair flow."""
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the confirm step of the repair flow."""
        if user_input is not None:
            # Get the config entry from context
            config_entry_id = self.context.get("entry_id")
            config_entry = None

            if config_entry_id:
                for entry in self.hass.config_entries.async_entries(DOMAIN):
                    if entry.entry_id == config_entry_id:
                        config_entry = entry
                        break

            if config_entry:
                # Update the config entry with new credentials
                self.hass.config_entries.async_update_entry(
                    config_entry,
                    data={
                        **config_entry.data,
                        "username": user_input.get("username"),
                        "password": user_input.get("password"),
                    },
                )
                # Reload the config entry
                await self.hass.config_entries.async_reload(config_entry.entry_id)

            return self.async_abort(reason="credential_updated")

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema(
                {
                    vol.Required("username"): str,  # type: ignore[dict-item]
                    vol.Required("password"): str,  # type: ignore[dict-item]
                }
            ),
            description_placeholders={
                "account": self.context.get("account", "unknown"),  # type: ignore[dict-item]
            },
            last_step=True,
        )
