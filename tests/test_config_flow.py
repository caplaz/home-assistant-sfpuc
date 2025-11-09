"""Tests for SF Water config flow."""

from homeassistant.data_entry_flow import FlowResultType
import pytest

from custom_components.sf_water.config_flow import ConfigFlowHandler, OptionsFlowHandler

from .common import MockConfigEntry


class TestSFWaterConfigFlow:
    """Test the SF Water config flow."""

    @pytest.fixture(autouse=True)
    def setup_method(self, hass):
        """Set up test fixtures."""
        self.hass = hass
        self.config_entry = MockConfigEntry()

    @pytest.mark.asyncio
    async def test_config_flow_user_step(self, hass):
        """Test the user step of the config flow."""
        flow = ConfigFlowHandler()
        flow.hass = hass

        result = await flow.async_step_user()

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"
        assert "username" in result["data_schema"].schema
        assert "password" in result["data_schema"].schema

    def test_config_flow_get_options_flow(self, hass):
        """Test getting the options flow."""
        config_entry = MockConfigEntry()

        options_flow_class = ConfigFlowHandler.async_get_options_flow(config_entry)
        assert options_flow_class is not None

        # Test that it's the correct class
        assert isinstance(options_flow_class, OptionsFlowHandler)
