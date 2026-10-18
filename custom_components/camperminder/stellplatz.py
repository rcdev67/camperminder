"""Stellplatz: Sonne, Satellit und Starlink im Verhältnis zum Fahrzeug.

Was beim Abstellen zählt, hängt an der Himmelsrichtung des Fahrzeugs:
Liegt die Markise am Nachmittag in der Sonne? Bekommt das Lüftungsgitter
des Absorberkühlschranks die Mittagssonne ab (dann kühlt er schlechter)?
Wohin muss die Satellitenschüssel, und steht dort der Baum? Wo ist Norden,
wohin Starlink freie Sicht braucht?

Level misst Neigung, aber keine Himmelsrichtung - einen Kompass hat die
Platine nicht. Die Richtung trägt der Nutzer deshalb selbst ein ("Front
zeigt nach"), am bequemsten mit den Drehknöpfen in der Karte. Den Ort nimmt
die Rechnung aus dem Heimatort von Home Assistant, der dem Fahrzeug folgen
kann (heimatort.py).

Alles hier rechnet ohne Home Assistant, damit es sich an bekannten Werten
prüfen lässt.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, tzinfo

# --- Satelliten ----------------------------------------------------------------
# Position über dem Äquator, Längengrad Ost. Die Schlüssel sind die Optionen
# des Auswahlfelds, die Namen stehen im Satz.
SATELLITEN: dict[str, tuple[str, float]] = {
    "astra_19_2": ("Astra 19,2° Ost", 19.2),
    "hotbird_13": ("Hotbird 13° Ost", 13.0),
    "astra_23_5": ("Astra 23,5° Ost", 23.5),
    "astra_28_2": ("Astra 28,2° Ost", 28.2),
}
SATELLIT_VORGABE = "astra_19_2"

# Fahrzeugseiten. "keine" heißt: nicht angegeben.
SEITE_RECHTS = "rechts"
SEITE_LINKS = "links"
SEITE_KEINE = "keine"
SEITEN = [SEITE_RECHTS, SEITE_LINKS, SEITE_KEINE]

# Eine Seite liegt in der Sonne, wenn die Sonne höher als 3° steht und nicht
# mehr als 70° von der Richtung abweicht, in die die Seite schaut. Streiflicht
# darüber hinaus wärmt eine Wand kaum.
SONNE_MIN_HOEHE = 3.0
SONNE_MAX_WINKEL = 70.0
# Abtastung des Tages für die Sonnenzeiten.
TAKT_MINUTEN = 10

HIMMELSRICHTUNGEN = (
    "Nord", "Nordnordost", "Nordost", "Ostnordost",
    "Ost", "Ostsüdost", "Südost", "Südsüdost",
    "Süd", "Südsüdwest", "Südwest", "Westsüdwest",
    "West", "Westnordwest", "Nordwest", "Nordnordwest",
)
KURZ = (
    "N", "NNO", "NO", "ONO", "O", "OSO", "SO", "SSO",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
)


def himmelsrichtung(azimut: float) -> str:
    return HIMMELSRICHTUNGEN[round((azimut % 360) / 22.5) % 16]


def himmelsrichtung_kurz(azimut: float) -> str:
    return KURZ[round((azimut % 360) / 22.5) % 16]


def vom_fahrzeug(azimut: float, front: float) -> str:
    """Wo eine Himmelsrichtung vom Fahrzeug aus liegt, in acht Stufen."""
    relativ = (azimut - front) % 360
    stufen = ("vorne", "rechts vorne", "rechts", "rechts hinten",
              "hinten", "links hinten", "links", "links vorne")
    return stufen[round(relativ / 45) % 8]


def relativ(azimut: float, front: float) -> float:
    """Winkel vom Fahrzeug aus: 0 vorne, positiv nach rechts, -180 bis 180."""
    return round(((azimut - front + 180) % 360) - 180, 1)


def vom_fahrzeug_genau(azimut: float, front: float) -> str:
    """Wo eine Richtung vom Fahrzeug aus liegt, auf das Grad.

    Für die Schüssel reichen acht Stufen nicht: "rechts vorne" sind 45° - so
    findet niemand den Satelliten. "17° links von vorne" lässt sich mit dem
    Arm abschätzen und an der Schüssel einstellen.
    """
    r = relativ(azimut, front)
    seite = "rechts" if r > 0 else "links"
    b = abs(r)
    if b <= 2:
        return "genau vorne"
    if b >= 178:
        return "genau hinten"
    if abs(b - 90) <= 2:
        return f"genau {seite}"
    if b < 90:
        return f"{round(b)}° {seite} von vorne"
    return f"{round(180 - b)}° {seite} von hinten"


def _winkelabstand(a: float, b: float) -> float:
    return abs((a - b + 180) % 360 - 180)


# --- Sonne -----------------------------------------------------------------------

def sonnenstand(zeit: datetime, breite: float, laenge: float) -> tuple[float, float]:
    """Azimut (0 = Nord, im Uhrzeigersinn) und Höhe der Sonne in Grad.

    Die vereinfachte Formel des Astronomical Almanac; auf ein halbes Grad
    genau, für eine Hauswand und eine Markise reichlich.
    """
    n = zeit.timestamp() / 86400.0 + 2440587.5 - 2451545.0
    mittlere_laenge = (280.460 + 0.9856474 * n) % 360
    anomalie = math.radians((357.528 + 0.9856003 * n) % 360)
    ekliptik_laenge = math.radians(
        mittlere_laenge + 1.915 * math.sin(anomalie) + 0.020 * math.sin(2 * anomalie)
    )
    schiefe = math.radians(23.439 - 0.0000004 * n)
    rektaszension = math.atan2(
        math.cos(schiefe) * math.sin(ekliptik_laenge), math.cos(ekliptik_laenge)
    )
    deklination = math.asin(math.sin(schiefe) * math.sin(ekliptik_laenge))
    sternzeit = (18.697374558 + 24.06570982441908 * n) % 24
    stundenwinkel = math.radians(sternzeit * 15 + laenge) - rektaszension

    phi = math.radians(breite)
    hoehe = math.asin(
        math.sin(phi) * math.sin(deklination)
        + math.cos(phi) * math.cos(deklination) * math.cos(stundenwinkel)
    )
    azimut = math.atan2(
        -math.sin(stundenwinkel),
        math.tan(deklination) * math.cos(phi) - math.sin(phi) * math.cos(stundenwinkel),
    )
    return math.degrees(azimut) % 360, math.degrees(hoehe)


# --- Satellit --------------------------------------------------------------------

def satellit_richtung(breite: float, laenge: float, satellit_laenge: float) -> tuple[float, float]:
    """Azimut und Höhe eines geostationären Satelliten in Grad.

    Für die Nordhalbkugel: Steht der Satellit östlich, zeigt die Schüssel
    südöstlich, steht er westlich, südwestlich.
    """
    phi = math.radians(breite)
    d = math.radians(((satellit_laenge - laenge) + 180) % 360 - 180)
    azimut = 180.0 - math.degrees(math.atan2(math.tan(d), math.sin(phi)))
    if breite < 0:
        azimut = math.degrees(math.atan2(math.tan(d), -math.sin(phi)))
    c = math.cos(d) * math.cos(phi)
    hoehe = math.degrees(math.atan2(c - 0.1512, math.sqrt(max(1e-12, 1 - c * c))))
    return azimut % 360, hoehe


# --- Zusammenfassung ---------------------------------------------------------------

@dataclass
class Stellplatz:
    """Alles, was Sensoren und Karte brauchen."""

    front: float | None
    sonne_azimut: float
    sonne_hoehe: float
    sonnenbahn: list[dict] = field(default_factory=list)
    sonnenzeiten: dict[str, list[str]] = field(default_factory=dict)
    satz_sonne: str = ""
    satellit: str = ""
    satellit_azimut: float = 0.0
    satellit_hoehe: float = 0.0
    # Vom Fahrzeug aus, 0 vorne, positiv nach rechts. None ohne Richtung.
    satellit_relativ: float | None = None
    satz_satellit: str = ""
    starlink_azimut: float = 0.0
    starlink_relativ: float | None = None
    satz_starlink: str = ""


def _zeitraeume(zeiten: list[datetime]) -> list[str]:
    """Aufeinanderfolgende Abtastzeiten zu "13:10–18:40" zusammenfassen."""
    raeume: list[str] = []
    beginn = vorher = None
    for t in zeiten:
        if beginn is None:
            beginn = vorher = t
            continue
        if t - vorher > timedelta(minutes=TAKT_MINUTEN):
            raeume.append(f"{beginn:%H:%M}–{vorher:%H:%M}")
            beginn = t
        vorher = t
    if beginn is not None:
        raeume.append(f"{beginn:%H:%M}–{vorher:%H:%M}")
    return raeume


def _seite_satz(name: str, seite: str, raeume: list[str], sonne_stoert: str = "") -> str:
    wo = f"{name} ({seite})"
    if not raeume:
        return f"{wo} bleibt heute im Schatten" + (" – gut so." if sonne_stoert else ".")
    return f"{wo} in der Sonne {', '.join(raeume)}" + (f" – {sonne_stoert}." if sonne_stoert else ".")


def berechne(
    jetzt: datetime,
    breite: float,
    laenge: float,
    zeitzone: tzinfo,
    *,
    front: float | None,
    markise: str = SEITE_RECHTS,
    kuehlschrank: str = SEITE_KEINE,
    satellit: str = SATELLIT_VORGABE,
) -> Stellplatz:
    sonne_az, sonne_h = sonnenstand(jetzt, breite, laenge)
    ergebnis = Stellplatz(front=front, sonne_azimut=round(sonne_az, 1), sonne_hoehe=round(sonne_h, 1))

    # Der heutige Tag in Ortszeit, in Schritten von zehn Minuten.
    lokal = jetzt.astimezone(zeitzone)
    mitternacht = lokal.replace(hour=0, minute=0, second=0, microsecond=0)
    seiten = (
        {"vorne": front, "rechts": front + 90, "hinten": front + 180, "links": front + 270}
        if front is not None else {}
    )
    besonnt: dict[str, list[datetime]] = {name: [] for name in seiten}
    for schritt in range(0, 24 * 60, TAKT_MINUTEN):
        t = mitternacht + timedelta(minutes=schritt)
        az, h = sonnenstand(t, breite, laenge)
        if h > 0 and t.minute == 0:
            ergebnis.sonnenbahn.append({"zeit": f"{t:%H}", "azimut": round(az, 1), "hoehe": round(h, 1)})
        if h < SONNE_MIN_HOEHE:
            continue
        for name, richtung in seiten.items():
            if _winkelabstand(az, richtung) < SONNE_MAX_WINKEL:
                besonnt[name].append(t)
    ergebnis.sonnenzeiten = {name: _zeitraeume(zeiten) for name, zeiten in besonnt.items()}

    # Sonne in einem Satz: zuerst, was Schaden nimmt oder warm wird.
    if front is None:
        ergebnis.satz_sonne = "Richtung des Fahrzeugs fehlt – unter „Front zeigt nach“ einstellen."
    else:
        teile = []
        if markise in (SEITE_RECHTS, SEITE_LINKS):
            teile.append(_seite_satz("Markise", markise, ergebnis.sonnenzeiten[markise]))
        if kuehlschrank in (SEITE_RECHTS, SEITE_LINKS):
            # Ein Absorberkühlschrank gibt seine Wärme über die Gitter ab.
            # Scheint die Sonne darauf, kühlt er schlechter.
            teile.append(_seite_satz(
                "Kühlschrank-Lüftung", kuehlschrank, ergebnis.sonnenzeiten[kuehlschrank],
                "dann kühlt er schlechter",
            ))
        if not teile:
            teile = [
                f"Sonne {name}: {', '.join(r) if r else 'keine'}."
                for name, r in ergebnis.sonnenzeiten.items() if name in ("rechts", "links")
            ]
        ergebnis.satz_sonne = " ".join(teile)

    # Satellit.
    name, laenge_sat = SATELLITEN.get(satellit, SATELLITEN[SATELLIT_VORGABE])
    sat_az, sat_h = satellit_richtung(breite, laenge, laenge_sat)
    ergebnis.satellit = name
    ergebnis.satellit_azimut = round(sat_az, 1)
    ergebnis.satellit_hoehe = round(sat_h, 1)
    if sat_h <= 0:
        ergebnis.satz_satellit = f"{name} ist von hier aus nicht zu empfangen."
    else:
        ergebnis.satz_satellit = (
            f"{name}: {himmelsrichtung(sat_az)} ({round(sat_az)}°), {round(sat_h)}° hoch"
            + (f" – vom Fahrzeug aus {vom_fahrzeug_genau(sat_az, front)}." if front is not None else ".")
        )
        if front is not None:
            ergebnis.satellit_relativ = relativ(sat_az, front)

    # Starlink: Auf der Nordhalbkugel richtet sich die Schüssel nach Norden
    # aus, dort braucht sie freien Himmel; auf der Südhalbkugel nach Süden.
    starlink_az = 0.0 if breite >= 0 else 180.0
    ergebnis.starlink_azimut = starlink_az
    himmel = "Norden" if breite >= 0 else "Süden"
    if front is None:
        ergebnis.satz_starlink = f"Starlink braucht freien Himmel, vor allem nach {himmel}."
    else:
        ergebnis.starlink_relativ = relativ(starlink_az, front)
        ergebnis.satz_starlink = (
            f"Starlink: {himmel} liegt {vom_fahrzeug_genau(starlink_az, front)} – "
            "dort keine Bäume oder Aufbauten."
        )
    return ergebnis
