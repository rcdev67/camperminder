"""Einstellbare Zahlenwerte: Fahrzeugmaße, Toleranz, Keilstufe."""

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
    CONF_HEADING,
    CONF_AWNING_GUST,
    CONF_AWNING_LEAD,
    CONF_AWNING_RAIN,
    CONF_AWNING_WIND,
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
    """Beschreibung samt Schlüssel im Rechenkern."""

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


# Wohin die Front des Fahrzeugs zeigt - von Hand, denn Level hat keinen
# Kompass. Davon hängen Sonnenzeiten, Satellit und Starlink ab.
HEADING = CamperNumberDescription(
    key="vehicle_heading",
    translation_key="vehicle_heading",
    value_key=CONF_HEADING,
    native_min_value=0,
    native_max_value=359,
    native_step=1,
    native_unit_of_measurement="°",
    mode=NumberMode.BOX,
    icon="mdi:compass-outline",
)


# Die Regler des Wetterwächters. Es gibt sie nur mit Wetter-Entität; das
# Gerät führt sie nicht, denn ohne Home Assistant gibt es kein Wetter.
AWNING_NUMBERS: tuple[CamperNumberDescription, ...] = (
    CamperNumberDescription(
        key="awning_gust",
        translation_key="awning_gust",
        value_key=CONF_AWNING_GUST,
        native_min_value=20,
        native_max_value=100,
        native_step=5,
        native_unit_of_measurement="km/h",
        mode=NumberMode.BOX,
        icon="mdi:weather-windy",
    ),
    CamperNumberDescription(
        key="awning_wind",
        translation_key="awning_wind",
        value_key=CONF_AWNING_WIND,
        native_min_value=10,
        native_max_value=80,
        native_step=5,
        native_unit_of_measurement="km/h",
        mode=NumberMode.BOX,
        icon="mdi:weather-windy-variant",
    ),
    CamperNumberDescription(
        key="awning_rain",
        translation_key="awning_rain",
        value_key=CONF_AWNING_RAIN,
        native_min_value=1,
        native_max_value=30,
        native_step=1,
        native_unit_of_measurement="mm",
        mode=NumberMode.BOX,
        icon="mdi:weather-pouring",
    ),
    CamperNumberDescription(
        key="awning_lead",
        translation_key="awning_lead",
        value_key=CONF_AWNING_LEAD,
        native_min_value=1,
        native_max_value=12,
        native_step=1,
        native_unit_of_measurement="h",
        mode=NumberMode.BOX,
        icon="mdi:clock-fast",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    stored = hass.data[DOMAIN][entry.entry_id]
    coordinator: CamperCoordinator = stored["coordinator"]
    # Werte, die das Gerät selbst führt, bekommen hier keinen zweiten Regler.
    # Sonst gäbe es sie doppelt - und der Nutzer hätte keine Chance zu
    # erkennen, welcher der beiden gilt.
    entities: list[CamperNumber] = [
        CamperNumber(coordinator, entry, description)
        for description in NUMBERS
        if description.value_key not in coordinator.device_sources
    ]
    entities.append(CamperHeadingNumber(coordinator, entry, HEADING))
    if (wetter := stored.get("wetter")) is not None:
        entities.extend(
            CamperAwningNumber(coordinator, entry, description, wetter)
            for description in AWNING_NUMBERS
        )
    async_add_entities(entities)


class CamperNumber(CamperEntity, RestoreNumber):
    """Ein Wert, den man im Betrieb verstellt - und der Neustarts übersteht."""

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
        # Nur für den Übergang von älteren Versionen, in denen sich die
        # Entität ihren Wert selbst merkte. Steht er in den Optionen, gewinnt
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


class CamperAwningNumber(CamperNumber):
    """Regler des Wetterwächters - wer ihn verstellt, sieht sofort das Ergebnis."""

    def __init__(self, coordinator, entry, description, wetter) -> None:
        super().__init__(coordinator, entry, description)
        self._wetter = wetter

    async def async_set_native_value(self, value: float) -> None:
        await super().async_set_native_value(value)
        self._wetter.einstellungen_geaendert()


class CamperHeadingNumber(CamperNumber):
    """Die Richtung bleibt leer, bis sie eingetragen ist - kein geratenes 0°."""

    @property
    def native_value(self) -> float | None:
        wert = self.coordinator.get_value(self.entity_description.value_key)
        return None if wert is None else float(wert)

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.async_set_value(self.entity_description.value_key, float(value) % 360)
