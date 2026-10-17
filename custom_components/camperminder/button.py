"""Knopf: Heimatort auf den Standort des Fahrzeugs setzen."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import CamperCoordinator
from .entity import CamperEntity
from .heimatort import HeimatortFolger


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    stored = hass.data[DOMAIN][entry.entry_id]
    # Nur mit GPS-Quelle - ohne sie weiß niemand, wo "hier" ist.
    if (folger := stored.get("heimatort")) is not None:
        async_add_entities([CamperHomeHereButton(stored["coordinator"], entry, folger)])


class CamperHomeHereButton(CamperEntity, ButtonEntity):
    """Für die erste Einrichtung und für alle, die nicht automatisch wollen."""

    _attr_icon = "mdi:home-map-marker"

    def __init__(
        self, coordinator: CamperCoordinator, entry: ConfigEntry, folger: HeimatortFolger
    ) -> None:
        super().__init__(coordinator, entry, "home_here")
        self._folger = folger

    async def async_press(self) -> None:
        await self._folger.async_hierher()
