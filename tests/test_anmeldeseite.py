"""Die Anmeldeseite antwortet der Pruefanfrage des Handys wie ESPHome.

Bis 4.2.3 kam eine Weiterleitung (302); das Samsung des Nutzers bekam sie
und oeffnete nichts. ESPHomes captive_portal, das auf Android aufgeht,
antwortet mit 200 und einer Seite - dem folgt anmeldeseite.h seit 4.2.4.
Die Seite ist eine Zwischenseite nach 192.168.4.1: Unter dem fremden Namen
wiese das Geraet die Befehle der Wasserwaage ab (allowed_origins).
"""

from __future__ import annotations

from conftest import WURZEL

QUELLE = (WURZEL / "esphome" / "level" / "anmeldeseite.h").read_text(encoding="utf-8")


def _antwort() -> str:
    start = QUELLE.index("void handleRequest(")
    return QUELLE[start:QUELLE.index("\n  }\n", start)]


def test_antwort_ist_eine_seite_keine_weiterleitung():
    antwort = _antwort()
    assert "redirect(" not in antwort
    assert 'beginResponse(200, "text/html"' in antwort


def test_zwischenseite_schickt_zur_eigenen_adresse():
    antwort = _antwort()
    assert "eigene_adresse(" in antwort
    assert 'http-equiv=\\"refresh\\"' in antwort
    assert "location.replace(" in antwort


def test_antwort_wird_nicht_zwischengespeichert():
    # Sie gilt nur, solange das eigene Netz offen ist.
    assert '"Cache-Control", "no-store"' in _antwort()
