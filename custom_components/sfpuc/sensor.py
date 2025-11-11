"""Sensor entities for San Francisco Water Power Sewer integration."""

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

from .const import CONF_USERNAME, DOMAIN
from .coordinator import SFWaterCoordinator

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class SFWaterEntityDescription(SensorEntityDescription):
    """Class describing San Francisco Water Power Sewer sensors entities.

    Extends SensorEntityDescription with a value_fn that extracts the
    appropriate value from coordinator data for each sensor type.
    """

    value_fn: Callable[[dict[str, Any]], StateType | date]


# Water usage sensors
WATER_SENSORS: tuple[SFWaterEntityDescription, ...] = (
    # Primary sensor: Current billing period usage to date
    SFWaterEntityDescription(
        key="current_bill_water_usage_to_date",
        translation_key="current_bill_water_usage_to_date",
        device_class=SensorDeviceClass.WATER,
        native_unit_of_measurement=UnitOfVolume.GALLONS,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("current_bill_usage", 0),
    ),
)


class SFWaterSensor(CoordinatorEntity[SFWaterCoordinator], SensorEntity):
    """San Francisco Water Power Sewer sensor entity.

    Displays current billing period water usage data fetched by the coordinator.
    Creates a single primary sensor showing cumulative usage since last bill.
    """

    entity_description: SFWaterEntityDescription

    def __init__(
        self,
        coordinator: SFWaterCoordinator,
        description: SFWaterEntityDescription,
    ) -> None:
        """Initialize the sensor.

        Args:
            coordinator: The data update coordinator instance.
            description: The sensor entity description with value extraction function.
        """
        super().__init__(coordinator)
        self.entity_description = description
        config_entry = cast(ConfigEntry[Any], coordinator.config_entry)
        # Generate unique_id that creates the proper entity_id
        account_number = coordinator.config_entry.data.get(CONF_USERNAME, "unknown")
        self._attr_unique_id = f"water_account_{account_number}_{description.key}"
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, config_entry.entry_id)},
            manufacturer="SFPUC",
            model="Water Usage",
            name="San Francisco Water Power Sewer",
        )

    @property
    def native_value(self) -> StateType | date:
        """Return the state of the sensor.

        Calls the value_fn from the entity description to extract the
        appropriate value from coordinator data.

        Returns:
            The current state of the sensor (typically a float for usage in gallons).
        """
        return self.entity_description.value_fn(self.coordinator.data)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry[Any],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up San Francisco Water Power Sewer sensors.

    Creates a single primary sensor entity showing current billing period
    water usage from the coordinator and adds it to Home Assistant.

    Args:
        hass: Home Assistant instance.
        config_entry: The config entry for this integration.
        async_add_entities: Callback to register newly created entities.
    """
    coordinator = config_entry.runtime_data

    async_add_entities(
        [SFWaterSensor(coordinator, description) for description in WATER_SENSORS]
    )
