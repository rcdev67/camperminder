"""Stellplatz-Gedächtnis: wann gemerkt wird, was, und was beim Wiederkommen steht.

Die Plätze sind öffentliche Orte (Domplatte Köln, Münsterplatz Bonn), keine
echten Stellplätze: Ein Repository, das jeder lesen kann, soll nicht
verraten, wo ein Fahrzeug steht.
"""

from __future__ import annotations

import importlib
from datetime import datetime, timedelta, timezone

from conftest import PAKET

gedaechtnis = importlib.import_module(f"{PAKET}.gedaechtnis")
heimatort = importlib.import_module(f"{PAKET}.heimatort")
Standort = heimatort.Standort
StellplatzGedaechtnis = gedaechtnis.StellplatzGedaechtnis

KOELN = (50.9413, 6.9583)
BONN = (50.7341, 7.0989)
T0 = datetime(2026, 10, 11, 11, 0, tzinfo=timezone.utc)

PLAN_ANKUNFT = [
    {"wheel": "vorne_links", "cm": 2.54, "steps": 1, "residual_cm": 0.0, "direction": "hoch"},
    {"wheel": "hinten_links", "cm": 1.2, "steps": 1, "residual_cm": 0.0, "direction": "hoch"},
]


def bei(minuten: float) -> datetime:
    return T0 + timedelta(minutes=minuten)


def meldung(ort, minuten, genauigkeit=10.0, nord_m=0.0):
    return Standort(ort[0] + nord_m / 111_320, ort[1], genauigkeit, None, bei(minuten))


def ankommen(g, ort, ab, nord_m=0.0):
    """Fahrt endet bei `ab` Minuten am Ort."""
    g.bewegung(True, bei(ab - 5))
    g.ort(meldung(ort, ab, nord_m=nord_m))
    g.bewegung(False, bei(ab))


def neu_mit_fahrt(start=BONN):
    """Ein Gedächtnis, das schon einmal gefahren ist (kein frischer Neustart)."""
    g = StellplatzGedaechtnis()
    g.ort(meldung(start, -60))
    g.bewegung(False, bei(-60))
    g.pruefen(bei(-58), [], "wohnmobil")
    return g


def test_erster_besuch_wird_nach_einer_minute_stillstand_gemerkt():
    g = neu_mit_fahrt()
    ankommen(g, KOELN, 0)
    assert not g.pruefen(bei(0.5), PLAN_ANKUNFT, "wohnmobil")
    assert g.pruefen(bei(1.1), PLAN_ANKUNFT, "wohnmobil")
    assert len(g.plaetze) == 1
    assert g.plaetze[0]["besuche"][0]["plan"][0] == {
        "rad": "vorne_links", "cm": 2.5, "stufen": 1, "richtung": "hoch"
    }
    assert "beim nächsten Mal" in g.satz()


def test_auffahren_auf_keile_ueberschreibt_den_ankunftsplan_nicht():
    g = neu_mit_fahrt()
    ankommen(g, KOELN, 0)
    assert g.pruefen(bei(2), PLAN_ANKUNFT, "wohnmobil")
    # Kurz bewegt zum Auffahren, danach eben.
    g.bewegung(True, bei(5))
    g.bewegung(False, bei(5.5))
    assert not g.pruefen(bei(10), [], "wohnmobil")
    assert g.plaetze[0]["besuche"][0]["plan"] != []
    assert len(g.plaetze[0]["besuche"]) == 1


def test_wiederkommen_nennt_den_letzten_besuch():
    g = neu_mit_fahrt()
    ankommen(g, KOELN, 0)
    g.pruefen(bei(2), PLAN_ANKUNFT, "wohnmobil")

    # Weg nach Bonn und eine Woche später zurück, GPS 25 m daneben.
    ankommen(g, BONN, 60)
    g.pruefen(bei(62), [], "wohnmobil")
    woche = 7 * 24 * 60
    ankommen(g, KOELN, woche, nord_m=25)
    g.pruefen(bei(woche + 2), PLAN_ANKUNFT, "wohnmobil")

    assert g.satz() == (
        "Hier am 11.10.2026: vorne links 2,5 cm (1 Stufe), hinten links 1,2 cm (1 Stufe)."
    )
    assert len(g.plaetze) == 2
    koeln = g._platz_bei(*KOELN)
    assert len(koeln["besuche"]) == 2


def test_nach_neustart_wird_erst_nach_der_naechsten_fahrt_gemessen():
    g = neu_mit_fahrt()
    ankommen(g, KOELN, 0)
    g.pruefen(bei(2), PLAN_ANKUNFT, "wohnmobil")

    # Neustart mitten im Aufenthalt: Das Fahrzeug steht längst eben.
    g2 = StellplatzGedaechtnis(g.daten())
    g2.ort(meldung(KOELN, 100))
    g2.bewegung(False, bei(100))
    assert not g2.pruefen(bei(110), [], "wohnmobil")
    assert len(g2.plaetze[0]["besuche"]) == 1
    # Den früheren Besuch kennt er trotzdem.
    assert g2.satz().startswith("Hier am 11.10.2026")


def test_beim_heranfahren_entsteht_kein_besuch():
    """Wandert das GPS weiter, steht das Fahrzeug nicht - auch ohne Bewegungssensor."""
    g = neu_mit_fahrt()
    g.bewegung(False, bei(0))
    for i in range(10):
        g.ort(meldung(KOELN, i * 0.5, nord_m=-500 + i * 50))
        assert not g.pruefen(bei(i * 0.5), PLAN_ANKUNFT, "wohnmobil")
    assert g.plaetze == []


def test_ungenaue_meldungen_zaehlen_nicht():
    g = neu_mit_fahrt()
    ankommen(g, KOELN, 0)
    g.ort(meldung(BONN, 0.5, genauigkeit=2000))
    assert g.pruefen(bei(2), PLAN_ANKUNFT, "wohnmobil")
    assert abs(g.plaetze[0]["breite"] - KOELN[0]) < 1e-4


def test_ohne_standort_gibt_es_nichts():
    g = StellplatzGedaechtnis()
    assert not g.pruefen(bei(5), PLAN_ANKUNFT, "wohnmobil")
    assert "GPS-Quelle" in g.satz()


def test_wohnwagen_nennt_raeder_und_stuetzrad():
    plan = [
        {"rad": "hinten_rechts", "cm": 3.0, "stufen": 2, "richtung": "hoch"},
        {"rad": "stuetzrad", "cm": 4.0, "stufen": None, "richtung": "runter"},
    ]
    assert gedaechtnis.plan_satz(plan, "wohnwagen") == (
        "rechtes rad 3,0 cm (2 Stufen), stützrad 4,0 cm runter"
    )
    assert gedaechtnis.plan_satz([], "wohnmobil") == "stand eben"


def test_je_platz_nur_die_letzten_besuche():
    g = neu_mit_fahrt()
    for n in range(8):
        t = n * 24 * 60
        ankommen(g, KOELN, t)
        assert g.pruefen(bei(t + 2), PLAN_ANKUNFT, "wohnmobil")
        ankommen(g, BONN, t + 60)
        g.pruefen(bei(t + 62), [], "wohnmobil")
    koeln = g._platz_bei(*KOELN)
    assert len(koeln["besuche"]) == gedaechtnis.BESUCHE_JE_PLATZ
    assert koeln["besuche"][0]["datum"] == "2026-10-18"
