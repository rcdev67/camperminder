"""Die Anweisung: Ecke für Ecke, auf halbe Zentimeter gerastet.

Dieselbe Regel steht in der Firmware ("Der nächste Handgriff" in
esphome/level/hardware.yaml). Was hier geprüft wird, muss dort genauso
gelten - test_gleichlauf.py hält die beiden Stellen zusammen.
"""

from __future__ import annotations

import math
import random
import struct
from types import SimpleNamespace

import pytest

from conftest import WOHNMOBIL, WOHNWAGEN, announce, rechenkern

# Der Live-Fall aus dem Wohnmobil vom 26.09.2026: nur längs schief, beide
# vorderen Ecken 3,9 cm.
NUR_LAENGS = (-0.5278, -0.4523)


def test_plan_fasst_keine_seiten_mehr_zusammen():
    kern = rechenkern(*NUR_LAENGS)
    assert [p["wheel"] for p in kern.wheel_plan] == ["vorne_links", "vorne_rechts"]


def test_keile_nur_hoechste_ecke_mit_keilstufe():
    anweisung = rechenkern(*NUR_LAENGS).instruction
    assert len(anweisung["steps"]) == 1
    assert anweisung["steps"][0]["wheel"] == "vorne_links"
    assert anweisung["text"] == "Vorne links 4,0 cm hoch – Keilstufe 1"


def test_keilstufe_null_heisst_aus():
    anweisung = rechenkern(*NUR_LAENGS, keilstufe=0).instruction
    assert anweisung["text"] == "Vorne links 4,0 cm hoch"


def test_hydraulik_alle_ecken_ohne_keilstufe():
    anweisung = rechenkern(*NUR_LAENGS, methode="hebesystem").instruction
    assert anweisung["text"] == "Vorne links 4,0 cm · Vorne rechts 4,0 cm hoch"
    assert all(schritt["wedge_steps"] is None for schritt in anweisung["steps"])


def test_hydraulik_hoechste_zuerst_und_gerastet():
    anweisung = rechenkern(2.0, 1.5, methode="hebesystem").instruction
    werte = [schritt["cm"] for schritt in anweisung["steps"]]
    assert len(werte) == 3
    assert werte == sorted(werte, reverse=True)
    assert all((wert * 2).is_integer() for wert in werte)


def test_eben():
    anweisung = rechenkern(-0.39, -0.50).instruction
    assert anweisung == {"steps": [], "then": None, "text": "Steht eben - fertig"}


def test_ohne_messwerte_keine_anweisung():
    assert rechenkern(None, 0.0).instruction is None


def test_wiederholtes_abfragen_aendert_nichts():
    # Karte, Sensor und Ansage fragen unabhängig voneinander.
    kern = rechenkern(*NUR_LAENGS)
    assert kern.instruction == kern.instruction


def test_wohnwagen_erst_rad_dann_stuetzrad_ohne_mass():
    anweisung = rechenkern(1.0, 1.5, fahrzeug=WOHNWAGEN).instruction
    assert len(anweisung["steps"]) == 1
    assert anweisung["then"] == "stuetzrad"
    assert anweisung["text"].startswith("Linkes Rad ")
    assert anweisung["text"].endswith(" hoch – Keilstufe 1, danach Stützrad")


def test_wohnwagen_nur_stuetzrad_runter_ohne_keilstufe():
    anweisung = rechenkern(1.0, 0.2, fahrzeug=WOHNWAGEN).instruction
    assert anweisung["steps"][0]["wheel"] == "stuetzrad"
    assert anweisung["steps"][0]["wedge_steps"] is None
    assert anweisung["text"].startswith("Stützrad ")
    assert anweisung["text"].endswith(" cm runter")


@pytest.mark.parametrize(
    ("folge", "erwartet"),
    [
        # Hysterese 0,3, Raster 0,5 - die Grenze genau bei 0,3 rastet.
        ([3.9, 4.1, 4.2, 4.3, 4.26, 3.9, 1.2], [4.0, 4.0, 4.0, 4.5, 4.5, 4.0, 1.0]),
    ],
)
def test_rasterung_und_hysterese(folge, erwartet):
    kern = rechenkern(0.0, 0.0)
    assert [kern._steady_cm("vl", wert) for wert in folge] == erwartet


def test_halbe_nach_oben_wie_roundf():
    # Pythons round() rundet 4,5 auf 4 - die Firmware (roundf) auf 5.
    assert rechenkern(0.0, 0.0)._steady_cm("x", 2.25) == 2.5


def _f32(wert: float) -> float:
    return struct.unpack("f", struct.pack("f", wert))[0]


def _roundf(wert: float) -> float:
    return math.floor(wert + 0.5) if wert >= 0 else -math.floor(-wert + 0.5)


def _ruhig_firmware(neu: float, alt: float) -> float:
    """ruhig() aus hardware.yaml, in float32 gerechnet wie auf dem ESP32."""
    neu, alt = _f32(neu), _f32(alt)
    grenze = _f32(_f32(0.3) - _f32(0.001))
    if _f32(abs(_f32(neu - alt))) >= grenze:
        return _f32(_f32(_roundf(_f32(neu * 2.0))) / 2.0)
    return alt


def test_rasterung_identisch_zur_firmware_in_float32():
    """Zufällige Messfolgen im 0,1-Raster: Integration und Firmware rasten gleich.

    Ohne das Spiel von 0,001 cm an der Grenze liefen sie genau bei 0,3 cm
    Abstand auseinander - 4,3 - 4,0 ist in Python 0,2999..., im float der
    Firmware 0,3000002.
    """
    zufall = random.Random(4711)
    abweichungen = 0
    for _ in range(400):
        kern = rechenkern(0.0, 0.0)
        firmware = 0.0
        wert = zufall.randint(10, 150) / 10
        for _ in range(60):
            wert = max(1.0, round(wert + zufall.choice([-0.3, -0.2, -0.1, 0, 0.1, 0.2, 0.3, 0.4]), 1))
            firmware = _ruhig_firmware(wert, firmware)
            if abs(kern._steady_cm("vl", wert) - firmware) > 1e-6:
                abweichungen += 1
    assert abweichungen == 0


def _ansage(kern) -> str | None:
    return announce.CamperAnnouncer(SimpleNamespace(), kern, {})._build_instruction_announcement()


def test_ansage_keile():
    assert _ansage(rechenkern(*NUR_LAENGS)) == "Vorne links 4 Zentimeter hoch, Keilstufe 1."


def test_ansage_hydraulik():
    assert (
        _ansage(rechenkern(*NUR_LAENGS, methode="hebesystem"))
        == "Vorne links 4 und Vorne rechts 4 Zentimeter hoch."
    )


def test_ansage_wohnwagen():
    text = _ansage(rechenkern(1.0, 1.5, fahrzeug=WOHNWAGEN))
    assert text.startswith("Linkes Rad ")
    assert text.endswith("Zentimeter hoch, Keilstufe 1, danach Stützrad.")


def test_ansage_eben_sagt_nichts_eigenes():
    # "Steht eben. Stopp." kommt aus der Phasenansage, nicht aus der Anweisung.
    assert _ansage(rechenkern(-0.39, -0.50)) is None


def test_fahrzeugart_wohnmobil_ist_voreinstellung():
    assert rechenkern(*NUR_LAENGS).vehicle_type == WOHNMOBIL
