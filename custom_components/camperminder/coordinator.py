"""Rechenkern der CamperMinder.

Hier liegt die einzige Wahrheit: Schwellen, Phase und Korrekturwerte. Karte,
Ansagen und alle Entitäten lesen ausschließlich von hier. Früher rechnete
jede Kachel und jede Automation ihre Toleranz selbst - und wich dadurch
voneinander ab.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime

from homeassistant.const import STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_LEVEL_HOLD,
    CONF_LEVEL_METHOD,
    CONF_TILT_LIMIT,
    CONF_MOTION_SENSOR,
    CONF_NOTIFY_SERVICE,
    CONF_PITCH_SENSOR,
    CONF_POSITION_CHANGED,
    CONF_PROFILE,
    CONF_PRECISE,
    CONF_CALIBRATION_CHECK,
    CONF_CALIBRATION_TEXT,
    CONF_FROST,
    CONF_INDOOR_TEMP,
    CONF_MOUNT_CHECK,
    CONF_FRIDGE_MINUTES,
    CONF_FRIDGE_TEXT,
    CONF_FRIDGE_WARNING,
    CONF_GUARD,
    CONF_GUARD_ACK,
    CONF_GUARD_ALARM,
    CONF_GUARD_STATUS,
    CONF_LAST_MOTION,
    CONF_ROLL_SENSOR,
    CONF_TARGET_LAT,
    CONF_TARGET_LONG,
    CONF_TILT_MINUTES,
    CONF_TOLERANCE_CM,
    CONF_TOLERANCE_DEG,
    CONF_TRACK,
    CONF_VEHICLE_TYPE,
    CONF_WEDGE_STEP,
    CONF_WHEELBASE,
    DEFAULT_LEVEL_METHOD,
    DEFAULT_TOLERANCE_CM,
    DEFAULT_TILT_LIMIT_DEG,
    DEFAULT_TOLERANCE_DEG,
    DEFAULT_TRACK,
    DEFAULT_WEDGE_STEP,
    DEFAULT_VEHICLE_TYPE,
    DEFAULT_WHEELBASE,
    DEVICE_METHOD_MAP,
    DEVICE_BINARY_VALUES,
    DEVICE_SWITCH_VALUES,
    DEVICE_TEXT_VALUES,
    DEVICE_VALUE_ENTITIES,
    DEVICE_VEHICLE_MAP,
    DIRECTION_DOWN,
    DIRECTION_UP,
    IMPLAUSIBLE_DEG,
    LEVEL_RELEASE,
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
    SIDES,
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


def _merge_side(
    plan: list[dict[str, float | int | None]],
) -> list[dict[str, float | int | None]]:
    """Zwei Räder derselben Seite mit gleichem Maß zu einer Anweisung machen.

    Steht das Fahrzeug nur quer schief, brauchen beide linken Räder exakt
    dasselbe. Die Rechnung liefert dafür zwei Einträge, und die lasen sich als
    "Vorne links 4 cm" und "Hinten links 4 cm" - zwei Handgriffe, wo einer
    gemeint ist, und beide nennen eine Längsrichtung, die gar nicht korrigiert
    wird. Wer nach Anweisung arbeitet, sucht dann nach einem Unterschied
    zwischen den beiden Zeilen, den es nicht gibt.

    Nur bei GENAU zwei Einträgen: Sobald beide Achsen schief stehen, entstehen
    drei mit verschiedenen Maßen, und dann ist jede Ecke wirklich einzeln
    gemeint. Ein zufälliges Zusammenfallen kann es dabei nicht geben - die
    beiden gleich großen Einträge lägen über Kreuz und teilten sich keine Seite.
    """
    if len(plan) != 2 or plan[0]["cm"] != plan[1]["cm"]:
        return plan

    erste = str(plan[0]["wheel"]).split("_")
    zweite = str(plan[1]["wheel"]).split("_")
    if len(erste) != 2 or len(zweite) != 2:
        return plan

    if erste[0] == zweite[0]:
        seite = erste[0]
    elif erste[1] == zweite[1]:
        seite = erste[1]
    else:
        return plan
    if seite not in SIDES:
        return plan

    zusammen = dict(plan[0])
    zusammen["wheel"] = seite
    return [zusammen]

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
    CONF_LEVEL_HOLD: LEVEL_RELEASE * 100.0,
    CONF_TILT_LIMIT: DEFAULT_TILT_LIMIT_DEG,
    CONF_LEVEL_METHOD: DEFAULT_LEVEL_METHOD,
    CONF_VEHICLE_TYPE: DEFAULT_VEHICLE_TYPE,
    CONF_NOTIFY_SERVICE: None,
    "voice": False,  # Sprachansage - neue Verhaltenserweiterungen starten aus
    CONF_PRECISE: False,  # Präzisionsmodus, sofern das Gerät ihn nicht führt
    CONF_POSITION_CHANGED: False,  # nur, wenn das Gerät sie meldet
}

# Diese Werte sind Zahlen, alle übrigen nicht.
NUMERIC_VALUES = (
    CONF_WHEELBASE,
    CONF_TRACK,
    CONF_TOLERANCE_CM,
    CONF_WEDGE_STEP,
    CONF_TOLERANCE_DEG,
    CONF_LEVEL_HOLD,
    CONF_TILT_LIMIT,
)


def _as_float(state) -> float | None:
    """Zustand in eine Zahl wandeln, oder None wenn er keine ist."""
    if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE, None, ""):
        return None
    try:
        return float(state.state)
    except (TypeError, ValueError):
        return None


def find_device_sources(hass: HomeAssistant, pitch_entity_id: str) -> dict[str, str]:
    """Die Werte suchen, die das Gerät selbst führt.

    Gesucht wird ausschließlich auf dem Gerät, zu dem der Neigungssensor
    gehört. Über alle Geräte zu suchen wäre gefährlich: bei zwei Fahrzeugen
    im selben Home Assistant könnte sonst der Radstand des einen mit der
    Neigung des anderen zusammentreffen.

    Findet sich nichts - etwa weil jemand einen fremden Neigungssensor
    eingerichtet hat -, bleibt es bei den eigenen Reglern.

    Steht hier und nicht im Rechenkern, weil auch der Einrichtungsdialog
    wissen muss, welche seiner Felder in Wahrheit das Gerät hält.
    """
    registry = er.async_get(hass)
    pitch = registry.async_get(pitch_entity_id)
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
    return found


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

        # Gedächtnis der Ebenheit je Achse - siehe _axis_level.
        self._level_hold: dict[str, bool] = {"pitch": False, "roll": False}
        # Gedächtnis der Schräglagenwarnung - siehe tilt_warning.
        self._tilt_hold: bool = False

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
        found = find_device_sources(self.hass, self._config[CONF_PITCH_SENSOR])
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
                if key in DEVICE_SWITCH_VALUES or key in DEVICE_BINARY_VALUES:
                    return state.state == STATE_ON
                if key in DEVICE_TEXT_VALUES:
                    return state.state
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
        return bool(self.get_value(CONF_PRECISE))

    @property
    def position_changed(self) -> bool:
        """Hat das Fahrzeug seine Ruhelage verlassen?

        Kommt aus dem Gerät und nicht aus einer Rechnung hier: Der Bezugspunkt
        muss über Stunden gelten, und Home Assistant darf in der Zeit neu
        starten dürfen, ohne dass die Überwachung von vorn beginnt.
        """
        return bool(self.get_value(CONF_POSITION_CHANGED))

    # -- Selbstüberwachung ---------------------------------------------------
    #
    # Reine Durchreichen. Entschieden wird alles im Gerät: Es kennt die
    # Temperatur bei der letzten Kalibrierung und zählt ununterbrochen mit -
    # Home Assistant darf in der Zeit neu starten.

    @property
    def calibration_check(self) -> bool:
        """Sollte nachkalibriert werden?

        Nicht die Zeit verschiebt den Nullpunkt eines Neigungsmessers, sondern
        die Temperatur. Ohne diese Meldung vertraut der Kunde im August einer
        Kalibrierung vom März - und merkt es nie.
        """
        return bool(self.get_value(CONF_CALIBRATION_CHECK))

    @property
    def calibration_text(self) -> str | None:
        """Wann und bei welcher Temperatur zuletzt kalibriert wurde."""
        wert = self.get_value(CONF_CALIBRATION_TEXT)
        return wert if isinstance(wert, str) else None

    @property
    def mount_check(self) -> bool:
        """Liefert der Sensor unglaubwürdige Werte?

        Ein Fahrzeug steht nie 45 Grad schief, und der Betrag der
        Erdbeschleunigung ist immer 1,0 g. Trifft eins davon nicht zu, hat sich
        das Gehäuse gelöst - sonst landet dieser Fehler als "misst falsch" in
        einer Rezension.

        Gerechnet wird das im Geraet, nicht hier. Diese Eigenschaft liest nur
        den fertigen Binaersensor - deshalb beruehrt der Einheitenwechsel von
        m/s2 auf g in 4.0.0 diese Datei nicht.
        """
        return bool(self.get_value(CONF_MOUNT_CHECK))

    @property
    def frost(self) -> bool:
        return bool(self.get_value(CONF_FROST))

    @property
    def indoor_temp(self) -> float | None:
        """Temperatur im Gerät. Kein Thermometer - der Chip erwärmt sich
        selbst -, aber genug für eine Frostwarnung."""
        if CONF_INDOOR_TEMP not in self._device_sources:
            return None
        try:
            return round(float(self.get_value(CONF_INDOOR_TEMP)), 1)
        except (TypeError, ValueError):
            return None

    # -- Zielprofile ---------------------------------------------------------

    def _target_deg(self, key: str, dimension_mm: float) -> float:
        """Die Zielneigung einer Achse in Grad.

        Dieselbe Umrechnung wie bei der Toleranz und wie im Gerät: Der
        Zentimeterwert gilt am jeweiligen Fahrzeugmaß. Führt das Gerät keine
        Profile - alte Firmware -, ist das Ziel null und alles bleibt, wie es
        war.
        """
        if key not in self._device_sources:
            return 0.0
        try:
            zentimeter = float(self.get_value(key))
        except (TypeError, ValueError):
            return 0.0
        if not zentimeter:
            return 0.0
        return math.degrees(math.atan(zentimeter * 10.0 / dimension_mm))

    @property
    def target_pitch(self) -> float:
        return self._target_deg(CONF_TARGET_LONG, self.wheelbase)

    @property
    def target_roll(self) -> float:
        return self._target_deg(CONF_TARGET_LAT, self.track)

    @property
    def profile(self) -> str | None:
        """Welches Zielprofil gilt - "Ausrichten", "Schlafen", "Ablassen"."""
        wert = self.get_value(CONF_PROFILE)
        return wert if isinstance(wert, str) else None

    @property
    def profile_entity(self) -> str | None:
        """Die Auswahl im Gerät, damit die Karte sie bedienen kann statt eine
        zweite danebenzustellen."""
        return self._device_sources.get(CONF_PROFILE)

    def _target_cm(self, key: str) -> float:
        """Die Zielneigung in Zentimetern - für die Anzeige, nicht zum
        Rechnen. Gerechnet wird in Grad, siehe _target_deg."""
        if key not in self._device_sources:
            return 0.0
        try:
            return round(float(self.get_value(key)), 1)
        except (TypeError, ValueError):
            return 0.0

    @property
    def target_long_cm(self) -> float:
        return self._target_cm(CONF_TARGET_LONG)

    @property
    def target_lat_cm(self) -> float:
        return self._target_cm(CONF_TARGET_LAT)

    @property
    def deviation_pitch(self) -> float | None:
        """Was noch zu tun ist: Neigung minus Ziel.

        Hierauf rechnet alles, was mit dem AUSRICHTEN zu tun hat. Der echte
        Winkel bleibt in pitch - den braucht die Schräglagenwarnung.
        """
        return None if self.pitch is None else self.pitch - self.target_pitch

    @property
    def deviation_roll(self) -> float | None:
        return None if self.roll is None else self.roll - self.target_roll

    # -- Kühlschrank-Zeitkonto ----------------------------------------------

    @property
    def fridge_warning(self) -> bool:
        """Steht es lange genug schief, dass der Kühlschrank leidet?

        Nicht dasselbe wie tilt_warning: Jene meldet den Winkel, diese den
        Winkel MAL DER ZEIT. Wer rangiert, löst tilt_warning aus und diese
        hier nicht - und genau darauf gehört eine Benachrichtigung gelegt.

        Führt das Gerät den Wert nicht - alte Firmware oder ein fremder
        Neigungssensor -, bleibt es beim reinen Winkel.
        """
        if CONF_FRIDGE_WARNING in self._device_sources:
            return bool(self.get_value(CONF_FRIDGE_WARNING))
        return self.tilt_warning

    @property
    def fridge_text(self) -> str | None:
        """Der Klartextsatz des Geräts zum Kühlschrank."""
        wert = self.get_value(CONF_FRIDGE_TEXT)
        return wert if isinstance(wert, str) else None

    @property
    def tilt_minutes(self) -> float | None:
        """Seit wie vielen Minuten es zu schief steht. None, wenn das Gerät
        die Zeit nicht mitzählt - dann zeigt die Karte nur den Winkel."""
        if CONF_TILT_MINUTES not in self._device_sources:
            return None
        try:
            return round(float(self.get_value(CONF_TILT_MINUTES)), 1)
        except (TypeError, ValueError):
            return None

    @property
    def fridge_minutes(self) -> float | None:
        """Ab wann das Gerät die Schräglage kritisch nennt."""
        if CONF_FRIDGE_MINUTES not in self._device_sources:
            return None
        try:
            return float(self.get_value(CONF_FRIDGE_MINUTES))
        except (TypeError, ValueError):
            return None

    # -- Wächter ------------------------------------------------------------
    #
    # Alles davon kommt aus dem Gerät, nichts wird hier nachgerechnet. Der
    # Grund ist derselbe wie bei der Lageänderung, nur schärfer: Ein
    # Wachdienst, der ausfällt, sobald Home Assistant neu startet, ist keiner.
    # Hier stehen nur die Durchreichen, damit die Karte einen Ort zum Fragen
    # hat.

    @property
    def guard(self) -> bool:
        """Ist der Wächter scharf?"""
        return bool(self.get_value(CONF_GUARD))

    @property
    def guard_alarm(self) -> bool:
        """Hat er ausgelöst? Rastet im Gerät ein und bleibt bis zum
        Quittieren stehen - deshalb ist das hier kein Ereignis, sondern ein
        Zustand, den man auch Stunden später noch sieht."""
        return bool(self.get_value(CONF_GUARD_ALARM))

    @property
    def guard_status(self) -> str | None:
        """Der Klartextsatz des Geräts - "scharf seit 2 h" oder "ALARM ...".

        Bewusst der Satz des Geräts und keine eigene Formulierung: Sonst
        stünde auf der Geräteseite etwas anderes als auf der Karte, und beim
        Zeitpunkt einer Meldung ist das kein Schönheitsfehler.
        """
        wert = self.get_value(CONF_GUARD_STATUS)
        return wert if isinstance(wert, str) else None

    @property
    def last_motion(self) -> str | None:
        """Wann zuletzt jemand am Fahrzeug war."""
        wert = self.get_value(CONF_LAST_MOTION)
        return wert if isinstance(wert, str) else None

    @property
    def guard_entity(self) -> str | None:
        """Der Schalter des Geräts, damit die Karte ihn bedienen kann."""
        return self._device_sources.get(CONF_GUARD)

    @property
    def guard_ack_entity(self) -> str | None:
        """Der Quittierknopf des Geräts."""
        return self._device_sources.get(CONF_GUARD_ACK)

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

    # -- Ebenheit je Achse -------------------------------------------------

    def _axis_level(self, key: str, value: float | None, tolerance: float) -> bool:
        """Steht diese Achse innerhalb der Toleranz? Mit Hysterese.

        Die Frage hat genau eine Antwort, und die gilt für alles: Text,
        Wasserwaage, Blase, Fahrzeugneigung und Anweisung. Vorher rechnete
        jede dieser Stellen dieselbe Bedingung selbst aus - beim gleichen
        Messwert kam zwar überall dasselbe heraus, aber jede Stelle sprang für
        sich, sobald der Messwert auf der Schwelle stand.

        Der Rückweg liegt über dem Hinweg (LEVEL_RELEASE): Wer einmal
        drinsteht, bleibt drin, bis die Neigung deutlich darüber hinausgeht.
        Das ist keine Beschönigung, sondern die einzige Art, mit einem
        rauschenden Messwert eine ruhige Aussage zu treffen - die Alternative
        ist eine Anzeige, die im Stand zwischen "fertig" und "5 cm fehlen"
        hin und her springt.

        Absichtlich beim Lesen fortgeschrieben und nicht in _read_sources:
        Auch eine geänderte Toleranz oder ein geändertes Fahrzeugmaß muss
        sofort wirken, und die kommen nicht über die Sensoren herein.
        Mehrfaches Auswerten desselben Messwerts ändert nichts - die Regel
        kennt keinen Zwischenzustand.
        """
        if value is None:
            self._level_hold[key] = False
            return False

        deviation = abs(value)
        if self._level_hold[key]:
            if deviation > tolerance * self.level_release:
                self._level_hold[key] = False
        elif deviation <= tolerance:
            self._level_hold[key] = True
        return self._level_hold[key]

    @property
    def level_release(self) -> float:
        """Wie weit die Neigung über die Toleranz darf, bevor "eben" fällt.

        Kommt als Prozentangabe vom Gerät, weil "125 %" sich als "ein Viertel
        über der Toleranz" liest und "1,25" erst übersetzt werden muss. Unter
        100 % wäre es keine Hysterese mehr, sondern eine Anzeige, die "eben"
        schon vor der Toleranz zurücknimmt - deshalb die Untergrenze.
        """
        try:
            faktor = float(self.get_value(CONF_LEVEL_HOLD)) / 100.0
        except (TypeError, ValueError):
            return LEVEL_RELEASE
        return faktor if faktor >= 1.0 else LEVEL_RELEASE

    # -- Schräglagenwarnung -------------------------------------------------

    @property
    def tilt_limit(self) -> float:
        """Ab welcher Neigung ein Absorberkühlschrank aussteigt, in Grad."""
        try:
            return float(self.get_value(CONF_TILT_LIMIT))
        except (TypeError, ValueError):
            return DEFAULT_TILT_LIMIT_DEG

    @property
    def tilt_warning(self) -> bool:
        """Steht das Fahrzeug so schief, dass der Kühlschrank leidet?

        Ausdrücklich NICHT dasselbe wie "nicht eben": Die Toleranz setzt der
        Nutzer nach Geschmack, diese Grenze kommt aus der Technik. Wer acht
        Zentimeter erlaubt, weil ihm das zum Schlafen reicht, soll trotzdem
        erfahren, wenn sein Kühlschrank nicht mehr kühlt.

        Dieselben 20 Prozent Hysterese wie in der Firmware: Ohne sie flattert
        die Meldung genau an der Grenze, und eine Warnung, die im Minutentakt
        kommt und geht, schaltet man ab.
        """
        if self.pitch is None or self.roll is None:
            self._tilt_hold = False
            return False
        grenze = self.tilt_limit
        abweichung = max(abs(self.pitch), abs(self.roll))
        self._tilt_hold = (
            abweichung > grenze * 0.8 if self._tilt_hold else abweichung > grenze
        )
        return self._tilt_hold

    @property
    def level_pitch(self) -> bool:
        """Längsachse innerhalb der Toleranz - gemessen am ZIEL des Profils."""
        return self._axis_level("pitch", self.deviation_pitch, self.tolerance_pitch)

    @property
    def level_roll(self) -> bool:
        """Querachse innerhalb der Toleranz - gemessen am ZIEL des Profils."""
        return self._axis_level("roll", self.deviation_roll, self.tolerance_roll)

    @property
    def correction_pitch_cm(self) -> float | None:
        """Wie hoch die Front bzw. das Heck noch müsste, in cm.

        Gegen das Ziel des Profils, nicht gegen die Waagerechte: Im
        Schlafprofil sind die letzten zwei Zentimeter Heckhöhe kein
        Korrekturbedarf, sondern die Absicht.
        """
        if self.deviation_pitch is None:
            return None
        return self.wheelbase * math.tan(math.radians(abs(self.deviation_pitch))) / 10.0

    @property
    def correction_roll_cm(self) -> float | None:
        if self.deviation_roll is None:
            return None
        return self.track * math.tan(math.radians(abs(self.deviation_roll))) / 10.0

    @property
    def phase(self) -> str:
        """Grobe Lage als ein Wort - Grundlage für Ansagen und Karte.

        Gegen das Ziel des Profils gerechnet: Die Phase treibt die Ansage, und
        die soll nicht "Heck hoch" sagen, wenn das Heck genau so hoch steht,
        wie es im Schlafprofil soll.
        """
        pitch, roll = self.deviation_pitch, self.deviation_roll
        if pitch is None or roll is None:
            return PHASE_UNKNOWN
        if abs(pitch) > IMPLAUSIBLE_DEG or abs(roll) > IMPLAUSIBLE_DEG:
            return PHASE_UNKNOWN

        tol_p = self.tolerance_pitch
        tol_r = self.tolerance_roll

        # Über _axis_level und nicht über den nackten Vergleich: sonst hätte
        # die Phase - und damit die Ansage - eine andere Schwelle als die
        # Anzeige, die dieselbe Frage bereits beantwortet hat.
        if self.level_pitch and self.level_roll:
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

        # Eine Achse, die innerhalb ihrer Toleranz steht, ist FERTIG - ihr
        # Restwinkel darf die Anweisung nicht mehr formen.
        #
        # Ohne das nützt der Zusammenzug in _merge_side nichts. Von Hand kippt
        # niemand exakt auf einer Achse: Schon 0,3 Grad Rest längs - ein Drittel
        # der Toleranz - erzeugen aus einer reinen Querneigung wieder drei
        # verschiedene Eckmaße, und die Anweisung nennt eine Längsrichtung, die
        # nach den eigenen Maßstäben des Nutzers gar nicht korrigiert werden
        # muss.
        #
        # Bezugsgröße ist dieselbe Toleranz, die auch über "steht eben"
        # entscheidet. Damit kann die Anweisung nichts verlangen, was die
        # Phasenanzeige bereits als erledigt ausweist - vorher konnte sie genau
        # das.
        # Gegen das ZIEL des Profils, nicht gegen die Waagerechte - siehe
        # deviation_pitch. Bei "Ausrichten" ist das Ziel null und die Rechnung
        # unverändert.
        pitch = 0.0 if self.level_pitch else self.deviation_pitch
        roll = 0.0 if self.level_roll else self.deviation_roll

        half_long = self.wheelbase * math.tan(math.radians(pitch)) / 20.0
        half_lat = self.track * math.tan(math.radians(roll)) / 20.0

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

        # Eine Achse innerhalb der Toleranz ist fertig und kommt nicht in die
        # Anweisung - dieselbe Regel wie beim Wohnmobil in wheel_lifts_cm.
        # Ohne sie stünde beim Wohnwagen "Stützrad hoch, 3 cm" unter einer
        # Anzeige, die für dieselbe Achse gerade "EBEN - STOP" meldet.

        # Quer: das tiefere Rad auf den Keil. roll > 0 = rechts höher.
        across_cm = (
            0.0
            if self.level_roll
            else round(
                self.track * math.tan(math.radians(abs(self.deviation_roll))) / 10.0, 1
            )
        )
        if across_cm >= WHEEL_LIFT_IGNORE_CM:
            plan.append(
                {
                    "wheel": (
                        WHEEL_REAR_LEFT
                        if self.deviation_roll > 0
                        else WHEEL_REAR_RIGHT
                    ),
                    "cm": across_cm,
                    "steps": self.wedge_steps_for(across_cm),
                    "direction": DIRECTION_UP,
                }
            )

        # Längs: Stützrad. pitch > 0 = Front höher, also senken.
        along_cm = (
            0.0
            if self.level_pitch
            else round(
                self.wheelbase
                * math.tan(math.radians(abs(self.deviation_pitch)))
                / 10.0,
                1,
            )
        )
        if along_cm >= WHEEL_LIFT_IGNORE_CM:
            plan.append(
                {
                    "wheel": POINT_JOCKEY,
                    "cm": along_cm,
                    # Gekurbelt wird stufenlos - eine Keilstufe wäre hier
                    # eine Angabe, die niemand umsetzen kann.
                    "steps": None,
                    "direction": (
                        DIRECTION_DOWN if self.deviation_pitch > 0 else DIRECTION_UP
                    ),
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
        return _merge_side(plan)
