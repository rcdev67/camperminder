# ============================================================================
#  Erzeugt die drei Dateien, die an ein GitHub-Release gehängt werden.
#
#      pwsh ./build_release.ps1
#
#  Ergebnis in  esphome/release/ :
#      firmware.ota.bin        die Firmware
#      firmware.ota.bin.md5    ihre Prüfsumme
#      manifest.json           was das Gerät abfragt
#
#  Warum ein Skript: Die Prüfsumme und die Versionsnummer müssen zur
#  Firmwaredatei passen. Von Hand gepflegt gehen sie früher oder später
#  auseinander - und dann verweigert entweder jedes Gerät die Installation
#  (falsche MD5) oder es meldet dauerhaft "Update verfügbar" (falsche
#  Version). Beides fällt erst beim Kunden auf.
#
#  Die Version kommt aus esphome/level/hardware.yaml und wird
#  nicht hier gepflegt - eine Quelle, keine zweite Wahrheit.
# ============================================================================

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$here = Join-Path $root 'esphome\level'

$repoUrl = 'https://github.com/rcdev67/campermaid'

# --- Version aus der einen Quelle lesen ------------------------------------
$hardware = Join-Path $here 'hardware.yaml'
if (-not (Test-Path $hardware)) { throw "Nicht gefunden: $hardware" }
$m = [regex]::Match((Get-Content $hardware -Raw), '(?m)^\s*firmware_version\s*:\s*"([^"]+)"')
if (-not $m.Success) { throw "firmware_version nicht gefunden in $hardware" }
$version = $m.Groups[1].Value
Write-Host "Version aus der Firmware-Quelle: $version"

# --- Die Integration muss dieselbe Nummer tragen ----------------------------
# Ein Release trägt genau ein Tag, und HACS richtet sich allein nach diesem Tag
# - nicht nach der manifest.json. Läuft die Integration unter einer anderen
# Nummer, geht das doppelt schief:
#
#   1. HACS bietet "2.0.3" an und installiert es, die Integration meldet aber
#      weiterhin ihre alte Nummer. Was installiert ist, lässt sich dann nicht
#      mehr ablesen.
#   2. Schlimmer: Die Lovelace-Karte wird als "campermaid-card.js?v=<Nummer aus
#      manifest.json>" eingebunden. Bleibt die Nummer stehen, bleibt die
#      Adresse gleich - und der Browser liefert weiter die Karte aus seinem
#      Zwischenspeicher. Die neuen Dateien liegen dann zwar auf der Platte,
#      sind aber unsichtbar.
#
# Deshalb hier eine harte Prüfung statt einer stillen Abweichung.
$manifest = Join-Path $root 'custom_components\campermaid\manifest.json'
if (-not (Test-Path $manifest)) { throw "Nicht gefunden: $manifest" }
$integrationsVersion = (Get-Content $manifest -Raw | ConvertFrom-Json).version
if ($integrationsVersion -cne $version) {
  throw @"
Versionen weichen ab:
    esphome/level/hardware.yaml          firmware_version = $version
    custom_components/campermaid/...json version          = $integrationsVersion
Ein Release hat eine Nummer. Beide angleichen, dann erneut bauen.
"@
}
Write-Host "Integration traegt dieselbe Nummer: $integrationsVersion"

# --- Gebaute Firmware suchen -----------------------------------------------
# esphome legt sie unter .esphome/build/<name>/.pioenvs/<name>/ ab.
# Gesucht wird der Name, den ESPHome vergibt. Das Produktpräfix bekommt erst
# die Kopie im Ausgabeordner - die Release-Anhänge müssen je Produkt
# unterscheidbar sein, im Bauverzeichnis heißen sie bei allen gleich.
$candidates = Get-ChildItem (Join-Path $root 'esphome') -Recurse -Filter 'firmware.ota.bin' -ErrorAction SilentlyContinue |
              Sort-Object LastWriteTime -Descending
if (-not $candidates) {
  throw "firmware.ota.bin nicht gefunden. Erst bauen:  esphome compile campermaid-level.yaml"
}
$bin = $candidates[0]
Write-Host ("Firmware: {0}  ({1:N0} Bytes, {2})" -f $bin.FullName, $bin.Length, $bin.LastWriteTime)

# Die Factory-Datei liegt daneben und enthält zusätzlich Bootloader und
# Partitionstabelle. Sie gehört ans Release, damit sich jede veröffentlichte
# Version auch auf ein leeres Board bringen lässt - ohne vorher zu bauen und
# ohne diesen Rechner. Verwechseln geht schief: Die OTA-Datei auf einen leeren
# Chip geschrieben ergibt ein Gerät, das nicht startet.
$factory = Join-Path $bin.DirectoryName 'firmware.factory.bin'
if (-not (Test-Path $factory)) { throw "firmware.factory.bin nicht gefunden neben $($bin.Name)" }

# Warnen, wenn die Firmware älter ist als eine ihrer Quellen - dann wurde nach
# der letzten Änderung nicht neu gebaut, und das Release enthielte einen alten
# Stand unter neuer Nummer. Geprüft wird jede Datei, die in die Firmware
# eingeht: die Gerätedatei, das Paket und die Bedienoberfläche. Letztere steckt
# über js_include mit im Abbild - eine Änderung daran ist von außen nicht zu
# sehen, fällt also ohne diese Prüfung erst beim Anwender auf.
$quellen = @('campermaid-level.yaml', 'hardware.yaml', 'webui.js') |
           ForEach-Object { Join-Path $here $_ } |
           Where-Object   { Test-Path $_ } |
           ForEach-Object { Get-Item $_ }
$veraltet = $quellen | Where-Object { $_.LastWriteTime -gt $bin.LastWriteTime }
if ($veraltet) {
  Write-Warning ("Die Firmware ist ÄLTER als: {0}" -f (($veraltet.Name) -join ', '))
  Write-Warning "Vor dem Release neu bauen - sonst liegt ein alter Stand unter neuer Nummer."
}

# --- Ausgabeordner ----------------------------------------------------------
$out = Join-Path $root 'release'
if (-not (Test-Path $out)) { New-Item -ItemType Directory -Path $out | Out-Null }
Copy-Item $bin.FullName (Join-Path $out 'level-firmware.ota.bin') -Force
Copy-Item $factory      (Join-Path $out 'level-firmware.factory.bin') -Force

# --- Prüfsumme -------------------------------------------------------------
# Genau 32 Zeichen, klein geschrieben, ohne Zeilenumbruch: Das Gerät
# vergleicht den Inhalt der Datei unverändert.
$md5 = (Get-FileHash (Join-Path $out 'level-firmware.ota.bin') -Algorithm MD5).Hash.ToLower()
[System.IO.File]::WriteAllText((Join-Path $out 'level-firmware.ota.bin.md5'), $md5)
Write-Host "MD5: $md5"

# --- Manifest ---------------------------------------------------------------
# path als vollständige Adresse: Beginnt der Wert mit http, nimmt das Gerät
# ihn unverändert. Relative Angaben scheitern, weil GitHub den Download auf
# einen anderen Rechner umleitet.
$manifest = [ordered]@{
  name    = 'CamperMaid Level'
  version = $version
  builds  = @(
    [ordered]@{
      chipFamily = 'ESP32-C3'
      ota        = [ordered]@{
        md5         = $md5
        path        = "$repoUrl/releases/latest/download/level-firmware.ota.bin"
        summary     = "CamperMaid $version"
        release_url = "$repoUrl/releases/latest"
      }
    }
  )
}
$json = $manifest | ConvertTo-Json -Depth 6
[System.IO.File]::WriteAllText((Join-Path $out 'level-manifest.json'), $json, (New-Object System.Text.UTF8Encoding $false))

Write-Host ""
Write-Host "Fertig. Diese Dateien an das Release hängen:"
Get-ChildItem $out | ForEach-Object { "   {0,-24} {1,10:N0} Bytes" -f $_.Name, $_.Length }
Write-Host ""
Write-Host "Zum Veröffentlichen:  veroeffentlichen.cmd"
Write-Host ""
Write-Host "Beim Hochladen von Hand: erst die .bin und die .md5, zuletzt das Manifest."
Write-Host "Andersherum sehen Geräte kurz eine Version, die es noch nicht zum Laden gibt."
Write-Host "veroeffentlichen.cmd umgeht das - es lädt in einen Entwurf und schaltet"
Write-Host "erst danach sichtbar."
