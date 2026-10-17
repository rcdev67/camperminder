"""Heimatort folgt dem Fahrzeug.

Ein Home Assistant im Wohnmobil oder Wohnwagen zieht mit um, sein Heimatort
nicht. Steht er falsch, rechnet Home Assistant Sonnenauf- und -untergang für
einen fremden Ort, eine Wettervorhersage, die dem Heimatort folgt, gilt für
den falschen Platz, und "zu Hause" ist niemand, der am Fahrzeug sitzt.

Den Ort liefert eine GPS-Quelle in Home Assistant (das Tablet oder Handy im
Fahrzeug), denn Level hat kein GPS. Level liefert dafür, was die GPS-Quelle
nicht weiß: ob sich das FAHRZEUG bewegt hat. Ohne das hätte, wer das Tablet
ins Restaurant mitnimmt, nach fünf Minuten dort sein Zuhause.

Die Entscheidung steckt in HeimatortNachzug und kommt ohne Home Assistant
aus, damit sie sich prüfen lässt. HeimatortFolger hängt sie an Home Assistant.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta

from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.util import dt as dt_util

from .const import (
    CONF_HOME_FOLLOW,
    CONF_LOCATION_SOURCE,
    CONF_MOTION_SENSOR,
    HOME_CHECK_INTERVAL_SECONDS,
    HOME_DRIVE_SECONDS,
    HOME_MAX_ACCURACY_M,
    HOME_MIN_DISTANCE_M,
    HOME_STANDSTILL_RADIUS_M,
    HOME_STANDSTILL_SECONDS,
)

_LOGGER = logging.getLogger(__name__)

ERDRADIUS_M = 6371000.0


@dataclass(frozen=True)
class Standort:
    """Eine GPS-Meldung."""

    breite: float
    laenge: float
    genauigkeit: float | None
    hoehe: float | None
    zeit: datetime


def abstand_m(breite1: float, laenge1: float, breite2: float, laenge2: float) -> float:
    """Entfernung über die Erdoberfläche (Haversine), in Metern."""
    p1, p2 = math.radians(breite1), math.radians(breite2)
    dp, dl = p2 - p1, math.radians(laenge2 - laenge1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * ERDRADIUS_M * math.asin(math.sqrt(a))


class HeimatortNachzug:
    """Entscheidet, wann der Heimatort umzieht.

    Umgezogen wird, wenn alles drei zutrifft:

    1. Die GPS-Quelle steht seit fünf Minuten (bleibt innerhalb von 100 m).
       Ein Halt an der Ampel verschiebt nichts.
    2. Sie steht mehr als 500 m vom bisherigen Heimatort entfernt. Darunter
       ist es derselbe Stellplatz.
    3. Level hat seit dem letzten Umzug eine Fahrt gemessen: mindestens zwei
       Minuten Bewegung am Stück. Geprüft nur, wenn ein Bewegungssensor
       eingerichtet ist; ohne ihn entscheidet das GPS allein.

    Nach einem Neustart von Home Assistant ist unbekannt, ob dazwischen
    gefahren wurde. Das gilt dann als gefahren: Ein Home Assistant, das erst
    am neuen Platz wieder Strom bekommt, soll dort ankommen. Meldet die Quelle
    danach einen Ort nahe am Heimatort, ist geklärt, dass das Fahrzeug noch
    da steht, und die Annahme fällt weg.
    """

    def __init__(self) -> None:
        # Wo die Quelle stehen geblieben ist, und seit wann.
        self._anker: Standort | None = None
        self._letzter: Standort | None = None
        self.fahrt_gesehen = True
        self._bewegt_seit: datetime | None = None
        # Beginn der letzten Fahrt. Was die Quelle davor gemeldet hat, gilt
        # nicht mehr - auch nicht, wenn es später noch einmal hereinkommt.
        self._fahrt_beginn: datetime | None = None

    @property
    def letzter(self) -> Standort | None:
        """Die letzte brauchbare Meldung - für den Knopf "hierher"."""
        return self._letzter

    def standort(self, meldung: Standort) -> None:
        """Eine GPS-Meldung aufnehmen."""
        if meldung.genauigkeit is not None and meldung.genauigkeit > HOME_MAX_ACCURACY_M:
            return
        if self._fahrt_beginn is not None and meldung.zeit < self._fahrt_beginn:
            return
        self._letzter = meldung
        if self._anker is None or abstand_m(
            self._anker.breite, self._anker.laenge, meldung.breite, meldung.laenge
        ) > HOME_STANDSTILL_RADIUS_M:
            self._anker = meldung

    def bewegung(self, an: bool, jetzt: datetime) -> None:
        """Den Bewegungssensor von Level aufnehmen."""
        if an:
            if self._bewegt_seit is None:
                self._bewegt_seit = jetzt
            return
        self._pruefe_fahrt(jetzt)
        self._bewegt_seit = None

    def _pruefe_fahrt(self, jetzt: datetime) -> bool:
        """Läuft gerade eine Fahrt? Merkt sie sich, sobald sie lang genug ist."""
        if self._bewegt_seit is None:
            return False
        if jetzt - self._bewegt_seit >= timedelta(seconds=HOME_DRIVE_SECONDS):
            self.fahrt_gesehen = True
            # Was die Quelle vor der Fahrt gemeldet hat, ist jetzt veraltet.
            # Schläft das Tablet unterwegs ein, bliebe sonst der alte Platz
            # stehen und würde nach der Ankunft als neuer übernommen.
            self._fahrt_beginn = self._bewegt_seit
            if self._anker is not None and self._anker.zeit < self._bewegt_seit:
                self._anker = None
            if self._letzter is not None and self._letzter.zeit < self._bewegt_seit:
                self._letzter = None
            return True
        return False

    def pruefen(
        self, jetzt: datetime, heimat: tuple[float, float], mit_bewegung: bool
    ) -> Standort | None:
        """Ist es Zeit umzuziehen? Liefert dann den neuen Ort."""
        if self._pruefe_fahrt(jetzt):
            # Das Fahrzeug fährt noch, auch wenn das GPS gerade steht (Stau).
            return None
        if self._anker is None or self._letzter is None:
            return None
        if jetzt - self._anker.zeit < timedelta(seconds=HOME_STANDSTILL_SECONDS):
            return None

        entfernt = abstand_m(heimat[0], heimat[1], self._letzter.breite, self._letzter.laenge)
        if entfernt <= HOME_MIN_DISTANCE_M:
            # Es steht noch am Heimatort - die Annahme nach dem Neustart ist
            # damit erledigt.
            if mit_bewegung:
                self.fahrt_gesehen = False
            return None
        if mit_bewegung and not self.fahrt_gesehen:
            return None

        self.fahrt_gesehen = False
        return self._letzter


def _standort_aus(state) -> Standort | None:
    """Eine GPS-Meldung aus dem Zustand eines device_tracker oder person."""
    if state is None:
        return None
    attr = state.attributes
    try:
        breite = float(attr["latitude"])
        laenge = float(attr["longitude"])
    except (KeyError, TypeError, ValueError):
        return None

    def zahl(schluessel: str) -> float | None:
        try:
            return float(attr[schluessel])
        except (KeyError, TypeError, ValueError):
            return None

    return Standort(breite, laenge, zahl("gps_accuracy"), zahl("altitude"), state.last_updated)


class HeimatortFolger:
    """Hängt den Nachzug an Home Assistant."""

    def __init__(self, hass: HomeAssistant, config: dict) -> None:
        self.hass = hass
        self.quelle: str = config[CONF_LOCATION_SOURCE]
        self.automatisch: bool = bool(config.get(CONF_HOME_FOLLOW))
        self._bewegung: str | None = config.get(CONF_MOTION_SENSOR)
        self.nachzug = HeimatortNachzug()
        self._abmelden: list = []

    @callback
    def async_start(self) -> None:
        verfolgt = [self.quelle] + ([self._bewegung] if self._bewegung else [])
        self._abmelden.append(
            async_track_state_change_event(self.hass, verfolgt, self._bei_aenderung)
        )
        self._abmelden.append(
            async_track_time_interval(
                self.hass, self._im_takt, timedelta(seconds=HOME_CHECK_INTERVAL_SECONDS)
            )
        )
        self._lies_quellen()

    @callback
    def async_stop(self) -> None:
        for abmelden in self._abmelden:
            abmelden()
        self._abmelden.clear()

    @callback
    def _lies_quellen(self) -> None:
        if (meldung := _standort_aus(self.hass.states.get(self.quelle))) is not None:
            self.nachzug.standort(meldung)
        if self._bewegung and (state := self.hass.states.get(self._bewegung)) is not None:
            self.nachzug.bewegung(state.state == "on", dt_util.utcnow())

    @callback
    def _bei_aenderung(self, event: Event[EventStateChangedData]) -> None:
        self._lies_quellen()
        self._pruefe()

    @callback
    def _im_takt(self, _jetzt: datetime) -> None:
        self._pruefe()

    @callback
    def _pruefe(self) -> None:
        if not self.automatisch:
            return
        heimat = (self.hass.config.latitude, self.hass.config.longitude)
        neu = self.nachzug.pruefen(dt_util.utcnow(), heimat, self._bewegung is not None)
        if neu is not None:
            self.hass.async_create_task(self._async_setzen(neu, "Fahrzeug steht an neuem Ort"))

    async def async_hierher(self) -> None:
        """Der Knopf: Heimatort sofort auf den letzten Standort setzen."""
        self._lies_quellen()
        if (neu := self.nachzug.letzter) is None:
            raise HomeAssistantError(
                f"{self.quelle} meldet keinen brauchbaren Standort "
                f"(fehlt, oder ungenauer als {HOME_MAX_ACCURACY_M:.0f} m)."
            )
        await self._async_setzen(neu, "von Hand")

    async def _async_setzen(self, neu: Standort, grund: str) -> None:
        vorher = (self.hass.config.latitude, self.hass.config.longitude)
        daten: dict[str, float | int] = {"latitude": neu.breite, "longitude": neu.laenge}
        if neu.hoehe is not None:
            daten["elevation"] = round(neu.hoehe)
        # Über die öffentliche Aktion statt über hass.config direkt: Sie
        # speichert den Ort, meldet die Änderung und ist dieselbe, die der
        # Nutzer in einer Automation verwenden würde.
        await self.hass.services.async_call(
            "homeassistant", "set_location", daten, blocking=True
        )
        _LOGGER.info(
            "Heimatort auf %.5f, %.5f gesetzt (%s, %.1f km vom bisherigen)",
            neu.breite,
            neu.laenge,
            grund,
            abstand_m(vorher[0], vorher[1], neu.breite, neu.laenge) / 1000,
        )
