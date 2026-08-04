"""Konstanten der CamperMaid."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "campermaid"

# --- Konfigurationsschluessel (Config Entry) --------------------------------
CONF_PITCH_SENSOR: Final = "pitch_sensor"
CONF_ROLL_SENSOR: Final = "roll_sensor"
CONF_MOTION_SENSOR: Final = "motion_sensor"
CONF_CALIBRATE_BUTTON: Final = "calibrate_button"
CONF_NOTIFY_SERVICE: Final = "notify_service"
CONF_NOTIFY_TTS: Final = "notify_tts"

CONF_WHEELBASE: Final = "wheelbase"
CONF_TRACK: Final = "track"
CONF_TOLERANCE_CM: Final = "tolerance_cm"
CONF_WEDGE_STEP: Final = "wedge_step"
CONF_TOLERANCE_DEG: Final = "tolerance_deg"
CONF_LEVEL_METHOD: Final = "level_method"

# --- Art des Ausrichtens ----------------------------------------------------
# Der Unterschied ist grundsaetzlich, nicht kosmetisch:
#
# Mit Keilen faehrst du auf. Anheben laesst sich damit immer nur eine ganze
# Seite oder eine ganze Achse, in Stufen, und zwischen zwei Versuchen muss das
# Fahrzeug bewegt werden. Sinnvoll ist deshalb genau eine Anweisung auf einmal,
# die schwerere zuerst.
#
# Mit Hydraulik oder Luftkissen steht das Fahrzeug still und jede Ecke geht
# einzeln und stufenlos. Da ist die Reihenfolge egal, und die nuetzliche
# Angabe ist eine Liste aller Raeder mit ihrer Hubhoehe - einmal ablesen,
# einmal einstellen.
METHOD_WEDGE: Final = "keile"
METHOD_LIFT: Final = "hebesystem"
METHODS: Final = [METHOD_WEDGE, METHOD_LIFT]
DEFAULT_LEVEL_METHOD: Final = METHOD_WEDGE

# --- Fahrzeugart ------------------------------------------------------------
# Auch das ist kein Beschriftungsunterschied, sondern eine andere Geometrie:
#
# Wohnmobil - vier Auflagepunkte, zwei Achsen. Korrigiert wird nur nach oben,
#   denn ein Keil kann nichts absenken.
#
# Wohnwagen - drei Auflagepunkte: zwei Raeder auf einer Achse und das
#   Stuetzrad vorn. Quer laeuft es wie beim Wohnmobil ueber die Spurweite.
#   Laengs dagegen ueber das Stuetzrad, und das geht in BEIDE Richtungen -
#   hoch wie runter. Das Laengenmass ist dabei nicht der Radstand, sondern
#   der Abstand Achse zu Stuetzrad.
#
# Hintere Kurbelstuetzen bleiben aussen vor: sie stabilisieren, sie richten
# nicht aus. Wer damit anhebt, verwindet den Aufbau.
CONF_VEHICLE_TYPE: Final = "vehicle_type"
VEHICLE_MOTORHOME: Final = "wohnmobil"
VEHICLE_CARAVAN: Final = "wohnwagen"
VEHICLE_TYPES: Final = [VEHICLE_MOTORHOME, VEHICLE_CARAVAN]
DEFAULT_VEHICLE_TYPE: Final = VEHICLE_MOTORHOME

# Auflagepunkt des Wohnwagens vorn.
POINT_JOCKEY: Final = "stuetzrad"

# Richtungen fuer die Anweisung. Nur das Stuetzrad kennt "runter".
DIRECTION_UP: Final = "hoch"
DIRECTION_DOWN: Final = "runter"

# --- Radpositionen ----------------------------------------------------------
WHEEL_FRONT_LEFT: Final = "vorne_links"
WHEEL_FRONT_RIGHT: Final = "vorne_rechts"
WHEEL_REAR_LEFT: Final = "hinten_links"
WHEEL_REAR_RIGHT: Final = "hinten_rechts"
WHEELS: Final = (
    WHEEL_FRONT_LEFT,
    WHEEL_FRONT_RIGHT,
    WHEEL_REAR_LEFT,
    WHEEL_REAR_RIGHT,
)

# Unterhalb dieser Hubhoehe wird ein Rad nicht erwaehnt. Ein halber Zentimeter
# ist weder mit einem Keil noch mit einer Stuetze sinnvoll einstellbar und
# stuende nur als Rauschen in der Liste.
WHEEL_LIFT_IGNORE_CM: Final = 1.0

# --- Werte, die das Geraet selbst fuehrt ------------------------------------
# Die Firmware haelt Radstand, Spurweite, Toleranz, Keilstufe und Ausrichtart
# als eigene Entitaeten - sonst waere die Betriebsart ohne Home Assistant
# blind. Damit es diese Werte nicht zweimal gibt, liest die Integration sie
# vom Geraet, statt eigene danebenzustellen.
#
# Gesucht wird ueber den urspruenglichen Namen aus der Firmware, wie schon bei
# den Sensoren: der ueberlebt jedes Umbenennen im Frontend.
DEVICE_VALUE_ENTITIES: Final = {
    CONF_WHEELBASE: ("number", "Radstand"),
    CONF_TRACK: ("number", "Spurweite"),
    CONF_TOLERANCE_CM: ("number", "Toleranz"),
    CONF_WEDGE_STEP: ("number", "Keilstufe"),
    CONF_LEVEL_METHOD: ("select", "Ausrichtart"),
    CONF_VEHICLE_TYPE: ("select", "Fahrzeugart"),
}

# Wie die Firmware ihre Ausrichtart benennt - sie spricht Klartext, wir
# intern Schluessel.
DEVICE_METHOD_MAP: Final = {
    "Auffahrkeile": METHOD_WEDGE,
    "Hydraulik oder Luftkissen": METHOD_LIFT,
}

DEVICE_VEHICLE_MAP: Final = {
    "Wohnmobil": VEHICLE_MOTORHOME,
    "Wohnwagen": VEHICLE_CARAVAN,
}

# --- Voreinstellungen -------------------------------------------------------
DEFAULT_WHEELBASE: Final = 3500.0  # mm
DEFAULT_TRACK: Final = 1800.0  # mm
DEFAULT_TOLERANCE_CM: Final = 5.0  # cm Hoehenunterschied, der noch nicht stoert
DEFAULT_WEDGE_STEP: Final = 0.0  # cm pro Keilstufe, 0 = Ansage in Zentimetern
DEFAULT_TOLERANCE_DEG: Final = 0.4  # nur im Praezisionsmodus

# --- Phasen -----------------------------------------------------------------
# Bewusst grob gehalten: eine zappelnde cm-Zahl als Ansagegrundlage fuehrt zu
# Dauergeplapper, weil sich der Text bei jedem Messwert aendert.
PHASE_UNKNOWN: Final = "unbekannt"
PHASE_LEVEL: Final = "eben"
PHASE_CLOSE: Final = "fast"
PHASE_LEFT: Final = "links"
PHASE_RIGHT: Final = "rechts"
PHASE_REAR: Final = "heck"
PHASE_FRONT: Final = "front"

PHASES: Final = [
    PHASE_UNKNOWN,
    PHASE_LEVEL,
    PHASE_CLOSE,
    PHASE_LEFT,
    PHASE_RIGHT,
    PHASE_REAR,
    PHASE_FRONT,
]

# Richtungsphasen: hier wird eine Seite konkret angehoben.
DIRECTION_PHASES: Final = (PHASE_LEFT, PHASE_RIGHT, PHASE_REAR, PHASE_FRONT)

# --- Verhalten --------------------------------------------------------------
# Eine Phase muss so lange stabil stehen, bevor angesagt wird. Verhindert
# Flattern an der Grenze zwischen zwei Phasen.
ANNOUNCE_STABLE_SECONDS: Final = 3.0

# Ab dieser Neigung sind die Werte unglaubwuerdig (Sensor verrutscht, nie
# kalibriert). Dann lieber nichts sagen als etwas Falsches.
IMPLAUSIBLE_DEG: Final = 45.0

# Nach dem Kalibrieren muessen beide Achsen bei ~0 stehen. Grosszuegig genug
# fuer Sensorrauschen, streng genug um eine falsche Achszuordnung zu erkennen.
CALIBRATION_CHECK_DELAY: Final = 5.0
CALIBRATION_MAX_RESIDUAL_DEG: Final = 0.15

# Kleinste zulaessige Schwelle, damit nie durch null geteilt wird.
MIN_TOLERANCE_DEG: Final = 0.05

# Ansage-Entfernungen werden auf dieses Raster gerundet.
ANNOUNCE_CM_STEP: Final = 5

SIGNAL_UPDATE: Final = f"{DOMAIN}_update_{{}}"

STATIC_URL: Final = "/campermaid_static"

# Ohne Versionsangabe - die haengt __init__.py aus der manifest.json an. Diese
# URL laesst sich im Browser direkt aufrufen und ist damit die schnellste
# Antwort auf die Frage, ob die Integration eingerichtet ist: liefert sie 404,
# lief async_setup_entry nie.
CARD_URL: Final = f"{STATIC_URL}/campermaid-card.js"
