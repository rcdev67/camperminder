# Software-Aktualisierung

**GitHub ist die einzige Quelle** — für Firmware, Integration und Karte
gleichermaßen. Es gibt keinen zweiten Weg und keinen eigenen Server.

| Was | Weg | Wo sichtbar |
|---|---|---|
| Integration + Lovelace-Karte | HACS aus dem GitHub-Release | HACS, Einstellungen → Updates |
| Firmware, mit Home Assistant | Update-Entität, prüft alle 12 h | Einstellungen → System → Updates |
| Firmware, ohne Home Assistant | Knopf auf der Geräteseite, Reiter *Technik* | Geräteseite |

Beide Betriebsarten laufen auf **derselben** Firmware und bekommen deshalb
dieselben Aktualisierungen — auch die visuellen. Die Geräteoberfläche steckt
über `js_include` in der Firmware, sie reist bei jedem Update mit.

## Feste Adressen — und warum nicht `latest`

Diese Firmware ist die **MPU6050-Linie** (Zweig `mpu6050`). Daneben gibt es auf
`main` die Linie für den LSM6DS3TR-C. Die beiden sind **nicht austauschbar**:
Jede spricht nur mit ihrem Sensor. Wer die falsche aufspielt, bekommt ein
Gerät, das startet und dessen Anzeige leer bleibt.

`releases/latest` gibt es bei GitHub genau **einmal fürs ganze Repository**.
Beide Linien darüber zu bedienen ist unmöglich: Sobald die andere eine
Auslieferung veröffentlicht, wird die zum `latest` — und jedes Gerät dieser
Linie mit Internet flasht sie sich binnen zwölf Stunden. Bei einem Testgerät
beim Nutzer heißt das: Kabel, und zwar unseres.

Deshalb hat diese Linie einen **eigenen Kanal**: das feste Tag `mpu`.

```
https://github.com/rcdev67/camperminder/releases/download/mpu/level-manifest.json
https://github.com/rcdev67/camperminder/releases/download/mpu/level-firmware.ota.bin
https://github.com/rcdev67/camperminder/releases/download/mpu/level-firmware.ota.bin.md5
```

Das ist **ein einziges, rollendes Release**, das `tools/github_release.ps1` bei
jeder Veröffentlichung neu bestückt. Es ist als Vorabfassung markiert und kann
damit nie zum `latest` werden; umgekehrt setzt das Skript auf diesem Zweig bei
**keinem** Release `make_latest`. `releases/latest` bleibt dauerhaft der
Produktlinie vorbehalten.

Der Vorteil gegenüber einer Absprache: Die Trennung steht in der **Adresse**,
nicht in einer Regel, an die jemand denken muss.

Das Produktpräfix `level-` trägt jede Datei, weil sich Level und Gas später ein
Release teilen.

Die Adressen stehen fest in
[`camperminder-level.yaml`](../esphome/level/camperminder-level.yaml) und müssen
bei einer neuen Version **nicht** angefasst werden. Wer sie doch ändert, muss
`$kanal` in [`tools/build_release.ps1`](../tools/build_release.ps1) und in
[`tools/github_release.ps1`](../tools/github_release.ps1) mitziehen — und
begreifen, dass bereits ausgelieferte Geräte die **alte** Adresse behalten und
nur über sie erreichbar bleiben.

### Zwei Releases je Fassung

| Tag | Enthält | Wofür |
|---|---|---|
| `v3.9.1` | alle vier Dateien | Verlauf, HACS, `factory.bin` für ein leeres Board |
| `mpu` | Manifest, OTA-Datei, MD5 | der Kanal, den die Geräte abfragen |

Die Factory-Datei liegt bewusst **nicht** im Kanal: Sie ist für ein leeres
Board über USB da, und dafür holt man sich das Versions-Release. Im Kanal wären
es 1,3 MB, die bei jeder Veröffentlichung ohne Zweck neu hochgeladen würden.

Das Tag `mpu` bleibt beim Auffrischen stehen — es beschreibt den **Kanal**,
nicht den Quellstand. Der Quelltext zu einer Firmware steht immer unter ihrem
Versions-Tag.

## Eine neue Version veröffentlichen

1. **Version erhöhen.** Die Firmware-Version steht an **einer** Stelle:
   `firmware_version` in den `substitutions` von
   [`hardware.yaml`](../esphome/level/hardware.yaml).
   Von dort zieht sie sich in `esphome.project.version` und in die
   angezeigte Fassung. Der Wert im Release-Manifest muss **zeichengleich**
   sein — die Prüfung im Gerät vergleicht die Zeichenketten:

   ```cpp
   #ifdef ESPHOME_PROJECT_VERSION
       info->current_version = ESPHOME_PROJECT_VERSION;
   ```

   Weicht das Manifest ab, meldet das Gerät dauerhaft „Update verfügbar" —
   auch direkt nach dem Aktualisieren.

   Getrennt davon: `manifest.json` der Home-Assistant-Integration.
2. **Firmware bauen.** Es muss die **`level-firmware.ota.bin`** sein. Die
   Factory-Datei ist für OTA ausdrücklich nicht verwendbar — sie enthält
   Bootloader und Partitionstabelle und wird abgewiesen.
3. **MD5-Summe bilden** und als eigene Datei ablegen:
   ```powershell
   (Get-FileHash .\level-firmware.ota.bin -Algorithm MD5).Hash.ToLower() | Out-File -Encoding ascii level-firmware.ota.bin.md5
   ```
4. **Release anlegen** mit dem Tag der Version, dann die vier Dateien
   anhängen: `level-firmware.ota.bin`, `level-firmware.ota.bin.md5`,
   `level-firmware.factory.bin`, `level-manifest.json`. Die Factory-Datei wird
   fürs Update nicht gebraucht — sie liegt bei, damit sich jede veröffentlichte
   Version ohne Bauen auf ein leeres Board bringen lässt.

Schritt 2 bis 4 nimmt `tools/veroeffentlichen.cmd` ab, samt Reihenfolge beim
Hochladen.

### Zugang zu GitHub

Das Skript braucht ein Token mit Schreibrecht und sucht es an drei Stellen, in
dieser Reihenfolge:

1. Umgebungsvariable `CAMPERMINDER_GH_TOKEN`
2. `tools/github_token.txt` (durch `.gitignore` ausgeschlossen)
3. **den Git Credential Manager** — also dasselbe Token, mit dem `git push`
   ohnehin arbeitet

Der dritte Weg braucht keine Pflege und ist deshalb der vorgesehene: Der
Credential Manager erneuert sein Token selbst. Von Hand angelegte Tokens laufen
ab — fein granulierte nach Voreinstellung schon nach 30 Tagen —, und das merkt
man immer erst mitten im Veröffentlichen. Wer keines von Hand pflegen will,
lässt `github_token.txt` leer; eine leere Datei zählt als nicht vorhanden.

Das Skript prüft das Token **vor** dem Anlegen des Releases mit einem
Lesezugriff und sagt im Klartext, was fehlt, statt mitten im Ablauf mit einem
nackten `(401) Nicht autorisiert` abzubrechen.

Ohne Release passiert nichts — weder in HACS noch an den Geräten. HACS folgt
seit dem ersten Tag ausschließlich Releases, nicht dem Branch.

## Interne Fassungen erproben

Eine neue Fassung soll geprüft werden können, ohne dass sie bei irgendjemandem
landet. Dafür gibt es zwei Arten von Veröffentlichung, und **die Versionsnummer
entscheidet, welche es wird**:

| Nummer | Art | Wer bekommt sie |
|---|---|---|
| `2.0.4` | Auslieferung | jedes Gerät mit Internet, HACS bietet sie an |
| `2.0.4-rc1` | Vorabfassung | niemand automatisch |

Der Bindestrich ist das ganze Verfahren. `tools/github_release.ps1` liest ihn
und setzt die Veröffentlichung auf *prerelease*.

**Warum das genügt:** Die Geräte fragen ausschließlich den Kanal `mpu` ab, und
eine Vorabfassung wird **nicht dorthin gespiegelt**. Sie existiert für die
Geräte damit schlicht nicht — sie bleiben auf der letzten Auslieferung stehen.
HACS blendet Vorabfassungen ebenfalls aus, solange beim Repository nicht
ausdrücklich Betafassungen eingeschaltet sind.

Das Versions-Release entsteht trotzdem, mit Tag und Dateien. Wer die Fassung
erproben will, lädt die OTA-Datei von dort und spielt sie von Hand auf.

### Eine Vorabfassung aufspielen

Auf das eigene Gerät am schnellsten direkt aus dem Arbeitsstand, ganz ohne
Veröffentlichung:

```bash
esphome run camperminder-level.yaml --device camperminder-level.local
```

Auf ein entferntes Gerät über die Geräteseite: *Technik → Software → Datei
aufspielen*, dann `level-firmware.ota.bin` aus der Vorabfassung wählen.

### Von der Erprobung zur Auslieferung

Taugt die Fassung, wird aus `2.0.4-rc1` schlicht `2.0.4` — in
`esphome/level/hardware.yaml` **und** in
`custom_components/camperminder/manifest.json`, beide müssen übereinstimmen. Dann
neu bauen und erneut veröffentlichen. Die Vorabfassung kann stehenbleiben; sie
stört nicht.

### Eine Eigenheit, die kein Fehler ist

Ein Gerät, auf dem eine Vorabfassung läuft, meldet dauerhaft „Update
verfügbar" — und zwar auf die letzte **ausgelieferte** Fassung. Die Prüfung
vergleicht nur, ob die Zeichenketten gleich sind; sie kennt kein „neuer" und
kein „älter". Auf einem Erprobungsgerät ist das hinnehmbar und sogar
brauchbar: Es zeigt an, dass hier gerade kein Auslieferungsstand läuft.

## Aufbau des Manifests

Nach der ESP-Web-Tools-Spezifikation mit der OTA-Erweiterung:

```json
{
  "name": "CamperMinder Level",
  "version": "2.0.0",
  "builds": [
    {
      "chipFamily": "ESP32-C3",
      "ota": {
        "md5": "…32 Zeichen…",
        "path": "https://github.com/rcdev67/camperminder/releases/download/mpu/level-firmware.ota.bin",
        "summary": "CamperMinder 2.0.0",
        "release_url": "https://github.com/rcdev67/camperminder/releases/tag/v2.0.0"
      }
    }
  ]
}
```

`path` steht bewusst als vollständige Adresse: Beginnt der Wert mit `http`,
nimmt das Gerät ihn unverändert. Relative Angaben würden hier scheitern, weil
GitHub den Download auf einen anderen Rechner umleitet.

`path` zeigt auf den **Kanal**, `release_url` dagegen auf die **konkrete
Fassung**. Das ist Absicht: Die erste Adresse liest das Gerät und sie muss
stehenbleiben, solange Geräte draußen sind; die zweite liest ein Mensch, und
der will wissen, was sich geändert hat.

**Pflichtfelder:** `name`, `version`, `builds[].chipFamily`,
`builds[].ota.md5`, `builds[].ota.path`. `summary` und `release_url` sind
optional, werden dem Nutzer aber angezeigt — ohne sie steht da nur eine
Nummer ohne Erklärung.

Stimmt die MD5-Summe nicht, verweigert das Gerät die Installation. Das ist die
einzige Sicherung gegen eine halb übertragene Datei — also niemals eine alte
Summe stehen lassen.

## Verschlüsselung

`http_request:` prüft das Zertifikat von GitHub (Voreinstellung). Scheitert
der Handschlag auf dem Gerät, lässt sich `verify_ssl: false` setzen — dann
entfällt aber die Echtheitsprüfung, und ein Angreifer im selben Netz könnte
eigene Firmware unterschieben. Die MD5-Summe hilft dagegen nicht, sie stammt
aus derselben Quelle. Erst versuchen, dann abschalten, nicht umgekehrt.

## Selbstbau mit eigenen Anpassungen

Wer die Firmware verändert hat — Gerätename, Pins, Achsvorzeichen —, sollte den
Update-Knopf stehen lassen, aber nicht drücken: Er holt den Werksstand und
ersetzt die Anpassungen kommentarlos. Der Weg dafür ist `esphome run` aus dem
eigenen Arbeitsstand, wie in [INSTALL.md](../INSTALL.md) beschrieben.

Die Einstellwerte im Gerät überstehen beide Wege. Verloren gehen sie beim
seriellen Aufspielen mit Löschen: Das räumt auch den Speicherbereich ab, in dem
Fahrzeugmaße und WLAN-Zugangsdaten liegen. Deshalb aktualisiert ein Gerät im
Einsatz über das Netz, nicht über das Kabel.
