# -*- coding: utf-8 -*-
"""Prueft die Annahmen, auf die sich die Geraeteseite stuetzt.

WARUM ES DIESE DATEI GIBT
=========================
Am 22.09.2026 ist die Geraeteseite vollstaendig ausgefallen, ohne eine einzige
Fehlermeldung. Ursache: ESPHome hatte das Format der Entitaetskennungen im
Ereignisstrom geaendert -

    bis 2026.7:  sensor-neigung_pitch
    ab  2026.8:  sensor/Neigung Pitch

- und webui.js suchte weiter nach dem alten. Nichts stuerzt dabei ab; die Seite
findet nur keine Entitaet wieder und bleibt leer. Gefunden wurde das nach
Stunden, und zwar von Hand.

Das darf sich nicht wiederholen, und es darf vor allem nicht beim Kunden
auffallen: Der bekommt die Firmware per OTA und steht damit auf dem
Stellplatz. Deshalb prueft dieses Skript die Schnittstelle GEGEN DEN
QUELLTEXT der installierten ESPHome-Fassung und bricht den Bau ab, sobald
eine Annahme nicht mehr stimmt.

Es prueft absichtlich den Quelltext und nicht nur die Versionsnummer: Eine
Fassung kann sich aendern, ohne dass die Nummer etwas darueber sagt, und die
Nummer kann sich aendern, ohne dass an dieser Schnittstelle etwas passiert.

AUFRUF
======
    python tools/pruefe_esphome.py
Rueckgabe 0 = alles in Ordnung, 1 = Annahme verletzt (Meldung nennt die
Stelle in webui.js, die nachgezogen werden muss).
"""
import io
import os
import re
import sys

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ESPHOME = os.path.join(WURZEL, ".venv", "Lib", "site-packages", "esphome")
WEBUI = os.path.join(WURZEL, "esphome", "level", "webui.js")


def lies(*teile):
    pfad = os.path.join(ESPHOME, *teile)
    if not os.path.exists(pfad):
        return None
    return io.open(pfad, encoding="utf-8", errors="replace").read()


def festgenagelte_fassung():
    text = io.open(os.path.join(WURZEL, "requirements.txt"), encoding="utf-8").read()
    treffer = re.search(r"^esphome==(\S+)", text, re.M)
    return treffer.group(1) if treffer else None


def installierte_fassung():
    text = lies("const.py") or ""
    treffer = re.search(r'__version__\s*=\s*"([^"]+)"', text)
    return treffer.group(1) if treffer else None


# --- Die einzelnen Annahmen ------------------------------------------------
#
# Jede Pruefung nennt: was die Seite annimmt, wo im ESPHome-Quelltext das
# herkommt, und was in webui.js zu aendern ist, wenn es nicht mehr stimmt.

def pruefungen():
    ergebnis = []

    def pruefe(titel, bedingung, quelle, folge):
        ergebnis.append((titel, bool(bedingung), quelle, folge))

    ws = lies("components", "web_server", "web_server.cpp") or ""
    idf = lies("components", "web_server_idf", "web_server_idf.cpp") or ""
    js = io.open(WEBUI, encoding="utf-8").read()

    # 1. Die Kennung im Ereignisstrom: <bereich>/<Anzeigename>
    #    In set_json_id() wird der Bereich geschrieben, dann '/', dann der
    #    NAME der Entitaet.
    kopf = re.search(r"static void set_json_id\(.*?\n\}", ws, re.S)
    kopf = kopf.group(0) if kopf else ""
    pruefe(
        "Kennung = <bereich>/<Anzeigename>",
        "*p++ = '/';" in kopf and "name.c_str()" in kopf,
        "web_server.cpp, set_json_id()",
        "objektKennung()/splitId() in webui.js - die Seite rechnet den "
        "Anzeigenamen in eine Kennung um.")

    # 2. Schreibzugriffe treffen die Entitaet ueber ihren NAMEN.
    pruefe(
        "Schreibziel = Anzeigename",
        re.search(r"this->id\s*==\s*entity->get_name\(\)", ws) is not None,
        "web_server.cpp, UrlMatch::match_entity()",
        "pathFor() in webui.js baut /<bereich>/<Anzeigename>.")

    # 3. Zahl setzen: Methode "set", Parameter "value".
    pruefe(
        'Zahl setzen: "set" mit Parameter "value"',
        re.search(r'method_equals\(ESPHOME_F\("set"\)\)', ws) is not None
        and re.search(r'parse_num_param_\(request, ESPHOME_F\("value"\)', ws) is not None,
        "web_server.cpp, handle_number_request()",
        "write()/setNumber() in webui.js.")

    # 4. Unsere Datei wird unter /0.js ausgeliefert.
    pruefe(
        "js_include liegt auf /0.js",
        re.search(r'url == ESPHOME_F\("/0\.js"\)', ws) is not None,
        "web_server.cpp, handle_js_request()",
        "Die Seite wird ueber js_include eingebettet; ein anderer Pfad "
        "hiesse, dass die eigene Oberflaeche nicht mehr geladen wird.")

    # 5. Der Ereignisstrom liegt auf /events und schickt Ereignisse namens
    #    "state".
    pruefe(
        'Ereignisstrom /events mit Ereignis "state"',
        "/events" in ws and re.search(r'"state"', ws) is not None,
        "web_server.cpp",
        'connect() in webui.js hoert auf EventSource("/events") und das '
        'Ereignis "state".')

    # 6. Die Datei wird ohne Zwischenspeicher-Angaben ausgeliefert. Das ist
    #    keine Annahme der Seite, sondern der Grund fuer den Veraltet-Balken:
    #    Fiele es weg, koennte der Balken entfallen.
    js_handler = re.search(r"void WebServer::handle_js_request.*?\n\}", ws, re.S)
    js_handler = js_handler.group(0) if js_handler else ""
    pruefe(
        "/0.js kommt ohne Cache-Control (Balken noch noetig)",
        "Cache-Control" not in js_handler and "ETag" not in js_handler,
        "web_server.cpp, handle_js_request()",
        "seiteVeraltet() in webui.js koennte entfallen, wenn ESPHome die "
        "Datei versioniert oder mit Validator ausliefert.")

    # 7. Die Seite selbst muss die Umrechnung mitbringen - sonst ist sie auf
    #    dem Stand vor dem 22.09.2026.
    pruefe(
        "webui.js rechnet Namen in Kennungen um",
        # Mit Klammer, sonst trifft der Teilstring auch eine
        # umbenannte Funktion - genau so ist diese Pruefung beim
        # ersten Gegentest durchgerutscht.
        re.search(r"function objektKennung\(", js) is not None,
        "esphome/level/webui.js",
        "Ohne objektKennung() findet die Seite keine Entitaet wieder.")

    # 8. url_decode im IDF-Webserver - sonst sind Namen mit Leerzeichen und
    #    Umlauten nicht adressierbar.
    pruefe(
        "Adressen werden dekodiert (Umlaute, Leerzeichen)",
        "url_decode" in idf,
        "web_server_idf.cpp",
        "pathFor() kodiert den Namen mit encodeURIComponent.")

    return ergebnis


def main():
    if not os.path.isdir(ESPHOME):
        print("FEHLER: ESPHome ist nicht eingerichtet (%s fehlt)." % ESPHOME)
        print("        tools/einrichten.cmd ausfuehren.")
        return 1

    fest = festgenagelte_fassung()
    ist = installierte_fassung()
    print("ESPHome festgenagelt: %s" % fest)
    print("ESPHome installiert:  %s" % ist)

    fehler = 0
    if fest and ist and fest != ist:
        print("")
        print("FEHLER: Die installierte Fassung weicht von requirements.txt ab.")
        print("        Entweder  .venv\\Scripts\\python.exe -m pip install -r requirements.txt")
        print("        oder requirements.txt bewusst aendern - dann aber den")
        print("        Ablauf in docs/firmware_update.md, Abschnitt")
        print('        "ESPHome wechseln", vollstaendig durchgehen.')
        fehler = 1

    print("")
    for titel, ok, quelle, folge in pruefungen():
        print("%-46s %s" % (titel, "ok" if ok else "ABWEICHUNG"))
        if not ok:
            print("      Quelle: %s" % quelle)
            print("      Folge:  %s" % folge)
            fehler = 1

    print("")
    if fehler:
        print("ABBRUCH: Die Geraeteschnittstelle passt nicht mehr zur Seite.")
        print("         Nachziehen, pruefen, dann erneut bauen - NICHT")
        print("         ausliefern. Beim Kunden faellt das erst auf dem")
        print("         Stellplatz auf.")
    else:
        print("Alle Annahmen der Geraeteseite gelten.")
    return fehler


if __name__ == "__main__":
    sys.exit(main())
