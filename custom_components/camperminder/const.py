"""Konstanten der CamperMinder."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "camperminder"

# --- Konfigurationsschlüssel (Config Entry) --------------------------------
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
CONF_PRECISE: Final = "precise"
CONF_LEVEL_HOLD: Final = "level_hold_percent"
CONF_TILT_LIMIT: Final = "tilt_limit"
CONF_POSITION_CHANGED: Final = "position_changed"

# --- Kühlschrank-Zeitkonto ---------------------------------------------------
# Was einen Absorberkühlschrank beschädigt, ist nicht der Winkel, sondern der
# Winkel mal der Zeit. Die Stufe entscheidet deshalb das Gerät, das die Zeit
# ununterbrochen mitzählt - Home Assistant darf zwischendurch neu starten.
CONF_FRIDGE_WARNING: Final = "fridge_warning"
CONF_FRIDGE_TEXT: Final = "fridge_text"
CONF_TILT_MINUTES: Final = "tilt_minutes"
CONF_FRIDGE_MINUTES: Final = "fridge_minutes"

# --- Zielprofile -------------------------------------------------------------
# Eine Wasserwaage kennt EIN Ziel: null. Dieses Gerät kennt Ziele - schlafen
# mit erhöhtem Kopfende, ablassen mit Neigung zum Ablasspunkt.
#
# Das Ziel wirkt ausschließlich auf das Ausrichten. Schräglagenwarnung und
# Wächter rechnen weiter mit der echten Neigung: Ein Absorberkühlschrank
# interessiert sich nicht dafür, wie jemand schlafen möchte.
#
# Die geltende Zielneigung liest die Integration als fertigen Zentimeterwert
# vom Gerät, statt sie aus Profil, Richtung und Betrag selbst abzuleiten. Sonst
# gäbe es dieselbe Entscheidung an drei Stellen - und seit 4.0.0 auch die
# Umrechnung von "Kopf links" in ein Vorzeichen.
# --- Selbstüberwachung -------------------------------------------------------
# Ein fest verbautes Gerät kann sich selbst beobachten, ein Handgerät nicht.
# Alles davon entsteht im Gerät: Es kennt die Temperatur bei der letzten
# Kalibrierung und zählt ununterbrochen mit, auch wenn Home Assistant neu
# startet.
CONF_CALIBRATION_CHECK: Final = "calibration_check"
CONF_CALIBRATION_TEXT: Final = "calibration_text"
CONF_MOUNT_CHECK: Final = "mount_check"
CONF_FROST: Final = "frost"
CONF_INDOOR_TEMP: Final = "indoor_temp"

CONF_PROFILE: Final = "profile"
CONF_TARGET_LONG: Final = "target_long"
CONF_TARGET_LAT: Final = "target_lat"

# --- Wächter ----------------------------------------------------------------
# Er wohnt vollständig im Gerät. Das ist keine Bequemlichkeit, sondern die
# Bedingung dafür, dass er etwas taugt: Ein Wachdienst, der ausfällt, sobald
# Home Assistant neu startet oder der Router aus ist, bewacht nichts.
#
# Die Integration liest ihn nur - und reicht die Entitätskennungen an die
# Karte weiter, damit die den Schalter und den Quittierknopf des GERÄTS
# bedienen kann statt eigene danebenzustellen.
CONF_GUARD: Final = "guard"
CONF_GUARD_ALARM: Final = "guard_alarm"
CONF_GUARD_STATUS: Final = "guard_status"
CONF_GUARD_ACK: Final = "guard_ack"
CONF_LAST_MOTION: Final = "last_motion"

# --- Art des Ausrichtens ----------------------------------------------------
# Der Unterschied ist grundsätzlich, nicht kosmetisch:
#
# Mit Keilen fährst du auf. Anheben lässt sich damit immer nur eine ganze
# Seite oder eine ganze Achse, in Stufen, und zwischen zwei Versuchen muss das
# Fahrzeug bewegt werden. Sinnvoll ist deshalb genau eine Anweisung auf einmal,
# die schwerere zuerst.
#
# Mit Hydraulik oder Luftkissen steht das Fahrzeug still und jede Ecke geht
# einzeln und stufenlos. Da ist die Reihenfolge egal, und die nützliche
# Angabe ist eine Liste aller Räder mit ihrer Hubhöhe - einmal ablesen,
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
# Wohnwagen - drei Auflagepunkte: zwei Räder auf einer Achse und das
#   Stützrad vorn. Quer läuft es wie beim Wohnmobil über die Spurweite.
#   Längs dagegen über das Stützrad, und das geht in BEIDE Richtungen -
#   hoch wie runter. Das Längenmaß ist dabei nicht der Radstand, sondern
#   der Abstand Achse zu Stützrad.
#
# Hintere Kurbelstützen bleiben außen vor: sie stabilisieren, sie richten
# nicht aus. Wer damit anhebt, verwindet den Aufbau.
CONF_VEHICLE_TYPE: Final = "vehicle_type"
VEHICLE_MOTORHOME: Final = "wohnmobil"
VEHICLE_CARAVAN: Final = "wohnwagen"
VEHICLE_TYPES: Final = [VEHICLE_MOTORHOME, VEHICLE_CARAVAN]
DEFAULT_VEHICLE_TYPE: Final = VEHICLE_MOTORHOME

# Auflagepunkt des Wohnwagens vorn.
POINT_JOCKEY: Final = "stuetzrad"

# Richtungen für die Anweisung. Nur das Stützrad kennt "runter".
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

# --- Seiten -----------------------------------------------------------------
# Steht nur EINE Achse schief, brauchen beide Räder derselben Seite exakt
# dasselbe Maß. Der Plan trägt dann nicht zwei Radpositionen, sondern eine
# Seite: "Vorne links 4 cm" und "Hinten links 4 cm" sind zwei Zeilen für einen
# Handgriff, und beide nennen eine Längsrichtung, die gar nicht korrigiert wird.
#
# Die Kennungen sind bewusst die Bestandteile der Radnamen - "vorne_links"
# zerfällt in "vorne" und "links". Dadurch findet der Zusammenzug sie ohne
# eigene Zuordnungstabelle.
SIDE_LEFT: Final = "links"
SIDE_RIGHT: Final = "rechts"
SIDE_FRONT: Final = "vorne"
SIDE_REAR: Final = "hinten"
SIDES: Final = (SIDE_LEFT, SIDE_RIGHT, SIDE_FRONT, SIDE_REAR)

# Unterhalb dieser Hubhöhe wird ein Rad nicht erwähnt. Ein halber Zentimeter
# ist weder mit einem Keil noch mit einer Stütze sinnvoll einstellbar und
# stünde nur als Rauschen in der Liste.
WHEEL_LIFT_IGNORE_CM: Final = 1.0

# --- Werte, die das Gerät selbst führt ------------------------------------
# Die Firmware hält Radstand, Spurweite, Toleranz, Keilstufe und Ausrichtart
# als eigene Entitäten - sonst wäre die Betriebsart ohne Home Assistant
# blind. Damit es diese Werte nicht zweimal gibt, liest die Integration sie
# vom Gerät, statt eigene danebenzustellen.
#
# Gesucht wird über den ursprünglichen Namen aus der Firmware, wie schon bei
# den Sensoren: der überlebt jedes Umbenennen im Frontend.
DEVICE_VALUE_ENTITIES: Final = {
    CONF_WHEELBASE: ("number", "Radstand"),
    CONF_TRACK: ("number", "Spurweite"),
    CONF_TOLERANCE_CM: ("number", "Toleranz"),
    CONF_TOLERANCE_DEG: ("number", "Toleranz genau"),
    CONF_WEDGE_STEP: ("number", "Keilstufe"),
    CONF_LEVEL_METHOD: ("select", "Ausrichtart"),
    CONF_VEHICLE_TYPE: ("select", "Fahrzeugart"),
    # Der Präzisionsmodus steht im Gerät, weil er ohne Home Assistant sonst
    # unerreichbar wäre - dieselbe Begründung wie bei der Einbaulage. Gesucht
    # wird über den Namen aus der Firmware, nicht über die Kennung: Aus dem
    # Umlaut macht ESPHome zwei Unterstriche, der Name bleibt lesbar.
    CONF_PRECISE: ("switch", "Präzisionsmodus"),
    # Der Haltebereich in Prozent. Bewusst OHNE eigenen Regler in dieser
    # Integration: Er beschreibt, wie sich die Anzeige anfühlt, und die
    # Anzeige steht in beiden Betriebsarten. Führt kein Gerät den Wert - etwa
    # bei einem fremden Neigungssensor -, gilt LEVEL_RELEASE.
    CONF_LEVEL_HOLD: ("number", "Haltebereich"),
    # Die Schwelle der Schräglagenwarnung. Auch sie führt das Gerät: Sie
    # betrifft die Technik des Kühlschranks, nicht den Geschmack des
    # Betrachters, und muss deshalb überall dieselbe sein.
    CONF_TILT_LIMIT: ("number", "Schräglage Grenzwert"),
    # Die Diebstahlmeldung. Sie entsteht im Gerät, weil sie eine Ruhelage
    # braucht, die über Stunden gilt - Home Assistant kann neu starten, das
    # Gerät läuft weiter.
    CONF_POSITION_CHANGED: ("binary_sensor", "Lageänderung"),
    # --- Wächter -----------------------------------------------------------
    # Ein Textsensor der Firmware landet in Home Assistant in der Domäne
    # "sensor". Der Schalter heißt genauso wie der Textsensor; gesucht wird
    # über das Paar aus Domäne und Name, deshalb stören sie sich nicht.
    # --- Selbstüberwachung -------------------------------------------------
    CONF_CALIBRATION_CHECK: ("binary_sensor", "Kalibrierung prüfen"),
    CONF_CALIBRATION_TEXT: ("sensor", "Kalibrierung"),
    CONF_MOUNT_CHECK: ("binary_sensor", "Montage prüfen"),
    CONF_FROST: ("binary_sensor", "Frostgefahr"),
    CONF_INDOOR_TEMP: ("sensor", "Innentemperatur"),
    # --- Zielprofile -------------------------------------------------------
    CONF_PROFILE: ("select", "Zielprofil"),
    CONF_TARGET_LONG: ("sensor", "Ziel längs"),
    CONF_TARGET_LAT: ("sensor", "Ziel quer"),
    # --- Kühlschrank-Zeitkonto ---------------------------------------------
    CONF_FRIDGE_WARNING: ("binary_sensor", "Kühlschrank Warnung"),
    CONF_FRIDGE_TEXT: ("sensor", "Kühlschrank"),
    CONF_TILT_MINUTES: ("sensor", "Schräglage Dauer"),
    CONF_FRIDGE_MINUTES: ("number", "Kühlschrank kritisch nach"),
    CONF_GUARD: ("switch", "Wächter"),
    CONF_GUARD_ALARM: ("binary_sensor", "Wächter Alarm"),
    CONF_GUARD_STATUS: ("sensor", "Wächter"),
    CONF_GUARD_ACK: ("button", "Alarm quittieren"),
    CONF_LAST_MOTION: ("sensor", "Letzte Bewegung"),
}

# Welche dieser Werte Schalter sind - ihr Zustand ist "on"/"off" und keine
# Zahl, die sich in eine Gleitkommazahl wandeln ließe.
DEVICE_SWITCH_VALUES: Final = (CONF_PRECISE, CONF_GUARD)

# Welche davon Binärsensoren sind - "on"/"off" statt einer Zahl, aber im
# Gegensatz zu einem Schalter nichts, was sich setzen ließe.
DEVICE_BINARY_VALUES: Final = (
    CONF_CALIBRATION_CHECK,
    CONF_MOUNT_CHECK,
    CONF_FROST,
    CONF_POSITION_CHANGED,
    CONF_GUARD_ALARM,
    CONF_FRIDGE_WARNING,
)

# Und welche Klartext liefern. Ohne diese Liste versuchte get_value, "scharf
# seit 2 h 10 min" in eine Zahl zu wandeln, scheiterte still und gäbe den
# Rückfallwert zurück - die Karte zeigte dann dauerhaft nichts.
#
# Der Quittierknopf steht mit in der Liste: Sein Zustand ist ein Zeitstempel,
# den niemand braucht. Gebraucht wird nur seine Entitätskennung, damit die
# Karte ihn drücken kann.
DEVICE_TEXT_VALUES: Final = (
    CONF_CALIBRATION_TEXT,
    CONF_PROFILE,
    CONF_GUARD_STATUS,
    CONF_LAST_MOTION,
    CONF_GUARD_ACK,
    CONF_FRIDGE_TEXT,
)

# Wie die Firmware ihre Ausrichtart benennt - sie spricht Klartext, wir
# intern Schlüssel.
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
DEFAULT_TOLERANCE_CM: Final = 5.0  # cm Höhenunterschied, der noch nicht stört
DEFAULT_WEDGE_STEP: Final = 0.0  # cm pro Keilstufe, 0 = Ansage in Zentimetern
DEFAULT_TOLERANCE_DEG: Final = 0.4  # nur im Präzisionsmodus

# Ab hier arbeitet ein Absorberkühlschrank nicht mehr zuverlässig. Keine
# gegriffene Zahl und nichts, was mit der Nivellier-Toleranz zu tun hat: Die
# darf jeder nach Geschmack setzen, diese Grenze kommt aus der Technik.
DEFAULT_TILT_LIMIT_DEG: Final = 3.0

# --- Phasen -----------------------------------------------------------------
# Bewusst grob gehalten: eine zappelnde cm-Zahl als Ansagegrundlage führt zu
# Dauergeplapper, weil sich der Text bei jedem Messwert ändert.
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

# Ab dieser Neigung sind die Werte unglaubwürdig (Sensor verrutscht, nie
# kalibriert). Dann lieber nichts sagen als etwas Falsches.
IMPLAUSIBLE_DEG: Final = 45.0

# Nach dem Kalibrieren müssen beide Achsen bei ~0 stehen. Großzügig genug
# für Sensorrauschen, streng genug um eine falsche Achszuordnung zu erkennen.
CALIBRATION_CHECK_DELAY: Final = 5.0
CALIBRATION_MAX_RESIDUAL_DEG: Final = 0.15

# Kleinste zulässige Schwelle, damit nie durch null geteilt wird.
MIN_TOLERANCE_DEG: Final = 0.05

# --- Ruhige Anzeige ---------------------------------------------------------
# Einmal "eben" bleibt "eben", bis die Neigung deutlich darüber hinausgeht.
#
# Ohne diese Hysterese entscheidet sich an EINEM Punkt, ob das Fahrzeug steht
# oder noch 5 cm fehlen - und genau auf diesem Punkt rauscht der Messwert. Bei
# 5 cm Toleranz stand deshalb abwechselnd "EBEN - STOP" und "noch 5,2 cm",
# mehrmals in der Sekunde. Der Anwender sieht ein zappelndes System, obwohl
# sich nichts bewegt, und weiß nicht mehr, welcher der beiden Sätze gilt.
#
# 1,25 ist bewusst deutlich: Der Rückweg muss größer sein als das Rauschen,
# sonst verschiebt die Hysterese das Flattern nur um ein paar Zehntel.
#
# Nur der Rückfallwert: Führt das Gerät den "Haltebereich", gilt dessen
# Prozentangabe. Wie ruhig eine Anzeige sein soll, ist Geschmack und gehört
# deshalb nicht in eine Konstante - siehe CONF_LEVEL_HOLD.
LEVEL_RELEASE: Final = 1.25

# Ansage-Entfernungen werden auf dieses Raster gerundet.
ANNOUNCE_CM_STEP: Final = 5

SIGNAL_UPDATE: Final = f"{DOMAIN}_update_{{}}"

STATIC_URL: Final = "/camperminder_static"

# Ohne Versionsangabe - die hängt __init__.py aus der manifest.json an. Diese
# URL lässt sich im Browser direkt aufrufen und ist damit die schnellste
# Antwort auf die Frage, ob die Integration eingerichtet ist: liefert sie 404,
# lief async_setup_entry nie.
CARD_URL: Final = f"{STATIC_URL}/camperminder-card.js"
