"""Stellplatz: Sonne, Satellit und Starlink im Verhältnis zum Fahrzeug.

Geprüft wird gegen Werte, die nicht aus derselben Rechnung stammen:

- Sonne: sun.sun eines echten Home Assistant (Bibliothek astral) am
  17.10.2026 um 19:54:55 UTC, Standort Amsterdam (der Standard von Home
  Assistant): Azimut 295,42°, Höhe -29,69°.
- Satellit: eine zweite, unabhängige Rechnung über Ortsvektoren im Raum
  (Erdradius, Bahnradius der geostationären Satelliten), statt über die
  geschlossene Formel aus stellplatz.py.
"""

from __future__ import annotations

import importlib
import json
import math
from datetime import datetime, timedelta, timezone

import pytest

from conftest import PAKET, WURZEL

sp = importlib.import_module(f"{PAKET}.stellplatz")

KOELN = (50.9413, 6.9583)
SOMMERZEIT = timezone(timedelta(hours=2))


def test_sonne_wie_home_assistant():
    az, h = sp.sonnenstand(datetime(2026, 10, 17, 19, 54, 55, tzinfo=timezone.utc),
                           52.3731339, 4.8903147)
    assert az == pytest.approx(295.42, abs=0.05)
    assert h == pytest.approx(-29.69, abs=0.05)


def _satellit_im_raum(breite, laenge, sat_laenge):
    """Unabhängige Rechnung: Vektor vom Standort zum Satelliten, im Ortssystem."""
    erde, bahn = 6378.137, 42164.0
    phi, lam, sl = map(math.radians, (breite, laenge, sat_laenge))
    ort = (erde * math.cos(phi) * math.cos(lam), erde * math.cos(phi) * math.sin(lam), erde * math.sin(phi))
    sat = (bahn * math.cos(sl), bahn * math.sin(sl), 0.0)
    d = [s - o for s, o in zip(sat, ort)]
    ost = (-math.sin(lam), math.cos(lam), 0.0)
    nord = (-math.sin(phi) * math.cos(lam), -math.sin(phi) * math.sin(lam), math.cos(phi))
    oben = (math.cos(phi) * math.cos(lam), math.cos(phi) * math.sin(lam), math.sin(phi))
    e, n, u = (sum(a * b for a, b in zip(d, achse)) for achse in (ost, nord, oben))
    return math.degrees(math.atan2(e, n)) % 360, math.degrees(math.atan2(u, math.hypot(e, n)))


@pytest.mark.parametrize(("ort", "breite", "laenge"), [
    ("Köln", 50.9413, 6.9583),
    ("Madrid", 40.4168, -3.7038),
    ("Nordkap", 71.1700, 25.7800),
    ("Lissabon", 38.7223, -9.1393),
])
@pytest.mark.parametrize("satellit", list(sp.SATELLITEN))
def test_satellit_wie_rechnung_im_raum(ort, breite, laenge, satellit):
    sat_laenge = sp.SATELLITEN[satellit][1]
    az, h = sp.satellit_richtung(breite, laenge, sat_laenge)
    az_raum, h_raum = _satellit_im_raum(breite, laenge, sat_laenge)
    assert az == pytest.approx(az_raum, abs=0.3), ort
    assert h == pytest.approx(h_raum, abs=0.3), ort


def test_astra_in_deutschland_suedsuedost_dreissig_grad():
    az, h = sp.satellit_richtung(*KOELN, 19.2)
    assert sp.himmelsrichtung(az) == "Südsüdost"
    assert 29 < h < 32


def _koeln(front, **kw):
    return sp.berechne(datetime(2026, 10, 18, 10, 0, tzinfo=timezone.utc), *KOELN, SOMMERZEIT,
                       front=front, **kw)


def test_front_nach_sueden_markise_rechts_nachmittags():
    # Front nach Süden: rechts ist Westen (Nachmittag), links Osten (Vormittag).
    s = _koeln(180, markise="rechts", kuehlschrank="links")
    assert s.sonnenzeiten["rechts"] == ["14:30–18:00"]
    assert s.sonnenzeiten["links"] == ["08:30–12:00"]
    assert s.sonnenzeiten["hinten"] == []
    assert s.satz_sonne == (
        "Markise (rechts) in der Sonne 14:30–18:00. "
        "Kühlschrank-Lüftung (links) in der Sonne 08:30–12:00 – dann kühlt er schlechter.")


def test_kuehlschrank_im_schatten_ist_gut():
    # Front nach Osten: Links ist Norden, dort steht die Sonne im Oktober nie.
    s = _koeln(90, markise="keine", kuehlschrank="links")
    assert s.sonnenzeiten["links"] == []
    assert s.satz_sonne == "Kühlschrank-Lüftung (links) bleibt heute im Schatten – gut so."
    # Die Markise im Schatten ist kein Lob wert, nur eine Feststellung.
    s = _koeln(90, markise="links")
    assert s.satz_sonne == "Markise (links) bleibt heute im Schatten."


def test_ohne_richtung_kein_raten():
    s = _koeln(None)
    assert "Richtung des Fahrzeugs fehlt" in s.satz_sonne
    assert s.sonnenzeiten == {}
    assert "vom Fahrzeug aus" not in s.satz_satellit
    assert s.satz_starlink == "Starlink braucht freien Himmel, vor allem nach Norden."
    # Die Sonnenbahn gibt es trotzdem - sie hängt nicht am Fahrzeug.
    assert s.sonnenbahn


def test_starlink_norden_vom_fahrzeug_aus():
    assert "Norden liegt genau vorne" in _koeln(0).satz_starlink
    assert "Norden liegt genau hinten" in _koeln(180).satz_starlink
    assert "Norden liegt genau links" in _koeln(90).satz_starlink
    assert "Norden liegt 45° rechts von vorne" in _koeln(315).satz_starlink
    assert "Norden liegt 20° links von hinten" in _koeln(160).satz_starlink
    assert _koeln(160).starlink_relativ == -160
    sued = sp.berechne(datetime(2026, 10, 18, 10, 0, tzinfo=timezone.utc), -33.9, 18.4,
                       timezone.utc, front=0)
    assert "Süden liegt genau hinten" in sued.satz_starlink


def test_satellit_vom_fahrzeug_aus():
    # Astra steht in Köln bei rund 164°.
    s = _koeln(180)
    r = s.satellit_relativ
    assert -18 < r < -14
    assert s.satz_satellit.endswith(f"vom Fahrzeug aus {round(abs(r))}° links von vorne.")
    assert _koeln(0).satz_satellit.endswith(f"vom Fahrzeug aus {round(abs(r))}° rechts von hinten.")
    assert _koeln(164).satz_satellit.endswith("vom Fahrzeug aus genau vorne.")
    assert _koeln(None).satellit_relativ is None


def test_genau_auf_das_grad():
    assert sp.vom_fahrzeug_genau(1, 0) == "genau vorne"
    assert sp.vom_fahrzeug_genau(359, 0) == "genau vorne"
    assert sp.vom_fahrzeug_genau(91, 0) == "genau rechts"
    assert sp.vom_fahrzeug_genau(268, 0) == "genau links"
    assert sp.vom_fahrzeug_genau(30, 0) == "30° rechts von vorne"
    assert sp.vom_fahrzeug_genau(120, 0) == "60° rechts von hinten"
    assert sp.vom_fahrzeug_genau(200, 0) == "20° links von hinten"
    assert sp.vom_fahrzeug_genau(10, 350) == "20° rechts von vorne"


def test_vom_fahrzeug_acht_stufen():
    erwartet = ["vorne", "rechts vorne", "rechts", "rechts hinten",
                "hinten", "links hinten", "links", "links vorne"]
    assert [sp.vom_fahrzeug(45 * i, 0) for i in range(8)] == erwartet
    assert sp.vom_fahrzeug(10, 350) == "vorne"


def test_sonnenbahn_stuendlich_ueber_dem_horizont():
    bahn = _koeln(180).sonnenbahn
    assert [b["zeit"] for b in bahn] == [f"{h:02d}" for h in range(9, 19)]
    assert all(b["hoehe"] > 0 for b in bahn)
    # Mittags am höchsten, im Süden.
    mittag = max(bahn, key=lambda b: b["hoehe"])
    assert 170 < mittag["azimut"] < 200


def test_texte_und_karte():
    ordner = WURZEL / "custom_components" / "camperminder"
    for datei in ("strings.json", "translations/de.json", "translations/en.json"):
        e = json.loads((ordner / datei).read_text(encoding="utf-8"))["entity"]
        for k in ("sun", "dish", "starlink"):
            assert k in e["sensor"], (datei, k)
        assert "vehicle_heading" in e["number"]
        assert set(e["select"]["satellite"]["state"]) == set(sp.SATELLITEN)
        for k in ("awning_side", "fridge_vent_side"):
            assert set(e["select"][k]["state"]) == set(sp.SEITEN), (datei, k)
    karte = (ordner / "www" / "camperminder-card.js").read_text(encoding="utf-8")
    for rolle in ('"sun"', '"dish"', '"starlink"', '"vehicle_heading"'):
        assert f"this._findRole(hass, {rolle})" in karte


def test_rollen_der_karte_eindeutig():
    # Die Karte findet Entitäten über ihre Rolle (= Schlüssel). Hießen zwei
    # gleich, fände sie die falsche - so stand am 17.10.2026 statt des
    # Satellitensatzes "astra_19_2" in der Karte.
    import re

    ordner = WURZEL / "custom_components" / "camperminder"
    texte = json.loads((ordner / "strings.json").read_text(encoding="utf-8"))["entity"]
    gesehen: dict[str, str] = {}
    for plattform, eintraege in texte.items():
        for schluessel in eintraege:
            assert schluessel not in gesehen, (schluessel, gesehen.get(schluessel), plattform)
            gesehen[schluessel] = plattform
    karte = (ordner / "www" / "camperminder-card.js").read_text(encoding="utf-8")
    for rolle in re.findall(r'_findRole\(hass, "([a-z_]+)"\)', karte):
        assert rolle in gesehen or rolle in ("phase",), rolle
