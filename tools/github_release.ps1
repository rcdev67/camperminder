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
#  ZUGANG: ein GitHub-Token mit Schreibrecht auf Inhalte. Drei Quellen, in
#  dieser Reihenfolge:
#
#    1. Umgebungsvariable CAMPERMINDER_GH_TOKEN
#    2. tools/github_token.txt  (durch .gitignore ausgeschlossen)
#    3. der Git Credential Manager - also das Token, mit dem `git push`
#       ohnehin schon arbeitet
#
#  Der dritte Weg ist der bequeme und braucht KEINE Pflege: Der Credential
#  Manager erneuert sein Token selbst. Von Hand angelegte Tokens laufen
#  dagegen ab - fein granulierte nach Voreinstellung schon nach 30 Tagen -,
#  und das merkt man immer erst mitten im Veröffentlichen.
#
#  Die ersten beiden bleiben, weil sie ausdrücklich sind: Wer ein bestimmtes
#  Token benutzen will (anderes Konto, engere Rechte, Bauknecht ohne
#  angemeldetes Git), setzt es und gewinnt damit gegen den Credential Manager.
#  Eine LEERE Datei zählt als nicht vorhanden - so wird man ein totes Token
#  los, ohne die Datei anfassen zu müssen.
#
#  Token von Hand erzeugen unter github.com/settings/tokens - fein granuliert,
#  nur dieses Repository, Berechtigung "Contents: Read and write".
# ============================================================================

$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $here

$owner = 'rcdev67'
$repo  = 'camperminder'

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

<#
.SYNOPSIS
  Das Token holen, mit dem Git bereits gegen github.com arbeitet.

.DESCRIPTION
  "git credential fill" fragt den eingerichteten Credential Manager. Der gibt
  ein OAuth-Token zurück und erneuert es bei Bedarf selbst - genau das, was
  einen sonst alle 30 Tage zwingt, von Hand ein neues anzulegen.

  Zwei Vorkehrungen gegen ein hängendes Skript: GIT_TERMINAL_PROMPT=0 und
  credential.interactive=false. Ohne sie könnte der Credential Manager auf
  einen Anmeldedialog warten - bei einem Skript, das per Doppelklick läuft,
  wäre das ein Fenster, das niemand erwartet.

  Die Anfrage geht über eine Datei und die Umleitung von cmd.exe, NICHT über
  die PowerShell-Pipeline und auch nicht über einen eigenen Datenstrom auf
  StandardInput. Beides wurde ausprobiert, beides scheitert unter Windows
  PowerShell 5.1 mit "fatal: refusing to work with credential missing protocol
  field" - Git bekommt die Zeilen schlicht nicht zu sehen, obwohl die
  geschriebenen Bytes nachweislich stimmen (32 Byte, reines LF, kein BOM).
  Die Umleitung umgeht die Verrohrung vollständig.

  In der Datei steht nur die FRAGE ("welches Token gilt für github.com?"),
  niemals die Antwort - das Token kommt über die Ausgabe zurück und bleibt in
  einer Variablen. Auf der Platte landet es nicht.
#>
function Hole-GitToken {
  $alt = $env:GIT_TERMINAL_PROMPT
  $env:GIT_TERMINAL_PROMPT = '0'
  $frage = Join-Path ([IO.Path]::GetTempPath()) ("camperminder-cred-" + [guid]::NewGuid().ToString('N') + ".txt")
  try {
    # Zeilenenden ausdrücklich als LF: Git erwartet das Format so, ein CR
    # landete sonst im Wert des letzten Feldes.
    [IO.File]::WriteAllText(
      $frage,
      "protocol=https`nhost=github.com`n`n",
      (New-Object System.Text.UTF8Encoding($false)))

    $ausgabe = cmd /c "git -c credential.interactive=false credential fill < ""$frage"" 2>NUL"
    foreach ($zeile in @($ausgabe)) {
      if ($zeile -match '^password=(.+)$') { return $matches[1].Trim() }
    }
    return $null
  } catch {
    return $null
  } finally {
    if (Test-Path $frage) { Remove-Item $frage -Force -ErrorAction SilentlyContinue }
    $env:GIT_TERMINAL_PROMPT = $alt
  }
}

$quelle = $null
$token = $env:CAMPERMINDER_GH_TOKEN
if ($token) { $quelle = 'Umgebungsvariable CAMPERMINDER_GH_TOKEN' }

if (-not $token) {
  $tf = Join-Path $here 'github_token.txt'
  # Eine leere Datei zählt als nicht vorhanden - siehe Kopf.
  #
  # Erst prüfen, dann trimmen: "Get-Content -Raw" liefert bei einer leeren
  # Datei $null, und $null.Trim() wirft "Es ist nicht möglich, eine Methode
  # für einen Ausdruck aufzurufen, der den Wert NULL hat". Das Leeren der
  # Datei ist aber gerade der vorgesehene Weg, ein totes Token loszuwerden -
  # er darf nicht mit einem Fehler enden.
  if (Test-Path $tf) {
    $ausDatei = Get-Content $tf -Raw
    if ($ausDatei) { $ausDatei = $ausDatei.Trim() }
    if ($ausDatei) { $token = $ausDatei; $quelle = 'tools\github_token.txt' }
  }
}

if (-not $token) {
  $token = Hole-GitToken
  if ($token) { $quelle = 'Git Credential Manager (dasselbe wie bei git push)' }
}

if (-not $token) {
  throw @"
Kein Token gefunden. Drei Wege, einer genügt:

  1. Am bequemsten: einmal 'git push' zum Laufen bringen, dann benutzt dieses
     Skript dasselbe Token - es erneuert sich von selbst.
  2. tools\github_token.txt anlegen (fein granuliert, nur dieses Repository,
     Berechtigung "Contents: Read and write").
  3. Umgebungsvariable CAMPERMINDER_GH_TOKEN setzen.
"@
}

$kopf = @{
  Authorization          = "Bearer $token"
  Accept                 = 'application/vnd.github+json'
  'X-GitHub-Api-Version' = '2022-11-28'
  'User-Agent'           = 'camperminder-release'
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
Write-Host "Token:      $quelle"

# --- Token sofort prüfen, nicht erst beim Anlegen --------------------------
# Ein ungültiges Token fiel bisher erst beim Erzeugen des Entwurfs auf: mitten
# im Ablauf, nach dem Bauen und nach der Rückfrage, und mit einem nackten
# "(401) Nicht autorisiert" samt PowerShell-Stapel. Ein Lesezugriff vorweg
# kostet nichts und sagt im Klartext, was fehlt.
try {
  Invoke-RestMethod -Uri $api -Headers $kopf -Method Get | Out-Null
} catch {
  $code = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
  if ($code -eq 401) {
    throw @"
GitHub weist das Token ab (401, "Bad credentials").
Quelle: $quelle

Das Token ist abgelaufen oder widerrufen - um Berechtigungen geht es hier noch
gar nicht, GitHub kennt es schlicht nicht. Von Hand angelegte Tokens laufen
ab, fein granulierte nach Voreinstellung schon nach 30 Tagen.

Der Ausweg ohne Pflege: tools\github_token.txt leeren oder löschen und
CAMPERMINDER_GH_TOKEN nicht setzen. Dann nimmt dieses Skript das Token des Git
Credential Managers - dasselbe, mit dem 'git push' arbeitet, und das erneuert
sich von selbst.
"@
  }
  if ($code -eq 403 -or $code -eq 404) {
    throw @"
GitHub antwortet mit $code auf $api.
Quelle: $quelle

Das Token ist gültig, darf dieses Repository aber nicht schreiben (404 statt
403 kommt, wenn es das Repository nicht einmal sehen darf). Nötig ist
"Contents: Read and write" für rcdev67/camperminder.
"@
  }
  throw
}
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
CamperMinder Level $version - interne Vorabfassung

Diese Fassung ist **nicht zur Verwendung bestimmt**. Sie dient der Erprobung
vor einer Auslieferung.

Geräte erhalten sie nicht von selbst: Die Aktualisierungsprüfung folgt
``releases/latest``, und dort werden Vorabfassungen ausgelassen. Wer sie
dennoch aufspielen will, lädt ``level-firmware.ota.bin`` von Hand über
Geräteseite -> Technik -> Software.
"@
  } else {
    $text = @"
CamperMinder Level $version

Firmware für CamperMinder Level.

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
    name       = "CamperMinder Level $version"
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
  Write-Host "   oder aus dem Arbeitsstand:  esphome run camperminder-level.yaml"
  Write-Host ""
  Write-Host "Taugt die Fassung, den Bindestrich aus firmware_version und aus"
  Write-Host "manifest.json entfernen und erneut veröffentlichen. Erst dann"
  Write-Host "wird daraus eine Auslieferung."
} else {
  Write-Host "Als AUSLIEFERUNG markiert."
  Write-Host "Geräte mit Internet melden das Update innerhalb von 12 Stunden,"
  Write-Host "nach einem Neustart von Home Assistant sofort."
}
