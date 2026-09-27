"""Die Geräteseite spricht Deutsch und Englisch - auch unter Technik.

Bis 4.0.5 zeigte die Technik-Tabelle die Namen der Entitäten, wie das Gerät
sie führt, und die deutschen Sätze der Firmware - auf Englisch stand dort
"Kühlschrank Warnung: OFF". Die Namen bleiben (Home Assistant, MQTT und die
Suche der Seite hängen daran); übersetzt wird die Anzeige über Schlüssel
"tech_<name>". Dieser Test sorgt dafür, dass eine neue Entität nicht wieder
unübersetzt auftaucht.
"""

from __future__ import annotations

import json
import re

import pytest

from conftest import WURZEL

WEBUI = (WURZEL / "esphome" / "level" / "webui.js").read_text(encoding="utf-8")
HARDWARE = (WURZEL / "esphome" / "level" / "hardware.yaml").read_text(encoding="utf-8")
STUB = json.loads((WURZEL / "tools" / "stub_entitaeten.json").read_text(encoding="utf-8"))
TECH_BEREICHE = ("sensor", "binary_sensor", "text_sensor")


def _schluessel(sprache: str) -> set[str]:
    start = WEBUI.index(f"    {sprache}: {{")
    ende = WEBUI.index("\n    }", start)
    return set(re.findall(r"^\s{6}([a-z0-9_]+):", WEBUI[start:ende], re.MULTILINE))


def tech_schluessel(name: str) -> str:
    """Wie techSchluessel() in webui.js."""
    name = name.lower()
    for alt, neu in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        name = name.replace(alt, neu)
    return "tech_" + re.sub(r"[^a-z0-9]+", "_", name).strip("_")


def _namen_aus_hardware() -> set[str]:
    """Alle Namen in den drei Bereichen - auch die aus wifi_info, die der
    Prüfstand nicht kennt."""
    namen, bereich = set(), None
    for zeile in HARDWARE.splitlines():
        if kopf := re.match(r"^([a-z_]+):", zeile):
            bereich = kopf.group(1)
        elif bereich in TECH_BEREICHE and (name := re.match(r'^\s+name:\s*"(.+)"', zeile)):
            namen.add(name.group(1))
    return namen


def _alle_namen() -> list[str]:
    aus_stub = {e["name"] for e in STUB["entitaeten"] if e["bereich"] in TECH_BEREICHE}
    return sorted(aus_stub | _namen_aus_hardware())


def test_findet_die_namen():
    namen = _alle_namen()
    for erwartet in ("Kühlschrank Warnung", "IP Adresse", "accel_x", "Werkskalibrierung"):
        assert erwartet in namen


@pytest.mark.parametrize("sprache", ["de", "en"])
@pytest.mark.parametrize("name", _alle_namen())
def test_jede_technikzeile_ist_uebersetzt(name, sprache):
    assert tech_schluessel(name) in _schluessel(sprache), name


def test_schluessel_regel_wie_auf_der_seite():
    assert '.replace(/ä/g, "ae").replace(/ö/g, "oe")' in WEBUI
    assert '.replace(/ü/g, "ue").replace(/ß/g, "ss"));' in WEBUI
    assert tech_schluessel("Kühlschrank Warnung") == "tech_kuehlschrank_warnung"
    assert tech_schluessel("Lageänderung") == "tech_lageaenderung"


def test_werte_uebersetzt():
    for schluessel in ("tech_ja", "tech_nein", "tech_netz_offen", "tech_netz_mit_passwort",
                       "tech_anweisung_eben", "tech_danach_stuetzrad", "tech_kein_messwert"):
        for sprache in ("de", "en"):
            assert schluessel in _schluessel(sprache), (schluessel, sprache)
    # Die deutschen Sätze der Firmware werden aus den Statuswerten neu gebildet.
    for satz in ("anweisungSatz()", "wacheSatz(werte.w)", "kuehlSatz(werte.k)",
                 "kalibrierSatz(werte.c)", "werkSatz(werte.f)", "bewegungSatz(werte.b)",
                 "mqttSatz()"):
        assert satz in WEBUI, satz
    # Die Statuswerte selbst sind Rohstoff und gehören nicht in die Tabelle.
    assert 'techSchluessel(name) === "tech_statuswerte"' in WEBUI


def test_dateiauswahl_mit_eigenem_knopf():
    # Das Dateifeld des Browsers beschriftet sich in der Sprache des Browsers.
    assert '<input type="file" accept=".bin" style="display:none">' in WEBUI
    assert 't("datei_waehlen")' in WEBUI
    for sprache in ("de", "en"):
        assert {"datei_waehlen", "keine_datei"} <= _schluessel(sprache)


def test_fehlermeldung_nennt_die_beschriftung():
    assert 't("kennt_wert_nicht", { was: label || needle })' in WEBUI
    assert "setNumber(key, v, label)" in WEBUI
    assert WEBUI.count('encodeURIComponent(option), t("label_') == 5


def test_sprache_des_dokuments():
    build = WEBUI[WEBUI.index("  function build() {"):]
    assert "document.documentElement.lang = sprache;" in build[:build.index("\n  }\n")]
