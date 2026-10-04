"""Erzeugt die Kunden-Anleitungen aus docs/kundenanleitung/, deutsch und englisch.

Je Fassung ein Paar aus Quelle und Ergebnissen (Liste FASSUNGEN):

    anleitung.html  ->  CamperMinder-Level-Anleitung.html / .pdf   (deutsch)
    manual.html     ->  CamperMinder-Level-Manual.html / .pdf      (englisch)

Schritt 1: Alle Bilder werden als data-URI in die HTML eingebettet, so dass
           die Ergebnis-HTML allein lesbar ist.
Schritt 2: Edge (headless) druckt daraus die PDF.
Alle Ergebnisdateien sind erzeugt und werden nicht von Hand geaendert. Die
englische Fassung ist eine Uebersetzung der deutschen: gleicher Aufbau, gleiche
Grafiken. Wer die deutsche aendert, zieht die englische nach.
"""
import base64
import io
import os
import re
import subprocess
import sys

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORDNER = os.path.join(WURZEL, "docs", "kundenanleitung")
# (Quelle, erzeugte HTML, erzeugte PDF) - alle im Ordner der Kundenanleitung
FASSUNGEN = [
    ("anleitung.html", "CamperMinder-Level-Anleitung.html", "CamperMinder-Level-Anleitung.pdf"),
    ("manual.html", "CamperMinder-Level-Manual.html", "CamperMinder-Level-Manual.pdf"),
]
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
    edge = next((e for e in EDGE if os.path.exists(e)), None)
    fehlt = []
    for quelle, html_name, pdf_name in FASSUNGEN:
        html = os.path.join(ORDNER, html_name)
        pdf = os.path.join(ORDNER, pdf_name)
        with io.open(os.path.join(ORDNER, quelle), encoding="utf-8", newline="") as f:
            text = f.read()
        text = re.sub(r"""src=(["'])(?!data:)([^"']+\.(?:svg|png|jpg))\1""", einbetten, text)
        with io.open(html, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        print(html)
        if not edge:
            fehlt.append(pdf_name)
            continue
        subprocess.run([edge, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                        "--print-to-pdf=" + pdf, "file:///" + html.replace("\\", "/")],
                       check=True, stderr=subprocess.DEVNULL)
        print(pdf)
    if fehlt:
        sys.exit("Edge nicht gefunden - HTML ist erzeugt, PDF fehlt: " + ", ".join(fehlt))


if __name__ == "__main__":
    main()
