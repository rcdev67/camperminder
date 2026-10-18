"""Richtung aus der Fahrt: Fahrtrichtung des GPS plus Drehung aus Level."""

from __future__ import annotations

import importlib
from datetime import datetime, timedelta, timezone

from conftest import PAKET, WURZEL

au = importlib.import_module(f"{PAKET}.ausrichtung")
T0 = datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc)


def bei(sekunden: float) -> datetime:
    return T0 + timedelta(seconds=sekunden)


def fahrt(r, kurs, drehung_dabei=0.0, bis=0.0, level=True):
    """Flotte Fahrt mit Kurs `kurs`, Level summiert dabei `drehung_dabei`."""
    r.bewegung(True, bei(bis - 120))
    r.drehung(drehung_dabei)
    r.gps(kurs, 15.0, 5.0, bei(bis - 60), level)


def test_vorwaerts_eingeparkt_mit_kurve():
    r = au.RichtungAusFahrt()
    fahrt(r, kurs=90, drehung_dabei=1000.0)
    # Danach rechts abgebogen (+90 im Uhrzeigersinn) und angehalten.
    r.drehung(1090.0)
    r.bewegung(False, bei(0))
    assert r.pruefen(bei(30)) is None            # noch keine Minute
    ergebnis = r.pruefen(bei(61))
    assert ergebnis == au.Richtung(180.0, au.QUELLE_FAHRT)
    # Nur einmal je Halt.
    assert r.pruefen(bei(120)) is None


def test_rueckwaerts_eingeparkt():
    """Wenden zum Rückwärtseinparken ist eine halbe Drehung - die steckt in der Summe."""
    r = au.RichtungAusFahrt()
    fahrt(r, kurs=350, drehung_dabei=0.0)
    r.drehung(-175.0)
    r.bewegung(False, bei(0))
    assert r.pruefen(bei(70)).grad == 175.0


def test_ueber_null_hinweg():
    r = au.RichtungAusFahrt()
    fahrt(r, kurs=10, drehung_dabei=50.0)
    r.drehung(20.0)
    r.bewegung(False, bei(0))
    assert r.pruefen(bei(70)).grad == 340.0


def test_ohne_drehung_nur_ganz_frisch():
    r = au.RichtungAusFahrt()
    r.bewegung(True, bei(-100))
    r.gps(200, 10.0, 5.0, bei(-20), True)
    r.bewegung(False, bei(0))
    assert r.pruefen(bei(70)) == au.Richtung(200.0, au.QUELLE_GPS)

    r = au.RichtungAusFahrt()
    r.bewegung(True, bei(-300))
    r.gps(200, 10.0, 5.0, bei(-200), True)
    r.bewegung(False, bei(0))
    assert r.pruefen(bei(70)) is None


def test_neustart_des_geraets_trennt_die_summe():
    r = au.RichtungAusFahrt()
    fahrt(r, kurs=90, drehung_dabei=500.0)
    r.drehung(None)        # Gerät startet neu
    r.drehung(3.0)         # Summe beginnt bei 0
    r.bewegung(False, bei(0))
    # Die Fahrtrichtung ist eine Minute alt - ohne gültige Drehung zu alt.
    assert r.pruefen(bei(70)) is None


def test_zu_alte_fahrtrichtung():
    r = au.RichtungAusFahrt()
    r.bewegung(True, bei(-1000))
    r.drehung(0.0)
    r.gps(90, 15.0, 5.0, bei(-900), True)
    r.drehung(30.0)
    r.bewegung(False, bei(0))
    assert r.pruefen(bei(70)) is None


def test_langsam_ungenau_oder_fremdes_auto_zaehlt_nicht():
    r = au.RichtungAusFahrt()
    r.bewegung(True, bei(-100))
    r.drehung(0.0)
    r.gps(90, 2.0, 5.0, bei(-50), True)       # zu langsam
    r.gps(90, 15.0, 200.0, bei(-50), True)    # zu ungenau
    r.gps(90, 15.0, 5.0, bei(-50), False)     # Level steht: Handy fährt woanders
    r.gps(-1, 15.0, 5.0, bei(-50), True)      # iOS: ungültiger Kurs
    r.bewegung(False, bei(0))
    assert r.pruefen(bei(70)) is None


def test_ohne_bewegungssensor():
    r = au.RichtungAusFahrt()
    r.bewegung(True, bei(-100))
    r.drehung(0.0)
    r.gps(45, 15.0, 5.0, bei(-50), None)
    r.drehung(10.0)
    r.bewegung(False, bei(0))
    assert r.pruefen(bei(70)).grad == 55.0


def test_namen_wie_in_der_firmware():
    hardware = (WURZEL / "esphome" / "level" / "hardware.yaml").read_text(encoding="utf-8")
    assert f'name: "{au.DREHUNG}"' in hardware


def test_karte_kennt_die_quellen():
    karte = (WURZEL / "custom_components" / "camperminder" / "www" / "camperminder-card.js")
    text = karte.read_text(encoding="utf-8")
    for quelle in (au.QUELLE_FAHRT, au.QUELLE_GPS):
        assert f'quelle === "{quelle}"' in text
