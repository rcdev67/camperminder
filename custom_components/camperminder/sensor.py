"""Sensoren: Schwellen, Phase, Korrekturbedarf, letzte Kalibrierung."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from .const import CONF_PRECISE, DOMAIN, PHASES
from .coordinator import CamperCoordinator
from .entity import CamperEntity


@dataclass(frozen=True, kw_only=True)
class CamperSensorDescription(SensorEntityDescription):
    """Beschreibung samt Rechenvorschrift."""

    value_fn: Callable[[CamperCoordinator], float | str | None]


SENSORS: tuple[CamperSensorDescription, ...] = (
    CamperSensorDescription(
        key="tolerance_pitch",
        translation_key="tolerance_pitch",
        native_unit_of_measurement="°",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:angle-acute",
        value_fn=lambda c: round(c.tolerance_pitch, 2),
    ),
    CamperSensorDescription(
        key="tolerance_roll",
        translation_key="tolerance_roll",
        native_unit_of_measurement="°",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:angle-acute",
        value_fn=lambda c: round(c.tolerance_roll, 2),
    ),
    CamperSensorDescription(
        key="correction_pitch",
        translation_key="correction_pitch",
        native_unit_of_measurement="cm",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:arrow-up-down",
        value_fn=lambda c: (
            None if c.correction_pitch_cm is None else round(c.correction_pitch_cm, 1)
        ),
    ),
    CamperSensorDescription(
        key="correction_roll",
        translation_key="correction_roll",
        native_unit_of_measurement="cm",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:arrow-up-down",
        value_fn=lambda c: (
            None if c.correction_roll_cm is None else round(c.correction_roll_cm, 1)
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: CamperCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities: list[SensorEntity] = [
        CamperSensor(coordinator, entry, description) for description in SENSORS
    ]
    entities.append(CamperPhaseSensor(coordinator, entry))
    entities.append(CamperCalibrationSensor(coordinator, entry))
    async_add_entities(entities)


class CamperSensor(CamperEntity, SensorEntity):
    """Einfacher Rechenwert."""

    entity_description: CamperSensorDescription

    def __init__(
        self,
        coordinator: CamperCoordinator,
        entry: ConfigEntry,
        description: CamperSensorDescription,
    ) -> None:
        super().__init__(coordinator, entry, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | str | None:
        return self.entity_description.value_fn(self.coordinator)


class CamperPhaseSensor(CamperEntity, SensorEntity):
    """Die grobe Lage als ein Wort."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = PHASES
    _attr_icon = "mdi:sign-direction"

    def __init__(self, coordinator: CamperCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "phase")

    @property
    def native_value(self) -> str:
        return self.coordinator.phase

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Alles, was die Karte zum Zeichnen braucht - an einer Stelle.

        Die Karte muss dadurch nur diese eine Entität finden und kann nicht in
        den Zustand geraten, Messwert und Schwelle aus unterschiedlichen
        Quellen zu mischen.
        """
        coordinator = self.coordinator
        return {
            **super().extra_state_attributes,
            "pitch": coordinator.pitch,
            "roll": coordinator.roll,
            "tolerance_pitch": round(coordinator.tolerance_pitch, 3),
            "tolerance_roll": round(coordinator.tolerance_roll, 3),
            # Die Ebenheit je Achse gehört mit übertragen und wird NICHT auf
            # der Karte nachgerechnet: Sie trägt eine Hysterese, also ein
            # Gedächtnis. Zwei Stellen mit eigenem Gedächtnis driften
            # auseinander, sobald eine von beiden einen Messwert verpasst -
            # und dann zeigt die Karte "eben", während der Zustandssensor
            # etwas anderes sagt.
            "level_pitch": coordinator.level_pitch,
            "level_roll": coordinator.level_roll,
            # Schräglagenwarnung. Sie gehört mit auf die Karte, weil sie einen
            # anderen Anlass hat als der Rest: Der übrige Inhalt hilft beim
            # Ausrichten, diese Angabe sagt, dass etwas Schaden nimmt.
            "tilt_warning": coordinator.tilt_warning,
            "position_changed": coordinator.position_changed,
            "tilt_limit": round(coordinator.tilt_limit, 1),
            "correction_pitch_cm": (
                None
                if coordinator.correction_pitch_cm is None
                else round(coordinator.correction_pitch_cm, 1)
            ),
            "correction_roll_cm": (
                None
                if coordinator.correction_roll_cm is None
                else round(coordinator.correction_roll_cm, 1)
            ),
            "wedge_step": coordinator.wedge_step,
            "wedge_steps_pitch": coordinator.wedge_steps_for(
                coordinator.correction_pitch_cm
            ),
            "wedge_steps_roll": coordinator.wedge_steps_for(
                coordinator.correction_roll_cm
            ),
            "level_method": coordinator.level_method,
            "vehicle_type": coordinator.vehicle_type,
            "wheel_plan": coordinator.wheel_plan,
            "in_motion": coordinator.in_motion,
            "precise": coordinator.precise,
            # Führt das Gerät den Präzisionsmodus selbst, gibt es dafür keinen
            # eigenen Schalter in dieser Integration - dann muss die Karte den
            # des Geräts bedienen und braucht dessen Entity-ID. Steht hier
            # None, findet sie ihren eigenen über die Rollenkennung.
            "precise_entity": coordinator.device_sources.get(CONF_PRECISE),
            "sensors_available": coordinator.available,
        }


class CamperCalibrationSensor(CamperEntity, SensorEntity, RestoreEntity):
    """Wann zuletzt kalibriert wurde.

    Ohne Wert zeigt Home Assistant von selbst "Unbekannt" an - ein Datumsfeld
    mit einem Ersatzdatum würde dagegen eine Kalibrierung behaupten, die nie
    stattgefunden hat.
    """

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:calendar-check"

    def __init__(self, coordinator: CamperCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "last_calibration")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None:
            if (moment := dt_util.parse_datetime(last.state)) is not None:
                self.coordinator.async_set_calibration(moment)

    @property
    def native_value(self) -> datetime | None:
        return self.coordinator.last_calibration
