# CamperMinder Level mit Home Assistant

Für das **Gerät selbst** ist diese Seite nicht nötig — dort führt
[docs/inbetriebnahme.md](docs/inbetriebnahme.md) durch drei Schritte, ganz ohne
Home Assistant.

Hier geht es um die Erweiterung: das Gerät in Home Assistant einbinden.
Voraussetzung ist ein Gerät, das in deinem WLAN angemeldet ist (Abschnitt
*Ins eigene WLAN* der Anleitung) und **HACS** in Home Assistant.

---

## 1. WLAN eintragen

Auf der Geräteseite unter *Technik → WLAN*. Das Gerät startet neu und
verbindet sich; das Netz `CamperMinder` verschwindet dabei.

## 2. Gerät übernehmen

Home Assistant findet es von selbst und fragt nach dem API-Schlüssel des
Geräts.

## 3. Integration installieren

HACS → Dreipunktmenü → *Benutzerdefinierte Repositories*:

| Feld | Wert |
|---|---|
| Repository | `https://github.com/rcdev67/camperminder` |
| Typ | **Integration** |

Danach **CamperMinder** herunterladen und Home Assistant neu starten.

## 4. Einrichten

Einstellungen → Geräte & Dienste → *Integration hinzufügen* →
**CamperMinder**. Die Sensorfelder sind vorausgefüllt, sofern die
mitgelieferte Firmware läuft.

- ✔ Es entsteht ein Gerät **CamperMinder** mit „Phase", „Steht eben",
  „Schwelle längs/quer", „Korrektur längs/quer" und „Ansageziel".
- ✔ Fahrzeugmaße, Ausrichtart und Präzisionsmodus erscheinen **nicht**
  doppelt — die liest die Integration vom Gerät. Die Karte bedient dann den
  Schalter des Geräts.

## 5. Karte aufs Dashboard

Dashboard → Bearbeiten → *Karte hinzufügen* → „CamperMinder" suchen.

Erscheint sie nicht in der Auswahl, prüf unter Einstellungen → Dashboards → ⋮
→ *Ressourcen*, ob `/camperminder_karte/camperminder-card.js` eingetragen ist.
Die Integration legt den Eintrag beim Start selbst an.

## 6. Blueprints importieren (Erweiterung)

Drei fertige Automatisierungen, die die Meldungen des Geräts aufs Handy oder
an eine Sirene bringen. Einstellungen → Automatisierungen & Szenen →
Blueprints → *Blueprint importieren*, dann die Adresse einfügen:

| Blueprint | Adresse |
|---|---|
| Kühlschrankwarnung | `https://github.com/rcdev67/camperminder/blob/main/blueprints/automation/camperminder/kuehlschrank_warnung.yaml` |
| Wächteralarm | `https://github.com/rcdev67/camperminder/blob/main/blueprints/automation/camperminder/waechter_alarm.yaml` |
| Frostwarnung | `https://github.com/rcdev67/camperminder/blob/main/blueprints/automation/camperminder/frostwarnung.yaml` |

Danach *Automatisierung erstellen → Aus einem Blueprint*. Mehr dazu, auch der
Import per Klick und ohne Internet, in [blueprints/README.md](blueprints/README.md).

---

## Kalibrieren

Zum Schluss einmal im Fahrzeug — wie und warum steht in
[docs/kalibrierung.md](docs/kalibrierung.md).
