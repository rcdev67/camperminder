"""Heimatort folgt dem Fahrzeug: wann umgezogen wird und wann nicht.

Der alte Heimatort ist der Standard von Home Assistant in Amsterdam - dort
steht er, solange niemand einen eingetragen hat. Der Stellplatz ist ein
öffentlicher Ort (Domplatte in Köln), kein echter: Ein Repository, das
jeder lesen kann, soll nicht verraten, wo ein Fahrzeug steht.
"""

from __future__ import annotations

import importlib
from datetime import datetime, timedelta, timezone

import pytest

from conftest import PAKET, config_flow, const

heimatort = importlib.import_module(f"{PAKET}.heimatort")
Standort = heimatort.Standort

AMSTERDAM = (52.3731339, 4.8903147)
STELLPLATZ = (50.9413, 6.9583)
T0 = datetime(2026, 10, 11, 11, 0, tzinfo=timezone.utc)


def bei(minuten: float) -> datetime:
    return T0 + timedelta(minutes=minuten)


def meldung(ort, minuten, genauigkeit=10.0, hoehe=106.0, nord_m=0.0):
    """Eine GPS-Meldung, auf Wunsch um einige Meter nach Norden versetzt."""
    return Standort(ort[0] + nord_m / 111_320, ort[1], genauigkeit, hoehe, bei(minuten))


def gefahren(nachzug, von=0.0, bis=5.0):
    """Level meldet eine Fahrt von `von` bis `bis` Minuten."""
    nachzug.bewegung(True, bei(von))
    nachzug.bewegung(False, bei(bis))


def test_abstand_amsterdam_koeln():
    km = heimatort.abstand_m(*AMSTERDAM, *STELLPLATZ) / 1000
    assert 210 < km < 217  # Luftlinie Dam - Dom, rund 214 km


def test_nach_der_fahrt_zieht_der_heimatort_um():
    n = heimatort.HeimatortNachzug()
    n.fahrt_gesehen = False  # kein Neustart, sondern laufender Betrieb
    gefahren(n, 0, 30)
    n.standort(meldung(STELLPLATZ, 31))
    assert n.pruefen(bei(34), AMSTERDAM, mit_bewegung=True) is None  # erst 3 min
    neu = n.pruefen(bei(36.5), AMSTERDAM, mit_bewegung=True)
    assert (neu.breite, neu.laenge) == STELLPLATZ and neu.hoehe == 106.0
    # Einmal umgezogen, nicht noch einmal - auch nicht am alten Heimatort.
    assert n.pruefen(bei(40), AMSTERDAM, mit_bewegung=True) is None
    assert n.pruefen(bei(40), STELLPLATZ, mit_bewegung=True) is None


def test_tablet_im_restaurant_verschiebt_nichts():
    # Das Tablet wandert 2 km weg, das Fahrzeug steht: Level meldet nichts.
    n = heimatort.HeimatortNachzug()
    n.standort(meldung(STELLPLATZ, 0))
    assert n.pruefen(bei(10), STELLPLATZ, mit_bewegung=True) is None  # am Platz
    n.standort(meldung(STELLPLATZ, 20, nord_m=2000))
    assert n.pruefen(bei(60), STELLPLATZ, mit_bewegung=True) is None


def test_kurze_bewegung_im_fahrzeug_ist_keine_fahrt():
    n = heimatort.HeimatortNachzug()
    n.fahrt_gesehen = False
    gefahren(n, 0, 1.5)  # jemand geht umher
    n.standort(meldung(STELLPLATZ, 2, nord_m=2000))
    assert n.pruefen(bei(20), STELLPLATZ, mit_bewegung=True) is None


def test_halt_an_der_ampel_reicht_nicht():
    n = heimatort.HeimatortNachzug()
    gefahren(n, 0, 10)
    n.standort(meldung(STELLPLATZ, 10))
    assert n.pruefen(bei(14), AMSTERDAM, mit_bewegung=True) is None


def test_stau_gps_steht_aber_level_faehrt():
    n = heimatort.HeimatortNachzug()
    n.bewegung(True, bei(0))
    n.standort(meldung(STELLPLATZ, 1))
    assert n.pruefen(bei(20), AMSTERDAM, mit_bewegung=True) is None


def test_derselbe_stellplatz_bleibt():
    n = heimatort.HeimatortNachzug()
    gefahren(n, 0, 3)
    n.standort(meldung(STELLPLATZ, 4, nord_m=400))  # nur 400 m weiter
    assert n.pruefen(bei(20), STELLPLATZ, mit_bewegung=True) is None


def test_gps_rauschen_im_stand_haelt_den_stillstand():
    n = heimatort.HeimatortNachzug()
    gefahren(n, 0, 3)
    # Gemessen am 11.10.2026: im Stand Sprünge um einige zehn Meter.
    for minute, versatz in ((4, 0), (5, 40), (6, -35), (7, 55), (8, 10)):
        n.standort(meldung(STELLPLATZ, minute, genauigkeit=30, nord_m=versatz))
    assert n.pruefen(bei(9.5), AMSTERDAM, mit_bewegung=True) is not None


def test_weiterfahren_setzt_den_stillstand_zurueck():
    n = heimatort.HeimatortNachzug()
    n.standort(meldung(STELLPLATZ, 0))
    n.standort(meldung(STELLPLATZ, 4, nord_m=300))
    assert n.pruefen(bei(7), AMSTERDAM, mit_bewegung=False) is None
    assert n.pruefen(bei(9.5), AMSTERDAM, mit_bewegung=False) is not None


def test_ungenaue_meldung_zaehlt_nicht():
    n = heimatort.HeimatortNachzug()
    n.standort(meldung(STELLPLATZ, 0, genauigkeit=150))
    assert n.letzter is None
    assert n.pruefen(bei(20), AMSTERDAM, mit_bewegung=False) is None


def test_nach_neustart_am_neuen_platz():
    # Home Assistant bekommt erst am neuen Platz wieder Strom: ob gefahren
    # wurde, weiß niemand, es gilt als gefahren.
    n = heimatort.HeimatortNachzug()
    n.standort(meldung(STELLPLATZ, 0))
    assert n.pruefen(bei(6), AMSTERDAM, mit_bewegung=True) is not None


def test_nach_neustart_am_alten_platz_gilt_wieder_level():
    n = heimatort.HeimatortNachzug()
    n.standort(meldung(STELLPLATZ, 0))
    assert n.pruefen(bei(6), STELLPLATZ, mit_bewegung=True) is None
    assert n.fahrt_gesehen is False
    n.standort(meldung(STELLPLATZ, 10, nord_m=2000))  # Tablet ins Restaurant
    assert n.pruefen(bei(30), STELLPLATZ, mit_bewegung=True) is None


def test_meldung_von_vor_der_fahrt_ist_veraltet():
    # Das Tablet schläft unterwegs ein. Seine letzte Meldung stammt vom alten
    # Platz und kommt beim Neueinlesen immer wieder herein.
    n = heimatort.HeimatortNachzug()
    n.fahrt_gesehen = False
    alt = Standort(AMSTERDAM[0] + 0.02, AMSTERDAM[1], 10.0, 0.0, bei(0))  # 2 km weg
    n.standort(alt)
    gefahren(n, 5, 120)
    n.standort(alt)
    assert n.letzter is None
    assert n.pruefen(bei(140), AMSTERDAM, mit_bewegung=True) is None
    n.standort(meldung(STELLPLATZ, 141))
    assert n.pruefen(bei(147), AMSTERDAM, mit_bewegung=True) is not None


def test_ohne_bewegungssensor_entscheidet_das_gps():
    n = heimatort.HeimatortNachzug()
    n.fahrt_gesehen = False
    n.standort(meldung(STELLPLATZ, 0))
    assert n.pruefen(bei(6), AMSTERDAM, mit_bewegung=False) is not None


@pytest.mark.parametrize(("eingabe", "fehler"), [
    ({"home_follow": True}, {"base": "location_source_missing"}),
    ({"home_follow": True, "location_source": None}, {"base": "location_source_missing"}),
    ({"home_follow": True, "location_source": "device_tracker.fold_5"}, {}),
    ({"home_follow": False}, {}),
    ({}, {}),
])
def test_dialog_verlangt_eine_quelle(eingabe, fehler):
    assert config_flow._check_home_follow(eingabe) == fehler


def test_quelle_laesst_sich_wieder_leeren():
    assert const.CONF_LOCATION_SOURCE in config_flow.CLEARABLE_KEYS


def test_texte_in_allen_sprachen():
    import json

    from conftest import WURZEL

    ordner = WURZEL / "custom_components" / "camperminder"
    for datei in ("strings.json", "translations/de.json", "translations/en.json"):
        texte = json.loads((ordner / datei).read_text(encoding="utf-8"))
        for teil, schritt in (("config", "user"), ("options", "init")):
            step = texte[teil]["step"][schritt]
            for schluessel in (const.CONF_LOCATION_SOURCE, const.CONF_HOME_FOLLOW):
                assert schluessel in step["data"], (datei, teil, schluessel)
                assert schluessel in step["data_description"], (datei, teil, schluessel)
            assert "location_source_missing" in texte[teil]["error"]
        assert "home_here" in texte["entity"]["button"]
