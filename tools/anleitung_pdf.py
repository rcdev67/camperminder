"""Erzeugt die Kunden-Anleitung aus docs/kundenanleitung/anleitung.html.

Schritt 1: Alle Bilder werden als data-URI in die HTML eingebettet, so dass
           CamperMinder-Level-Anleitung.html allein lesbar ist.
Schritt 2: Edge (headless) druckt daraus CamperMinder-Level-Anleitung.pdf.
Beide Ergebnisdateien sind erzeugt und werden nicht von Hand geaendert.
"""
import base64
import io
import os
import re
import subprocess
import sys

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORDNER = os.path.join(WURZEL, "docs", "kundenanleitung")
QUELLE = os.path.join(ORDNER, "anleitung.html")
HTML = os.path.join(ORDNER, "CamperMinder-Level-Anleitung.html")
PDF = os.path.join(ORDNER, "CamperMinder-Level-Anleitung.pdf")
EDGE = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"]
TYPEN = {".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg"}


def einbetten(treffer):
    anf = treffer.group(1)
    pfad = os.path.normpath(os.path.join(ORDNER, treffer.group(2)))
    typ = TYPEN[os.path.splitext(pfad)[1].lower()]
    with open(pfad, "rb") as f:
        daten = base64.b64encode(f.read()).decode("ascii")
    return "src=%sdata:%s;base64,%s%s" % (anf, typ, daten, anf)


def main():
    with io.open(QUELLE, encoding="utf-8", newline="") as f:
        text = f.read()
    text = re.sub(r"""src=(["'])(?!data:)([^"']+\.(?:svg|png|jpg))\1""", einbetten, text)
    with io.open(HTML, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    edge = next((e for e in EDGE if os.path.exists(e)), None)
    if not edge:
        sys.exit("Edge nicht gefunden - HTML ist erzeugt, PDF fehlt.")
    subprocess.run([edge, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    "--print-to-pdf=" + PDF, "file:///" + HTML.replace("\\", "/")],
                   check=True, stderr=subprocess.DEVNULL)
    print(HTML)
    print(PDF)


if __name__ == "__main__":
    main()
