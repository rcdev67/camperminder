# -*- coding: utf-8 -*-
"""Erzeugt den Entitaetsbestand des Pruefstands aus der echten Firmware.

WARUM ES DIESE DATEI GIBT
=========================
Der Pruefstand (tools/geraetestub.py) hatte seinen Entitaetsbestand von Hand
eingetragen - aus einem Bericht, der im Sommer 2026 einmal von einem Geraet
abgelesen worden war. Am 22.09.2026 hat er der Geraeteseite dreimal grünes
Licht gegeben, während am echten Geraet gar nichts lief: Die Kennungen im
Bestand waren das Format von gestern.

Ein Pruefstand, der die Wirklichkeit nicht abbildet, ist schlimmer als keiner.
Deshalb wird der Bestand jetzt ABGELEITET, und zwar aus derselben Quelle, aus
der die Firmware entsteht:

    esphome config camperminder-level.yaml

Daraus stehen Bereich und Anzeigename jeder Entitaet fest - und genau aus
diesen beiden bildet ESPHome die Kennung im Ereignisstrom
(set_json_id in web_server.cpp):

    <bereich>/<Anzeigename>        z. B. "sensor/Neigung Pitch"

Aendert sich das Format in ESPHome, faellt es in tools/pruefe_esphome.py auf;
aendern sich unsere Entitaeten, faellt es hier auf.

AUFRUF
======
    .venv\\Scripts\\python.exe tools/stub_erzeugen.py

Ergebnis: tools/stub_entitaeten.json - wird von tools/geraetestub.py gelesen.
"""
import io
import json
import os
import subprocess
import sys

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KONFIG = os.path.join(WURZEL, "esphome", "level")
ZIEL = os.path.join(WURZEL, "tools", "stub_entitaeten.json")

# Die Bereiche, die der Webserver als Entitaeten ausliefert. "sensor" und
# Verwandte heissen in der Konfiguration genauso wie im Ereignisstrom.
BEREICHE = [
    "sensor", "binary_sensor", "text_sensor", "number", "select", "switch",
    "button", "text", "update", "light", "cover", "fan", "climate", "lock",
    "valve", "siren", "datetime", "event", "alarm_control_panel",
]

# Plausible Startwerte je Bereich. Der Pruefstand braucht IRGENDEINEN Wert;
# die laufenden Aenderungen erzeugt er selbst.
VORGABE = {
    "sensor": ("0.0", 0.0),
    "binary_sensor": ("OFF", False),
    "text_sensor": ("", None),
    "number": ("0", 0.0),
    "select": ("", None),
    "switch": ("OFF", False),
    "button": ("", None),
    "text": ("", None),
    "update": ("OFF", False),
}


def konfiguration():
    """Den aufgeloesten Konfigurationsbaum von ESPHome holen."""
    esphome = os.path.join(WURZEL, ".venv", "Scripts", "esphome.exe")
    if not os.path.exists(esphome):
        sys.exit("Nicht gefunden: %s  (tools/einrichten.cmd ausfuehren)" % esphome)

    umgebung = dict(os.environ)
    umgebung.setdefault("PYTHONIOENCODING", "utf-8")
    lauf = subprocess.run(
        [esphome, "config", "camperminder-level.yaml"],
        cwd=KONFIG, capture_output=True, text=True, encoding="utf-8",
        errors="replace", env=umgebung)
    if lauf.returncode != 0:
        sys.stderr.write(lauf.stdout or "")
        sys.stderr.write(lauf.stderr or "")
        sys.exit("esphome config ist fehlgeschlagen - Meldung oben lesen.")

    try:
        import yaml
    except ImportError:
        sys.exit("PyYAML fehlt - es kommt normalerweise mit ESPHome mit.")

    # ESPHome schreibt Hinweiszeilen vor den Baum; alles bis zur ersten Zeile
    # ohne Einrueckung, die nicht mit INFO/WARNING beginnt, gehoert dazu.
    zeilen = []
    begonnen = False
    for zeile in (lauf.stdout or "").split("\n"):
        if not begonnen:
            if zeile[:1].isalpha() and zeile.rstrip().endswith(":") \
                    and not zeile.startswith(("INFO", "WARNING", "ERROR")):
                begonnen = True
            else:
                continue
        zeilen.append(zeile)
    text = "\n".join(zeilen)

    # Die Ausgabe enthaelt Steuerzeichen zur Hervorhebung (\033[8m ...).
    text = text.replace("\\033[8m", "").replace("\\033[28m", "")
    # ESPHome schreibt eigene Marken in den Baum (!lambda, !secret, ...).
    # Sie interessieren hier nicht - ein Leser, der jede unbekannte Marke als
    # Zeichenkette nimmt, kommt ohne sie durch.
    class Leser(yaml.SafeLoader):
        pass

    Leser.add_multi_constructor(
        "", lambda lader, marke, knoten: str(getattr(knoten, "value", "")))

    return yaml.load(text, Loader=Leser) or {}


def entitaeten(baum):
    """(kennung, name, bereich, zustand, wert) je Entitaet."""
    raus = []
    for bereich in BEREICHE:
        eintraege = baum.get(bereich)
        if not isinstance(eintraege, list):
            continue
        for eintrag in eintraege:
            if not isinstance(eintrag, dict):
                continue
            name = eintrag.get("name")
            if not name:
                continue  # interne Entitaet ohne Namen - kommt nicht heraus
            zustand, wert = VORGABE.get(bereich, ("", None))
            # Auswahlen: die erste Option ist ein plausibler Startwert.
            if bereich == "select":
                optionen = eintrag.get("options") or []
                if optionen:
                    zustand = eintrag.get("initial_option") or optionen[0]
            if bereich == "number":
                anfang = eintrag.get("initial_value")
                if anfang is not None:
                    zustand, wert = str(anfang), float(anfang)
            raus.append({
                "kennung": "%s/%s" % (bereich, name),
                "name": name,
                "bereich": bereich,
                "zustand": zustand,
                "wert": wert,
            })
    return raus


def main():
    baum = konfiguration()
    liste = entitaeten(baum)
    if not liste:
        sys.exit("Keine Entitaeten gefunden - stimmt der Konfigurationspfad?")

    io.open(ZIEL, "w", encoding="utf-8").write(
        json.dumps({
            "hinweis": ("Erzeugt von tools/stub_erzeugen.py aus "
                        "esphome config - NICHT von Hand pflegen."),
            "entitaeten": liste,
        }, ensure_ascii=False, indent=2) + "\n")

    nach_bereich = {}
    for e in liste:
        nach_bereich[e["bereich"]] = nach_bereich.get(e["bereich"], 0) + 1
    print("%d Entitaeten nach %s" % (len(liste), os.path.relpath(ZIEL, WURZEL)))
    for bereich in sorted(nach_bereich):
        print("  %-16s %d" % (bereich, nach_bereich[bereich]))
    print("")
    print("Beispielkennung: %s" % liste[0]["kennung"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
