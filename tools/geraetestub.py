# -*- coding: utf-8 -*-
"""Pruefstand fuer die Geraeteseite - das Geraet, ohne Geraet.

Liefert dieselben drei Dinge wie die Firmware:
    /            eine Seite, die /0.js laedt (wie ESPHomes web_server)
    /0.js        die echte esphome/level/webui.js aus dem Repository
    /events      den Ereignisstrom, im Format der festgenagelten
                 ESPHome-Fassung
Alles andere per POST beantwortet er mit 200, damit Schreibzugriffe nicht als
Fehler erscheinen. WAS die Seite schreibt, prueft er nicht - dafuer braucht es
echte Hardware.

WICHTIG, UND TEUER GELERNT
==========================
Der Entitaetsbestand wird NICHT hier gepflegt, sondern von
tools/stub_erzeugen.py aus "esphome config" abgeleitet. Bis zum 22.09.2026
stand er von Hand in dieser Datei - mit den Kennungen einer aelteren
ESPHome-Fassung. Der Pruefstand gab dreimal gruenes Licht, waehrend die
Geraeteseite am echten Geraet vollstaendig tot war.

Neu erzeugen nach jeder Aenderung an den Entitaeten:
    .venv\\Scripts\\python.exe tools/stub_erzeugen.py

AUFRUF
======
    .venv\\Scripts\\python.exe tools/geraetestub.py
    .venv\\Scripts\\python.exe tools/geraetestub.py --port 8123 \\
        --zustand "select/Zielprofil=Ablassen" \\
        --zustand "select/Fahrzeugart=Wohnwagen"

Dann http://127.0.0.1:8123/ im Browser oeffnen. Der Fehlerfaenger der Seite
sammelt jeden unbehandelten Fehler in window.__fehler - ein Fehler im
Ereignisbehandler verpufft sonst lautlos, und genau daran ist am 22.09.2026
ein Nachmittag vergangen.
"""
import argparse
import http.server
import io
import json
import math
import os
import socketserver
import sys
import time

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEBUI = os.path.join(WURZEL, "esphome", "level", "webui.js")
BESTAND = os.path.join(WURZEL, "tools", "stub_entitaeten.json")

SEITE = """<!doctype html><html><head><meta charset="utf-8">
<title>CamperMinder Pruefstand</title></head><body>
<script>
/* Fehlerfaenger: ein Fehler im Ereignisbehandler stirbt sonst still. */
window.__fehler = [];
window.addEventListener("error", function (e) {
  window.__fehler.push((e.error && e.error.stack) || e.message);
});
window.addEventListener("unhandledrejection", function (e) {
  window.__fehler.push("Versprechen: " + (e.reason && (e.reason.stack || e.reason)));
});
</script>
<script src="/0.js"></script></body></html>"""


def lade_bestand(ueberschreibungen):
    if not os.path.exists(BESTAND):
        sys.exit("Nicht gefunden: %s\n"
                 "Erst erzeugen:  python tools/stub_erzeugen.py" % BESTAND)
    daten = json.loads(io.open(BESTAND, encoding="utf-8").read())
    liste = daten["entitaeten"]

    for eintrag in ueberschreibungen:
        kennung, _, wert = eintrag.partition("=")
        treffer = [e for e in liste if e["kennung"] == kennung]
        if not treffer:
            sys.exit("Unbekannte Kennung: %s\nVorhanden sind z. B.:\n  %s"
                     % (kennung, "\n  ".join(e["kennung"] for e in liste[:8])))
        treffer[0]["zustand"] = wert
        if wert in ("ON", "OFF"):
            treffer[0]["wert"] = (wert == "ON")
        else:
            try:
                treffer[0]["wert"] = float(wert)
            except ValueError:
                treffer[0]["wert"] = None
    return liste


def finde(liste, name):
    for e in liste:
        if e["name"] == name:
            return e["kennung"]
    return None


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    bestand = []

    def log_message(self, *a):
        pass

    def _sende(self, leib, typ):
        self.send_response(200)
        self.send_header("Content-Type", typ)
        self.send_header("Content-Length", str(len(leib)))
        self.end_headers()
        self.wfile.write(leib)

    def do_GET(self):
        pfad = self.path.split("?")[0]

        if pfad == "/" or pfad.startswith("/index"):
            self._sende(SEITE.encode("utf-8"), "text/html; charset=utf-8")
            return

        if pfad == "/0.js":
            leib = io.open(WEBUI, encoding="utf-8").read().encode("utf-8")
            self._sende(leib, "application/javascript; charset=utf-8")
            return

        if pfad == "/events":
            self._strom()
            return

        self.send_response(404)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _ereignis(self, daten):
        roh = "event: state\ndata: " + json.dumps(daten, ensure_ascii=False) + "\n\n"
        self.wfile.write(roh.encode("utf-8"))

    def _strom(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        liste = self.bestand
        try:
            # Erstbericht: MIT name und domain, wie ESPHome ihn bei
            # DETAIL_ALL schickt.
            for e in liste:
                daten = {"id": e["kennung"], "name": e["name"],
                         "domain": e["bereich"], "state": e["zustand"]}
                if e["wert"] is not None:
                    daten["value"] = e["wert"]
                self._ereignis(daten)
            self.wfile.flush()

            # Laufende Aktualisierungen: NUR id, state, value - ohne name.
            # Genau daran hat sich gezeigt, dass die Seite den Namen aus dem
            # Erstbericht behalten muss.
            pitch = finde(liste, "Neigung Pitch")
            roll = finde(liste, "Neigung Roll")
            hub = finde(liste, "Hub vorne links")
            n = 0
            while True:
                time.sleep(0.2)
                n += 1
                werte = [
                    (pitch, round(2.0 * math.sin(n / 12.0), 1), " °"),
                    (roll, round(2.5 * math.cos(n / 17.0), 1), " °"),
                    (hub, round(abs(2.0 * math.sin(n / 12.0)), 1), " cm"),
                ]
                for kennung, wert, einheit in werte:
                    if not kennung:
                        continue
                    self._ereignis({"id": kennung,
                                    "state": ("%.1f" % wert) + einheit,
                                    "value": wert})
                self.wfile.flush()
        except Exception:
            return

    def do_POST(self):
        self.send_response(200)
        self.send_header("Content-Length", "0")
        self.end_headers()


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main():
    p = argparse.ArgumentParser(description="Pruefstand fuer die Geraeteseite")
    p.add_argument("--port", type=int, default=8123)
    p.add_argument("--zustand", action="append", default=[],
                   metavar="kennung=wert",
                   help='z. B. "select/Zielprofil=Ablassen"')
    args = p.parse_args()

    Handler.bestand = lade_bestand(args.zustand)
    print("%d Entitaeten geladen" % len(Handler.bestand))
    print("Pruefstand laeuft auf http://127.0.0.1:%d/" % args.port)
    with Server(("127.0.0.1", args.port), Handler) as srv:
        srv.serve_forever()


if __name__ == "__main__":
    main()
