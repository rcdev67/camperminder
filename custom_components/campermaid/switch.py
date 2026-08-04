"""Schalter: Sprachansage und Präzisionsmodus."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .coordinator import CamperCoordinator
from .entity import CamperEntity


@dataclass(frozen=True, kw_only=True)
class CamperSwitchDescription(SwitchEntityDescription):
    value_key: str


SWITCHES: tuple[CamperSwitchDescription, ...] = (
    # Beide starten bewusst ausgeschaltet: eine Verhaltenserweiterung soll
    # niemanden überraschen, der die Integration gerade erst einrichtet.
    CamperSwitchDescription(
        key="voice",
        translation_key="voice",
        value_key="voice",
        icon="mdi:bullhorn",
    ),
    CamperSwitchDescription(
        key="precise",
        translation_key="precise",
        value_key="precise",
        icon="mdi:target",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: CamperCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(
        CamperSwitch(coordinator, entry, description) for description in SWITCHES
    )


class CamperSwitch(CamperEntity, SwitchEntity, RestoreEntity):
    entity_description: CamperSwitchDescription

    def __init__(
        self,
        coordinator: CamperCoordinator,
        entry: ConfigEntry,
        description: CamperSwitchDescription,
    ) -> None:
        super().__init__(coordinator, entry, description.key)
        self.entity_description = description

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        # Nur für den Übergang - siehe async_restore_value im Rechenkern.
        if (last := await self.async_get_last_state()) is not None:
            self.coordinator.async_restore_value(
                self.entity_description.value_key, last.state == STATE_ON
            )

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.get_value(self.entity_description.value_key))

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.coordinator.async_set_value(self.entity_description.value_key, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.coordinator.async_set_value(self.entity_description.value_key, False)
