"""Sensor platform for SFPUC integration."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SENSOR_USAGE, SENSOR_COST
from .coordinator import SFPUCCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SFPUC sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        SFPUCUsageSensor(coordinator, entry),
        SFPUCCostSensor(coordinator, entry),
    ]

    async_add_entities(entities)


class SFPUCUsageSensor(SensorEntity):
    """SFPUC water usage sensor."""

    def __init__(self, coordinator: SFPUCCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__()
        self.coordinator = coordinator
        self.config_entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}_{SENSOR_USAGE}"
        self._attr_name = "Water Usage"
        self._attr_native_unit_of_measurement = "ccf"
        self._attr_device_class = "water"
        self._attr_state_class = "total_increasing"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get("usage")

    @property
    def available(self):
        """Return if entity is available."""
        return self.coordinator.last_update_success


class SFPUCCostSensor(SensorEntity):
    """SFPUC water cost sensor."""

    def __init__(self, coordinator: SFPUCCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__()
        self.coordinator = coordinator
        self.config_entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}_{SENSOR_COST}"
        self._attr_name = "Current Bill Water Cost"
        self._attr_native_unit_of_measurement = "USD"
        self._attr_device_class = "monetary"
        self._attr_state_class = "total"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get("cost")

    @property
    def available(self):
        """Return if entity is available."""
        return self.coordinator.last_update_success