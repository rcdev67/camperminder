"""Stellplatz-Gedächtnis: Was es beim letzten Mal hier zum Ausrichten brauchte.

Wer einen Platz wieder anfährt, steht meist wieder genauso schief. Level
merkt sich deshalb beim Ankommen, welche Räder wie viel hoch mussten, und
sagt es beim nächsten Besuch: "Hier am 11.10.2026: vorne links 2,5 cm
(1 Stufe)". Die Keile liegen dann schon bereit, bevor das Fahrzeug steht.

Gemerkt wird der Plan BEIM ANKOMMEN, nicht der eben erreichte Zustand: Wer
ausgerichtet hat, steht eben, und "stand eben" hilft beim nächsten Mal
niemandem. Deshalb genau eine Messung je Besuch, sobald das Fahrzeug nach
der Fahrt eine Minute still steht - typischerweise, während die Keile
ausgelegt werden. Das Auffahren auf die Keile danach überschreibt nichts.

Den Ort liefert die GPS-Quelle aus dem Einrichtungsdialog (dieselbe wie für
den Heimatort). Gespeichert wird nur im eigenen Home Assistant.

StellplatzGedaechtnis rechnet ohne Home Assistant; GedaechtnisFolger hängt
es an.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timedelta

from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CARAVAN_INSTRUCTION_NAMES,
    CONF_LOCATION_SOURCE,
    CONF_MOTION_SENSOR,
    DIRECTION_DOWN,
    DOMAIN,
    INSTRUCTION_NAMES,
    VEHICLE_CARAVAN,
)
from .heimatort import Standort, _standort_aus, abstand_m

_LOGGER = logging.getLogger(__name__)

# Zwei Besuche gehören zum selben Platz, wenn sie höchstens so weit
# auseinanderliegen. Das GPS springt im Stand um einige zehn Meter.
PLATZ_RADIUS_M = 60.0
# So weit muss sich das Fahrzeug entfernen, damit ein Besuch endet.
WEG_RADIUS_M = 200.0
# So lange muss es nach der Fahrt still stehen, bis gemessen wird.
STILL_SEKUNDEN = 60
# Wandert das GPS weiter als das, fährt das Fahrzeug noch.
STILL_RADIUS_M = 30.0
# Je Platz die letzten Besuche, und höchstens so viele Plätze.
BESUCHE_JE_PLATZ = 5
PLAETZE_MAX = 500
# Schlechtere GPS-Meldungen zählen nicht.
GENAUIGKEIT_MAX_M = 100.0


def _zahl(cm: float) -> str:
    return f"{cm:.1f}".replace(".", ",")


def plan_satz(plan: list[dict], fahrzeug: str | None = None) -> str:
    """Ein gespeicherter Plan als kurzer Text."""
    if not plan:
        return "stand eben"
    # Beim Wohnwagen heißen die Räder anders, wie in der Anweisung.
    namen = (
        {**INSTRUCTION_NAMES, **CARAVAN_INSTRUCTION_NAMES}
        if fahrzeug == VEHICLE_CARAVAN
        else {**CARAVAN_INSTRUCTION_NAMES, **INSTRUCTION_NAMES}
    )
    teile = []
    for eintrag in plan:
        rad = eintrag["rad"]
        name = namen.get(rad, rad).lower()
        cm = float(eintrag["cm"])
        if eintrag.get("richtung") == DIRECTION_DOWN or cm < 0:
            teil = f"{name} {_zahl(abs(cm))} cm runter"
        else:
            teil = f"{name} {_zahl(cm)} cm"
        stufen = eintrag.get("stufen")
        if stufen:
            teil += f" ({stufen} {'Stufe' if stufen == 1 else 'Stufen'})"
        teile.append(teil)
    return ", ".join(teile)


class StellplatzGedaechtnis:
    """Plätze, Besuche und die Frage, ob gerade gemessen werden soll."""

    def __init__(self, daten: dict | None = None) -> None:
        self.plaetze: list[dict] = list((daten or {}).get("plaetze", []))
        self._ort: Standort | None = None
        # Still steht es, wenn der Bewegungssensor (falls vorhanden) seit
        # einer Minute aus ist UND das GPS so lange am selben Fleck bleibt.
        self._still_seit: datetime | None = None
        self._bewegt = False
        self._anker: Standort | None = None
        # Der laufende Besuch: Platz, ob schon gemessen, und was vorher war.
        self._besuch: dict | None = None
        # Nach einem Neustart erst nach der nächsten Fahrt messen.
        self._gefahren = False

    def daten(self) -> dict:
        return {"plaetze": self.plaetze}

    # -- Eingänge ---------------------------------------------------------

    def ort(self, meldung: Standort) -> None:
        if meldung.genauigkeit is not None and meldung.genauigkeit > GENAUIGKEIT_MAX_M:
            return
        if self._besuch is not None and abstand_m(
            self._besuch["breite"], self._besuch["laenge"], meldung.breite, meldung.laenge
        ) > WEG_RADIUS_M:
            # Weggefahren: Der Besuch ist vorbei, der nächste darf messen.
            self._besuch = None
            self._gefahren = True
        if self._anker is None or abstand_m(
            self._anker.breite, self._anker.laenge, meldung.breite, meldung.laenge
        ) > STILL_RADIUS_M:
            self._anker = meldung
        self._ort = meldung

    def bewegung(self, an: bool, jetzt: datetime) -> None:
        if an:
            self._bewegt = True
            self._still_seit = None
        elif self._bewegt or self._still_seit is None:
            self._bewegt = False
            self._still_seit = jetzt

    # -- Entscheidung -----------------------------------------------------

    def _platz_bei(self, breite: float, laenge: float) -> dict | None:
        bester, abstand_bester = None, PLATZ_RADIUS_M
        for platz in self.plaetze:
            d = abstand_m(platz["breite"], platz["laenge"], breite, laenge)
            if d <= abstand_bester:
                bester, abstand_bester = platz, d
        return bester

    def _steht(self, jetzt: datetime) -> bool:
        if self._ort is None or self._anker is None:
            return False
        if self._bewegt or self._still_seit is None:
            return False
        frist = timedelta(seconds=STILL_SEKUNDEN)
        return jetzt - self._still_seit >= frist and jetzt - self._anker.zeit >= frist

    def pruefen(self, jetzt: datetime, plan: list[dict] | None, fahrzeug: str) -> bool:
        """Besuch beginnen und messen, wenn es so weit ist. True = gespeichert."""
        if not self._steht(jetzt):
            return False
        if self._besuch is None:
            # Erst im Stand: Beim Heranfahren läge der Besuch sonst am
            # Ortseingang statt auf dem Platz.
            platz = self._platz_bei(self._ort.breite, self._ort.laenge)
            self._besuch = {
                "breite": self._ort.breite,
                "laenge": self._ort.laenge,
                "platz": platz,
                "vorher": dict(platz["besuche"][0]) if platz and platz["besuche"] else None,
                "gemessen": False,
            }
        besuch = self._besuch
        if besuch["gemessen"] or not self._gefahren or plan is None:
            return False

        eintrag = {
            "datum": jetzt.strftime("%Y-%m-%d"),
            "fahrzeug": fahrzeug,
            "plan": [
                {
                    "rad": p["wheel"],
                    "cm": round(float(p["cm"]), 1),
                    "stufen": p.get("steps"),
                    "richtung": p.get("direction"),
                }
                for p in plan
            ],
        }
        platz = besuch["platz"]
        if platz is None:
            platz = {
                "breite": round(besuch["breite"], 5),
                "laenge": round(besuch["laenge"], 5),
                "besuche": [],
            }
            self.plaetze.append(platz)
            besuch["platz"] = platz
            if len(self.plaetze) > PLAETZE_MAX:
                # Der am längsten nicht besuchte Platz fällt heraus.
                self.plaetze.sort(key=lambda p: p["besuche"][0]["datum"] if p["besuche"] else "")
                del self.plaetze[0]
        platz["besuche"].insert(0, eintrag)
        del platz["besuche"][BESUCHE_JE_PLATZ:]
        besuch["gemessen"] = True
        return True

    def satz(self) -> str:
        if self._ort is None:
            return "Kein Standort - GPS-Quelle unter „Konfigurieren“ eintragen."
        if self._besuch is None:
            return "Noch kein Stellplatz erkannt."
        vorher = self._besuch["vorher"]
        if vorher is None:
            if self._besuch["gemessen"]:
                return "Neuer Stellplatz - beim nächsten Mal steht hier, was er brauchte."
            return "Neuer Stellplatz."
        datum = datetime.strptime(vorher["datum"], "%Y-%m-%d").strftime("%d.%m.%Y")
        return f"Hier am {datum}: {plan_satz(vorher['plan'], vorher.get('fahrzeug'))}."

    @property
    def vorher(self) -> dict | None:
        return self._besuch["vorher"] if self._besuch else None


class GedaechtnisFolger:
    """Hängt das Gedächtnis an Home Assistant und speichert es dauerhaft."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        config: dict,
        plan: Callable[[], list[dict] | None],
        fahrzeug: Callable[[], str],
        melden: Callable[[], None],
    ) -> None:
        self.hass = hass
        self.quelle: str = config[CONF_LOCATION_SOURCE]
        self._bewegung: str | None = config.get(CONF_MOTION_SENSOR)
        self._plan = plan
        self._fahrzeug = fahrzeug
        self._melden = melden
        self._store: Store = Store(hass, 1, f"{DOMAIN}_stellplaetze_{entry_id}")
        self.gedaechtnis = StellplatzGedaechtnis()
        self._abmelden: list = []

    async def async_start(self) -> None:
        self.gedaechtnis = StellplatzGedaechtnis(await self._store.async_load())
        verfolgt = [self.quelle] + ([self._bewegung] if self._bewegung else [])
        self._abmelden.append(
            async_track_state_change_event(self.hass, verfolgt, self._bei_aenderung)
        )
        self._abmelden.append(
            async_track_time_interval(self.hass, self._im_takt, timedelta(seconds=15))
        )
        self._lies_quellen()
        self._pruefe()

    @callback
    def async_stop(self) -> None:
        for abmelden in self._abmelden:
            abmelden()
        self._abmelden.clear()

    @callback
    def _lies_quellen(self) -> None:
        if (meldung := _standort_aus(self.hass.states.get(self.quelle))) is not None:
            self.gedaechtnis.ort(meldung)
        jetzt = dt_util.utcnow()
        if self._bewegung and (state := self.hass.states.get(self._bewegung)) is not None:
            self.gedaechtnis.bewegung(state.state == "on", jetzt)
        elif not self._bewegung:
            # Ohne Bewegungssensor zählt nur das GPS: still, solange es steht.
            self.gedaechtnis.bewegung(False, jetzt)

    @callback
    def _bei_aenderung(self, event: Event[EventStateChangedData]) -> None:
        vorher = self.gedaechtnis.satz()
        self._lies_quellen()
        self._pruefe(vorher)

    @callback
    def _im_takt(self, _jetzt: datetime) -> None:
        self._pruefe()

    @callback
    def _pruefe(self, satz_vorher: str | None = None) -> None:
        satz_vorher = satz_vorher if satz_vorher is not None else self.gedaechtnis.satz()
        if self.gedaechtnis.pruefen(dt_util.now(), self._plan(), self._fahrzeug()):
            self._store.async_delay_save(self.gedaechtnis.daten, 10)
            _LOGGER.info("Stellplatz gemerkt: %s", self.gedaechtnis.satz())
        if self.gedaechtnis.satz() != satz_vorher:
            self._melden()
