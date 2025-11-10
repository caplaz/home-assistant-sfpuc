"""Tests for SF Water sensors."""

from unittest.mock import Mock

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType

from custom_components.sfpuc.coordinator import SFWaterCoordinator
from custom_components.sfpuc.sensor import WATER_SENSORS, SFWaterSensor

from .common import MockConfigEntry


class TestSFWaterSensor:
    """Test the SF Water sensor functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.hass = Mock(spec=HomeAssistant)
        self.config_entry = MockConfigEntry()
        self.coordinator = Mock(spec=SFWaterCoordinator)
        self.coordinator.config_entry = self.config_entry
        self.coordinator.data = {
            "daily_usage": 150.5,
            "hourly_usage": 25.0,
            "monthly_usage": 1200.0,
            "last_updated": "2023-10-01T12:00:00Z",
        }

    def test_sensor_initialization(self):
        """Test sensor initialization."""
        description = WATER_SENSORS[0]  # Daily usage sensor
        sensor = SFWaterSensor(self.coordinator, description)

        assert sensor.coordinator == self.coordinator
        assert sensor.entity_description == description
        assert sensor._attr_unique_id == f"{self.config_entry.entry_id}_daily_usage"
        assert sensor._attr_device_info["entry_type"] == DeviceEntryType.SERVICE
        assert sensor._attr_device_info["identifiers"] == {
            ("sfpuc", self.config_entry.entry_id)
        }
        assert sensor._attr_device_info["manufacturer"] == "SFPUC"
        assert sensor._attr_device_info["model"] == "Water Usage"
        assert sensor._attr_device_info["name"] == "SF Water"

    def test_daily_usage_sensor_properties(self):
        """Test daily usage sensor properties."""
        description = WATER_SENSORS[0]  # Daily usage sensor
        sensor = SFWaterSensor(self.coordinator, description)

        assert sensor.device_class == SensorDeviceClass.WATER
        assert sensor.native_unit_of_measurement == UnitOfVolume.GALLONS
        assert sensor.state_class == SensorStateClass.TOTAL_INCREASING
        assert sensor.suggested_display_precision == 1

    def test_hourly_usage_sensor_properties(self):
        """Test hourly usage sensor properties."""
        description = WATER_SENSORS[1]  # Hourly usage sensor
        sensor = SFWaterSensor(self.coordinator, description)

        assert sensor.device_class == SensorDeviceClass.WATER
        assert sensor.native_unit_of_measurement == UnitOfVolume.GALLONS
        assert sensor.state_class == SensorStateClass.TOTAL_INCREASING
        assert sensor.suggested_display_precision == 2

    def test_monthly_usage_sensor_properties(self):
        """Test monthly usage sensor properties."""
        description = WATER_SENSORS[2]  # Monthly usage sensor
        sensor = SFWaterSensor(self.coordinator, description)

        assert sensor.device_class == SensorDeviceClass.WATER
        assert sensor.native_unit_of_measurement == UnitOfVolume.GALLONS
        assert sensor.state_class == SensorStateClass.TOTAL_INCREASING
        assert sensor.suggested_display_precision == 1

    def test_daily_usage_sensor_value(self):
        """Test daily usage sensor value."""
        description = WATER_SENSORS[0]  # Daily usage sensor
        sensor = SFWaterSensor(self.coordinator, description)

        assert sensor.native_value == 150.5

    def test_hourly_usage_sensor_value(self):
        """Test hourly usage sensor value."""
        description = WATER_SENSORS[1]  # Hourly usage sensor
        sensor = SFWaterSensor(self.coordinator, description)

        assert sensor.native_value == 25.0

    def test_monthly_usage_sensor_value(self):
        """Test monthly usage sensor value."""
        description = WATER_SENSORS[2]  # Monthly usage sensor
        sensor = SFWaterSensor(self.coordinator, description)

        assert sensor.native_value == 1200.0

    def test_sensor_value_with_missing_data(self):
        """Test sensor value when data is missing."""
        self.coordinator.data = {}
        description = WATER_SENSORS[0]  # Daily usage sensor
        sensor = SFWaterSensor(self.coordinator, description)

        assert sensor.native_value == 0  # Default value

    def test_sensor_descriptions_count(self):
        """Test that we have the expected number of sensor descriptions."""
        assert len(WATER_SENSORS) == 3

    def test_sensor_descriptions_keys(self):
        """Test sensor description keys."""
        keys = [desc.key for desc in WATER_SENSORS]
        assert "daily_usage" in keys
        assert "hourly_usage" in keys
        assert "monthly_usage" in keys

    def test_sensor_descriptions_translation_keys(self):
        """Test sensor description translation keys."""
        translation_keys = [desc.translation_key for desc in WATER_SENSORS]
        assert "daily_usage" in translation_keys
        assert "hourly_usage" in translation_keys
        assert "monthly_usage" in translation_keys
