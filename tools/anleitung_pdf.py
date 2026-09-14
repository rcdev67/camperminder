"""Macht aus docs/anleitung-prototyp.md ein druckfertiges PDF fuer die Tester.

Aufruf:  .venv\\Scripts\\python.exe tools\\anleitung_pdf.py
         (ueblich per Doppelklick auf tools\\anleitung-drucken.cmd)

Ergebnis:  druck\\CamperMinder-Level-Anleitung.pdf

WARUM ES DAS GIBT: Eine .md-Datei laesst sich ohne Zusatzprogramm weder
vernuenftig oeffnen noch ausdrucken. Die Anleitung soll aber in genau EINER
Fassung gepflegt werden - im Repository, wo sie neben der Firmware steht, zu
der sie gehoert. Das PDF wird daraus erzeugt und nie von Hand bearbeitet.

DER API-SCHLUESSEL: Ist esphome/level/secrets.yaml vorhanden, traegt dieses
Skript den Schluessel ins PDF ein - oben in "Auf einen Blick" und in
Abschnitt 11 zusaetzlich als QR-Code. Damit braucht es keinen Aufkleber.
In der .md-Datei steht er NIE; dort markieren zwei HTML-Kommentare die
Stellen, die GitHub nicht anzeigt.

Deshalb gehoert das PDF auch nicht ins Repository: Der Ordner druck/ ist
durch .gitignore ausgeschlossen. Weitergeben ja, veroeffentlichen nein.

Umgewandelt wird mit Python-Markdown, gedruckt mit Edge oder Chrome im
Hintergrund - beides ist auf einem Windows-Rechner ohnehin vorhanden bzw.
wird von anleitung-drucken.cmd nachgezogen.
"""
import base64
import html
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

import markdown
import qrcode
import qrcode.image.svg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUELLE = os.path.join(ROOT, "docs", "anleitung-prototyp.md")
SECRETS = os.path.join(ROOT, "esphome", "level", "secrets.yaml")
LOGO = os.path.join(ROOT, "brand", "camperminder-wordmark-light.png")
ZIEL_ORDNER = os.path.join(ROOT, "druck")
ZIEL = os.path.join(ZIEL_ORDNER, "CamperMinder-Level-Anleitung.pdf")

BROWSER = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def api_schluessel():
    """Der Schluessel aus der secrets.yaml - oder None, mit Begruendung."""
    if not os.path.isfile(SECRETS):
        return None, "esphome\\level\\secrets.yaml fehlt"
    text = io.open(SECRETS, encoding="utf-8").read()
    m = re.search(r'^\s*camperminder_api_key\s*:\s*["\']?([A-Za-z0-9+/=]+)["\']?\s*$',
                  text, re.M)
    if not m:
        return None, "kein camperminder_api_key in der secrets.yaml"
    key = m.group(1)
    # Ein ESPHome-Schluessel sind genau 32 Bytes in Base64. Alles andere ist
    # der Platzhalter aus der Vorlage oder ein Tippfehler - und ein falscher
    # Schluessel auf Papier ist schlimmer als keiner.
    try:
        if len(base64.b64decode(key, validate=True)) != 32:
            raise ValueError
    except ValueError:
        return None, "camperminder_api_key ist kein gueltiger 32-Byte-Schluessel"
    return key, ""


def github_slug(text):
    """Anker wie bei GitHub, damit die Links im Inhaltsverzeichnis in BEIDEN
    Fassungen stimmen: klein, Satzzeichen weg, Leerzeichen zu Bindestrichen,
    Umlaute bleiben."""
    text = re.sub(r"<[^>]+>", "", text).strip().lower()
    text = re.sub(r"[^\w\- ]", "", text, flags=re.U)
    return text.replace(" ", "-")


def qr_svg(daten):
    bild = qrcode.make(daten, image_factory=qrcode.image.svg.SvgPathImage,
                       box_size=10, border=2)
    svg = bild.to_string(encoding="unicode")
    # Feste Druckgroesse statt der Pixelangabe der Bibliothek.
    return re.sub(r'<svg ([^>]*?)width="[^"]*" height="[^"]*"',
                  r'<svg \1width="34mm" height="34mm"', svg, count=1)


def einsetzen(md, key):
    if key:
        kurz = ('<code class="schluessel">%s</code><br>'
                '<span class="klein">QR-Code zum Abscannen in Abschnitt 11</span>' % key)
        kasten = (
            '<div class="kasten">'
            '<div class="kasten-text">'
            '<div class="kasten-titel">Dein API-Schlüssel</div>'
            '<code class="schluessel gross">%s</code>'
            '<p>Mit der Handykamera den QR-Code scannen, den Text kopieren und in '
            'Home Assistant ins Feld <b>Verschlüsselungsschlüssel</b> einfügen.</p>'
            '</div>'
            '<div class="qr">%s</div>'
            '</div>' % (key, qr_svg(key)))
    else:
        kurz = "liegt dem Gerät bei"
        kasten = ""
    md = re.sub(r"<!--API-->.*?<!--/API-->", lambda _: kurz, md, count=1)
    md = md.replace("<!--API-KASTEN-->", kasten)
    return md


CSS = """
@page {
  size: A4;
  margin: 16mm 16mm 18mm 16mm;
  @bottom-left { content: "CamperMinder Level – Anleitung für Testgeräte";
                 font: 8pt 'Segoe UI', Arial, sans-serif; color: #777; }
  @bottom-right { content: "Seite " counter(page) " von " counter(pages);
                  font: 8pt 'Segoe UI', Arial, sans-serif; color: #777; }
}
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font: 10pt/1.45 'Segoe UI', Arial, sans-serif; color: #1d2327; margin: 0; }
.logo { width: 62mm; margin: 0 0 4mm; }
h1 { font-size: 20pt; margin: 0 0 3mm; color: #12343b; }
h2 { font-size: 14pt; color: #12343b; border-bottom: 2px solid #2fb6c9;
     padding-bottom: 1mm; margin: 8mm 0 3mm; break-after: avoid; }
h3 { font-size: 11pt; color: #12343b; margin: 5mm 0 2mm; break-after: avoid; }
p, li { orphans: 3; widows: 3; }
ul, ol { padding-left: 6mm; }
li { margin: 0.8mm 0; }
a { color: #137c8b; text-decoration: none; }
code { font-family: Consolas, 'Courier New', monospace; font-size: 9pt;
       background: #eef3f4; padding: 0 1mm; border-radius: 1mm; }
pre { background: #eef3f4; padding: 2.5mm 3mm; border-radius: 1.5mm;
      font-size: 7.6pt; line-height: 1.35; white-space: pre-wrap; break-inside: avoid; }
pre code { background: none; padding: 0; font-size: inherit; }
table { border-collapse: collapse; width: 100%; margin: 2mm 0 3mm; font-size: 9.3pt; }
th, td { border: 0.3mm solid #c9d4d6; padding: 1.4mm 2mm; text-align: left; vertical-align: top; }
th { background: #e3f4f6; }
tr { break-inside: avoid; }
thead th:empty { display: none; }
blockquote { margin: 3mm 0; padding: 2mm 3.5mm; background: #fff7e6;
             border-left: 1.2mm solid #f0a020; border-radius: 1mm; break-inside: avoid; }
blockquote p { margin: 1mm 0; }
hr { border: 0; margin: 0; }
.klein { font-size: 8pt; color: #555; }
code.schluessel { font-size: 10pt; background: #fff; border: 0.3mm solid #2fb6c9;
                  padding: 0.5mm 1.5mm; letter-spacing: 0.02em; word-break: break-all; }
code.schluessel.gross { font-size: 11.5pt; display: inline-block; margin: 1mm 0 2mm; }
.kasten { display: flex; gap: 5mm; align-items: center; border: 0.6mm solid #2fb6c9;
          border-radius: 2mm; padding: 3.5mm 4mm; margin: 3mm 0; background: #f2fbfc;
          break-inside: avoid; }
.kasten-text { flex: 1; }
.kasten-titel { font-weight: 700; font-size: 11pt; color: #12343b; }
.kasten p { margin: 1mm 0 0; font-size: 9pt; }
.qr svg { display: block; background: #fff; }
.hinweis-druck { font-size: 8.5pt; color: #666; border-top: 0.3mm solid #ccc;
                 margin-top: 8mm; padding-top: 2mm; }
"""


def main():
    key, grund = api_schluessel()
    md = io.open(QUELLE, encoding="utf-8").read()
    md = einsetzen(md, key)

    wandler = markdown.Markdown(
        extensions=["tables", "fenced_code", "sane_lists", "toc"],
        extension_configs={"toc": {"slugify": lambda t, sep: github_slug(t)}})
    rumpf = wandler.convert(md)

    logo = ""
    if os.path.isfile(LOGO):
        with open(LOGO, "rb") as fh:
            logo = ('<img class="logo" alt="CamperMinder" src="data:image/png;base64,%s">'
                    % base64.b64encode(fh.read()).decode("ascii"))

    fuss = ('<div class="hinweis-druck">Erzeugt aus docs/anleitung-prototyp.md. '
            'Diese Fassung enthält den API-Schlüssel der Testgeräte – bitte an '
            'Tester weitergeben, aber nicht öffentlich ins Netz stellen.</div>'
            if key else "")

    seite = ('<!doctype html><html lang="de"><head><meta charset="utf-8">'
             '<title>CamperMinder Level – Anleitung für Testgeräte</title>'
             '<style>%s</style></head><body>%s%s%s</body></html>'
             % (CSS, logo, rumpf, fuss))

    browser = next((b for b in BROWSER if os.path.isfile(b)), None)
    if not browser:
        sys.exit("FEHLER: Weder Edge noch Chrome gefunden - damit wird gedruckt.")

    os.makedirs(ZIEL_ORDNER, exist_ok=True)
    arbeit = tempfile.mkdtemp(prefix="cm-anleitung-")
    try:
        html_datei = os.path.join(arbeit, "anleitung.html")
        io.open(html_datei, "w", encoding="utf-8").write(seite)
        # Eigenes Profilverzeichnis: Laeuft der Browser schon, haengte sich
        # der Aufruf sonst an das offene Fenster und druckte nichts.
        profil = os.path.join(arbeit, "profil")
        if os.path.exists(ZIEL):
            os.remove(ZIEL)
        subprocess.run([browser, "--headless=new", "--disable-gpu",
                        "--no-first-run", "--user-data-dir=" + profil,
                        "--no-pdf-header-footer",
                        "--print-to-pdf=" + ZIEL,
                        "file:///" + html_datei.replace("\\", "/")],
                       check=False, capture_output=True, timeout=120)
    finally:
        shutil.rmtree(arbeit, ignore_errors=True)

    if not os.path.isfile(ZIEL) or os.path.getsize(ZIEL) < 10000:
        sys.exit("FEHLER: Das PDF wurde nicht erzeugt.")

    print("PDF erzeugt: " + ZIEL)
    if key:
        print("Der API-Schluessel ist eingetragen. Weitergeben ja, veroeffentlichen nein.")
    else:
        print("OHNE API-Schluessel (%s) - dort steht 'liegt dem Geraet bei'." % grund)


if __name__ == "__main__":
    main()
