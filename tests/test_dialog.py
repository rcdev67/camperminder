"""Einrichtungs- und Optionsdialog.

Zwei Fehler aus dem Live-Test vom 25.09.2026 dürfen nicht wiederkommen:
- Radstand, Spurweite, Toleranz und Keilstufe aus dem Dialog blieben
  wirkungslos, weil das Gerät sie führt und Vorrang hat.
- Nach einem Gerätetausch schlug der Optionsdialog die Sensoren des
  abgesteckten Geräts vor.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from conftest import FakeHass, config_flow, eintrag, registrierung

PITCH = "sensor.muster_neigung_pitch"
GERAET = {
    "wheelbase": "number.muster_radstand",
    "track": "number.muster_spurweite",
    "tolerance_cm": "number.muster_toleranz",
    "wedge_step": "number.muster_keilstufe",
}
EINGABE = {"pitch_sensor": PITCH, "roll_sensor": "sensor.muster_neigung_roll",
           "wheelbase": 4213, "track": 1710, "tolerance_cm": 3, "wedge_step": 5,
           "notify_tts": True}
GEZEIGT = {"wheelbase": 3500.0, "track": 1800.0, "tolerance_cm": 5.0, "wedge_step": 0.0}


def geraetezustaende(radstand="3500.0", spur="1800.0", toleranz="5.0", keil="0.0"):
    return {GERAET["wheelbase"]: radstand, GERAET["track"]: spur,
            GERAET["tolerance_cm"]: toleranz, GERAET["wedge_step"]: keil}


@pytest.fixture(autouse=True)
def geraet_am_pitch_sensor(monkeypatch):
    """Nur der Muster-Pitch-Sensor gehört zu einem Gerät mit eigenen Werten.

    Dazu der Formularaufbau als Wörterbuch: Die Selektoren sind Platzhalter,
    und der Aufbau selbst ist nicht Gegenstand dieser Tests.
    """
    monkeypatch.setattr(config_flow, "find_device_sources",
                        lambda hass, pitch: dict(GERAET) if pitch == PITCH else {})
    monkeypatch.setattr(config_flow, "_schema", lambda hass, vorgaben: dict(vorgaben))


def schreibe(hass, eingabe, gezeigt):
    return asyncio.run(config_flow._async_write_to_device(hass, eingabe, gezeigt))


def test_vorbelegung_mit_geraetewerten_statt_optionen():
    hass = FakeHass(geraetezustaende())
    gezeigt = config_flow._effective_values(hass, {"pitch_sensor": PITCH, "wheelbase": 9999})
    assert gezeigt["wheelbase"] == 3500.0
    assert gezeigt["wedge_step"] == 0.0


def test_vorbelegung_bei_geraet_aus_aus_optionen():
    gezeigt = config_flow._effective_values(FakeHass(), {"pitch_sensor": PITCH, "wheelbase": 4000})
    assert gezeigt["wheelbase"] == 4000


def test_geaenderte_masse_gehen_ins_geraet():
    hass = FakeHass(geraetezustaende())
    assert schreibe(hass, EINGABE, GEZEIGT) == {}
    assert ("number", "set_value", GERAET["wheelbase"], 4213.0) in hass.aufrufe
    assert sorted(a[2] for a in hass.aufrufe) == sorted(GERAET.values())


def test_gleiche_werte_nichts_geschrieben():
    hass = FakeHass(geraetezustaende("4213.0", "1710.0", "3.0", "5.0"))
    assert schreibe(hass, EINGABE, GEZEIGT) == {}
    assert hass.aufrufe == []


def test_geraet_aus_unveraendert_darf_speichern():
    unveraendert = dict(EINGABE, wheelbase=4000, track=1800, tolerance_cm=5, wedge_step=0)
    gezeigt = {"wheelbase": 4000, "track": 1800, "tolerance_cm": 5, "wedge_step": 0}
    hass = FakeHass()
    assert schreibe(hass, unveraendert, gezeigt) == {}
    assert hass.aufrufe == []


def test_geraet_aus_geaendert_meldet_fehler():
    gezeigt = {"wheelbase": 4000, "track": 1800, "tolerance_cm": 5, "wedge_step": 0}
    assert schreibe(FakeHass(), EINGABE, gezeigt) == {"base": "device_unreachable"}


def test_dienstfehler_meldet_fehler():
    hass = FakeHass(geraetezustaende(), dienst_fehler=True)
    assert schreibe(hass, EINGABE, GEZEIGT) == {"base": "device_unreachable"}


def test_fremder_sensor_nichts_geschrieben():
    hass = FakeHass(geraetezustaende())
    assert schreibe(hass, dict(EINGABE, pitch_sensor="sensor.fremd"), GEZEIGT) == {}
    assert hass.aufrufe == []


def _optionsdialog(hass, data, options):
    dialog = config_flow.CamperOptionsFlow()
    dialog.hass = hass
    dialog.config_entry = SimpleNamespace(data=data, options=options)
    return dialog


def test_optionsdialog_speichert_und_schreibt_ins_geraet():
    hass = FakeHass(geraetezustaende())
    dialog = _optionsdialog(
        hass,
        {"pitch_sensor": "sensor.alt_pitch", "roll_sensor": "sensor.alt_roll"},
        {"wheelbase": 3500, "track": 1800, "tolerance_cm": 5, "wedge_step": 0},
    )
    assert asyncio.run(dialog.async_step_init())["errors"] == {}
    ergebnis = asyncio.run(dialog.async_step_init(dict(EINGABE)))
    assert ergebnis["type"] == "create_entry"
    assert hass.zustaende[GERAET["wheelbase"]] == "4213.0"
    # Geleerte Felder müssen ausdrücklich None sein, sonst überlebt der alte Wert.
    assert ergebnis["data"]["motion_sensor"] is None
    assert ergebnis["data"]["calibrate_button"] is None


def test_optionsdialog_geraet_aus_bleibt_beim_fehler():
    dialog = _optionsdialog(
        FakeHass(),
        {"pitch_sensor": PITCH, "roll_sensor": "sensor.r"},
        {"wheelbase": 3500, "track": 1800, "tolerance_cm": 5, "wedge_step": 0},
    )
    asyncio.run(dialog.async_step_init())
    for _ in range(2):  # auch der zweite Versuch darf nicht still speichern
        ergebnis = asyncio.run(dialog.async_step_init(dict(EINGABE)))
        assert ergebnis["type"] == "form"
        assert ergebnis["errors"] == {"base": "device_unreachable"}


TAUSCH = registrierung(
    eintrag("sensor.alt_pitch", "alt", "sensor", "Neigung Pitch"),
    eintrag("sensor.alt_roll", "alt", "sensor", "Neigung Roll"),
    eintrag("binary_sensor.alt_bewegung", "alt", "binary_sensor", "In Bewegung"),
    eintrag("button.alt_kalibrieren", "alt", "button", "Neigung kalibrieren"),
    eintrag(PITCH, "neu", "sensor", "Neigung Pitch"),
    eintrag("sensor.muster_neigung_roll", "neu", "sensor", "Neigung Roll"),
    eintrag("binary_sensor.muster_in_bewegung", "neu", "binary_sensor", "In Bewegung"),
)
LEBENDIG = dict(geraetezustaende(), **{
    PITCH: "0.1", "sensor.muster_neigung_roll": "0.2", "sensor.alt_pitch": "unavailable",
})


def test_erkennung_lebendes_geraet_vor_vollstaendigem_toten(mit_registrierung):
    mit_registrierung(TAUSCH)
    assert config_flow._autodetect(FakeHass(LEBENDIG))["pitch_sensor"] == PITCH


def test_geraetetausch_neue_sensoren_alte_masse(mit_registrierung):
    mit_registrierung(TAUSCH)
    hass = FakeHass(LEBENDIG)
    dialog = _optionsdialog(
        hass,
        {"pitch_sensor": "sensor.alt_pitch", "roll_sensor": "sensor.alt_roll",
         "motion_sensor": "binary_sensor.alt_bewegung",
         "calibrate_button": "button.alt_kalibrieren"},
        {"wheelbase": 4213, "track": 1710, "tolerance_cm": 3, "wedge_step": 5},
    )
    gezeigt = asyncio.run(dialog.async_step_init())["data_schema"]
    assert gezeigt["pitch_sensor"] == PITCH
    assert gezeigt["roll_sensor"] == "sensor.muster_neigung_roll"
    assert gezeigt["motion_sensor"] == "binary_sensor.muster_in_bewegung"
    assert gezeigt["calibrate_button"] is None  # die tote Taste des alten Geräts
    assert gezeigt["wheelbase"] == 4213 and gezeigt["track"] == 1710

    eingabe = {k: v for k, v in gezeigt.items() if v is not None}
    ergebnis = asyncio.run(dialog.async_step_init(eingabe))
    assert ergebnis["type"] == "create_entry"
    # Die Fahrzeugmaße wandern ins neue Gerät, statt dessen Werkswerte zu behalten.
    assert hass.zustaende[GERAET["wheelbase"]] == "4213.0"
    assert hass.zustaende[GERAET["wedge_step"]] == "5.0"


def test_kein_tausch_solange_eingetragenes_geraet_lebt(mit_registrierung):
    mit_registrierung(TAUSCH)
    hass = FakeHass(dict(LEBENDIG, **{"sensor.alt_pitch": "0.3"}))
    assert config_flow._replacement_sensors(hass, {"pitch_sensor": "sensor.alt_pitch"}) == {}
