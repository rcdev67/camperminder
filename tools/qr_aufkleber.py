# -*- coding: utf-8 -*-
"""Erzeugt den QR-Aufkleber fuer das Geraet.

WARUM ES IHN GIBT
=================
Der Massstab ist ein Bluetooth-Geraet mit App: auspacken, koppeln, fertig.
Der Aufkleber kommt dem so nahe, wie es mit WLAN geht - niemand muss etwas
tippen:

    Code 1   WIFI:T:nopass;S:CamperMinder;;   Handy tritt dem Netz bei
    Code 2   http://192.168.4.1/              die Wasserwaage oeffnet sich
    Code 3   http://camperminder-level.local/ Geraet im Heim-WLAN

GESCHICHTE, damit niemand denselben Weg zweimal geht (28.09.2026):

  1. Code 1 Netzbeitritt, Code 2 192.168.4.1 - aber fuer das Heim-WLAN
     nichts.
  2. Code 1 192.168.4.1, Code 2 .local - nach Lage, aber das Handy musste
     erst von Hand ins Netz, sonst oeffnete Code 1 nichts.
  3. Code 1 Netzbeitritt, Code 2 .local, dazu die Anmeldeseite (4.2.0):
     Das Geraet leitet die Internetpruefung des Handys auf die Wasserwaage
     um, und das Handy sollte sie von selbst oeffnen. Das iPhone tut das;
     am Samsung (Android) nachweislich nicht - die Umleitung kam an, das
     Protokoll zeigte sie, aber das Handy oeffnete weder die Seite noch eine
     Meldung. Ein Scan fuer alle Handys gibt es damit nicht.
  4. Jetzt: drei Codes. 1 und 2 sind der erste Start, nacheinander; auf dem
     iPhone ist die Seite nach Code 1 meist schon offen. 3 ist das
     Heim-WLAN. In einem Code laesst sich Netzbeitritt und Adresse nicht
     vereinen - das WIFI-Format kennt kein Feld fuer eine Adresse.

Code 3 geht ueber mDNS (<Name>.local), weil die Adresse im Heim-WLAN in
jedem Haushalt eine andere ist - der Name ist der einzige feste Weg. Auf
dem iPhone traegt er, auf Android nicht auf jedem Geraet; fuer diesen Fall
nennt die Anleitung die Suche der Geraeteseite und den Router.

Alle drei Codes sind fuer JEDES Geraet gleich: Adresse und Name haengen an der
Firmware, nicht am einzelnen Geraet. Ein Aufkleber, eine Druckvorlage -
auch fuer das Handmuster, das seit 28.09.2026 ebenfalls camperminder-level
heisst.

Netzname, Adresse und Geraetename werden aus
esphome/level/camperminder-level.yaml GELESEN, nicht hier abgeschrieben.
Aendert sich dort etwas davon, passt der naechste Lauf den Aufkleber an -
und ein alter Aufkleber faellt auf, weil das Ergebnis im Repository dann
anders aussieht.

AUFRUF
======
    py -3 -m pip install segno      (einmal je Rechner)
    py -3 tools/qr_aufkleber.py

ERGEBNIS
========
    docs/bilder/aufkleber-qr.svg    Vorlage fuer Anleitung und Druck
    docs/bilder/aufkleber-qr.pdf    dieselbe Seite in Originalgroesse,
                                    90 x 52 mm - zum Drucken bei 100 %

Das PDF entsteht ueber Microsoft Edge ohne Fenster. Fehlt Edge, bleibt es
beim SVG, und der Lauf sagt das.
"""
import io
import os
import re
import subprocess
import sys
import tempfile

try:
    import segno
    from segno import helpers
except ImportError:
    sys.exit("segno fehlt:  py -3 -m pip install segno")

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GERAET = os.path.join(WURZEL, "esphome", "level", "camperminder-level.yaml")
MARKE = os.path.join(WURZEL, "brand", "camperminder-mark.svg")
ZIEL_SVG = os.path.join(WURZEL, "docs", "bilder", "aufkleber-qr.svg")
ZIEL_PDF = os.path.join(WURZEL, "docs", "bilder", "aufkleber-qr.pdf")

BREITE, HOEHE = 90.0, 52.0      # mm
QR_GROESSE = 20.0               # mm - Module um 0,7 mm, fuer eine Handykamera
                                # aus 10 bis 30 cm reichlich
SPALTEN = (15.0, 45.0, 75.0)    # mm - Mitte je Code
ZIFFER_Y = 12.0                 # mm - Mitte der Ziffern ueber den Codes
QR_OBEN = 17.2                  # mm - Oberkante der Codes
TUERKIS = "#2fb6c9"
DUNKEL = "#1b2430"
GRAU = "#6b7787"
SCHRIFT = "Bahnschrift, 'Segoe UI', Arial, sans-serif"

EDGE = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def aus_geraetedatei():
    """Netzname, Adresse des eigenen Netzes und Geraetename, wie die
    Firmware sie setzt."""
    text = io.open(GERAET, encoding="utf-8").read()
    name = re.search(r"^\s+device_name:\s*([a-z0-9-]+)", text, re.MULTILINE)
    ap = text[text.index("\n  ap:"):]
    netz = re.search(r'^\s+ssid:\s*"([^"]+)"', ap, re.MULTILINE)
    ip = re.search(r"^\s+static_ip:\s*([0-9.]+)", ap, re.MULTILINE)
    if not name or not netz or not ip:
        sys.exit("device_name, ssid oder static_ip nicht gefunden: %s" % GERAET)
    # Ohne mDNS gibt es kein <Name>.local, und Code 3 liefe ins Leere.
    if re.search(r"^mdns:\s*\n\s+disabled:\s*true", text, re.MULTILINE):
        sys.exit("mDNS ist in der Geraetedatei abgeschaltet - Code 3 wuerde nicht tragen.")
    # Code 1 tritt einem Netz OHNE Passwort bei. Stuende in der Geraetedatei
    # eines, passte er nicht. (Ein Passwort, das der Nutzer spaeter selbst
    # vergibt, kann der Aufkleber nicht kennen - das sagt die Anleitung.)
    kopf = ap[:ap.index("manual_ip")]
    if re.search(r"^\s+password:", kopf, re.MULTILINE):
        sys.exit("Das eigene Netz hat in der Geraetedatei ein Passwort - Code 1 passt nicht.")
    # Ohne Anmeldeseite oeffnete Code 1 auch auf dem iPhone nur das Netz -
    # dann stimmte die Anleitung nicht mehr, die dort Code 2 fuer entbehrlich
    # erklaert.
    hardware = io.open(os.path.join(os.path.dirname(GERAET), "hardware.yaml"),
                       encoding="utf-8").read()
    if "anmeldeseite::schritt" not in hardware:
        sys.exit("Die Anmeldeseite ist nicht eingebunden - Code 1 oeffnete die Seite nicht.")
    return netz.group(1), ip.group(1), name.group(1)


def qr_pfad(inhalt, x, y, groesse):
    """Ein QR-Code als ein einziger schwarzer Pfad, Kante auf Kante.

    Fehlerkorrektur Q (25 %): Ein Aufkleber im Fahrzeug bekommt Kratzer und
    Staub. Die Ruhezone von vier Modulen rundherum haelt das Layout frei,
    sie steht hier nicht mit drin."""
    qr = segno.make_qr(inhalt, error="q", boost_error=False)
    zeilen = [list(z) for z in qr.matrix_iter(border=0)]
    n = len(zeilen)
    m = groesse / n
    teile = []
    for r, zeile in enumerate(zeilen):
        c = 0
        while c < n:
            if zeile[c]:
                anfang = c
                while c < n and zeile[c]:
                    c += 1
                breite = (c - anfang) * m
                teile.append("M%.3f %.3fh%.3fv%.3fh-%.3fz"
                             % (x + anfang * m, y + r * m, breite, m, breite))
            else:
                c += 1
    return '<path fill="#000" d="%s"/>' % "".join(teile), qr.version, n, m


def marke_pfad():
    """Der Pfad der Bildmarke aus brand/ - dort ist er gepflegt."""
    text = io.open(MARKE, encoding="utf-8").read()
    return re.search(r'<path[^>]*\sd="([^"]+)"', text, re.S).group(1)


def text(x, y, inhalt, groesse, farbe=DUNKEL, gewicht=400, anker="middle"):
    return ('<text x="%.2f" y="%.2f" font-family="%s" font-size="%.2f" '
            'font-weight="%d" fill="%s" text-anchor="%s">%s</text>'
            % (x, y, SCHRIFT, groesse, gewicht, farbe, anker, inhalt))


def ziffer(x, y, n):
    return ('<circle cx="%.2f" cy="%.2f" r="2.3" fill="%s"/>' % (x, y, TUERKIS) +
            text(x, y + 1.05, str(n), 3.0, "#ffffff", 700))


def aufkleber(netz, ip, name):
    # Drei Codes, in der Reihenfolge, in der man sie braucht. Code 1 und 2
    # sind der erste Start: erst ins Netz, dann die Seite. Auf dem iPhone
    # oeffnet die Anmeldeseite die Wasserwaage schon nach Code 1 von selbst;
    # Android (Samsung) tut das nicht verlaesslich, dafuer Code 2. Code 3 ist
    # das Heim-WLAN.
    #
    # Kein "ohne Passwort" in den Beschriftungen: Das las sich wie das
    # Einbinden ins Heim-WLAN, und dort gibt man sehr wohl eines ein.
    codes = [
        (helpers.make_wifi_data(ssid=netz, password=None, security="nopass"),
         "Handy verbinden", "Connect your phone", "Netz %s" % netz),
        ("http://%s/" % ip,
         "Wasserwaage öffnen", "Open the level", ip),
        ("http://%s.local/" % name,
         "Im Heim-WLAN", "On your home Wi-Fi", "%s.local" % name),
    ]
    unten = QR_OBEN + QR_GROESSE

    teile = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="%gmm" height="%gmm" '
        'viewBox="0 0 %g %g">' % (BREITE, HOEHE, BREITE, HOEHE),
        "<!-- Erzeugt von tools/qr_aufkleber.py - NICHT von Hand aendern.",
    ]
    teile += ["     Code %d: %s" % (i + 1, c[0]) for i, c in enumerate(codes)]
    teile[-1] += " -->"
    teile += [
        # Schnittkante, hell: Sie zeigt, wo der Aufkleber endet, und stoert
        # auf dem Etikett nicht, falls der Drucker sie mitdruckt.
        '<rect x="0.25" y="0.25" width="%g" height="%g" rx="3" fill="#fff" '
        'stroke="#c9d1da" stroke-width="0.3"/>' % (BREITE - 0.5, HOEHE - 0.5),
        '<g transform="translate(4 0.4) scale(0.08)"><path fill="%s" '
        'fill-rule="evenodd" d="%s"/></g>' % (TUERKIS, marke_pfad()),
        '<text x="13.5" y="6.3" font-family="%s" font-size="3.6" font-weight="600" '
        'letter-spacing="0.2" fill="%s">CAMPER<tspan fill="%s">MINDER</tspan>'
        '<tspan fill="%s" font-weight="400"> LEVEL</tspan></text>'
        % (SCHRIFT, DUNKEL, TUERKIS, GRAU),
    ]
    module = []
    for i, (inhalt, fett, englisch, detail) in enumerate(codes):
        mitte = SPALTEN[i]
        pfad, version, n, m = qr_pfad(inhalt, mitte - QR_GROESSE / 2, QR_OBEN, QR_GROESSE)
        module.append(m)
        teile += [
            ziffer(mitte, ZIFFER_Y, i + 1),
            pfad,
            text(mitte, unten + 5.1, fett, 2.7, DUNKEL, 700),
            text(mitte, unten + 8.3, englisch, 2.3, GRAU),
            text(mitte, unten + 11.6, detail, 2.1, DUNKEL),
        ]
        print("Code %d  %-36s Version %d, %d Module, %.2f mm je Modul"
              % (i + 1, inhalt, version, n, m))
    teile.append("</svg>")

    # Ruhezone pruefen statt hoffen: vier Module frei um jeden Code.
    ruhe = min(module) * 4
    links = SPALTEN[0] - QR_GROESSE / 2
    abstaende = {
        "links": links,
        "rechts": BREITE - (SPALTEN[-1] + QR_GROESSE / 2),
        "zwischen den Codes": min(SPALTEN[i + 1] - SPALTEN[i] for i in range(2)) - QR_GROESSE,
        "ueber den Codes": QR_OBEN - (ZIFFER_Y + 2.3),
        "unter den Codes": (unten + 5.1 - 2.7 * 0.72) - unten,
    }
    zu_eng = [k for k, v in abstaende.items() if v < ruhe]
    if zu_eng:
        sys.exit("Ruhezone (%.1f mm) zu knapp: %s" % (ruhe, ", ".join(zu_eng)))
    return "\n".join(teile) + "\n"


def pdf(svg):
    # Eine alte Druckvorlage darf nicht stehenbleiben und als neue gelten.
    if os.path.exists(ZIEL_PDF):
        os.remove(ZIEL_PDF)
    edge = next((p for p in EDGE if os.path.exists(p)), None)
    if not edge:
        print("Edge nicht gefunden - kein PDF, nur das SVG.")
        return False
    with tempfile.TemporaryDirectory() as tmp:
        seite = os.path.join(tmp, "aufkleber.html")
        io.open(seite, "w", encoding="utf-8").write(
            '<!doctype html><html><head><meta charset="utf-8"><style>'
            "@page{size:%gmm %gmm;margin:0}html,body{margin:0}"
            "svg{display:block;width:%gmm;height:%gmm}</style></head><body>%s"
            "</body></html>" % (BREITE, HOEHE, BREITE, HOEHE, svg))
        # Eigenes Profil: Ein laufendes Edge des Nutzers bleibt unberuehrt.
        profil = os.path.join(tmp, "profil")
        subprocess.run([edge, "--headless=new", "--disable-gpu",
                        "--no-pdf-header-footer", "--user-data-dir=" + profil,
                        "--print-to-pdf=" + ZIEL_PDF, "file:///" + seite.replace("\\", "/")],
                       capture_output=True, timeout=120)
    return os.path.exists(ZIEL_PDF)


def main():
    netz, ip, name = aus_geraetedatei()
    svg = aufkleber(netz, ip, name)
    os.makedirs(os.path.dirname(ZIEL_SVG), exist_ok=True)
    io.open(ZIEL_SVG, "w", encoding="utf-8", newline="\n").write(svg)
    print("geschrieben: %s" % os.path.relpath(ZIEL_SVG, WURZEL))
    if pdf(svg):
        print("geschrieben: %s" % os.path.relpath(ZIEL_PDF, WURZEL))
    return 0


if __name__ == "__main__":
    sys.exit(main())
