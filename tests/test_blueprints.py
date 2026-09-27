"""Die drei Blueprints: Aufbau, Anschluss an die Firmware, Meldetexte.

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


def test_drei_blueprints():
    assert DATEIEN == ["frostwarnung.yaml", "kuehlschrank_warnung.yaml", "waechter_alarm.yaml"]


@pytest.mark.parametrize("name", DATEIEN)
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
