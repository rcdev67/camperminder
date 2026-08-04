"""Gemeinsame Basis aller Entitäten dieser Integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, SIGNAL_UPDATE
from .coordinator import CamperCoordinator


class CamperEntity(Entity):
    """Hängt am Rechenkern und gehört zum selben Gerät."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self, coordinator: CamperCoordinator, entry: ConfigEntry, key: str
    ) -> None:
        self.coordinator = coordinator
        self._entry_id = entry.entry_id
        self._role = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="CamperMaid",
            model="CamperMaid",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Rollenkennung für die mitgelieferte Karte.

        Die Karte sucht ihre Entitäten über diese Kennung statt über
        Entity-IDs - die hängen an übersetzten Namen und ändern sich, sobald
        jemand das Gerät umbenennt.
        """
        return {"camper_role": self._role}

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_UPDATE.format(self._entry_id),
                self.async_write_ha_state,
            )
        )
