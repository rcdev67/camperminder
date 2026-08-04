"""Rechenkern der CamperMaid.

Hier liegt die einzige Wahrheit: Schwellen, Phase und Korrekturwerte. Karte,
Ansagen und alle Entitäten lesen ausschließlich von hier. Früher rechnete
jede Kachel und jede Automation ihre Toleranz selbst - und wich dadurch
voneinander ab.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_LEVEL_METHOD,
    CONF_MOTION_SENSOR,
    CONF_NOTIFY_SERVICE,
    CONF_PITCH_SENSOR,
    CONF_ROLL_SENSOR,
    CONF_TOLERANCE_CM,
    CONF_TOLERANCE_DEG,
    CONF_TRACK,
    CONF_VEHICLE_TYPE,
    CONF_WEDGE_STEP,
    CONF_WHEELBASE,
    DEFAULT_LEVEL_METHOD,
    DEFAULT_TOLERANCE_CM,
    DEFAULT_TOLERANCE_DEG,
    DEFAULT_TRACK,
    DEFAULT_WEDGE_STEP,
    DEFAULT_VEHICLE_TYPE,
    DEFAULT_WHEELBASE,
    DEVICE_METHOD_MAP,
    DEVICE_VALUE_ENTITIES,
    DEVICE_VEHICLE_MAP,
    DIRECTION_DOWN,
    DIRECTION_UP,
    IMPLAUSIBLE_DEG,
    METHOD_WEDGE,
    METHODS,
    MIN_TOLERANCE_DEG,
    PHASE_CLOSE,
    PHASE_FRONT,
    PHASE_LEFT,
    PHASE_LEVEL,
    PHASE_REAR,
    PHASE_RIGHT,
    PHASE_UNKNOWN,
    POINT_JOCKEY,
    SIGNAL_UPDATE,
    VEHICLE_CARAVAN,
    VEHICLE_TYPES,
    WHEEL_FRONT_LEFT,
    WHEEL_FRONT_RIGHT,
    WHEEL_LIFT_IGNORE_CM,
    WHEEL_REAR_LEFT,
    WHEEL_REAR_RIGHT,
)

_LOGGER = logging.getLogger(__name__)

# Einstellbare Werte und ihre Voreinstellungen. Alles hier drin gehört einer
# Entität und ist damit auf der Geräteseite sichtbar, in Automationen
# verwendbar und aufs Dashboard legbar. Was nur im Einrichtungsdialog steht,
# findet niemand wieder - deshalb liegen auch Ausrichtart und Ansageziel hier.
VALUE_DEFAULTS: dict[str, float | bool | str | None] = {
    CONF_WHEELBASE: DEFAULT_WHEELBASE,
    CONF_TRACK: DEFAULT_TRACK,
    CONF_TOLERANCE_CM: DEFAULT_TOLERANCE_CM,
    CONF_WEDGE_STEP: DEFAULT_WEDGE_STEP,
    CONF_TOLERANCE_DEG: DEFAULT_TOLERANCE_DEG,
    CONF_LEVEL_METHOD: DEFAULT_LEVEL_METHOD,
    CONF_VEHICLE_TYPE: DEFAULT_VEHICLE_TYPE,
    CONF_NOTIFY_SERVICE: None,
    "voice": False,  # Sprachansage - neue Verhaltenserweiterungen starten aus
    "precise": False,  # Präzisionsmodus
}

# Diese Werte sind Zahlen, alle übrigen nicht.
NUMERIC_VALUES = (
    CONF_WHEELBASE,
    CONF_TRACK,
    CONF_TOLERANCE_CM,
    CONF_WEDGE_STEP,
    CONF_TOLERANCE_DEG,
)


def _as_float(state) -> float | None:
    """Zustand in eine Zahl wandeln, oder None wenn er keine ist."""
    if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE, None, ""):
        return None
    try:
        return float(state.state)
    except (TypeError, ValueError):
        return None


class CamperCoordinator:
    """Hält Messwerte und Einstellungen und leitet daraus alles Weitere ab."""

    def __init__(self, hass: HomeAssistant, entry_id: str, config: dict) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self._config = config

        self.pitch: float | None = None
        self.roll: float | None = None
        self.in_motion: bool = False
        self.last_calibration: datetime | None = None

        self.values: dict[str, float | bool | str | None] = dict(VALUE_DEFAULTS)
        self._apply_config(config)

        # Wird in async_start gefüllt, sobald die Entitätsregistrierung
        # befragt werden kann.
        self._device_sources: dict[str, str] = {}
        self._unsub = None

    def _apply_config(self, config: dict) -> None:
        """Einstellbare Werte aus dem Config-Eintrag übernehmen."""
        for key in VALUE_DEFAULTS:
            if key not in config:
                continue
            value = config[key]
            if value is None:
                # Nur das Ansageziel darf ausdrücklich leer sein - bei einer
                # Zahl wäre None ein Datenfehler und keine Absicht.
                if key == CONF_NOTIFY_SERVICE:
                    self.values[key] = None
                continue
            self.values[key] = float(value) if key in NUMERIC_VALUES else value

    # -- Lebenszyklus -------------------------------------------------------

    @callback
    def async_start(self) -> None:
        """Auf die Quell-Entitäten horchen."""
        self._device_sources = self._find_device_sources()

        tracked = [self._config[CONF_PITCH_SENSOR], self._config[CONF_ROLL_SENSOR]]
        if motion := self._config.get(CONF_MOTION_SENSOR):
            tracked.append(motion)
        tracked.extend(self._device_sources.values())

        self._unsub = async_track_state_change_event(
            self.hass, tracked, self._handle_source_change
        )
        self._read_sources()

    def _find_device_sources(self) -> dict[str, str]:
        """Die Werte suchen, die das Gerät selbst führt.

        Gesucht wird ausschließlich auf dem Gerät, zu dem der Neigungssensor
        gehört. Über alle Geräte zu suchen wäre gefährlich: bei zwei
        Fahrzeugen im selben Home Assistant könnte sonst der Radstand des
        einen mit der Neigung des anderen zusammentreffen.

        Findet sich nichts - etwa weil jemand einen fremden Neigungssensor
        eingerichtet hat -, bleibt es bei den eigenen Reglern.
        """
        registry = er.async_get(self.hass)
        pitch = registry.async_get(self._config[CONF_PITCH_SENSOR])
        if pitch is None or pitch.device_id is None:
            return {}

        wanted = {
            (domain, name): key
            for key, (domain, name) in DEVICE_VALUE_ENTITIES.items()
        }
        found: dict[str, str] = {}
        for entry in registry.entities.values():
            if entry.device_id != pitch.device_id or entry.disabled_by is not None:
                continue
            if (key := wanted.get((entry.domain, entry.original_name))) is not None:
                found[key] = entry.entity_id

        if found:
            _LOGGER.debug("Werte vom Gerät übernommen: %s", sorted(found))
        return found

    @property
    def device_sources(self) -> dict[str, str]:
        """Welche Werte das Gerät führt - die Plattformen fragen hier nach,
        damit sie dafür keine zweite Entität anlegen."""
        return self._device_sources

    @callback
    def async_stop(self) -> None:
        if self._unsub is not None:
            self._unsub()
            self._unsub = None

    @callback
    def _handle_source_change(self, event: Event[EventStateChangedData]) -> None:
        self._read_sources()
        self.async_notify()

    @callback
    def _read_sources(self) -> None:
        states = self.hass.states
        self.pitch = _as_float(states.get(self._config[CONF_PITCH_SENSOR]))
        self.roll = _as_float(states.get(self._config[CONF_ROLL_SENSOR]))

        if motion := self._config.get(CONF_MOTION_SENSOR):
            state = states.get(motion)
            self.in_motion = state is not None and state.state == "on"
        else:
            # Ohne Bewegungssensor gilt immer "könnte gerade rangiert werden".
            self.in_motion = True

    @callback
    def async_notify(self) -> None:
        """Alle Entitäten auffordern, sich neu zu lesen."""
        async_dispatcher_send(self.hass, SIGNAL_UPDATE.format(self.entry_id))

    # -- Einstellbare Werte -------------------------------------------------

    @callback
    def async_set_value(self, key: str, value: float | bool | str | None) -> None:
        if self.values.get(key) == value:
            return
        self.values[key] = value
        self.async_notify()
        self._async_persist(key, value)

    @callback
    def _async_persist(self, key: str, value: float | bool | str | None) -> None:
        """Den Wert in den Config-Eintrag schreiben.

        Früher merkten sich die Entitäten ihren letzten Zustand selbst. Damit
        gab es zwei Speicher: was im Einrichtungsdialog stand, und was die
        Entität zuletzt hatte - und beim Neustart gewann die Entität. Wer
        seinen Radstand im Dialog korrigierte, sah die Änderung nach jedem
        Neustart wieder verschwinden. Jetzt gibt es nur noch den Config-Eintrag.
        """
        entry = self.hass.config_entries.async_get_entry(self.entry_id)
        if entry is None:
            return
        if entry.options.get(key) == value:
            return
        self.hass.config_entries.async_update_entry(
            entry, options={**entry.options, key: value}
        )

    @callback
    def async_restore_value(self, key: str, value: float | bool | str | None) -> None:
        """Einen wiederhergestellten Entitätszustand übernehmen - einmalig.

        Nur für den Übergang: Wer vor dieser Version einen Regler verstellt
        hatte, hätte den Wert sonst verloren, weil die Einrichtungsdaten nichts
        davon wissen. Sobald der Wert einmal in den Optionen steht, gewinnt
        immer der Config-Eintrag und der alte Zustand wird ignoriert.
        """
        entry = self.hass.config_entries.async_get_entry(self.entry_id)
        if entry is not None and key in entry.options:
            return
        self.async_set_value(key, value)

    @callback
    def async_apply_config(self, config: dict) -> None:
        """Geänderte Einstellungen im laufenden Betrieb übernehmen."""
        self._config = config
        self._apply_config(config)
        self.async_notify()

    @property
    def config(self) -> dict:
        return self._config

    def get_value(self, key: str) -> float | bool | str | None:
        """Der geltende Wert - vom Gerät, wenn es ihn führt.

        Das Gerät hat Vorrang, weil es die Betriebsart ohne Home Assistant
        bedienen muss und dort die einzige Quelle ist. Zwei Speicher für
        dieselbe Zahl führen unweigerlich dazu, dass sie auseinanderlaufen -
        und der Nutzer sieht nicht, welcher gilt.
        """
        if (source := self._device_sources.get(key)) is not None:
            state = self.hass.states.get(source)
            if state is not None and state.state not in (
                STATE_UNKNOWN,
                STATE_UNAVAILABLE,
            ):
                if key == CONF_LEVEL_METHOD:
                    return DEVICE_METHOD_MAP.get(state.state, DEFAULT_LEVEL_METHOD)
                if key == CONF_VEHICLE_TYPE:
                    return DEVICE_VEHICLE_MAP.get(state.state, DEFAULT_VEHICLE_TYPE)
                if (number := _as_float(state)) is not None:
                    return number
            # Gerät gerade nicht erreichbar: lieber der zuletzt bekannte
            # eigene Wert als gar keiner - die Anzeige soll nicht ausfallen,
            # nur weil das Fahrzeug kurz offline ist.
        return self.values.get(key, VALUE_DEFAULTS.get(key, 0))

    @callback
    def async_set_calibration(self, moment: datetime | None) -> None:
        self.last_calibration = moment
        self.async_notify()

    # -- Abgeleitete Größen ----------------------------------------------

    @property
    def available(self) -> bool:
        """Liefern beide Neigungssensoren gerade brauchbare Werte?"""
        return self.pitch is not None and self.roll is not None

    @property
    def wheelbase(self) -> float:
        return float(self.get_value(CONF_WHEELBASE)) or DEFAULT_WHEELBASE

    @property
    def track(self) -> float:
        return float(self.get_value(CONF_TRACK)) or DEFAULT_TRACK

    @property
    def wedge_step(self) -> float:
        return float(self.get_value(CONF_WEDGE_STEP))

    @property
    def precise(self) -> bool:
        return bool(self.get_value("precise"))

    @property
    def voice(self) -> bool:
        return bool(self.get_value("voice"))

    def _tolerance(self, dimension_mm: float) -> float:
        """Toleranz in Grad für eine Achse.

        Im Realitätsmodus wird die cm-Angabe über das jeweilige Fahrzeugmaß
        umgerechnet - dadurch ist längs und quer gleich streng bewertet. Eine
        einzelne Gradzahl für beide Achsen wäre das nicht: bei 3500 mm
        Radstand und 1800 mm Spurweite bedeuten 0,4 Grad längs 2,4 cm, quer
        aber nur 1,3 cm.
        """
        if self.precise:
            return max(float(self.get_value(CONF_TOLERANCE_DEG)), MIN_TOLERANCE_DEG)
        tolerance_mm = float(self.get_value(CONF_TOLERANCE_CM)) * 10.0
        return max(math.degrees(math.atan(tolerance_mm / dimension_mm)), MIN_TOLERANCE_DEG)

    @property
    def tolerance_pitch(self) -> float:
        return self._tolerance(self.wheelbase)

    @property
    def tolerance_roll(self) -> float:
        return self._tolerance(self.track)

    @property
    def correction_pitch_cm(self) -> float | None:
        """Wie hoch die Front bzw. das Heck müsste, in cm."""
        if self.pitch is None:
            return None
        return self.wheelbase * math.tan(math.radians(abs(self.pitch))) / 10.0

    @property
    def correction_roll_cm(self) -> float | None:
        if self.roll is None:
            return None
        return self.track * math.tan(math.radians(abs(self.roll))) / 10.0

    @property
    def phase(self) -> str:
        """Grobe Lage als ein Wort - Grundlage für Ansagen und Karte."""
        pitch, roll = self.pitch, self.roll
        if pitch is None or roll is None:
            return PHASE_UNKNOWN
        if abs(pitch) > IMPLAUSIBLE_DEG or abs(roll) > IMPLAUSIBLE_DEG:
            return PHASE_UNKNOWN

        tol_p = self.tolerance_pitch
        tol_r = self.tolerance_roll

        if abs(pitch) <= tol_p and abs(roll) <= tol_r:
            return PHASE_LEVEL
        if abs(pitch) <= 2 * tol_p and abs(roll) <= 2 * tol_r:
            return PHASE_CLOSE

        # Achsen relativ zur je eigenen Schwelle vergleichen, nicht in
        # absoluten Grad - sonst gewänne bei ungleichen Schwellen immer quer.
        if abs(roll) / tol_r >= abs(pitch) / tol_p:
            return PHASE_LEFT if roll > 0 else PHASE_RIGHT
        return PHASE_REAR if pitch > 0 else PHASE_FRONT

    @property
    def is_level(self) -> bool:
        return self.phase == PHASE_LEVEL

    def wedge_steps_for(self, centimetres: float | None) -> int | None:
        """cm in Keilstufen umrechnen, sofern eine Stufenhöhe hinterlegt ist."""
        if centimetres is None or self.wedge_step <= 0:
            return None
        return max(round(centimetres / self.wedge_step), 1)

    def residual_cm(self, centimetres: float | None) -> float | None:
        """Was nach dem Auflegen der gerundeten Stufen übrig bleibt.

        Positiv heißt zu niedrig geblieben, negativ überfahren. Ohne diesen
        Wert steht man vor der Frage, ob die nächste Stufe noch lohnt, und
        rechnet sie im Kopf aus.
        """
        steps = self.wedge_steps_for(centimetres)
        if steps is None or centimetres is None:
            return None
        return round(centimetres - steps * self.wedge_step, 1)

    # -- Hubhöhe je Rad ----------------------------------------------------

    @property
    def level_method(self) -> str:
        """Keile oder Hebesystem - bestimmt, wie die Hinweise aussehen."""
        method = self.get_value(CONF_LEVEL_METHOD)
        return method if method in METHODS else DEFAULT_LEVEL_METHOD

    @property
    def notify_service(self) -> str | None:
        """Wohin die Ansagen gehen, oder None wenn nirgendwohin."""
        target = self.get_value(CONF_NOTIFY_SERVICE)
        return str(target) if target else None

    @property
    def uses_wedges(self) -> bool:
        return self.level_method == METHOD_WEDGE

    @property
    def wheel_lifts_cm(self) -> dict[str, float] | None:
        """Wie hoch jedes einzelne Rad muss, damit das Fahrzeug eben steht.

        Bezugspunkt ist das höchste Rad: es bleibt stehen, alle anderen
        steigen. Anders herum ginge es nicht - absenken kann weder ein Keil
        noch eine Stütze.

        Die Vorzeichen folgen der Phasenlogik weiter oben: pitch > 0 heißt
        Heck zu tief, roll > 0 heißt linke Seite zu tief.

        Gegenprobe: steht nur eine Achse schief, ergibt sich für deren beide
        Räder genau correction_pitch_cm - die Einzelradrechnung ist also
        dieselbe Physik, nur feiner aufgelöst.
        """
        if self.pitch is None or self.roll is None:
            return None
        if abs(self.pitch) > IMPLAUSIBLE_DEG or abs(self.roll) > IMPLAUSIBLE_DEG:
            return None

        half_long = self.wheelbase * math.tan(math.radians(self.pitch)) / 20.0
        half_lat = self.track * math.tan(math.radians(self.roll)) / 20.0

        ground = {
            WHEEL_FRONT_LEFT: +half_long - half_lat,
            WHEEL_FRONT_RIGHT: +half_long + half_lat,
            WHEEL_REAR_LEFT: -half_long - half_lat,
            WHEEL_REAR_RIGHT: -half_long + half_lat,
        }
        highest = max(ground.values())
        return {wheel: round(highest - value, 1) for wheel, value in ground.items()}

    @property
    def vehicle_type(self) -> str:
        """Wohnmobil oder Wohnwagen - bestimmt die Geometrie, nicht nur Text."""
        kind = self.get_value(CONF_VEHICLE_TYPE)
        return kind if kind in VEHICLE_TYPES else DEFAULT_VEHICLE_TYPE

    @property
    def is_caravan(self) -> bool:
        return self.vehicle_type == VEHICLE_CARAVAN

    def _caravan_plan(self) -> list[dict] | None:
        """Wohnwagen: zwei Räder auf einer Achse plus Stützrad.

        Bewusst nicht über wheel_lifts_cm: Dort ist das höchste Rad der
        Bezug, weil ein Keil nur anheben kann. Beim Wohnwagen stimmt das nur
        quer. Längs sitzt das Stützrad, und das kurbelt in beide Richtungen
        - dort wäre "nur anheben" eine künstliche Einschränkung, die den
        Nutzer unnötig auf Keile schicken würde.

        Die Reihenfolge ist Absicht: erst quer, dann längs. Das Auffahren auf
        den Keil kippt den Wagen längs mit, eine vorher berechnete
        Stützradhöhe wäre danach falsch.
        """
        if self.pitch is None or self.roll is None:
            return None
        if abs(self.pitch) > IMPLAUSIBLE_DEG or abs(self.roll) > IMPLAUSIBLE_DEG:
            return None

        plan: list[dict] = []

        # Quer: das tiefere Rad auf den Keil. roll > 0 = rechts höher.
        across_cm = round(self.track * math.tan(math.radians(abs(self.roll))) / 10.0, 1)
        if across_cm >= WHEEL_LIFT_IGNORE_CM:
            plan.append(
                {
                    "wheel": WHEEL_REAR_LEFT if self.roll > 0 else WHEEL_REAR_RIGHT,
                    "cm": across_cm,
                    "steps": self.wedge_steps_for(across_cm),
                    "direction": DIRECTION_UP,
                }
            )

        # Längs: Stützrad. pitch > 0 = Front höher, also senken.
        along_cm = round(self.wheelbase * math.tan(math.radians(abs(self.pitch))) / 10.0, 1)
        if along_cm >= WHEEL_LIFT_IGNORE_CM:
            plan.append(
                {
                    "wheel": POINT_JOCKEY,
                    "cm": along_cm,
                    # Gekurbelt wird stufenlos - eine Keilstufe wäre hier
                    # eine Angabe, die niemand umsetzen kann.
                    "steps": None,
                    "direction": DIRECTION_DOWN if self.pitch > 0 else DIRECTION_UP,
                }
            )
        return plan

    @property
    def wheel_plan(self) -> list[dict[str, float | int | None]] | None:
        """Die Räder, die wirklich hoch müssen - das höchste zuerst.

        Räder unterhalb der Erwähnungsschwelle fallen raus. Steht das
        Fahrzeug eben, bleibt die Liste leer; das ist ein gültiges Ergebnis
        und nicht dasselbe wie None (keine Messwerte).
        """
        if self.is_caravan:
            return self._caravan_plan()

        lifts = self.wheel_lifts_cm
        if lifts is None:
            return None

        plan: list[dict[str, float | int | None]] = []
        for wheel, centimetres in lifts.items():
            if centimetres < WHEEL_LIFT_IGNORE_CM:
                continue
            plan.append(
                {
                    "wheel": wheel,
                    "cm": centimetres,
                    "steps": self.wedge_steps_for(centimetres),
                    "residual_cm": self.residual_cm(centimetres),
                    # Beim Wohnmobil geht es nur nach oben - ein Keil senkt
                    # nichts ab. Das Feld gibt es trotzdem, damit Karte und
                    # Geräteseite für beide Fahrzeugarten dieselbe Form
                    # lesen können.
                    "direction": DIRECTION_UP,
                }
            )
        plan.sort(key=lambda item: item["cm"], reverse=True)
        return plan
