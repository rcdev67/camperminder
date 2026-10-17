"""Abfahrtscheck: Fährt das Fahrzeug los, obwohl noch etwas offen ist?

Die teuren Fehler beim Losfahren sind immer dieselben: die Markise, die
Trittstufe, die Dachluke, die Tür. Level merkt als Erstes, dass das
Fahrzeug rollt ("In Bewegung"), und Home Assistant weiß, was noch offen
steht - zusammen ergibt das eine Warnung, solange man noch auf dem Platz
ist und nicht erst an der Ausfahrt.

Gewarnt wird SOFORT beim Anrollen, nicht erst nach einer Strecke: Auch beim
Rangieren auf die Keile hat eine ausgefahrene Stufe oder Markise nichts
draußen zu suchen. Welche Entitäten zählen, wählt man selbst aus; wer beim
Einweisen die Tür offen lässt, nimmt die Tür eben nicht in die Liste.

Gemeldet wird dreifach: der Melder "Abfahrt Warnung" (für Karte und
Blueprint), eine Ansage über das Ansageziel und ein Piepen am Gerät über
dessen Knopf "Hinweiston" - den hört man auch, wenn das Handy in der Tasche
steckt.

bewerte() entscheidet ohne Home Assistant; AbfahrtsWaechter hängt es an.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_AWNING_ENTITY,
    CONF_DEPARTURE_ENTITIES,
    CONF_MOTION_SENSOR,
    CONF_PITCH_SENSOR,
)

_LOGGER = logging.getLogger(__name__)

# Was je Bereich als "offen" gilt. Ein binary_sensor für Tür oder Fenster
# meldet "on" für offen; ein Schloss ist offen, solange es nicht zu ist.
OFFEN = {
    "binary_sensor": ("on",),
    "cover": ("open", "opening", "closing"),
    "lock": ("unlocked", "open", "opening", "unlocking"),
    "switch": ("on",),
    "input_boolean": ("on",),
}


def ist_offen(entity_id: str, zustand: str | None) -> bool:
    """Unbekannt oder nicht erreichbar zählt nicht als offen.

    Sonst warnte jede leere Batterie eines Türkontakts bei jeder Fahrt, und
    nach der dritten Fehlwarnung hört niemand mehr hin.
    """
    if zustand is None:
        return False
    return zustand in OFFEN.get(entity_id.split(".", 1)[0], ("on",))


@dataclass(frozen=True)
class Befund:
    offen: tuple[str, ...]
    satz: str


RUHIG = Befund((), "Alles zu.")

# Der Knopf der Firmware, über seinen ursprünglichen Namen gefunden - der
# übersteht jedes Umbenennen im Frontend.
HINWEISTON = "Hinweiston"


def finde_hinweiston(hass: HomeAssistant, pitch_entity_id: str | None) -> str | None:
    """Der Knopf "Hinweiston" auf demselben Gerät wie der Neigungssensor."""
    if not pitch_entity_id:
        return None
    registry = er.async_get(hass)
    pitch = registry.async_get(pitch_entity_id)
    if pitch is None or pitch.device_id is None:
        return None
    for entry in registry.entities.values():
        if (
            entry.device_id == pitch.device_id
            and entry.domain == "button"
            and entry.original_name == HINWEISTON
            and entry.disabled_by is None
        ):
            return entry.entity_id
    return None


def bewerte(rollt: bool, offen: list[str]) -> Befund:
    """offen: die Namen der offenen Dinge, in der Reihenfolge der Auswahl."""
    if not rollt or not offen:
        return RUHIG
    return Befund(tuple(offen), f"Abfahrt - noch offen: {', '.join(offen)}.")


class AbfahrtsWaechter:
    """Hängt den Check an Home Assistant."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: dict,
        melden: Callable[[], None],
        sagen: Callable[[str], Awaitable[None]],
    ) -> None:
        self.hass = hass
        self.bewegung: str = config[CONF_MOTION_SENSOR]
        # Die Markise aus dem Wetterwächter gehört immer dazu, wenn es sie gibt.
        auswahl = list(config.get(CONF_DEPARTURE_ENTITIES) or [])
        if (markise := config.get(CONF_AWNING_ENTITY)) and markise not in auswahl:
            auswahl.insert(0, markise)
        self.auswahl: list[str] = auswahl
        self._melden = melden
        self._sagen = sagen
        self._pitch: str | None = config.get(CONF_PITCH_SENSOR)
        # Erst beim Start gesucht: Beim Einrichten kann das Gerät noch fehlen.
        self.ton: str | None = None
        self.befund: Befund = RUHIG
        self._abmelden = None

    @property
    def warnung(self) -> bool:
        return bool(self.befund.offen)

    @callback
    def async_start(self) -> None:
        # Ältere Firmware hat den Knopf nicht - dann eben ohne Piepen.
        self.ton = finde_hinweiston(self.hass, self._pitch)
        self._abmelden = async_track_state_change_event(
            self.hass, [self.bewegung, *self.auswahl], self._bei_aenderung
        )
        self._pruefen(ansagen=False)

    @callback
    def async_stop(self) -> None:
        if self._abmelden is not None:
            self._abmelden()
            self._abmelden = None

    def _name(self, entity_id: str) -> str:
        state = self.hass.states.get(entity_id)
        return state.name if state is not None else entity_id

    @callback
    def _bei_aenderung(self, _event: Event[EventStateChangedData]) -> None:
        self._pruefen(ansagen=True)

    @callback
    def _pruefen(self, ansagen: bool) -> None:
        state = self.hass.states.get(self.bewegung)
        rollt = state is not None and state.state == "on"
        offen = []
        for entity_id in self.auswahl:
            zustand = self.hass.states.get(entity_id)
            if ist_offen(entity_id, zustand.state if zustand else None):
                offen.append(self._name(entity_id))
        neu = bewerte(rollt, offen)
        if neu == self.befund:
            return
        vorher = self.befund
        self.befund = neu
        self._melden()
        # Angesagt wird nur, was dazugekommen ist - nicht jedes Mal, wenn
        # jemand während der Fahrt die zweite von drei offenen Sachen schließt.
        dazu = [n for n in neu.offen if n not in vorher.offen]
        if ansagen and dazu:
            _LOGGER.info("%s", neu.satz)
            self.hass.async_create_task(
                self._sagen(f"Achtung, noch offen: {', '.join(dazu)}.")
            )
            if self.ton:
                self.hass.async_create_task(
                    self.hass.services.async_call(
                        "button", "press", {"entity_id": self.ton}, blocking=False
                    )
                )
