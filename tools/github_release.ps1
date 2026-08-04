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

# --- Vorabfassung oder Auslieferung? ---------------------------------------
# Die Versionsnummer entscheidet, nicht ein Schalter: Enthält sie einen
# Bindestrich ("2.0.4-rc1"), ist es eine interne Fassung. Das ist die
# Schreibweise aus der Versionierungsregel und zugleich der Punkt, an dem man
# es nicht vergessen kann - anders als bei einem Haken, den man beim
# fünfzehnten Release übersieht.
#
# Was der Unterschied bewirkt:
#
#   GitHub liefert unter "releases/latest" ausdrücklich die neueste Fassung,
#   die WEDER Entwurf NOCH Vorabversion ist. Genau diese Adresse fragen die
#   Geräte ab. Eine Vorabversion ist für sie damit nicht vorhanden - sie
#   bleiben auf der letzten ausgelieferten Fassung stehen.
#
#   HACS blendet Vorabversionen ebenfalls aus, solange beim Repository nicht
#   ausdrücklich Betafassungen eingeschaltet sind.
$istVorab = $version.Contains('-')

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

# JSON immer selbst nach UTF-8 wandeln und als Bytes senden.
#
# Invoke-RestMethod kodiert eine Zeichenkette in Windows PowerShell 5.1 nicht
# als UTF-8, wenn im ContentType keine Kodierung steht. Umlaute im
# Beschreibungstext kommen dann als ungültige Bytes an, und GitHub antwortet
# mit "Problems parsing JSON" - einer Meldung, die auf alles Mögliche zeigt,
# nur nicht auf die Ursache.
function Sende-Json {
  param($Uri, $Methode, $Daten)
  $json  = $Daten | ConvertTo-Json -Depth 6
  $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
  Invoke-RestMethod -Uri $Uri -Headers $kopf -Method $Methode `
    -Body $bytes -ContentType 'application/json; charset=utf-8'
}

Write-Host "Repository: $owner/$repo"
Write-Host "Version:    $version   (Tag $tag)"
if ($istVorab) {
  Write-Host "Art:        VORABFASSUNG - bleibt fuer Geraete und HACS unsichtbar." -ForegroundColor Yellow
} else {
  Write-Host "Art:        AUSLIEFERUNG - jedes Geraet mit Internet holt sie sich." -ForegroundColor Cyan
}
Write-Host ""

# --- Gibt es das Release schon? --------------------------------------------
# Zuerst über das Tag. Das findet allerdings KEINE Entwürfe: Ein Entwurf legt
# das Tag noch nicht an. Bricht ein Lauf nach dem Anlegen ab, entstünde beim
# nächsten Versuch ein zweiter Entwurf. Deshalb danach die Liste durchsehen.
$release = $null
try   { $release = Invoke-RestMethod -Uri "$api/releases/tags/$tag" -Headers $kopf -Method Get }
catch { $release = $null }

if (-not $release) {
  try {
    $alle = Invoke-RestMethod -Uri "$api/releases?per_page=100" -Headers $kopf -Method Get
    $release = $alle | Where-Object { $_.tag_name -eq $tag } | Select-Object -First 1
    if ($release) { Write-Host "Vorhandenen Entwurf $tag gefunden - wird weiterverwendet." }
  } catch { }
}

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
  $release = Sende-Json -Uri "$api/releases/$($release.id)" -Methode Patch -Daten @{ draft = $true }
} else {
  if ($istVorab) {
    $text = @"
CamperMaid Level $version - interne Vorabfassung

Diese Fassung ist **nicht zur Verwendung bestimmt**. Sie dient der Erprobung
vor einer Auslieferung.

Geräte erhalten sie nicht von selbst: Die Aktualisierungsprüfung folgt
``releases/latest``, und dort werden Vorabfassungen ausgelassen. Wer sie
dennoch aufspielen will, lädt ``level-firmware.ota.bin`` von Hand über
Geräteseite -> Technik -> Software.
"@
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
  }
  $release = Sende-Json -Uri "$api/releases" -Methode Post -Daten @{
    tag_name   = $tag
    name       = "CamperMaid Level $version"
    body       = $text
    draft      = $true
    prerelease = $istVorab
  }
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
# make_latest wird bei einer Vorabfassung ausdrücklich auf "false" gesetzt.
# GitHub würde sie zwar ohnehin nicht als neueste führen, solange prerelease
# gilt - aber wer den Haken später von Hand entfernt, hätte sonst schlagartig
# eine ungeprüfte Fassung auf allen Geräten. Zwei Schlösser statt einem.
$fertig = Sende-Json -Uri "$api/releases/$($release.id)" -Methode Patch -Daten @{
  draft       = $false
  prerelease  = $istVorab
  make_latest = $(if ($istVorab) { 'false' } else { 'true' })
}

Write-Host ""
Write-Host "Angelegt: $($fertig.html_url)"
Write-Host ""
if ($istVorab) {
  Write-Host "Als VORABFASSUNG markiert. Kein Gerät und kein HACS holt sie sich."
  Write-Host "Zum Erproben von Hand aufspielen:"
  Write-Host "   Geräteseite -> Technik -> Software -> Datei aufspielen"
  Write-Host "   oder aus dem Arbeitsstand:  esphome run campermaid-level.yaml"
  Write-Host ""
  Write-Host "Taugt die Fassung, den Bindestrich aus firmware_version und aus"
  Write-Host "manifest.json entfernen und erneut veröffentlichen. Erst dann"
  Write-Host "wird daraus eine Auslieferung."
} else {
  Write-Host "Als AUSLIEFERUNG markiert."
  Write-Host "Geräte mit Internet melden das Update innerhalb von 12 Stunden,"
  Write-Host "nach einem Neustart von Home Assistant sofort."
}
