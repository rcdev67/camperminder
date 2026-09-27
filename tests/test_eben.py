"""Ob eine Achse eben ist, entscheidet das Gerät - und alle übernehmen es.

Bis 4.0.5 entschieden vier Stellen selbst: die Firmware für Anweisung und
Hub-Werte (ohne Haltebereich), die Firmware für "Camper steht gerade" (mit
einem gemeinsamen Gedächtnis für beide Achsen), die Geräteseite und die
Integration (je mit eigenem Gedächtnis). Im Bereich zwischen Toleranz und
Haltebereich nannte das Gerät dann noch "Vorne links 1,0 cm hoch", während
die Karte schon "eben" zeigte.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from conftest import WURZEL, FakeHass, const, coordinator

HARDWARE = (WURZEL / "esphome" / "level" / "hardware.yaml").read_text(encoding="utf-8")
WEBUI = (WURZEL / "esphome" / "level" / "webui.js").read_text(encoding="utf-8")

# Längs 0,5 Grad über 4213 mm Radstand bei 3 cm Toleranz (Schwelle 0,41 Grad):
# außerhalb der Toleranz, aber innerhalb des Haltebereichs (125 %: 0,51 Grad).
IM_HALTEBEREICH = 0.45


def kern(pitch, roll, zustaende=None, mit_geraet=True):
    hass = FakeHass(zustaende or {})
    k = coordinator.CamperCoordinator(hass, "eintrag", {
        "pitch_sensor": "sensor.pitch", "roll_sensor": "sensor.roll",
        "wheelbase": 4213, "track": 1710, "tolerance_cm": 3, "wedge_step": 5,
        "level_method": "keile",
    })
    k.pitch, k.roll = pitch, roll
    if mit_geraet:
        k._device_sources = {
            const.CONF_LEVEL_PITCH_DEVICE: "binary_sensor.pitch_eben",
            const.CONF_LEVEL_ROLL_DEVICE: "binary_sensor.roll_eben",
        }
    return k


def test_geraet_sagt_eben_obwohl_eigene_rechnung_nicht():
    # Frisch gestartet kennt die eigene Rechnung den Verlauf nicht und sagt
    # im Haltebereich "nicht eben" - das Gerät weiß es besser.
    k = kern(IM_HALTEBEREICH, 0.0, {"binary_sensor.pitch_eben": "on", "binary_sensor.roll_eben": "on"})
    assert k.level_pitch is True
    # ... und die Anweisung folgt: nichts zu tun.
    assert k.instruction["steps"] == []


def test_geraet_sagt_nicht_eben():
    k = kern(0.1, 0.0, {"binary_sensor.pitch_eben": "off", "binary_sensor.roll_eben": "on"})
    assert k.level_pitch is False


@pytest.mark.parametrize("zustand", ["unavailable", "unknown"])
def test_geraet_ohne_wert_eigene_rechnung(zustand):
    k = kern(0.1, 0.0, {"binary_sensor.pitch_eben": zustand, "binary_sensor.roll_eben": zustand})
    assert k.level_pitch is True  # 0,1 Grad liegt in der Toleranz


def test_ohne_geraetesensoren_eigene_hysterese():
    # Fremder Neigungssensor oder ältere Firmware: wie bisher.
    k = kern(0.1, 0.0, mit_geraet=False)
    assert k.level_pitch is True
    k.pitch = IM_HALTEBEREICH
    assert k.level_pitch is True   # bleibt im Haltebereich eben
    k.pitch = 0.6
    assert k.level_pitch is False  # darüber hinaus nicht mehr


def test_integration_kennt_die_geraetesensoren():
    assert const.DEVICE_VALUE_ENTITIES[const.CONF_LEVEL_PITCH_DEVICE] == ("binary_sensor", "Pitch eben")
    assert const.DEVICE_VALUE_ENTITIES[const.CONF_LEVEL_ROLL_DEVICE] == ("binary_sensor", "Roll eben")


def _block(name: str) -> str:
    block = HARDWARE[HARDWARE.index(f'name: "{name}"'):]
    return block[:block.index("- platform:")]


@pytest.mark.parametrize(("name", "merker"), [("Pitch eben", "eben_p"), ("Roll eben", "eben_r")])
def test_firmware_veroeffentlicht_die_entscheidung(name, merker):
    block = _block(name)
    assert "internal: true" not in block  # überall: Geräteseite, HA, MQTT
    assert f"return id({merker});" in block


def test_firmware_eine_entscheidung_fuer_alles():
    # Hub-Werte und Anweisung
    assert "const float p = id(eben_p) ? 0.0f : p_soll;" in HARDWARE
    assert "const float r = id(eben_r) ? 0.0f : r_soll;" in HARDWARE
    # "Camper steht gerade"
    assert "return id(eben_p) && id(eben_r);" in _block("Camper steht gerade")
    # Keine zweite Rechnung mehr
    assert "level_hold" not in HARDWARE
    assert "fabsf(p_soll) <= tol_p" not in HARDWARE


def test_haltebereich_regel_gleich():
    # Firmware: toleranz * Haltebereich, sobald eben - sonst toleranz.
    assert "toleranz * (vorher ? halten / 100.0f : 1.0f)" in HARDWARE
    assert 'level_release_default: "125"' in HARDWARE
    assert const.LEVEL_RELEASE * 100 == 125


def test_geraeteseite_uebernimmt():
    assert 'geraetEben("pitch_eben")' in WEBUI
    assert 'geraetEben("roll_eben")' in WEBUI
    assert "pitch_eben/state" in (WURZEL / "docs" / "mqtt.md").read_text(encoding="utf-8")
