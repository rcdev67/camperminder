"""Binärsensor: steht das Fahrzeug eben?"""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import CamperCoordinator
from .entity import CamperEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: CamperCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([CamperLevelBinarySensor(coordinator, entry)])


class CamperLevelBinarySensor(CamperEntity, BinarySensorEntity):
    """An, wenn das Fahrzeug innerhalb der eingestellten Toleranz steht."""

    _attr_icon = "mdi:spirit-level"

    def __init__(self, coordinator: CamperCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "level")

    @property
    def available(self) -> bool:
        # Ohne Messwerte lieber nicht verfügbar sein, als fälschlich "eben"
        # zu melden. Ein stiller Sensor fällt auf, ein falsches Ja nicht.
        return self.coordinator.available

    @property
    def is_on(self) -> bool:
        return self.coordinator.is_level
