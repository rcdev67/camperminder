"""Die Blueprints: Aufbau, Anschluss an die Firmware, Meldetexte.

Eine echte Home-Assistant-Instanz ersetzt das nicht - aber es fängt die
Fehler, die beim Ändern entstehen: ein Eingang, der nirgends benutzt wird,
ein Sensorname, den die Firmware nicht mehr führt, eine Pause, die kürzer ist
als der Takt, in dem das Gerät seinen Satz neu schreibt.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jinja2
import pytest
import yaml

from conftest import WURZEL

ORDNER = WURZEL / "blueprints" / "automation" / "camperminder"
HARDWARE = (WURZEL / "esphome" / "level" / "hardware.yaml").read_text(encoding="utf-8")
README = (WURZEL / "blueprints" / "README.md").read_text(encoding="utf-8")
DATEIEN = sorted(p.name for p in ORDNER.glob("*.yaml"))
# Die drei, die an einem Melder des Geräts hängen. Der Wetterwächter für die
# Markise braucht das Gerät nicht und hat seine eigenen Prüfungen.
GERAETE = ["frostwarnung.yaml", "kuehlschrank_warnung.yaml", "waechter_alarm.yaml"]


class Eingang(str):
    """Platzhalter für !input - merkt sich, welcher Eingang gemeint ist."""


class Lader(yaml.SafeLoader):
    pass


Lader.add_constructor("!input", lambda lader, knoten: Eingang(lader.construct_scalar(knoten)))


def laden(name: str) -> dict:
    return yaml.load((ORDNER / name).read_text(encoding="utf-8"), Loader=Lader)


def eingaenge_im_rumpf(knoten) -> set[str]:
    if isinstance(knoten, Eingang):
        return {str(knoten)}
    if isinstance(knoten, dict):
        return set().union(*(eingaenge_im_rumpf(v) for v in knoten.values()), set())
    if isinstance(knoten, list):
        return set().union(*(eingaenge_im_rumpf(v) for v in knoten), set())
    return set()


def schritte(knoten, art: str) -> list:
    """Alle Schritte einer Art, auch verschachtelte (repeat, choose)."""
    gefunden = []
    if isinstance(knoten, dict):
        if art in knoten:
            gefunden.append(knoten)
        for wert in knoten.values():
            gefunden += schritte(wert, art)
    elif isinstance(knoten, list):
        for wert in knoten:
            gefunden += schritte(wert, art)
    return gefunden


def test_vier_blueprints():
    assert DATEIEN == sorted(GERAETE + ["markise_wetter.yaml"])


@pytest.mark.parametrize("name", GERAETE)
def test_aufbau(name):
    b = laden(name)
    kopf = b["blueprint"]
    assert kopf["domain"] == "automation"
    assert kopf["source_url"] == (
        "https://github.com/rcdev67/camperminder/blob/main/blueprints/automation/camperminder/" + name)
    rumpf = {k: v for k, v in b.items() if k != "blueprint"}
    # Jeder Eingang wird benutzt, und nichts Unbekanntes wird verlangt.
    assert eingaenge_im_rumpf(rumpf) == set(kopf["input"])
    # Die Benachrichtigung ist frei wählbar und läuft über choose/default.
    assert kopf["input"]["benachrichtigung"]["selector"] == {"action": {}}
    assert schritte(b["action"], "choose")[0]["default"] == "benachrichtigung"
    # Ausgelöst wird an einem Melder des Geräts, beim Wechsel auf "an".
    (ausloeser,) = b["trigger"]
    assert ausloeser["platform"] == "state" and ausloeser["to"] == "on"
    melder = kopf["input"][str(ausloeser["entity_id"])]
    assert melder["selector"]["entity"]["filter"] == [{"domain": "binary_sensor"}]


@pytest.mark.parametrize("name", DATEIEN)
def test_nur_bereiche_die_es_in_home_assistant_gibt(name):
    # Ein ESPHome-Textsensor heißt in Home Assistant "sensor" - "text_sensor"
    # gibt es dort nicht, der Filter fände nie etwas.
    assert "text_sensor" not in (ORDNER / name).read_text(encoding="utf-8")


@pytest.mark.parametrize("name", DATEIEN)
def test_freiwillige_felder_leer_vorbelegt(name):
    for eingang in laden(name)["blueprint"]["input"].values():
        if "entity" in eingang["selector"] and "default" in eingang:
            assert eingang["default"] == ""


def _firmware_namen(bereich: str) -> set[str]:
    namen, aktuell = set(), None
    for zeile in HARDWARE.splitlines():
        if kopf := re.match(r"^([a-z_]+):", zeile):
            aktuell = kopf.group(1)
        elif aktuell == bereich and (name := re.match(r'^\s+name:\s*"(.+)"', zeile)):
            namen.add(name.group(1))
    return namen


@pytest.mark.parametrize(("name", "melder", "text"), [
    ("kuehlschrank_warnung.yaml", "Kühlschrank Warnung", "Kühlschrank"),
    ("waechter_alarm.yaml", "Wächter Alarm", "Wächter"),
    ("frostwarnung.yaml", "Frostgefahr", None),
])
def test_die_genannten_sensoren_gibt_es(name, melder, text):
    inhalt = (ORDNER / name).read_text(encoding="utf-8")
    assert melder in _firmware_namen("binary_sensor")
    assert f"„{melder}“" in inhalt
    if text:
        assert text in _firmware_namen("text_sensor")
        assert f"Der Sensor „{text}“ des Geräts" in inhalt
    else:
        assert "Innentemperatur" in _firmware_namen("sensor")


def _takt(name: str) -> int:
    """Takt des Textsensors - "Wächter" gibt es auch als Schalter."""
    textsensoren = HARDWARE[re.search(r"^text_sensor:", HARDWARE, re.MULTILINE).start():]
    block = textsensoren[textsensoren.index(f'name: "{name}"\n'):]
    block = block[:block.index("- platform:")]
    return int(re.search(r"update_interval:\s*(\d+)s", block).group(1))


@pytest.mark.parametrize(("name", "text"), [
    ("kuehlschrank_warnung.yaml", "Kühlschrank"),
    ("waechter_alarm.yaml", "Wächter"),
])
def test_pause_laenger_als_der_takt_des_satzes(name, text):
    b = laden(name)
    pause = b["action"][0]["delay"]["seconds"]
    assert pause > _takt(text)
    # Erst danach wird der Satz gelesen.
    assert "meldung" in b["action"][1 if "variables" in b["action"][1] else 2]["variables"]


@pytest.mark.parametrize("name", ["kuehlschrank_warnung.yaml", "frostwarnung.yaml"])
def test_kein_doppel_nach_neustart(name):
    (bedingung,) = laden(name)["condition"]
    vorlage = bedingung["value_template"]
    jetzt = datetime(2026, 9, 27, 22, 0, tzinfo=timezone.utc)

    def pruefe(von, zuletzt):
        umgebung = jinja2.Environment()
        umgebung.globals.update(now=lambda: jetzt, timedelta=timedelta)
        return umgebung.from_string(vorlage).render(
            trigger=SimpleNamespace(from_state=None if von is None else SimpleNamespace(state=von)),
            this=SimpleNamespace(attributes=SimpleNamespace(last_triggered=zuletzt)),
        ).strip() == "True"

    vor_einer_stunde = jetzt - timedelta(hours=1)
    assert pruefe("off", vor_einer_stunde)                    # echter Wechsel: immer
    assert not pruefe("unavailable", vor_einer_stunde)        # Neustart: schon gemeldet
    assert pruefe("unavailable", jetzt - timedelta(hours=13))  # lange her: wieder
    assert pruefe("unavailable", None)                        # nie gemeldet
    assert pruefe(None, vor_einer_stunde)


def test_waechter_wiederholt_bis_zum_quittieren():
    b = laden("waechter_alarm.yaml")
    assert b["mode"] == "restart"
    (schleife,) = schritte(b["action"], "repeat")
    warten = schritte(schleife, "wait_for_trigger")[0]
    assert warten["wait_for_trigger"][0]["to"] == "off"
    assert warten["continue_on_timeout"] is True
    # Der Satz wird bei jeder Wiederholung neu gelesen.
    assert any("meldung" in s["variables"] for s in schritte(schleife, "variables"))


def _meldung(name: str) -> str:
    b = laden(name)
    for quelle in [b.get("variables", {})] + [s["variables"] for s in schritte(b["action"], "variables")]:
        if "meldung" in quelle:
            return quelle["meldung"]
    raise AssertionError("keine meldung")


def _rendern(vorlage: str, **werte) -> str:
    zustaende = werte.pop("zustaende", {})
    umgebung = jinja2.Environment()
    umgebung.globals["states"] = lambda e: zustaende.get(e, "unknown")

    def ist_zahl(wert):
        try:
            float(wert)
            return True
        except (TypeError, ValueError):
            return False

    umgebung.filters["is_number"] = ist_zahl
    return " ".join(umgebung.from_string(vorlage).render(**werte).split())


def test_frost_meldung_mit_komma():
    vorlage = _meldung("frostwarnung.yaml")
    assert _rendern(vorlage, temperatur_entitaet="sensor.t", zustaende={"sensor.t": "2.34"}) \
        == "Frostgefahr im Fahrzeug: 2,3 °C."
    assert "unter dem Grenzwert" in _rendern(vorlage, temperatur_entitaet="")
    assert "unter dem Grenzwert" in _rendern(
        vorlage, temperatur_entitaet="sensor.t", zustaende={"sensor.t": "unavailable"})


@pytest.mark.parametrize("name", ["kuehlschrank_warnung.yaml", "waechter_alarm.yaml"])
def test_meldung_vom_geraet_oder_allgemein(name):
    vorlage = _meldung(name)
    assert _rendern(vorlage, text_entitaet="sensor.x", zustaende={"sensor.x": "Satz vom Gerät"}) \
        == "Satz vom Gerät"
    for ohne in ({"text_entitaet": ""}, {"text_entitaet": "sensor.x"}):
        text = _rendern(vorlage, **ohne)
        assert text and "Satz" not in text
        assert "Waechter" not in text and "ausgeloest" not in text  # Umlaute, nicht ae/oe


def test_readme_verweist_auf_alle():
    for name in DATEIEN:
        assert f"camperminder%2F{name})" in README
        assert f"automation/camperminder/{name})" in README
    assert "Fernalarm" in README and "noch nicht gebaut" not in README


def test_kuehlschranksatz_mit_komma():
    # Der Satz steht auf der Karte neben Gradzahlen mit Komma.
    assert '"%s° schief seit %s%s", grad, wie_lange, folge' in HARDWARE


# --- Wetterwächter Markise ---------------------------------------------------
#
# Die Einträge unten sind wörtlich aus weather.get_forecasts (type: hourly)
# eines echten Home Assistant vom 17.10.2026 übernommen: met.no ohne Böen,
# OpenWeatherMap mit. Die Vorlage wird an der Schreibweise geprüft, in der
# Home Assistant die Vorhersage tatsächlich liefert, nicht an einer
# ausgedachten. Für die Fälle mit Unwetter sind einzelne Werte geändert;
# welche, steht jeweils dabei.

MARKISE = "markise_wetter.yaml"
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


def _markise_meldung(eintraege, *, entitaet="weather.ort", einheiten=None,
                     vorlauf=3, boeen=40, wind=25, regen=5) -> str:
    attribute = {"wind_speed_unit": "km/h", "precipitation_unit": "mm", **(einheiten or {})}
    umgebung = jinja2.Environment()
    umgebung.globals.update(
        now=lambda: JETZT,
        timedelta=timedelta,
        as_datetime=datetime.fromisoformat,
        as_local=lambda t: t.astimezone(SOMMERZEIT),
        state_attr=lambda e, a: attribute.get(a) if e == "weather.ort" else None,
    )
    return " ".join(umgebung.from_string(_meldung(MARKISE)).render(
        vorhersage={entitaet: {"forecast": eintraege}},
        wetter_entitaet="weather.ort",
        vorlauf=vorlauf, grenze_boeen=boeen, grenze_wind=wind, grenze_regen=regen,
    ).split())


def test_markise_aufbau():
    b = laden(MARKISE)
    kopf = b["blueprint"]
    assert kopf["domain"] == "automation"
    assert kopf["source_url"].endswith("/blueprints/automation/camperminder/" + MARKISE)
    rumpf = {k: v for k, v in b.items() if k != "blueprint"}
    assert eingaenge_im_rumpf(rumpf) == set(kopf["input"])
    assert kopf["input"]["benachrichtigung"]["selector"] == {"action": {}}
    assert schritte(b["action"], "choose")[0]["default"] == "benachrichtigung"
    # Kein Filter auf supported_features: Home Assistant 2026.10 schreibt ihn
    # beim Speichern als Zahl zurück und lehnt ihn beim Laden dann ab.
    (filter_,) = kopf["input"]["wetter"]["selector"]["entity"]["filter"]
    assert filter_ == {"domain": "weather"}
    (abfrage,) = schritte(b["action"], "response_variable")
    assert abfrage["action"] == "weather.get_forecasts"
    assert abfrage["data"] == {"type": "hourly"}
    # Der Markisen-Melder ist freiwillig. Ein Zustandsauslöser mit leerer
    # entity_id machte die Automatisierung ungültig.
    assert kopf["input"]["markise"]["default"] == ""
    assert all(a["platform"] != "state" for a in b["trigger"])


def test_markise_ruhezeit_statt_gedaechtnis():
    b = laden(MARKISE)
    # Was während der Ruhezeit auslöst, verfällt still.
    assert b["mode"] == "single" and b["max_exceeded"] == "silent"
    warten = b["action"][-1]
    assert warten["timeout"] == {"hours": "ruhezeit"}
    assert warten["continue_on_timeout"] is True
    # Die Benachrichtigung kommt vor der Ruhezeit, nicht danach.
    assert "choose" in b["action"][-2]


def test_markise_ruhiges_wetter_meldet_nichts():
    assert _markise_meldung(MET_NO) == ""
    assert _markise_meldung(OWM) == ""


def test_markise_boeen_aus_openweathermap():
    # Echte Werte: Böen 26 km/h um 21 Uhr UTC (23 Uhr Berlin), höchstens 31.
    assert _markise_meldung(OWM, boeen=25) == "Markise einfahren: ab 23 Uhr Böen bis 31 km/h."


def test_markise_ohne_boeen_zaehlt_der_mittlere_wind():
    # met.no liefert keine Böen. Gemeldet wird dann der mittlere Wind, und
    # nicht "Böen bis 0".
    assert _markise_meldung(MET_NO, wind=15) == "Markise einfahren: ab 23 Uhr Wind bis 17 km/h."


def test_markise_laufende_stunde_heisst_jetzt():
    # Der Eintrag von 20 Uhr UTC gilt bis 21 Uhr, um 20:30 also jetzt.
    assert _markise_meldung(MET_NO, wind=13) == "Markise einfahren: jetzt Wind bis 17 km/h."


def test_markise_rechnet_die_einheit_um():
    # 16,9 m/s sind 61 km/h - in km/h gelesen bliebe es unter der Grenze.
    assert _markise_meldung(MET_NO, einheiten={"wind_speed_unit": "m/s"}) \
        == "Markise einfahren: jetzt Wind bis 61 km/h."
    regen = _geaendert(MET_NO, 21, precipitation=0.3)
    assert _markise_meldung(regen, einheiten={"precipitation_unit": "in"}).startswith("7,6 mm Regen")


def test_markise_nur_im_vorlauf():
    # Der Eintrag von 19 Uhr UTC ist vorbei, der von 0 Uhr liegt hinter drei
    # Stunden Vorlauf. Geändert: Gewitter in beiden.
    daneben = _geaendert(_geaendert(OWM, 19, condition="lightning"), 0, condition="lightning")
    assert _markise_meldung(daneben) == ""
    assert _markise_meldung(daneben, vorlauf=4) == "Markise einfahren: ab 2 Uhr Gewitter."


def test_markise_mehrere_gruende_in_einem_satz():
    # Geändert: Gewitter mit Sturmböen um 22 Uhr UTC, Hagel um 23 Uhr UTC.
    unwetter = _geaendert(OWM, 22, condition="lightning-rainy", wind_gust_speed=72.4)
    unwetter = _geaendert(unwetter, 23, condition="hail")
    assert _markise_meldung(unwetter) \
        == "Markise einfahren: ab 0 Uhr Böen bis 72 km/h, ab 0 Uhr Gewitter, ab 1 Uhr Hagel."


def test_markise_regen_heisst_absenken():
    # Geändert: 4,4 mm um 21 Uhr UTC statt 0,82.
    regen = _geaendert(OWM, 21, precipitation=4.4)
    assert _markise_meldung(regen) == ""
    assert _markise_meldung(_geaendert(regen, 22, precipitation=1.8)) == (
        "6,2 mm Regen in den nächsten 3 Stunden: "
        "Markise auf einer Seite absenken, damit das Wasser abläuft.")
    assert "in der nächsten Stunde" in _markise_meldung(
        _geaendert(MET_NO, 20, precipitation=5.5), vorlauf=1)


def test_markise_einfahren_geht_vor_absenken():
    viel = _geaendert(_geaendert(OWM, 21, precipitation=9.0), 22, condition="pouring")
    assert _markise_meldung(viel) == "Markise einfahren: ab 0 Uhr Starkregen."


def test_markise_andere_wetter_entitaet_in_der_antwort():
    assert _markise_meldung(OWM, entitaet="weather.anderswo", boeen=25) == ""
