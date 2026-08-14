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

## Feste Adressen

Alles hängt an `releases/latest/download/…`. GitHub löst das selbst auf die
neueste Veröffentlichung auf, die Adressen ändern sich also **nie**:

```
https://github.com/rcdev67/campermaid/releases/latest/download/level-manifest.json
https://github.com/rcdev67/campermaid/releases/latest/download/level-firmware.ota.bin
https://github.com/rcdev67/campermaid/releases/latest/download/level-firmware.ota.bin.md5
```

Das Produktpräfix `level-` trägt jede Datei, weil sich Level und Gas später ein
Release teilen.

Sie stehen fest in [`campermaid-level.yaml`](../esphome/level/campermaid-level.yaml)
und müssen bei einer neuen Version **nicht** angefasst werden.

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

1. Umgebungsvariable `CAMPERMAID_GH_TOKEN`
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

**Warum das genügt:** Die Geräte fragen `releases/latest/download/…` ab. GitHub
liefert unter `latest` ausdrücklich die neueste Fassung, die **weder Entwurf
noch Vorabversion** ist. Eine Vorabfassung existiert für die Geräte damit
schlicht nicht — sie bleiben auf der letzten Auslieferung stehen. HACS
verfährt ebenso, solange beim Repository nicht ausdrücklich Betafassungen
eingeschaltet sind.

Zusätzlich setzt das Skript `make_latest` auf `false`. Zwei Schlösser statt
einem: Wer den Haken später von Hand entfernt, hätte sonst schlagartig eine
ungeprüfte Fassung auf allen Geräten.

### Eine Vorabfassung aufspielen

Auf das eigene Gerät am schnellsten direkt aus dem Arbeitsstand, ganz ohne
Veröffentlichung:

```bash
esphome run campermaid-level.yaml --device campermaid-level.local
```

Auf ein entferntes Gerät über die Geräteseite: *Technik → Software → Datei
aufspielen*, dann `level-firmware.ota.bin` aus der Vorabfassung wählen.

### Von der Erprobung zur Auslieferung

Taugt die Fassung, wird aus `2.0.4-rc1` schlicht `2.0.4` — in
`esphome/level/hardware.yaml` **und** in
`custom_components/campermaid/manifest.json`, beide müssen übereinstimmen. Dann
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
  "name": "CamperMaid Level",
  "version": "2.0.0",
  "builds": [
    {
      "chipFamily": "ESP32-C3",
      "ota": {
        "md5": "…32 Zeichen…",
        "path": "https://github.com/rcdev67/campermaid/releases/latest/download/level-firmware.ota.bin",
        "summary": "CamperMaid 2.0.0",
        "release_url": "https://github.com/rcdev67/campermaid/releases/latest"
      }
    }
  ]
}
```

`path` steht bewusst als vollständige Adresse: Beginnt der Wert mit `http`,
nimmt das Gerät ihn unverändert. Relative Angaben würden hier scheitern, weil
GitHub den Download auf einen anderen Rechner umleitet.

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
