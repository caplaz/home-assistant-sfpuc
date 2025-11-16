"""Tests for the repairs platform."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from custom_components.sfpuc.repairs import (
    SFWaterCredentialsRepair,
    async_create_fix_flow,
)


class TestRepairs:
    """Test suite for repairs framework."""

    async def test_credentials_repair_init_step(self, hass, config_entry):
        """Test the repair flow init step."""
        flow = SFWaterCredentialsRepair()
        flow.hass = hass
        flow.context = {"entry_id": config_entry.entry_id, "account": "testuser"}  # type: ignore[assignment,typeddict-unknown-key]

        result = await flow.async_step_init()
        assert result["type"] == "form"
        assert result["step_id"] == "repair_confirm"

    async def test_credentials_repair_confirm_step(self, hass, config_entry):
        """Test the repair flow confirm step without input."""
        flow = SFWaterCredentialsRepair()
        flow.hass = hass
        flow.context = {"entry_id": config_entry.entry_id, "account": "testuser"}  # type: ignore[assignment,typeddict-unknown-key]

        result = await flow.async_step_confirm()
        assert result["type"] == "form"
        assert result["step_id"] == "repair_confirm"
        assert "data_schema" in result

    async def test_credentials_repair_updates_entry(self, hass, config_entry):
        """Test the repair flow updating config entry."""
        flow = SFWaterCredentialsRepair()
        flow.hass = hass
        flow.context = {"entry_id": config_entry.entry_id, "account": "testuser"}  # type: ignore[assignment,typeddict-unknown-key]

        user_input = {"username": "newuser", "password": "newpass"}

        # Mock config_entries methods
        with patch.object(
            hass.config_entries, "async_entries", return_value=[config_entry]
        ):
            with patch.object(hass.config_entries, "async_update_entry"):
                with patch.object(
                    hass.config_entries, "async_reload", new_callable=AsyncMock
                ):
                    result = await flow.async_step_confirm(user_input)

        assert result["type"] == "abort"
        assert result["reason"] == "credential_updated"

    async def test_async_create_fix_flow(self, hass):
        """Test creating a fix flow."""
        data = {"entry_id": "test_entry", "account": "testuser"}
        flow = await async_create_fix_flow(hass, "invalid_credentials", data)

        assert isinstance(flow, SFWaterCredentialsRepair)
        assert flow.context["entry_id"] == "test_entry"
        assert flow.context["account"] == "testuser"

    async def test_async_create_fix_flow_unknown_issue(self, hass):
        """Test creating a fix flow for unknown issue."""
        data = {"entry_id": "test_entry"}

        with pytest.raises(ValueError, match="Unknown issue"):
            await async_create_fix_flow(hass, "unknown_issue", data)
