"""Einstellbare Zahlenwerte: Fahrzeugmasse, Toleranz, Keilstufe."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntityDescription,
    NumberMode,
    RestoreNumber,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_TOLERANCE_CM,
    CONF_TOLERANCE_DEG,
    CONF_TRACK,
    CONF_WEDGE_STEP,
    CONF_WHEELBASE,
    DOMAIN,
)
from .coordinator import CamperCoordinator
from .entity import CamperEntity


@dataclass(frozen=True, kw_only=True)
class CamperNumberDescription(NumberEntityDescription):
    """Beschreibung samt Schluessel im Rechenkern."""

    value_key: str


NUMBERS: tuple[CamperNumberDescription, ...] = (
    CamperNumberDescription(
        key="wheelbase",
        translation_key="wheelbase",
        value_key=CONF_WHEELBASE,
        native_min_value=1000,
        native_max_value=8000,
        native_step=10,
        native_unit_of_measurement="mm",
        device_class=NumberDeviceClass.DISTANCE,
        mode=NumberMode.BOX,
        icon="mdi:arrow-expand-horizontal",
        entity_category=None,
    ),
    CamperNumberDescription(
        key="track",
        translation_key="track",
        value_key=CONF_TRACK,
        native_min_value=800,
        native_max_value=2600,
        native_step=10,
        native_unit_of_measurement="mm",
        device_class=NumberDeviceClass.DISTANCE,
        mode=NumberMode.BOX,
        icon="mdi:arrow-expand-vertical",
    ),
    CamperNumberDescription(
        key="tolerance_cm",
        translation_key="tolerance_cm",
        value_key=CONF_TOLERANCE_CM,
        native_min_value=1,
        native_max_value=20,
        native_step=0.5,
        native_unit_of_measurement="cm",
        mode=NumberMode.BOX,
        icon="mdi:ruler",
    ),
    CamperNumberDescription(
        key="wedge_step",
        translation_key="wedge_step",
        value_key=CONF_WEDGE_STEP,
        native_min_value=0,
        native_max_value=10,
        native_step=0.5,
        native_unit_of_measurement="cm",
        mode=NumberMode.BOX,
        icon="mdi:stairs",
    ),
    CamperNumberDescription(
        key="tolerance_deg",
        translation_key="tolerance_deg",
        value_key=CONF_TOLERANCE_DEG,
        native_min_value=0.1,
        native_max_value=3,
        native_step=0.1,
        native_unit_of_measurement="°",
        mode=NumberMode.BOX,
        icon="mdi:plus-minus-variant",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: CamperCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    # Werte, die das Geraet selbst fuehrt, bekommen hier keinen zweiten Regler.
    # Sonst gaebe es sie doppelt - und der Nutzer haette keine Chance zu
    # erkennen, welcher der beiden gilt.
    async_add_entities(
        CamperNumber(coordinator, entry, description)
        for description in NUMBERS
        if description.value_key not in coordinator.device_sources
    )


class CamperNumber(CamperEntity, RestoreNumber):
    """Ein Wert, den man im Betrieb verstellt - und der Neustarts uebersteht."""

    entity_description: CamperNumberDescription

    def __init__(
        self,
        coordinator: CamperCoordinator,
        entry: ConfigEntry,
        description: CamperNumberDescription,
    ) -> None:
        super().__init__(coordinator, entry, description.key)
        self.entity_description = description

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        # Nur fuer den Uebergang von aelteren Versionen, in denen sich die
        # Entitaet ihren Wert selbst merkte. Steht er in den Optionen, gewinnt
        # der Config-Eintrag und der alte Zustand bleibt unbeachtet.
        if (last := await self.async_get_last_number_data()) is not None:
            if last.native_value is not None:
                self.coordinator.async_restore_value(
                    self.entity_description.value_key, float(last.native_value)
                )

    @property
    def native_value(self) -> float:
        return float(self.coordinator.get_value(self.entity_description.value_key))

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.async_set_value(self.entity_description.value_key, value)
