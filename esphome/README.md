# Firmware

```
esphome/
  common/                     geteilte Bausteine — noch leer, siehe dort
  level/                      CamperMinder Level
    camperminder-level.yaml   die auszuliefernde Firmware
    hardware.yaml             Messlogik, Status-LED, Summer, Einstellwerte
    anzeige-oled.yaml         Werkstattvariante: 0,42"-OLED an J4, NICHT im Produkt
    webui.js                  Bedienoberfläche auf dem Gerät
    muster-supermini.yaml     Handmuster auf ESP32-C3 SuperMini, nicht im Produkt
    diagnose.js               Fehlersuche: zeigt den Ereignisstrom roh an
    tools_fehlerfaenger.js    Fehlersuche: schreibt Abstürze auf die Seite
    secrets.yaml.example
```

Die beiden Dateien zur Fehlersuche treten über `js_include` **an die Stelle**
von `webui.js` und gehören nicht ins Produkt — wie sie benutzt werden, steht
im Kopf von `muster-supermini.yaml`. Auf dem Handy gibt es keine
Browserkonsole; ohne sie ist ein Fehler in der Bedienoberfläche von außen
nicht zu sehen.

Der Prüfstand für die Bedienoberfläche liegt in `tools/` —
`stub_erzeugen.py` leitet seinen Entitätsbestand aus `esphome config` ab,
`geraetestub.py` spielt damit das Gerät. Begründung in
`docs/firmware_update.md`.

Die ausgelieferte Ausführung hat **kein Display**. `anzeige-oled.yaml` wird nur
gebaut, wenn man in `camperminder-level.yaml` unter `packages:` die
entsprechende Zeile einkommentiert — für Werkstatt und Messplatz, mit einem
OLED an der Stiftleiste J4 der Platine.

## Bauen

```bash
cd esphome/level
esphome run camperminder-level.yaml
```

Voraussetzung ist eine `secrets.yaml` in `esphome/level/` mit zwei Einträgen —
Vorlage danebenliegend. **Der API-Schlüssel darf sich nie ändern**: Er steckt
in jedem ausgelieferten Gerät und auf jedem Aufkleber.

Ein Passwort für das geräteeigene Netz steht dort bewusst nicht: Das Netz ist
ab Werk offen, und wer es abschließen will, vergibt auf der Geräteseite ein
eigenes.

## Versionen

Firmware und Integration tragen **immer dieselbe Nummer**. `firmware_version`
in [`level/hardware.yaml`](level/hardware.yaml) und `version` in
`custom_components/camperminder/manifest.json` müssen zeichengleich sein —
`tools/build_release.ps1` vergleicht beide und bricht bei Abweichung ab.

Der Grund ist der Nutzer: Zwei verschiedene Nummern für **ein** Gerät lassen
sich niemandem erklären. Wer in HACS die eine und auf der Geräteseite die
andere sieht, weiß nicht mehr, welchen Stand er hat. Dazu kommt, dass eine
Änderung auf der einen Seite fast immer eine auf der anderen nach sich zieht —
die beiden gehören zusammen.

Eigenständig zählen die **Produkte**, nicht die Bestandteile eines Produkts:
CamperMinder Gas bekommt später eine eigene Nummer, damit eine Änderung an der
Gaswaage nicht jedem Nivelliergerät ein Update aufzwingt.

## Veröffentlichen

```powershell
cd esphome/level
esphome compile camperminder-level.yaml
pwsh ../../tools/build_release.ps1
```

Erzeugt in `release/` die vier Anhänge fürs GitHub-Release:
`level-firmware.ota.bin`, dessen `.md5`, `level-firmware.factory.bin` und
`level-manifest.json`. Die Namen tragen das Produktpräfix, weil sich Level und
Gas ein Release teilen.

Beide `.bin` haben verschiedene Aufgaben: Die OTA-Datei geht über das Netz auf
ein laufendes Gerät, die Factory-Datei mit Bootloader und Partitionstabelle auf
ein leeres Board. Vertauscht startet das Gerät nicht mehr.

Einzelheiten in [docs/firmware_update.md](../docs/firmware_update.md).

## Warum `common/` leer ist

Was Level und Gas teilen, weiß man erst, wenn Gas existiert. Eine falsch
geschnittene Gemeinsamkeit ist teurer als eine späte — deshalb wird erst
herausgelöst, wenn sich etwas tatsächlich doppelt.
