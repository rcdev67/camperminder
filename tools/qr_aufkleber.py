# -*- coding: utf-8 -*-
"""Erzeugt den QR-Aufkleber fuer das Geraet.

WARUM ES IHN GIBT
=================
Der Massstab ist ein Bluetooth-Geraet mit App: auspacken, koppeln, fertig.
Unsere WLAN-Loesung verlangt, eine Adresse zu tippen - und nach dem Einbinden
ins Heim-WLAN eine andere. Der Aufkleber nimmt beides ab, je Lage ein Code:

    Code 1   http://192.168.4.1/              Handy im Netz CamperMinder:
                                              erster Start, unterwegs
    Code 2   http://camperminder-level.local/ Geraet im Heim-WLAN

Nach Lage und nicht nach Handgriff, entschieden am 28.09.2026. Ein erster
Entwurf hatte als Code 1 den Beitritt zum Netz (WIFI:...) und als Code 2
192.168.4.1 - das bildete den Weg in zwei Codes ab, die man immer
hintereinander braucht, und liess den Kunden im Heim-WLAN ohne Hilfe. Das
Handy verbindet sich jetzt von Hand mit dem Netz CamperMinder, wie mit jedem
WLAN.

Code 2 geht ueber mDNS (<Name>.local), weil die Adresse im Heim-WLAN in
jedem Haushalt eine andere ist - der Name ist der einzige feste Weg. Auf
dem iPhone traegt er, auf Android nicht auf jedem Geraet; fuer diesen Fall
nennt die Anleitung die Suche der Geraeteseite und den Router.

Beide Codes sind fuer JEDES Geraet gleich: Adresse und Name haengen an der
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
                                    80 x 50 mm - zum Drucken bei 100 %

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
except ImportError:
    sys.exit("segno fehlt:  py -3 -m pip install segno")

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GERAET = os.path.join(WURZEL, "esphome", "level", "camperminder-level.yaml")
MARKE = os.path.join(WURZEL, "brand", "camperminder-mark.svg")
ZIEL_SVG = os.path.join(WURZEL, "docs", "bilder", "aufkleber-qr.svg")
ZIEL_PDF = os.path.join(WURZEL, "docs", "bilder", "aufkleber-qr.pdf")

BREITE, HOEHE = 80.0, 50.0      # mm
QR_GROESSE = 22.0               # mm - bei 3 m Leseabstand der Kamera reichlich
ZIFFER1_X = 5.2                 # mm - Mitte der Ziffer 1, vor der Ruhezone von Code 1
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
    # Ohne mDNS gibt es kein <Name>.local, und Code 2 liefe ins Leere.
    if re.search(r"^mdns:\s*\n\s+disabled:\s*true", text, re.MULTILINE):
        sys.exit("mDNS ist in der Geraetedatei abgeschaltet - Code 2 wuerde nicht tragen.")
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
    unterwegs = "http://%s/" % ip
    zuhause = "http://%s.local/" % name

    oben = 11.5
    links, rechts = 11.0, 51.0
    qr1, v1, n1, m1 = qr_pfad(unterwegs, links, oben, QR_GROESSE)
    qr2, v2, n2, m2 = qr_pfad(zuhause, rechts, oben, QR_GROESSE)
    mitte1, mitte2 = links + QR_GROESSE / 2, rechts + QR_GROESSE / 2
    unten = oben + QR_GROESSE

    teile = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="%gmm" height="%gmm" '
        'viewBox="0 0 %g %g">' % (BREITE, HOEHE, BREITE, HOEHE),
        "<!-- Erzeugt von tools/qr_aufkleber.py - NICHT von Hand aendern.",
        "     Code 1: %s" % unterwegs,
        "     Code 2: %s -->" % zuhause,
        # Schnittkante, hell: Sie zeigt, wo der Aufkleber endet, und stoert
        # auf dem Etikett nicht, falls der Drucker sie mitdruckt.
        '<rect x="0.25" y="0.25" width="%g" height="%g" rx="3" fill="#fff" '
        'stroke="#c9d1da" stroke-width="0.3"/>' % (BREITE - 0.5, HOEHE - 0.5),
        '<g transform="translate(4 1.2) scale(0.09)"><path fill="%s" '
        'fill-rule="evenodd" d="%s"/></g>' % (TUERKIS, marke_pfad()),
        '<text x="14.5" y="7.4" font-family="%s" font-size="4" font-weight="600" '
        'letter-spacing="0.2" fill="%s">CAMPER<tspan fill="%s">MINDER</tspan>'
        '<tspan fill="%s" font-weight="400"> LEVEL</tspan></text>'
        % (SCHRIFT, DUNKEL, TUERKIS, GRAU),
        qr1, qr2,
        ziffer(ZIFFER1_X, oben + QR_GROESSE / 2, 1),
        ziffer(45.5, oben + QR_GROESSE / 2, 2),
        # Kein "ohne Passwort": Das las sich wie das Einbinden ins
        # Heim-WLAN, und dort gibt man sehr wohl eines ein. Ein Passwort des
        # eigenen Netzes ist ohnehin freiwillig und kann gesetzt sein.
        text(mitte1, unten + 5.3, "Handy verbinden", 3.1, DUNKEL, 700),
        text(mitte1, unten + 8.7, "Connect your phone", 2.5, GRAU),
        text(mitte1, unten + 12.5, "Netz %s · %s" % (netz, ip), 2.3, DUNKEL),
        text(mitte2, unten + 5.3, "Im Heim-WLAN", 3.1, DUNKEL, 700),
        text(mitte2, unten + 8.7, "On your home Wi-Fi", 2.5, GRAU),
        text(mitte2, unten + 12.5, "%s.local" % name, 2.3, DUNKEL),
        "</svg>",
    ]
    ruhe = min(m1, m2) * 4
    # Ruhezone pruefen statt hoffen: vier Module frei um jeden Code.
    abstaende = {
        "Code 1 oben": oben - 8.2,          # Unterkante der Bildmarke
        "Code 1 links": links - (ZIFFER1_X + 2.3),
        "zwischen den Codes": rechts - (links + QR_GROESSE),
        "Code 2 links": rechts - (45.5 + 2.3),
        "Code 2 rechts": BREITE - (rechts + QR_GROESSE),
        "unter den Codes": (unten + 5.3 - 3.1 * 0.72) - unten,
    }
    zu_eng = [k for k, v in abstaende.items() if v < ruhe]
    if zu_eng:
        sys.exit("Ruhezone (%.1f mm) zu knapp: %s" % (ruhe, ", ".join(zu_eng)))
    print("Code 1  %-36s Version %d, %d Module, %.2f mm je Modul" % (unterwegs, v1, n1, m1))
    print("Code 2  %-36s Version %d, %d Module, %.2f mm je Modul" % (zuhause, v2, n2, m2))
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
