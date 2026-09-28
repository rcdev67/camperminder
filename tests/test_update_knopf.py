"""Die Taste "Firmware aktualisieren" und die Geraeteseite sprechen denselben Satz.

Seit 4.2.3 prueft die Taste erst bei GitHub und spielt nur eine hoehere
Fassung auf; seit 4.2.4 meldet auch die Pruefung im Hintergrund ihren Befund
("Update verfügbar: ...") und die Seite zeigt ihn als Hinweis. Das Ergebnis
steht im Sensor "Update Stand" als deutscher Satz (fuer Home Assistant und
MQTT); die Geraeteseite erkennt ihn am Anfang und
zeigt ihn in ihrer Sprache (updateSatz in webui.js). Aendert jemand einen
Satz auf der einen Seite, ohne die andere, stuende auf der Seite der rohe
deutsche Satz - oder gar nichts, weil sie auf "prüft" wartet.
"""

from __future__ import annotations

import re

import pytest

from conftest import WURZEL

GERAET = (WURZEL / "esphome" / "level" / "camperminder-level.yaml").read_text(encoding="utf-8")
WEBUI = (WURZEL / "esphome" / "level" / "webui.js").read_text(encoding="utf-8")

# Satzanfang in der Firmware -> Schluessel, den die Seite dafuer zeigt.
SAETZE = {
    "neue Fassung ": "update_neu",
    "Update verfügbar: ": "update_verfuegbar",
    "aktuell (": "update_aktuell",
    "kein Internet": "update_kein_internet",
    "prüft": "update_prueft",
    "Prüfung fehlgeschlagen": "update_fehlgeschlagen",
}


def _update_satz() -> str:
    start = WEBUI.index("function updateSatz(")
    return WEBUI[start:WEBUI.index("\n  }\n", start)]


@pytest.mark.parametrize("anfang", sorted(SAETZE))
def test_firmware_schreibt_den_satz(anfang):
    assert 'publish_state("' + anfang in GERAET


@pytest.mark.parametrize("anfang,schluessel", sorted(SAETZE.items()))
def test_seite_erkennt_den_satz(anfang, schluessel):
    satz = _update_satz()
    erstes_wort = anfang.strip().split(" ")[0]
    assert re.search(r"/\^" + re.escape(erstes_wort), satz), anfang
    assert f't("{schluessel}"' in satz
    for sprache in ("de", "en"):
        start = WEBUI.index(f"    {sprache}: {{")
        assert f"      {schluessel}:" in WEBUI[start:WEBUI.index("\n    }", start)], (sprache, schluessel)


def test_taste_spielt_nur_hoehere_fassungen_auf():
    # Die Update-Entitaet haelt jede ANDERE Nummer fuer verfuegbar - ohne den
    # Vergleich stufte die Taste ein Geraet mit unveroeffentlichter Fassung
    # auf die veroeffentlichte zurueck.
    assert "vergleich > 0" in GERAET
    assert "ota.http_request.flash" not in _taste()


def _taste() -> str:
    return GERAET.split("button:", 1)[1].split("\n  - platform: factory_reset", 1)[0]


def test_rueckruf_haengt_nicht_an_der_taste():
    # Meldete sich der Rueckruf erst beim ersten Druck an, fiele der Befund
    # der Hintergrundpruefung nach dem Start ins Leere - und der Hinweis auf
    # der Seite erschiene nie.
    assert "add_on_state_callback" not in _taste()
    assert "add_on_state_callback" in GERAET.split("\ninterval:", 1)[1]


def test_hintergrund_meldet_nur_und_installiert_nicht():
    # Aufgespielt wird nur nach einem Druck. Ein Neustart von allein, mitten
    # in der Nacht oder waehrend der Fahrt, waere ein Fehler.
    rueckruf = GERAET.split("add_on_state_callback", 1)[1]
    knopf = rueckruf.index("if (knopf) {")
    sonst = rueckruf.index("} else {", knopf)
    installieren = rueckruf.index("id(update_installieren) = true;")
    assert knopf < installieren < sonst
    assert rueckruf.index('publish_state("Update verfügbar: "') > sonst
    assert rueckruf.count("id(update_installieren) = true;") == 1


def test_hinweis_steht_auf_jedem_reiter():
    start = WEBUI.index("  function update() {")
    assert "updateHinweis(liveEl);" in WEBUI[start:WEBUI.index("\n  }\n", start)]

