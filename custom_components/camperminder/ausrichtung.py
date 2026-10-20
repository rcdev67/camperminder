"""Richtung des Fahrzeugs aus der Fahrt: wohin die Front beim Abstellen zeigt.

Level hat keinen Kompass. Zwei Dinge zusammen ersetzen ihn:

- Die GPS-Quelle im Fahrzeug (die Home-Assistant-App) meldet bei flotter
  Fahrt ihre Fahrtrichtung ("course") - das ist dann die Richtung der Front.
- Level summiert, um wie viel sich das Fahrzeug seitdem gedreht hat
  (Sensor "Drehung"). Das Einbiegen auf den Platz, das Rangieren, auch das
  Rückwärtseinparken: Alles steckt in dieser Summe.

Richtung beim Abstellen = letzte flotte Fahrtrichtung + Drehung seitdem.

Ohne den Sensor "Drehung" (ältere Firmware) bleibt nur die Fahrtrichtung.
Die stimmt nur, wenn zuletzt geradeaus vorwärts eingefahren wurde; deshalb
wird sie dann nur übernommen, wenn sie ganz frisch ist, und die Karte bietet
"180° drehen" für das Rückwärtseinparken an.

Wer die Richtung von Hand einstellt, hat recht - bis zur nächsten Fahrt.

RichtungAusFahrt entscheidet ohne Home Assistant; RichtungsFolger hängt sie
an.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.util import dt as dt_util

from .const import CONF_LOCATION_SOURCE, CONF_MOTION_SENSOR, CONF_PITCH_SENSOR

_LOGGER = logging.getLogger(__name__)

# Ab dieser Geschwindigkeit ist die Fahrtrichtung des GPS verlässlich
# (m/s, wie die Home-Assistant-App sie meldet; 4 m/s sind rund 15 km/h).
MIN_TEMPO_MS = 4.0
# Schlechtere Standorte zählen nicht.
GENAUIGKEIT_MAX_M = 50.0
# So lange muss das Fahrzeug stehen, bis die Richtung übernommen wird.
STILL_SEKUNDEN = 60
# Wie alt die letzte flotte Fahrtrichtung beim Anhalten höchstens sein darf.
# Mit Drehung großzügig: Level summiert nur während der Fahrt, der Fehler
# wächst langsam. Ohne Drehung muss sie ganz frisch sein - jede Kurve danach
# wäre unbemerkt.
MAX_ALTER_MIT_DREHUNG = timedelta(minutes=10)
MAX_ALTER_OHNE_DREHUNG = timedelta(seconds=45)

# Der Sensor der Firmware, über seinen ursprünglichen Namen gefunden.
DREHUNG = "Drehung"

QUELLE_FAHRT = "fahrt"
QUELLE_GPS = "gps"
QUELLE_HAND = "hand"


@dataclass(frozen=True)
class Richtung:
    grad: float
    quelle: str  # QUELLE_FAHRT (mit Drehung) oder QUELLE_GPS (ohne)


@dataclass(frozen=True)
class _Fix:
    kurs: float
    zeit: datetime
    drehung: float | None
    epoche: int


class RichtungAusFahrt:
    """Merkt sich die letzte flotte Fahrtrichtung und rechnet beim Abstellen."""

    def __init__(self) -> None:
        self._fix: _Fix | None = None
        self._drehung: float | None = None
        # Zählt hoch, wenn die Drehung abreißt (Neustart des Geräts): Werte
        # aus verschiedenen Epochen lassen sich nicht voneinander abziehen.
        self._epoche = 0
        self._still_seit: datetime | None = None
        self._rollt = False

    def drehung(self, wert: float | None) -> None:
        if wert is None:
            if self._drehung is not None:
                self._epoche += 1
            self._drehung = None
            return
        self._drehung = wert

    def bewegung(self, an: bool, jetzt: datetime) -> None:
        if an:
            self._rollt = True
            self._still_seit = None
        elif self._rollt or self._still_seit is None:
            self._rollt = False
            self._still_seit = jetzt

    def gps(
        self,
        kurs: float | None,
        tempo: float | None,
        genauigkeit: float | None,
        zeit: datetime,
        level_rollt: bool | None,
    ) -> None:
        """Eine GPS-Meldung. level_rollt: None, wenn es keinen Bewegungssensor gibt.

        Meldet Level, dass das Fahrzeug steht, gehört die Fahrt nicht zu ihm:
        Dann fährt das Handy gerade in einem anderen Auto.
        """
        if kurs is None or tempo is None or kurs < 0 or tempo < MIN_TEMPO_MS:
            return
        if genauigkeit is not None and genauigkeit > GENAUIGKEIT_MAX_M:
            return
        if level_rollt is False:
            return
        self._fix = _Fix(kurs % 360, zeit, self._drehung, self._epoche)

    def pruefen(self, jetzt: datetime) -> Richtung | None:
        """Die Richtung, sobald das Fahrzeug nach einer Fahrt steht - einmal."""
        fix = self._fix
        if fix is None or self._rollt or self._still_seit is None:
            return None
        if jetzt - self._still_seit < timedelta(seconds=STILL_SEKUNDEN):
            return None
        # Was es nach dem Abstellen gibt, gehört zu dieser Fahrt; danach ist
        # sie verbraucht, bis die nächste flotte Meldung kommt.
        self._fix = None
        alter = self._still_seit - fix.zeit
        if (
            fix.drehung is not None
            and self._drehung is not None
            and fix.epoche == self._epoche
            and alter <= MAX_ALTER_MIT_DREHUNG
        ):
            return Richtung(round((fix.kurs + self._drehung - fix.drehung) % 360, 1), QUELLE_FAHRT)
        if alter <= MAX_ALTER_OHNE_DREHUNG:
            return Richtung(round(fix.kurs, 1), QUELLE_GPS)
        return None


def finde_drehung(hass: HomeAssistant, pitch_entity_id: str | None) -> str | None:
    """Der Sensor "Drehung" auf demselben Gerät wie der Neigungssensor."""
    if not pitch_entity_id:
        return None
    registry = er.async_get(hass)
    pitch = registry.async_get(pitch_entity_id)
    if pitch is None or pitch.device_id is None:
        return None
    for entry in registry.entities.values():
        if (
            entry.device_id == pitch.device_id
            and entry.domain == "sensor"
            and entry.original_name == DREHUNG
            and entry.disabled_by is None
        ):
            return entry.entity_id
    return None


def _zahl(wert) -> float | None:
    try:
        return float(wert)
    except (TypeError, ValueError):
        return None


class RichtungsFolger:
    """Hängt die Rechnung an Home Assistant."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: dict,
        setzen: Callable[[float, str], None],
    ) -> None:
        self.hass = hass
        self.quelle: str = config[CONF_LOCATION_SOURCE]
        self._bewegung: str | None = config.get(CONF_MOTION_SENSOR)
        self._pitch: str | None = config.get(CONF_PITCH_SENSOR)
        self._setzen = setzen
        self.rechnung = RichtungAusFahrt()
        self.drehung: str | None = None
        self._geraete: list[str] = [self.quelle]
        self._abmelden: list = []

    def _fahrzeuge(self) -> list[str]:
        """Die Entitäten, die Fahrtrichtung und Tempo melden.

        Eine Person hat weder "course" noch "speed" - die liefert nur das
        Gerät dahinter (die Home-Assistant-App am Handy). Wer eine Person als
        GPS-Quelle wählt, meint dieses Gerät.
        """
        if not self.quelle.startswith("person."):
            return [self.quelle]
        state = self.hass.states.get(self.quelle)
        geraete = state.attributes.get("device_trackers") if state is not None else None
        return [self.quelle, *(geraete or [])]

    @callback
    def async_start(self) -> None:
        self.drehung = finde_drehung(self.hass, self._pitch)
        self._geraete = self._fahrzeuge()
        verfolgt = list(self._geraete)
        if self._bewegung:
            verfolgt.append(self._bewegung)
        if self.drehung:
            verfolgt.append(self.drehung)
        self._abmelden.append(
            async_track_state_change_event(self.hass, verfolgt, self._bei_aenderung)
        )
        self._abmelden.append(
            async_track_time_interval(self.hass, self._im_takt, timedelta(seconds=15))
        )
        self._lies_drehung()
        self._lies_bewegung(dt_util.utcnow())

    @callback
    def async_stop(self) -> None:
        for abmelden in self._abmelden:
            abmelden()
        self._abmelden.clear()

    def _level_rollt(self) -> bool | None:
        if not self._bewegung:
            return None
        state = self.hass.states.get(self._bewegung)
        return state is not None and state.state == "on"

    @callback
    def _lies_drehung(self) -> None:
        if not self.drehung:
            return
        state = self.hass.states.get(self.drehung)
        self.rechnung.drehung(_zahl(state.state) if state is not None else None)

    @callback
    def _lies_bewegung(self, jetzt: datetime) -> None:
        rollt = self._level_rollt()
        if rollt is None:
            # Ohne Bewegungssensor entscheidet das Tempo des GPS.
            tempo = None
            for geraet in self._geraete:
                state = self.hass.states.get(geraet)
                tempo = _zahl(state.attributes.get("speed")) if state is not None else None
                if tempo is not None:
                    break
            rollt = tempo is not None and tempo >= 1.0
        self.rechnung.bewegung(rollt, jetzt)

    @callback
    def _bei_aenderung(self, event: Event[EventStateChangedData]) -> None:
        jetzt = dt_util.utcnow()
        entity_id = event.data["entity_id"]
        if entity_id == self.drehung:
            self._lies_drehung()
            return
        if entity_id in self._geraete:
            state = event.data.get("new_state")
            if state is not None:
                attr = state.attributes
                self.rechnung.gps(
                    _zahl(attr.get("course")),
                    _zahl(attr.get("speed")),
                    _zahl(attr.get("gps_accuracy")),
                    jetzt,
                    self._level_rollt(),
                )
        self._lies_bewegung(jetzt)

    @callback
    def _im_takt(self, _jetzt: datetime) -> None:
        if (richtung := self.rechnung.pruefen(dt_util.utcnow())) is None:
            return
        _LOGGER.info("Richtung aus der Fahrt: %.1f° (%s)", richtung.grad, richtung.quelle)
        self._setzen(richtung.grad, richtung.quelle)
