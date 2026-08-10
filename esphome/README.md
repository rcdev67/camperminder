# Firmware

```
esphome/
  common/     geteilte Bausteine — noch leer, siehe dort
  level/      CamperMaid Level
    campermaid-level.yaml            die auszuliefernde Firmware
    hardware.yaml                    Messlogik, Anzeige, Einstellwerte
    webui.js                         Bedienoberfläche auf dem Gerät
    secrets.yaml.example
```

## Bauen

```bash
cd esphome/level
esphome run campermaid-level.yaml
```

Voraussetzung ist eine `secrets.yaml` in `esphome/level/` mit drei Einträgen —
Vorlage danebenliegend. **Der API-Schlüssel darf sich nie ändern**: Er steckt
in jedem ausgelieferten Gerät und auf jedem Aufkleber.

## Versionen

Firmware und Integration tragen **immer dieselbe Nummer**. `firmware_version`
in [`level/hardware.yaml`](level/hardware.yaml) und `version` in
`custom_components/campermaid/manifest.json` müssen zeichengleich sein —
`tools/build_release.ps1` vergleicht beide und bricht bei Abweichung ab.

Der Grund ist der Nutzer: Zwei verschiedene Nummern für **ein** Gerät lassen
sich niemandem erklären. Wer in HACS die eine und auf der Geräteseite die
andere sieht, weiß nicht mehr, welchen Stand er hat. Dazu kommt, dass eine
Änderung auf der einen Seite fast immer eine auf der anderen nach sich zieht —
die beiden gehören zusammen.

Eigenständig zählen die **Produkte**, nicht die Bestandteile eines Produkts:
CamperMaid Gas bekommt später eine eigene Nummer, damit eine Änderung an der
Gaswaage nicht jedem Nivelliergerät ein Update aufzwingt.

## Veröffentlichen

```powershell
cd esphome/level
esphome compile campermaid-level.yaml
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
