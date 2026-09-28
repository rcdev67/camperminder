"""Die Suche der Geraeteseite im Heimnetz braucht eine Freigabe im Geraet.

Nach dem Eintragen des WLANs fragt die Geraeteseite - geladen von
http://192.168.4.1 - das Geraet unter seiner neuen Adresse ab. Fuer den
Browser ist das eine Anfrage von einer fremden Seite, und ESPHome weist sie
mit 500 ab, solange der Ursprung nicht unter web_server: allowed_origins
steht (is_request_origin_allowed_ in web_server.cpp). Am 28.09.2026 fand die
Suche deshalb nichts, obwohl das Geraet antwortete - curl schickt keinen
Origin-Kopf, jeder Browser schon, und der Pruefstand war damals grosszuegiger
als das Geraet.

Diese Tests halten beides fest: die Freigabe in der Geraetedatei und die
Pruefung im Pruefstand.
"""

from __future__ import annotations

import importlib.util
import re

from conftest import WURZEL

GERAET = (WURZEL / "esphome" / "level" / "camperminder-level.yaml").read_text(encoding="utf-8")
WEBUI = (WURZEL / "esphome" / "level" / "webui.js").read_text(encoding="utf-8")


def _web_server_block() -> str:
    start = GERAET.index("\nweb_server:")
    ende = re.search(r"\n\S", GERAET[start + 1:])
    return GERAET[start: start + 1 + ende.start()] if ende else GERAET[start:]


def test_eigenes_netz_ist_als_ursprung_erlaubt():
    block = _web_server_block()
    assert "allowed_origins:" in block
    assert '"http://192.168.4.1"' in block


def test_kein_freibrief_fuer_jede_seite():
    # "*" oeffnete das Geraet jeder Webseite, die der Kunde im Heimnetz besucht.
    assert not re.search(r'allowed_origins:\s*\n\s+-\s*"?\*"?', _web_server_block())


def test_suche_fragt_das_geraet_ueber_die_rest_schnittstelle():
    # Die Freigabe nuetzt nur, solange die Suche das Geraet so abfragt.
    assert 'pathFor("text_sensor", "wlan_mac")' in WEBUI
    assert "heimFrage(" in WEBUI


def test_pruefstand_prueft_die_herkunft_wie_das_geraet():
    spec = importlib.util.spec_from_file_location("geraetestub", WURZEL / "tools" / "geraetestub.py")
    stub = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stub)
    assert "http://192.168.4.1" in stub.ERLAUBTE_URSPRUENGE
    assert "*" not in stub.ERLAUBTE_URSPRUENGE
