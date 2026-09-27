"""Werkskalibrierung: Speicheraufteilung, Firmware und Geräteseite passen zusammen.

Die Werkskalibrierung liegt in einem eigenen Flash-Bereich "werk", damit sie
"Werkseinstellungen" übersteht. Die Aufteilung lässt sich nur per USB ändern -
ein Fehler hier fiele erst an einem ausgelieferten Gerät auf. Deshalb prüfen
diese Tests die Dateien selbst.
"""

from __future__ import annotations

import csv
import io
import re

import pytest

from conftest import WURZEL

LEVEL = WURZEL / "esphome" / "level"
HARDWARE = (LEVEL / "hardware.yaml").read_text(encoding="utf-8")
HEADER = (LEVEL / "werkskalibrierung.h").read_text(encoding="utf-8")
WEBUI = (LEVEL / "webui.js").read_text(encoding="utf-8")

# Die Voreinstellung von ESPHome für 4 MB, wie sie bis 4.0.5 gebaut wurde
# (aus partition-table.bin ausgelesen). Die App-Bereiche MÜSSEN so bleiben,
# sonst passen Updates über das Netz nicht mehr auf ältere Geräte.
APP_UNVERAENDERT = {
    "otadata": (0x9000, 0x2000),
    "phy_init": (0xB000, 0x1000),
    "app0": (0x10000, 0x1C0000),
    "app1": (0x1D0000, 0x1C0000),
}
NVS_START = 0x390000
FLASH_ENDE = 0x400000


def _aufteilung() -> dict[str, dict]:
    zeilen = [
        z for z in (LEVEL / "partitions.csv").read_text(encoding="utf-8").splitlines()
        if z.strip() and not z.lstrip().startswith("#")
    ]
    bereiche = {}
    for name, typ, untertyp, start, groesse in csv.reader(io.StringIO("\n".join(zeilen))):
        bereiche[name.strip()] = {
            "typ": typ.strip(),
            "untertyp": untertyp.strip(),
            "start": int(start, 16),
            "groesse": int(groesse, 16),
        }
    return bereiche


def test_app_bereiche_unveraendert():
    bereiche = _aufteilung()
    for name, (start, groesse) in APP_UNVERAENDERT.items():
        assert (bereiche[name]["start"], bereiche[name]["groesse"]) == (start, groesse), name


def test_werk_hinter_nvs_bis_zum_ende():
    bereiche = _aufteilung()
    nvs, werk = bereiche["nvs"], bereiche["werk"]
    assert nvs["start"] == NVS_START  # die Einstellungen bleiben, wo sie waren
    assert werk["start"] == nvs["start"] + nvs["groesse"]
    assert werk["start"] + werk["groesse"] == FLASH_ENDE
    assert werk["groesse"] == 0x1000  # ein Löschblock
    assert werk["typ"] == "data" and werk["untertyp"] == "0x40"


def test_keine_ueberlappung():
    bereiche = sorted(_aufteilung().values(), key=lambda b: b["start"])
    for vorher, nachher in zip(bereiche, bereiche[1:]):
        assert vorher["start"] + vorher["groesse"] <= nachher["start"]


def test_firmware_nutzt_aufteilung_und_bereich():
    assert "partitions: partitions.csv" in HARDWARE
    assert "- werkskalibrierung.h" in HARDWARE
    assert 'ESP_PARTITION_SUBTYPE_ANY, "werk")' in HEADER  # derselbe Name wie in partitions.csv


def test_korrektur_an_den_rohachsen():
    """Abgezogen wird an accel_x/accel_y - dann gilt es für jede Einbaulage."""
    for achse, wert in (("accel_x", "werk_bx"), ("accel_y", "werk_by")):
        block = HARDWARE[HARDWARE.index(f"id: {achse}\n"):]
        block = block[:block.index("- platform:")]
        assert f"return x - id({wert});" in block, achse


def _knopf(name: str) -> str:
    block = HARDWARE[HARDWARE.index(f'name: "{name}"'):]
    return block[:block.index("- platform:")] if "- platform:" in block else block


@pytest.mark.parametrize("name", ["Werkskalibrierung Messung 1", "Werkskalibrierung Messung 2"])
def test_werkstatt_nicht_beim_kunden(name):
    assert "internal: true" in _knopf(name)


def test_zuruecksetzen_ueberall():
    """Der Kunde kann überall auf ab Werk zurück - Geräteseite, HA, MQTT."""
    knopf = _knopf("Kalibrierung zurücksetzen")
    assert "internal: true" not in knopf
    assert "command_topic: camperminder/level/button/kalibrierung_zuruecksetzen/command" in knopf
    assert "kalibrierung_zuruecksetzen/command" in (WURZEL / "docs" / "mqtt.md").read_text(encoding="utf-8")


def _texte(sprache: str) -> str:
    start = WEBUI.index(f"    {sprache}: {{")
    ende = WEBUI.index("\n    }", start)
    return WEBUI[start:ende]


def _schluessel(sprache: str) -> set[str]:
    return set(re.findall(r"^\s{6}([a-z0-9_]+):", _texte(sprache), re.MULTILINE))


def test_jedes_werkstatt_ergebnis_hat_einen_text():
    ergebnisse = re.search(r"ERGEBNIS\[\] = \{([^}]*)\}", HARDWARE).group(1)
    codes = [c.strip().strip('"') for c in ergebnisse.replace("\n", " ").split(",")]
    for code in filter(None, codes):
        for sprache in ("de", "en"):
            assert f"werkstatt_{code}" in _schluessel(sprache), (code, sprache)


def test_deutsch_und_englisch_haben_dieselben_texte():
    assert _schluessel("de") == _schluessel("en")


def test_statuswerte_dokumentiert():
    for zeile in ("#   f  Werkskalib.", "#   fw Werkstatt", "#   c  Kalibrierung  nie | werk |"):
        assert zeile in HARDWARE, zeile
    assert ';f=%s;fw=%s"' in HARDWARE
    assert 'if (teil[0] === "werk") return t("kal_werk");' in WEBUI
