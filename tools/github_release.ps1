# ============================================================================
#  Legt auf GitHub ein Release an und hängt die Dateien aus release/ daran.
#
#      pwsh ./github_release.ps1            (üblich über veroeffentlichen.cmd)
#
#  ABLAUF: erst als ENTWURF anlegen, dann Dateien hochladen, zuletzt
#  veröffentlichen. Grund: "releases/latest/download/..." zeigt sofort auf ein
#  veröffentlichtes Release. Legte man es fertig an und lud danach hoch, gäbe
#  es ein Zeitfenster, in dem Geräte ein Manifest sehen, dessen Firmware noch
#  fehlt - und einen Update-Versuch ins Leere starten.
#
#  ZUGANG: ein GitHub-Token mit Schreibrecht auf Inhalte. Entweder in der
#  Umgebungsvariablen CAMPERMAID_GH_TOKEN oder in tools/github_token.txt
#  (durch .gitignore ausgeschlossen). Token erzeugen unter
#  github.com/settings/tokens - fein granuliert, nur dieses Repository,
#  Berechtigung "Contents: Read and write".
# ============================================================================

$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $here

$owner = 'rcdev67'
$repo  = 'campermaid'

# --- Version aus der einen Quelle ------------------------------------------
$hardware = Join-Path $root 'esphome\level\hardware.yaml'
$m = [regex]::Match((Get-Content $hardware -Raw), '(?m)^\s*firmware_version\s*:\s*"([^"]+)"')
if (-not $m.Success) { throw "firmware_version nicht gefunden in $hardware" }
$version = $m.Groups[1].Value
$tag = "v$version"

# --- Anhänge --------------------------------------------------------------
$out = Join-Path $root 'release'
$dateien = @('level-firmware.ota.bin', 'level-firmware.ota.bin.md5',
             'level-firmware.factory.bin', 'level-manifest.json')
foreach ($d in $dateien) {
  if (-not (Test-Path (Join-Path $out $d))) {
    throw "Fehlt: release\$d  -  erst bauen.cmd ausführen."
  }
}

# --- Sicherheitsnetz: Stand muss gepusht sein ------------------------------
# Ein Release zeigt auf einen Commit. Liegt lokal etwas, das nicht auf GitHub
# ist, veröffentlicht man eine Firmware zu einem Quelltext, den niemand sehen
# kann - bei GPLv3 nicht nur unsauber, sondern ein Verstoß.
#
# Geprüft wird ausdrücklich nur der Zweig, auf dem gerade gearbeitet wird.
# "--branches --not --remotes" sähe jeden lokalen Zweig an und schlüge auch bei
# einer bewusst zurückgehaltenen Sicherung an - die soll gerade nicht auf
# GitHub landen.
Push-Location $root
$dirty  = git status --porcelain
$zweig  = (git rev-parse --abbrev-ref HEAD).Trim()
$oben   = (git rev-parse --abbrev-ref --symbolic-full-name "$zweig@{upstream}")
$hatOben = ($LASTEXITCODE -eq 0 -and $oben)
$unpush = if ($hatOben) { git log "$($oben.Trim())..HEAD" --oneline } else { $null }
Pop-Location

if ($dirty)    { throw "Es gibt nicht committete Änderungen. Erst committen." }
if (-not $hatOben) {
  throw "Der Zweig '$zweig' hat kein Gegenstück auf GitHub. Erst pushen:  git push -u origin $zweig"
}
if ($unpush) {
  $liste = ($unpush | ForEach-Object { "    $_" }) -join "`n"
  throw "Auf '$zweig' liegen Commits, die nicht auf GitHub sind:`n$liste`nErst pushen."
}

# --- Token -----------------------------------------------------------------
$token = $env:CAMPERMAID_GH_TOKEN
if (-not $token) {
  $tf = Join-Path $here 'github_token.txt'
  if (Test-Path $tf) { $token = (Get-Content $tf -Raw).Trim() }
}
if (-not $token) {
  throw "Kein Token. Entweder CAMPERMAID_GH_TOKEN setzen oder tools\github_token.txt anlegen."
}

$kopf = @{
  Authorization          = "Bearer $token"
  Accept                 = 'application/vnd.github+json'
  'X-GitHub-Api-Version' = '2022-11-28'
  'User-Agent'           = 'campermaid-release'
}
$api = "https://api.github.com/repos/$owner/$repo"

Write-Host "Repository: $owner/$repo"
Write-Host "Version:    $version   (Tag $tag)"
Write-Host ""

# --- Gibt es das Release schon? --------------------------------------------
$release = $null
try   { $release = Invoke-RestMethod -Uri "$api/releases/tags/$tag" -Headers $kopf -Method Get }
catch { $release = $null }

if ($release) {
  Write-Host "Release $tag besteht bereits - vorhandene Anhänge werden ersetzt."
  foreach ($a in $release.assets) {
    if ($dateien -contains $a.name) {
      Invoke-RestMethod -Uri "$api/releases/assets/$($a.id)" -Headers $kopf -Method Delete | Out-Null
      Write-Host "  entfernt: $($a.name)"
    }
  }
  # Zum Hochladen zurück in den Entwurf, damit "latest" nicht auf ein
  # Release ohne vollständige Dateien zeigt.
  $release = Invoke-RestMethod -Uri "$api/releases/$($release.id)" -Headers $kopf -Method Patch `
    -Body (@{ draft = $true } | ConvertTo-Json) -ContentType 'application/json'
} else {
  $text = @"
CamperMaid Level $version

Firmware für CamperMaid Level.

**Aktualisieren:** Geräte mit Internet melden das Update von selbst.
Ohne Internet: Geräteseite -> Technik -> Software -> Datei aufspielen,
dann ``level-firmware.ota.bin`` wählen.

**Neues Gerät:** ``level-firmware.factory.bin`` über USB aufspielen, etwa
mit web.esphome.io. Die OTA-Datei ist dafür nicht geeignet - sie enthält
keinen Bootloader.
"@
  $body = @{
    tag_name = $tag
    name     = "CamperMaid Level $version"
    body     = $text
    draft    = $true
  } | ConvertTo-Json
  $release = Invoke-RestMethod -Uri "$api/releases" -Headers $kopf -Method Post `
    -Body $body -ContentType 'application/json'
  Write-Host "Entwurf angelegt."
}

# --- Anhänge hochladen ----------------------------------------------------
$uploadBase = ($release.upload_url -split '\{')[0]
foreach ($d in $dateien) {
  $pfad = Join-Path $out $d
  Write-Host ("  lade hoch: {0} ({1:N0} Bytes)" -f $d, (Get-Item $pfad).Length)
  Invoke-RestMethod -Uri "$uploadBase`?name=$d" -Headers $kopf -Method Post `
    -InFile $pfad -ContentType 'application/octet-stream' | Out-Null
}

# --- Erst jetzt veröffentlichen -------------------------------------------
$fertig = Invoke-RestMethod -Uri "$api/releases/$($release.id)" -Headers $kopf -Method Patch `
  -Body (@{ draft = $false; make_latest = 'true' } | ConvertTo-Json) -ContentType 'application/json'

Write-Host ""
Write-Host "Veröffentlicht: $($fertig.html_url)"
Write-Host ""
Write-Host "Geräte mit Internet melden das Update innerhalb von 12 Stunden,"
Write-Host "nach einem Neustart von Home Assistant sofort."
