"""Das Passwort des geraeteeigenen Netzes aus einer MAC-Adresse errechnen.

    python tools/netzpasswort.py A0:B7:65:12:34:56

Wofuer: Der Aufkleber. Ein Geraet MIT Display zeigt sein Passwort selbst an,
eines ohne nicht - und beim Bestuecken der Aufkleber will man es ohnehin
vorher wissen, nicht erst beim Einschalten.

Die MAC-Adresse nennt esptool beim Aufspielen ("MAC: a0:b7:65:..."), und die
Firmware schreibt sie samt Passwort in ihr Log.

DIESE RECHNUNG MUSS ZEICHENGLEICH ZU DER IN hardware.yaml BLEIBEN. Weicht eine
der beiden ab, druckt der Aufkleber etwas anderes, als das Geraet erwartet -
und das faellt erst auf, wenn ein Kunde davorsteht. Aendert sich hier etwas,
gehoert die Aenderung in beide Dateien.
"""

from __future__ import annotations

import os
import re
import sys

# Ohne verwechselbare Zeichen: kein O gegen 0, kein I gegen 1, kein S gegen 5,
# kein B gegen 8. Wer das vom Aufkleber abtippt, soll nicht raten muessen.
ZEICHEN = "ACDEFGHJKLMNPQRTUVWXY34679"
LAENGE = 10

MASKE64 = (1 << 64) - 1
FNV_START = 14695981039346656037
FNV_PRIM = 1099511628211


def _einruehren(h: int, text: str) -> int:
    """FNV-1a ueber die Bytes - dasselbe wie die Lambda in hardware.yaml."""
    for b in text.encode("ascii"):
        h = ((h ^ b) * FNV_PRIM) & MASKE64
    return h


def passwort(salt: str, mac: str) -> str:
    """Aus geheimer Zutat und MAC-Adresse.

    Die MAC geht in derselben Schreibweise ein, die ESPHomes
    get_mac_address() liefert: zwoelf Kleinbuchstaben ohne Trenner.
    """
    sauber = re.sub(r"[^0-9a-fA-F]", "", mac).lower()
    if len(sauber) != 12:
        raise ValueError("MAC-Adresse braucht 12 Hexziffern, gelesen: %r" % mac)

    h = _einruehren(_einruehren(FNV_START, salt), sauber)

    aus = []
    for _ in range(LAENGE):
        # xorshift64, Schritt fuer Schritt wie im Geraet
        h ^= (h << 13) & MASKE64
        h ^= h >> 7
        h ^= (h << 17) & MASKE64
        h &= MASKE64
        aus.append(ZEICHEN[h % len(ZEICHEN)])
    return "".join(aus)


def _salt_aus_secrets() -> str:
    """Die Zutat aus esphome/level/secrets.yaml holen.

    Bewusst mit einem Muster statt mit einem YAML-Leser: Diese eine Zeile
    rechtfertigt keine Abhaengigkeit, und das Werkzeug soll auch dann laufen,
    wenn nur Python da ist.
    """
    hier = os.path.dirname(os.path.abspath(__file__))
    pfad = os.path.join(hier, os.pardir, "esphome", "level", "secrets.yaml")
    if not os.path.exists(pfad):
        raise SystemExit(
            "Nicht gefunden: %s\n"
            "Ohne die geheime Zutat laesst sich das Passwort nicht errechnen."
            % os.path.normpath(pfad)
        )
    with open(pfad, encoding="utf-8") as fh:
        treffer = re.search(
            r'(?m)^\s*camperminder_ap_salt\s*:\s*"?([^"\r\n]+)"?\s*$', fh.read()
        )
    if not treffer:
        raise SystemExit("camperminder_ap_salt fehlt in secrets.yaml.")
    return treffer.group(1)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.strip().splitlines()[2].strip())
        print()
        print("Beispiel:  python tools/netzpasswort.py A0:B7:65:12:34:56")
        return 2

    salt = _salt_aus_secrets()
    mac = argv[1]
    try:
        pw = passwort(salt, mac)
    except ValueError as fehler:
        # Klartext statt Stapelabzug: Wer Aufkleber druckt, hat sich vertippt
        # und braucht keinen Python-Auszug, sondern den Hinweis darauf.
        print("Fehler: %s" % fehler)
        print("Erwartet werden 12 Hexziffern, Trenner sind egal:")
        print("  A0:B7:65:12:34:56   a0-b7-65-12-34-56   a0b765123456")
        return 1
    print()
    print("  Geraet (MAC) : %s" % mac.lower())
    print("  Netz         : CamperMinder")
    print("  Passwort     : %s" % pw)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
