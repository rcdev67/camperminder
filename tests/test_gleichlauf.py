"""Gleichlauf: Geräteseite, Home Assistant, MQTT und Karte sagen dasselbe.

Der Grundsatz des Produkts: Ob direkt am Gerät per WLAN, in Home Assistant
oder über MQTT - dieselben Funktionen, dieselben Werte, derselbe Satz. Die
Anweisung entsteht dafür an zwei Stellen (Firmware und Integration), und die
Namen stehen an vier (Firmware, Integration, Karte, Geräteseite).

Diese Tests lesen die Quelltexte und schlagen an, sobald eine Stelle ohne die
anderen geändert wird. Sie ersetzen keinen Test am Prototyp - sie verhindern
nur, dass die Stellen still auseinanderlaufen, wie es bis 4.0.2 geschehen war.
"""

from __future__ import annotations

import json
import re

import pytest

from conftest import WURZEL, const, rechenkern, WOHNWAGEN

HARDWARE = (WURZEL / "esphome" / "level" / "hardware.yaml").read_text(encoding="utf-8")
WEBUI = (WURZEL / "esphome" / "level" / "webui.js").read_text(encoding="utf-8")
KARTE = (WURZEL / "custom_components" / "camperminder" / "www" / "camperminder-card.js").read_text(
    encoding="utf-8"
)
MANIFEST = json.loads(
    (WURZEL / "custom_components" / "camperminder" / "manifest.json").read_text(encoding="utf-8")
)


def _js_eintrag(text: str, schluessel: str) -> str | None:
    """Wert eines Eintrags  schluessel: "Wert"  im ersten Vorkommen."""
    treffer = re.search(rf'\b{re.escape(schluessel)}:\s*"([^"]*)"', text)
    return treffer.group(1) if treffer else None


def _webui_deutsch() -> str:
    """Nur das deutsche Wörterbuch der Geräteseite - dort stehen die Namen zuerst."""
    start = WEBUI.index("de: {")
    return WEBUI[start:WEBUI.index("en: {", start)]


def test_versionsnummern_gleich():
    firmware = re.search(r'firmware_version:\s*"([^"]+)"', HARDWARE).group(1)
    seite = re.search(r'var SEITE_VERSION = "([^"]+)"', WEBUI).group(1)
    assert firmware == seite == MANIFEST["version"]


def test_rasterung_gleich():
    assert const.INSTRUCTION_GRID_CM == 0.5
    assert const.INSTRUCTION_HYSTERESIS_CM == 0.3
    assert "fabsf(neu - alt) >= 0.3f - 0.001f ? roundf(neu * 2.0f) / 2.0f : alt" in HARDWARE


@pytest.mark.parametrize(("rad", "name"), sorted(const.INSTRUCTION_NAMES.items()))
def test_wohnmobil_namen_ueberall_gleich(rad, name):
    namen_firmware = re.search(r"namen_mobil\[5\] = \{([^}]*)\}", HARDWARE).group(1)
    assert f'"{name}"' in namen_firmware
    assert _js_eintrag(KARTE[KARTE.index("const WHEEL_NAMES"):], rad) == name
    assert _js_eintrag(_webui_deutsch(), f"rad_{rad}") == name


@pytest.mark.parametrize(("rad", "name"), sorted(const.CARAVAN_INSTRUCTION_NAMES.items()))
def test_wohnwagen_namen_ueberall_gleich(rad, name):
    namen_firmware = re.search(r"namen_wagen\[5\] = \{([^}]*)\}", HARDWARE).group(1)
    assert f'"{name}"' in namen_firmware
    assert _js_eintrag(KARTE[KARTE.index("const CARAVAN_WHEEL_NAMES"):], rad) == name
    assert _js_eintrag(_webui_deutsch(), f"wagen_rad_{rad}") == name


def test_satzbausteine_der_firmware_passen_zur_integration():
    """Die Integration baut den Satz aus denselben Bausteinen wie die Firmware."""
    for baustein in ('"%s %s cm"', '" · "', '" hoch"', '" runter"',
                     '" – Keilstufe %d"', '", danach Stützrad"',
                     f'"{const.INSTRUCTION_LEVEL_TEXT}"'):
        assert baustein in HARDWARE, baustein
    assert rechenkern(-0.5278, -0.4523).instruction["text"] == "Vorne links 4,0 cm hoch – Keilstufe 1"
    assert rechenkern(1.0, 1.5, fahrzeug=WOHNWAGEN).instruction["text"].endswith(", danach Stützrad")


def test_statuswerte_ecken_gleich_verschluesselt():
    """Firmware schickt die Schritte als Kürzel, die Geräteseite löst sie auf."""
    codes = re.search(r"codes\[5\] = \{([^}]*)\}", HARDWARE).group(1)
    assert [c.strip().strip('"') for c in codes.split(",")] == ["vl", "vr", "hl", "hr", "st"]
    ecken = WEBUI[WEBUI.index("var ECKEN = {"):]
    ecken = ecken[:ecken.index("};")]
    erwartet = {"vl": const.WHEEL_FRONT_LEFT, "vr": const.WHEEL_FRONT_RIGHT,
                "hl": const.WHEEL_REAR_LEFT, "hr": const.WHEEL_REAR_RIGHT,
                "st": const.POINT_JOCKEY}
    for kuerzel, rad in erwartet.items():
        assert _js_eintrag(ecken, kuerzel) == rad
    assert ";a=%s;d=%s" in HARDWARE


def test_abweichung_ueberall_und_nicht_intern():
    """Die Abweichung je Ecke gibt es auf allen Wegen - nicht nur auf der Seite."""
    for ecke in ("vorne links", "vorne rechts", "hinten links", "hinten rechts"):
        block = HARDWARE[HARDWARE.index(f'name: "Abweichung {ecke}"'):]
        block = block[:block.index("- platform:")]
        assert "internal: true" not in block, ecke
    assert "abweichung_stuetzrad/state" in (WURZEL / "docs" / "mqtt.md").read_text(encoding="utf-8")
