"""Tests for SF Water integration initialization."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from custom_components.sfpuc import async_setup_entry, async_unload_entry

from .common import MockConfigEntry


class TestSFWaterIntegration:
    """Test the SF Water integration setup and teardown."""

    @pytest.fixture(autouse=True)
    def setup_method(self, hass):
        """Set up test fixtures."""
        self.hass = hass
        self.config_entry = MockConfigEntry()

    @patch("custom_components.sfpuc.SFWaterCoordinator")
    async def test_async_setup_entry_success(
        self, mock_coordinator_class, hass, config_entry
    ):
        """Test successful integration setup."""
        mock_coordinator = Mock()
        mock_coordinator_class.return_value = mock_coordinator
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()

        # Mock async_setup_entry for sensors
        with patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
            return_value=None,
        ) as mock_forward:
            result = await async_setup_entry(hass, config_entry)

            assert result is True
            # Verify coordinator was created and stored
            mock_coordinator_class.assert_called_once_with(hass, config_entry)
            assert config_entry.runtime_data == mock_coordinator
            # Verify refresh was called
            mock_coordinator.async_config_entry_first_refresh.assert_called_once()
            # Verify platforms were forwarded
            mock_forward.assert_called_once_with(config_entry, ["sensor"])

    @patch("custom_components.sfpuc.SFWaterCoordinator")
    async def test_async_setup_entry_coordinator_refresh_failure(
        self, mock_coordinator_class, hass, config_entry
    ):
        """Test integration setup with coordinator refresh failure."""
        mock_coordinator = Mock()
        mock_coordinator_class.return_value = mock_coordinator
        mock_coordinator.async_config_entry_first_refresh = AsyncMock(
            side_effect=Exception("Refresh failed")
        )

        with pytest.raises(Exception, match="Refresh failed"):
            await async_setup_entry(hass, config_entry)

    async def test_async_unload_entry_success(self, hass, config_entry):
        """Test successful integration unload."""
        # Mock the config entry runtime data
        mock_coordinator = Mock()
        config_entry.runtime_data = mock_coordinator

        # Mock the platform unloading
        with patch(
            "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
            return_value=True,
        ) as mock_unload:
            result = await async_unload_entry(hass, config_entry)

            assert result is True
            mock_unload.assert_called_once_with(config_entry, ["sensor"])

    async def test_async_unload_entry_no_coordinator(self, hass, config_entry):
        """Test unload when no coordinator is present."""
        config_entry.runtime_data = None

        # Mock the platform unloading
        with patch(
            "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
            return_value=True,
        ) as mock_unload:
            result = await async_unload_entry(hass, config_entry)

            assert result is True
            mock_unload.assert_called_once_with(config_entry, ["sensor"])

    async def test_async_unload_entry_coordinator_unload_failure(
        self, hass, config_entry
    ):
        """Test unload when coordinator unload fails."""
        # Mock the config entry runtime data
        mock_coordinator = Mock()
        config_entry.runtime_data = mock_coordinator

        # Mock the platform unloading to fail
        with patch(
            "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
            return_value=False,
        ) as mock_unload:
            result = await async_unload_entry(hass, config_entry)

            assert result is False
            mock_unload.assert_called_once_with(config_entry, ["sensor"])
