"""Tests for San Francisco Water Power Sewer sensors."""

from unittest.mock import Mock

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType

from custom_components.sfpuc.coordinator import SFWaterCoordinator
from custom_components.sfpuc.sensor import WATER_SENSORS, SFWaterSensor

from .common import MockConfigEntry


class TestSFWaterSensor:
    """Test the San Francisco Water Power Sewer sensor functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.hass = Mock(spec=HomeAssistant)
        self.config_entry = MockConfigEntry()
        self.coordinator = Mock(spec=SFWaterCoordinator)
        self.coordinator.config_entry = self.config_entry
        self.coordinator.data = {
            "current_bill_usage": 150.5,
            "last_updated": "2023-10-01T12:00:00Z",
        }

    def test_sensor_initialization(self):
        """Test sensor initialization."""
        description = WATER_SENSORS[0]  # Daily usage sensor
        sensor = SFWaterSensor(self.coordinator, description)

        assert sensor.coordinator == self.coordinator
        assert sensor.entity_description == description
        assert (
            sensor._attr_unique_id
            == "water_account_test@example.com_current_bill_water_usage_to_date"
        )
        assert sensor._attr_device_info["entry_type"] == DeviceEntryType.SERVICE
        assert sensor._attr_device_info["identifiers"] == {
            ("sfpuc", self.config_entry.entry_id)
        }
        assert sensor._attr_device_info["manufacturer"] == "SFPUC"
        assert sensor._attr_device_info["model"] == "Water Usage"
        assert sensor._attr_device_info["name"] == "San Francisco Water Power Sewer"

    def test_daily_usage_sensor_properties(self):
        """Test daily usage sensor properties."""
        description = WATER_SENSORS[0]  # Daily usage sensor
        sensor = SFWaterSensor(self.coordinator, description)

        assert sensor.device_class == SensorDeviceClass.WATER
        assert sensor.native_unit_of_measurement == UnitOfVolume.GALLONS
        assert (
            sensor.state_class is None
        )  # No state_class to prevent duplicate statistics
        assert sensor.suggested_display_precision == 1

    def test_hourly_usage_sensor_properties(self):
        """Test hourly usage sensor properties."""
        # This sensor is no longer implemented
        pass

    def test_monthly_usage_sensor_properties(self):
        """Test monthly usage sensor properties."""
        # This sensor is no longer implemented
        pass

    def test_daily_usage_sensor_value(self):
        """Test daily usage sensor value."""
        description = WATER_SENSORS[0]  # Daily usage sensor
        sensor = SFWaterSensor(self.coordinator, description)

        assert sensor.native_value == 150.5

    def test_hourly_usage_sensor_value(self):
        """Test hourly usage sensor value."""
        # This sensor is no longer implemented
        pass

    def test_monthly_usage_sensor_value(self):
        """Test monthly usage sensor value."""
        # This sensor is no longer implemented
        pass

    def test_sensor_value_with_missing_data(self):
        """Test sensor value when data is missing."""
        self.coordinator.data = {}
        description = WATER_SENSORS[0]  # Daily usage sensor
        sensor = SFWaterSensor(self.coordinator, description)

        assert sensor.native_value == 0  # Default value

    def test_sensor_descriptions_count(self):
        """Test that we have the expected number of sensor descriptions."""
        assert len(WATER_SENSORS) == 1

    def test_sensor_descriptions_keys(self):
        """Test sensor description keys."""
        keys = [desc.key for desc in WATER_SENSORS]
        assert "current_bill_water_usage_to_date" in keys

    def test_sensor_descriptions_translation_keys(self):
        """Test sensor description translation keys."""
        translation_keys = [desc.translation_key for desc in WATER_SENSORS]
        assert "current_bill_water_usage_to_date" in translation_keys

    def test_extra_state_attributes_expose_data_freshness(self):
        """The sensor reports how current the underlying statistics are.

        The state is derived from statistics already in the recorder, so it
        stays plausible when collection breaks. These attributes are what
        make that visible.
        """
        from datetime import datetime, timezone

        data_through = datetime(2026, 9, 6, 23, 0, tzinfo=timezone.utc)
        self.coordinator.data = {
            "current_bill_usage": 150.5,
            "last_updated": "2026-09-08T12:00:00Z",
            "data_through": data_through,
            "data_age_days": 1.5,
        }

        sensor = SFWaterSensor(self.coordinator, WATER_SENSORS[0])

        assert sensor.extra_state_attributes == {
            "data_through": "2026-09-06T23:00:00+00:00",
            "data_age_days": 1.5,
        }

    def test_extra_state_attributes_without_freshness_data(self):
        """Missing freshness data yields None rather than raising."""
        self.coordinator.data = {"current_bill_usage": 0}

        sensor = SFWaterSensor(self.coordinator, WATER_SENSORS[0])

        assert sensor.extra_state_attributes == {
            "data_through": None,
            "data_age_days": None,
        }
