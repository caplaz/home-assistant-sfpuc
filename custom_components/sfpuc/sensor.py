"""Sensor entities for SF Water integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
import logging
from typing import Any, cast

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SFWaterCoordinator

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class SFWaterEntityDescription(SensorEntityDescription):
    """Class describing SF Water sensors entities."""

    value_fn: Callable[[dict[str, Any]], StateType | date]


# Water usage sensors
WATER_SENSORS: tuple[SFWaterEntityDescription, ...] = (
    SFWaterEntityDescription(
        key="daily_usage",
        translation_key="daily_usage",
        device_class=SensorDeviceClass.WATER,
        native_unit_of_measurement=UnitOfVolume.GALLONS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("daily_usage", 0),
    ),
    SFWaterEntityDescription(
        key="hourly_usage",
        translation_key="hourly_usage",
        device_class=SensorDeviceClass.WATER,
        native_unit_of_measurement=UnitOfVolume.GALLONS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        value_fn=lambda data: data.get("hourly_usage", 0),
    ),
    SFWaterEntityDescription(
        key="monthly_usage",
        translation_key="monthly_usage",
        device_class=SensorDeviceClass.WATER,
        native_unit_of_measurement=UnitOfVolume.GALLONS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("monthly_usage", 0),
    ),
    # TODO: Add more sensors like usage_to_date, forecasted_usage, etc.
)


class SFWaterSensor(CoordinatorEntity[SFWaterCoordinator], SensorEntity):
    """SF Water sensor entity."""

    entity_description: SFWaterEntityDescription

    def __init__(
        self,
        coordinator: SFWaterCoordinator,
        description: SFWaterEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        config_entry = cast(ConfigEntry[Any], coordinator.config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, config_entry.entry_id)},
            manufacturer="SFPUC",
            model="Water Usage",
            name="SF Water",
        )

    @property
    def native_value(self) -> StateType | date:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.coordinator.data)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry[Any],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up SF Water sensors."""
    coordinator = config_entry.runtime_data

    async_add_entities(
        SFWaterSensor(coordinator, description) for description in WATER_SENSORS
    )
