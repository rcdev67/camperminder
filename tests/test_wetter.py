"""Wetterwächter für die Markise: die Rechnung und das Halten der Warnung.

Die Einträge unten sind wörtlich aus weather.get_forecasts (type: hourly)
eines echten Home Assistant vom 17.10.2026 übernommen: met.no ohne Böen,
OpenWeatherMap mit. Die Rechnung wird an der Schreibweise geprüft, in der
Home Assistant die Vorhersage tatsächlich liefert, nicht an einer
ausgedachten. Für die Fälle mit Unwetter sind einzelne Werte geändert;
welche, steht jeweils dabei.

Bis 4.2.4 stand dieselbe Rechnung als Vorlage im Blueprint, mit denselben
Sätzen. Die Erwartungen hier sind von dort übernommen.
"""

from __future__ import annotations

import importlib
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from conftest import PAKET, WURZEL, config_flow, const

wetter = importlib.import_module(f"{PAKET}.wetter")

JETZT = datetime(2026, 10, 18, 20, 30, tzinfo=timezone.utc)  # 22:30 Uhr in Berlin
SOMMERZEIT = timezone(timedelta(hours=2))

MET_NO = [
    {"condition": "cloudy", "datetime": "2026-10-18T20:00:00+00:00", "wind_bearing": 66.1,
     "cloud_coverage": 100, "uv_index": 0, "temperature": 10.9, "wind_speed": 13.3,
     "precipitation": 0, "humidity": 88},
    {"condition": "cloudy", "datetime": "2026-10-18T21:00:00+00:00", "wind_bearing": 72.1,
     "cloud_coverage": 100, "uv_index": 0, "temperature": 11.1, "wind_speed": 15.8,
     "precipitation": 0, "humidity": 87},
    {"condition": "cloudy", "datetime": "2026-10-18T22:00:00+00:00", "wind_bearing": 69.3,
     "cloud_coverage": 100, "uv_index": 0, "temperature": 11, "wind_speed": 16.9,
     "precipitation": 0, "humidity": 87},
    {"condition": "cloudy", "datetime": "2026-10-18T23:00:00+00:00", "wind_bearing": 76.3,
     "cloud_coverage": 100, "uv_index": 0, "temperature": 11, "wind_speed": 16.6,
     "precipitation": 0, "humidity": 87},
]

OWM = [
    {"datetime": "2026-10-18T19:00:00+00:00", "condition": "cloudy", "temperature": 13.1,
     "pressure": 1026, "cloud_coverage": 100, "wind_speed": 10.98, "wind_bearing": 40,
     "uv_index": 0, "precipitation_probability": 46, "precipitation": 0,
     "apparent_temperature": 12.7, "dew_point": 8.9, "wind_gust_speed": 20.81, "humidity": 87},
    {"datetime": "2026-10-18T20:00:00+00:00", "condition": "cloudy", "temperature": 12.8,
     "pressure": 1026, "cloud_coverage": 100, "wind_speed": 11.16, "wind_bearing": 63,
     "uv_index": 0, "precipitation_probability": 47, "precipitation": 0,
     "apparent_temperature": 12.4, "dew_point": 9.3, "wind_gust_speed": 21.17, "humidity": 88},
    {"datetime": "2026-10-18T21:00:00+00:00", "condition": "rainy", "temperature": 12.2,
     "pressure": 1026, "cloud_coverage": 99, "wind_speed": 14.26, "wind_bearing": 70,
     "uv_index": 0, "precipitation_probability": 51, "precipitation": 0.82,
     "apparent_temperature": 11.8, "dew_point": 9.9, "wind_gust_speed": 26.35, "humidity": 92},
    {"datetime": "2026-10-18T22:00:00+00:00", "condition": "cloudy", "temperature": 12.1,
     "pressure": 1026, "cloud_coverage": 100, "wind_speed": 16.24, "wind_bearing": 71,
     "uv_index": 0, "precipitation_probability": 0, "precipitation": 0,
     "apparent_temperature": 11.8, "dew_point": 9.9, "wind_gust_speed": 30.53, "humidity": 92},
    {"datetime": "2026-10-18T23:00:00+00:00", "condition": "cloudy", "temperature": 10.9,
     "pressure": 1026, "cloud_coverage": 99, "wind_speed": 13.5, "wind_bearing": 83,
     "uv_index": 0, "precipitation_probability": 0, "precipitation": 0,
     "apparent_temperature": 10.4, "dew_point": 9.6, "wind_gust_speed": 24.91, "humidity": 90},
    {"datetime": "2026-10-19T00:00:00+00:00", "condition": "cloudy", "temperature": 10.6,
     "pressure": 1027, "cloud_coverage": 94, "wind_speed": 12.38, "wind_bearing": 79,
     "uv_index": 0, "precipitation_probability": 0, "precipitation": 0,
     "apparent_temperature": 10.1, "dew_point": 9.2, "wind_gust_speed": 23.08, "humidity": 90},
]



def _geaendert(eintraege, stunde, **werte):
    """Kopie, in der der Eintrag zur angegebenen UTC-Stunde geändert ist."""
    return [dict(e, **werte) if e["datetime"][11:13] == f"{stunde:02d}" else dict(e)
            for e in eintraege]


def _satz(eintraege, *, wind_einheit="km/h", regen_einheit="mm",
          vorlauf=3, boeen=40, wind=25, regen=5) -> str:
    return wetter.bewerte(
        eintraege, JETZT,
        vorlauf_h=vorlauf, boeen_kmh=boeen, wind_kmh=wind, regen_mm=regen,
        stunde_lokal=lambda t: t.astimezone(SOMMERZEIT).hour,
        windeinheit=wind_einheit, regeneinheit=regen_einheit,
    ).satz


def test_ruhiges_wetter_meldet_nichts():
    assert _satz(MET_NO) == ""
    assert _satz(OWM) == ""
    assert wetter.bewerte([], JETZT, vorlauf_h=3, boeen_kmh=40, wind_kmh=25, regen_mm=5,
                          stunde_lokal=lambda t: 0) == wetter.RUHIG


def test_boeen_aus_openweathermap():
    # Echte Werte: Böen 26 km/h um 21 Uhr UTC (23 Uhr Berlin), höchstens 31.
    befund = wetter.bewerte(OWM, JETZT, vorlauf_h=3, boeen_kmh=25, wind_kmh=25, regen_mm=5,
                            stunde_lokal=lambda t: t.astimezone(SOMMERZEIT).hour)
    assert befund == wetter.Befund("einfahren", "Markise einfahren: ab 23 Uhr Böen bis 31 km/h.")


def test_ohne_boeen_zaehlt_der_mittlere_wind():
    # met.no liefert keine Böen. Gemeldet wird dann der mittlere Wind, und
    # nicht "Böen bis 0".
    assert _satz(MET_NO, wind=15) == "Markise einfahren: ab 23 Uhr Wind bis 17 km/h."


def test_laufende_stunde_heisst_jetzt():
    # Der Eintrag von 20 Uhr UTC gilt bis 21 Uhr, um 20:30 also jetzt.
    assert _satz(MET_NO, wind=13) == "Markise einfahren: jetzt Wind bis 17 km/h."


def test_rechnet_die_einheit_um():
    # 16,9 m/s sind 61 km/h - in km/h gelesen bliebe es unter der Grenze.
    assert _satz(MET_NO, wind_einheit="m/s") == "Markise einfahren: jetzt Wind bis 61 km/h."
    regen = _geaendert(MET_NO, 21, precipitation=0.3)
    assert _satz(regen, regen_einheit="in").startswith("7,6 mm Regen")


def test_nur_im_vorlauf():
    # Der Eintrag von 19 Uhr UTC ist vorbei, der von 0 Uhr liegt hinter drei
    # Stunden Vorlauf. Geändert: Gewitter in beiden.
    daneben = _geaendert(_geaendert(OWM, 19, condition="lightning"), 0, condition="lightning")
    assert _satz(daneben) == ""
    assert _satz(daneben, vorlauf=4) == "Markise einfahren: ab 2 Uhr Gewitter."


def test_mehrere_gruende_in_einem_satz():
    # Geändert: Gewitter mit Sturmböen um 22 Uhr UTC, Hagel um 23 Uhr UTC.
    unwetter = _geaendert(OWM, 22, condition="lightning-rainy", wind_gust_speed=72.4)
    unwetter = _geaendert(unwetter, 23, condition="hail")
    assert _satz(unwetter) == \
        "Markise einfahren: ab 0 Uhr Böen bis 72 km/h, ab 0 Uhr Gewitter, ab 1 Uhr Hagel."


def test_regen_heisst_absenken():
    # Geändert: 4,4 mm um 21 Uhr UTC statt 0,82.
    regen = _geaendert(OWM, 21, precipitation=4.4)
    assert _satz(regen) == ""
    befund = wetter.bewerte(_geaendert(regen, 22, precipitation=1.8), JETZT, vorlauf_h=3,
                            boeen_kmh=40, wind_kmh=25, regen_mm=5,
                            stunde_lokal=lambda t: t.hour)
    assert befund.stufe == "absenken"
    assert befund.satz == ("6,2 mm Regen in den nächsten 3 Stunden: "
                           "Markise auf einer Seite absenken, damit das Wasser abläuft.")
    assert "in der nächsten Stunde" in _satz(_geaendert(MET_NO, 20, precipitation=5.5), vorlauf=1)


def test_einfahren_geht_vor_absenken():
    viel = _geaendert(_geaendert(OWM, 21, precipitation=9.0), 22, condition="pouring")
    assert _satz(viel) == "Markise einfahren: ab 0 Uhr Starkregen."


def test_kaputter_eintrag_stoert_nicht():
    kaputt = [{"condition": "hail"}, {"datetime": "kein Datum", "condition": "hail"}] + OWM
    assert _satz(kaputt) == ""


# --- Halten der Warnung --------------------------------------------------------

class _Zustaende:
    def __init__(self, **zustaende):
        self.z = zustaende

    def get(self, entity_id):
        if entity_id not in self.z:
            return None
        return SimpleNamespace(state=self.z[entity_id])


def _waechter(markise=None, markise_zustand=None):
    hass = SimpleNamespace(states=_Zustaende(**({markise: markise_zustand} if markise else {})))
    meldungen = []
    w = wetter.WetterWaechter(
        hass,
        {const.CONF_WEATHER_ENTITY: "weather.ort", const.CONF_AWNING_ENTITY: markise},
        lambda key: 0.0,
        lambda: meldungen.append(1),
    )
    return w, meldungen


GEFAHR = wetter.Befund("einfahren", "Markise einfahren: jetzt Böen bis 50 km/h.")


def test_warnung_bleibt_eine_stunde_stehen():
    w, meldungen = _waechter()
    w._setzen(GEFAHR, JETZT, halten=True)
    assert w.warnung and len(meldungen) == 1
    # Die nächste Vorhersage trägt die Warnung nicht mehr - sie bleibt.
    w._setzen(wetter.RUHIG, JETZT + timedelta(minutes=30), halten=True)
    assert w.warnung and len(meldungen) == 1
    # Nach einer Stunde ohne Gefahr geht sie.
    w._setzen(wetter.RUHIG, JETZT + timedelta(minutes=61), halten=True)
    assert not w.warnung and len(meldungen) == 2


def test_eingefahrene_markise_beendet_die_warnung_sofort():
    w, _ = _waechter()
    w._setzen(GEFAHR, JETZT, halten=True)
    w._setzen(wetter.RUHIG, JETZT + timedelta(minutes=5), halten=False)
    assert not w.warnung


def test_markise_draussen():
    assert _waechter()[0].markise_draussen is None
    for zustand, draussen in (("on", True), ("open", True), ("opening", True),
                              ("off", False), ("closed", False)):
        assert _waechter("cover.markise", zustand)[0].markise_draussen is draussen


# --- Einrichtung -----------------------------------------------------------------

def test_felder_lassen_sich_leeren():
    for key in (const.CONF_WEATHER_ENTITY, const.CONF_AWNING_ENTITY):
        assert key in config_flow.CLEARABLE_KEYS


def test_texte_in_allen_sprachen():
    ordner = WURZEL / "custom_components" / "camperminder"
    for datei in ("strings.json", "translations/de.json", "translations/en.json"):
        texte = json.loads((ordner / datei).read_text(encoding="utf-8"))
        for teil, schritt in (("config", "user"), ("options", "init")):
            step = texte[teil]["step"][schritt]
            for key in (const.CONF_WEATHER_ENTITY, const.CONF_AWNING_ENTITY):
                assert key in step["data"] and key in step["data_description"], (datei, key)
        assert "awning_warning" in texte["entity"]["binary_sensor"]
        for key in ("awning_gust", "awning_wind", "awning_rain", "awning_lead"):
            assert key in texte["entity"]["number"], (datei, key)


def test_regler_haben_die_vorgaben():
    kern = importlib.import_module(f"{PAKET}.coordinator")
    for key, vorgabe in ((const.CONF_AWNING_GUST, 40.0), (const.CONF_AWNING_WIND, 25.0),
                         (const.CONF_AWNING_RAIN, 5.0), (const.CONF_AWNING_LEAD, 3.0)):
        assert kern.VALUE_DEFAULTS[key] == vorgabe
        assert key in kern.NUMERIC_VALUES


@pytest.mark.parametrize("stufe", wetter.STUFEN)
def test_karte_kennt_jede_stufe(stufe):
    karte = (WURZEL / "custom_components" / "camperminder" / "www" / "camperminder-card.js")
    inhalt = karte.read_text(encoding="utf-8")
    assert "a.awning_level" in inhalt and "a.awning_text" in inhalt
    if stufe != "absenken":  # "absenken" ist der Rest-Fall der Karte
        assert f'"{stufe}"' in inhalt
