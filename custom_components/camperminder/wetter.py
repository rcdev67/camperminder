"""Wetterwächter für die Markise.

Liest die stündliche Vorhersage einer Wetter-Entität und sagt, ob die Markise
in den nächsten Stunden etwas abbekommt: Böen, Gewitter, Hagel, Schnee,
Starkregen, Unwetter - dann "einfahren". Bei gewöhnlichem Regen, aber genug
davon, heißt es "absenken": Eine waagerechte Markise sammelt das Wasser in
der Mitte, und an diesem Wassersack brechen die meisten.

Bis zur Version 4.2.4 stand diese Rechnung als Vorlage in einem Blueprint.
Dort hatte sie keine Entität, also nichts, was die Karte anzeigen könnte,
und die Automatisierung musste sich mit einer Ruhezeit behelfen, um nicht
alle halbe Stunde dieselbe Warnung zu schicken. Jetzt hält ein Melder den
Zustand, und der Blueprint meldet nur noch dessen Wechsel auf "an".

bewerte() ist die Rechnung ohne Home Assistant, damit sie sich an echten
Vorhersagen prüfen lässt. WetterWaechter hängt sie an Home Assistant.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
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
    AWNING_CHECK_MINUTES,
    AWNING_HOLD_MINUTES,
    CONF_AWNING_ENTITY,
    CONF_AWNING_GUST,
    CONF_AWNING_LEAD,
    CONF_AWNING_RAIN,
    CONF_AWNING_WIND,
    CONF_WEATHER_ENTITY,
)

_LOGGER = logging.getLogger(__name__)

STUFE_RUHIG = "ruhig"
STUFE_ABSENKEN = "absenken"
STUFE_EINFAHREN = "einfahren"
STUFEN = [STUFE_RUHIG, STUFE_ABSENKEN, STUFE_EINFAHREN]

# Die Vorhersage kommt in den Einheiten der Wetter-Entität. Gerechnet wird in
# km/h und mm, damit die Regler für jede Wetterquelle gelten.
NACH_KMH = {"km/h": 1.0, "m/s": 3.6, "mph": 1.609344, "kn": 1.852, "ft/s": 1.09728}
NACH_MM = {"mm": 1.0, "in": 25.4}

# Zustände, in denen die Markise draußen ist - für Schalter, Melder und
# Markisenantriebe (cover).
AUSGEFAHREN = ("on", "open", "opening")

# Wetterlagen, bei denen die Markise rein muss, und wie sie im Satz heißen.
LAGEN = (
    (("lightning", "lightning-rainy"), "Gewitter"),
    (("hail",), "Hagel"),
    (("snowy", "snowy-rainy"), "Schnee"),
    (("pouring",), "Starkregen"),
    (("exceptional",), "Unwetter"),
)
WINDIG = ("windy", "windy-variant")


@dataclass(frozen=True)
class Befund:
    """Was die Markise erwartet."""

    stufe: str
    satz: str


RUHIG = Befund(STUFE_RUHIG, "")


def _zahl(wert) -> float:
    try:
        return float(wert)
    except (TypeError, ValueError):
        return 0.0


def bewerte(
    eintraege: list[dict],
    jetzt: datetime,
    *,
    vorlauf_h: float,
    boeen_kmh: float,
    wind_kmh: float,
    regen_mm: float,
    stunde_lokal: Callable[[datetime], int],
    windeinheit: str | None = "km/h",
    regeneinheit: str | None = "mm",
) -> Befund:
    """Die Vorhersage der nächsten Stunden bewerten.

    Ein Eintrag gilt für die Stunde ab seiner Zeit; der laufende zählt mit.
    Felder, die nicht jede Quelle liefert, fehlen einfach: met.no hat keine
    Böen, dann zählt der mittlere Wind.
    """
    kmh = NACH_KMH.get(windeinheit or "km/h", 1.0)
    mm = NACH_MM.get(regeneinheit or "mm", 1.0)
    bis = jetzt + timedelta(hours=vorlauf_h)

    wind_ab: str | None = None
    boe_max = mittel_max = regen = 0.0
    boeen_da = False
    lagen: dict[str, str] = {}
    windig: str | None = None

    for e in eintraege:
        try:
            t = datetime.fromisoformat(str(e["datetime"]))
        except (KeyError, ValueError):
            continue
        if not (jetzt - timedelta(hours=1) < t < bis):
            continue
        ab = "jetzt" if t <= jetzt else f"ab {stunde_lokal(t)} Uhr"

        boe = _zahl(e.get("wind_gust_speed")) * kmh
        mittel = _zahl(e.get("wind_speed")) * kmh
        if e.get("wind_gust_speed") is not None:
            boeen_da = True
        if wind_ab is None and (boe >= boeen_kmh or mittel >= wind_kmh):
            wind_ab = ab
        boe_max = max(boe_max, boe)
        mittel_max = max(mittel_max, mittel)
        regen += _zahl(e.get("precipitation")) * mm

        bedingung = e.get("condition")
        for codes, name in LAGEN:
            if bedingung in codes and name not in lagen:
                lagen[name] = ab
        if windig is None and bedingung in WINDIG:
            windig = ab

    gruende: list[str] = []
    if wind_ab is not None:
        if boeen_da:
            gruende.append(f"{wind_ab} Böen bis {round(boe_max)} km/h")
        else:
            gruende.append(f"{wind_ab} Wind bis {round(mittel_max)} km/h")
    elif windig is not None:
        gruende.append(f"{windig} windig")
    for _, name in LAGEN:
        if name in lagen:
            gruende.append(f"{lagen[name]} {name}")

    if gruende:
        return Befund(STUFE_EINFAHREN, f"Markise einfahren: {', '.join(gruende)}.")
    if regen >= regen_mm:
        zeitraum = (
            "in der nächsten Stunde"
            if vorlauf_h <= 1
            else f"in den nächsten {int(vorlauf_h)} Stunden"
        )
        menge = f"{round(regen, 1)}".replace(".", ",")
        return Befund(
            STUFE_ABSENKEN,
            f"{menge} mm Regen {zeitraum}: Markise auf einer Seite absenken, "
            "damit das Wasser abläuft.",
        )
    return RUHIG


class WetterWaechter:
    """Hängt die Rechnung an Home Assistant und hält den Befund.

    `werte` liefert die geltenden Regler (Böen, Wind, Regen, Vorlauf),
    `melden` sagt den Entitäten, dass sich etwas geändert hat.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        config: dict,
        werte: Callable[[str], float],
        melden: Callable[[], None],
    ) -> None:
        self.hass = hass
        self.wetter: str = config[CONF_WEATHER_ENTITY]
        self.markise: str | None = config.get(CONF_AWNING_ENTITY) or None
        self._werte = werte
        self._melden = melden
        self.befund: Befund = RUHIG
        self.geprueft: datetime | None = None
        self._letzte_gefahr: datetime | None = None
        self._abmelden: list = []

    @property
    def warnung(self) -> bool:
        return self.befund.stufe != STUFE_RUHIG

    @property
    def markise_draussen(self) -> bool | None:
        """None ohne Melder - dann wird immer gewarnt."""
        if self.markise is None:
            return None
        state = self.hass.states.get(self.markise)
        return state is not None and state.state in AUSGEFAHREN

    @callback
    def async_start(self) -> None:
        verfolgt = [self.wetter] + ([self.markise] if self.markise else [])
        self._abmelden.append(
            async_track_state_change_event(self.hass, verfolgt, self._bei_aenderung)
        )
        self._abmelden.append(
            async_track_time_interval(
                self.hass, self._im_takt, timedelta(minutes=AWNING_CHECK_MINUTES)
            )
        )
        self.hass.async_create_task(self.async_pruefen())

    @callback
    def async_stop(self) -> None:
        for abmelden in self._abmelden:
            abmelden()
        self._abmelden.clear()

    @callback
    def _bei_aenderung(self, event: Event[EventStateChangedData]) -> None:
        # Die Wetter-Entität ändert ihren Zustand mit jeder neuen Vorhersage,
        # die Markise beim Aus- und Einfahren: beides ist ein Anlass.
        self.hass.async_create_task(self.async_pruefen())

    @callback
    def _im_takt(self, _jetzt: datetime) -> None:
        self.hass.async_create_task(self.async_pruefen())

    @callback
    def einstellungen_geaendert(self) -> None:
        """Ein Regler wurde verstellt - sofort neu bewerten, ohne Halten.

        Das Halten fängt eine Vorhersage ab, die an der Grenze schwankt. Wer
        dagegen eine Grenze bewusst verstellt, will das Ergebnis sofort sehen
        und nicht eine Stunde lang die alte Warnung.
        """
        self.hass.async_create_task(self.async_pruefen(halten=False))

    async def async_pruefen(self, halten: bool = True) -> None:
        jetzt = dt_util.utcnow()
        if self.markise_draussen is False:
            # Eingefahren: Es gibt nichts zu warnen, auch keine stehen
            # gebliebene Warnung von vorhin.
            self._setzen(RUHIG, jetzt, halten=False)
            return

        state = self.hass.states.get(self.wetter)
        if state is None or state.state in ("unavailable", "unknown"):
            return
        try:
            antwort = await self.hass.services.async_call(
                "weather",
                "get_forecasts",
                {"entity_id": self.wetter, "type": "hourly"},
                blocking=True,
                return_response=True,
            )
        except HomeAssistantError as err:
            _LOGGER.warning("Vorhersage von %s nicht lesbar: %s", self.wetter, err)
            return

        eintraege = (antwort or {}).get(self.wetter, {}).get("forecast") or []
        befund = bewerte(
            eintraege,
            jetzt,
            vorlauf_h=self._werte(CONF_AWNING_LEAD),
            boeen_kmh=self._werte(CONF_AWNING_GUST),
            wind_kmh=self._werte(CONF_AWNING_WIND),
            regen_mm=self._werte(CONF_AWNING_RAIN),
            stunde_lokal=lambda t: dt_util.as_local(t).hour,
            windeinheit=state.attributes.get("wind_speed_unit"),
            regeneinheit=state.attributes.get("precipitation_unit"),
        )
        self._setzen(befund, jetzt, halten=halten)

    @callback
    def _setzen(self, befund: Befund, jetzt: datetime, *, halten: bool) -> None:
        if befund.stufe != STUFE_RUHIG:
            self._letzte_gefahr = jetzt
        elif (
            halten
            and self.warnung
            and self._letzte_gefahr is not None
            and jetzt - self._letzte_gefahr < timedelta(minutes=AWNING_HOLD_MINUTES)
        ):
            # Die Vorhersage trägt die Warnung gerade nicht mehr - sie bleibt
            # trotzdem noch stehen, siehe AWNING_HOLD_MINUTES.
            befund = self.befund
        self.geprueft = jetzt
        if befund != self.befund:
            self.befund = befund
            self._melden()
