"""Rechenkern: Hub, Abweichung und die Werte, die das Gerät führt."""

from __future__ import annotations

from conftest import (
    WOHNMOBIL,
    WOHNWAGEN,
    const,
    coordinator,
    eintrag,
    rechenkern,
    registrierung,
)


def test_im_stand_plan_leer_aber_abweichung_sichtbar():
    # Beide Achsen in der Toleranz: nichts zu tun - die Eckfelder zeigen
    # trotzdem, wie weit jede Ecke noch von waagerecht entfernt ist.
    kern = rechenkern(-0.39, -0.50)
    assert kern.wheel_plan == []
    abweichung = kern.wheel_heights_cm
    assert abweichung == {"vorne_links": 2.9, "vorne_rechts": 4.4,
                          "hinten_links": 0.0, "hinten_rechts": 1.5}


def test_hoechstes_rad_ist_bezug():
    assert min(rechenkern(1.2, -0.8).wheel_heights_cm.values()) == 0.0


def test_weit_schief_abweichung_gleich_hub():
    kern = rechenkern(3.0, 2.0)
    assert kern.wheel_heights_cm == kern.wheel_lifts_cm


def test_achse_in_toleranz_zaehlt_nicht_zum_hub():
    # Quer in der Toleranz: der Hub rechnet nur längs, die Abweichung beides.
    kern = rechenkern(2.0, 0.4)
    hub = kern.wheel_lifts_cm
    assert hub["hinten_links"] == hub["hinten_rechts"]
    assert kern.wheel_heights_cm["hinten_links"] != kern.wheel_heights_cm["hinten_rechts"]


def test_wohnwagen_drei_punkte_stuetzrad_vorzeichenbehaftet():
    abweichung = rechenkern(-0.39, -0.50, fahrzeug=WOHNWAGEN).wheel_heights_cm
    assert set(abweichung) == {"hinten_links", "hinten_rechts", "stuetzrad"}
    assert abweichung["stuetzrad"] > 0  # Front zu tief: Stützrad hoch


def test_wohnwagen_front_hoch_stuetzrad_runter():
    kern = rechenkern(1.0, 0.0, fahrzeug=WOHNWAGEN)
    assert kern.wheel_heights_cm["stuetzrad"] < 0
    assert kern.wheel_plan[-1]["direction"] == const.DIRECTION_DOWN


def test_ohne_messwerte_keine_abweichung():
    assert rechenkern(None, 0.0).wheel_heights_cm is None


def test_unplausibel_keine_abweichung():
    assert rechenkern(60.0, 0.0).wheel_heights_cm is None


def test_voreinstellung_fahrzeugart():
    assert rechenkern(0.0, 0.0).vehicle_type == WOHNMOBIL


def test_geraetewerte_nur_vom_eigenen_geraet(mit_registrierung):
    """Bei zwei Fahrzeugen darf der Radstand des einen nicht mit der Neigung
    des anderen zusammentreffen - und deaktivierte Entitäten zählen nicht."""
    mit_registrierung(registrierung(
        eintrag("sensor.p", "d1", "sensor", "Neigung Pitch"),
        eintrag("number.radstand", "d1", "number", "Radstand"),
        eintrag("number.fremd_radstand", "d2", "number", "Radstand"),
        eintrag("number.spur_aus", "d1", "number", "Spurweite", deaktiviert="user"),
    ))
    assert coordinator.find_device_sources(None, "sensor.p") == {"wheelbase": "number.radstand"}


def test_unbekannter_sensor_keine_geraetewerte(mit_registrierung):
    assert coordinator.find_device_sources(None, "sensor.unbekannt") == {}
