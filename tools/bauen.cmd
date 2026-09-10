@echo off
rem Diese Datei ist in CP850 gespeichert - dort belegt jeder Umlaut genau
rem ein Byte. Nur deshalb ist das Umschalten gefahrlos: cmd.exe merkt sich die
rem Leseposition in Bytes, rechnet aber mit einem Zeichen je Byte. In einer
rem UTF-8-Datei verrutscht dadurch jede folgende Zeile.
chcp 850 >nul
rem ===========================================================================
rem  CamperMinder Level bauen - zum Doppelklicken.
rem
rem  Ruft esphome direkt aus der virtuellen Umgebung auf. Ein "Aktivieren" der
rem  Umgebung wÑre hier nicht nur unnîtig, sondern scheitert auf vielen
rem  Rechnern an der PowerShell-AusfÅhrungsrichtlinie.
rem
rem  Erzeugt danach die Release-AnhÑnge in  release/  - fertig zum Hochladen,
rem  aber ohne etwas zu verîffentlichen. Das macht veroeffentlichen.cmd.
rem ===========================================================================

setlocal
set ROOT=%~dp0..
set ESPHOME=%ROOT%\.venv\Scripts\esphome.exe

rem Beim ersten Start auf einem Rechner richtet sich ESPHome selbst ein,
rem statt mit einer Anleitung abzubrechen, die eine Konsole voraussetzt.
call "%~dp0einrichten.cmd"
if errorlevel 1 exit /b 1

if not exist "%ROOT%\esphome\level\secrets.yaml" (
  echo.
  echo FEHLER: esphome\level\secrets.yaml fehlt.
  echo Vorlage: esphome\level\secrets.yaml.example
  echo.
  echo ACHTUNG, nicht einfach einen neuen Schluessel erzeugen: Der
  echo camperminder_api_key steckt in jedem ausgelieferten Geraet und auf
  echo jedem Aufkleber. Er muss derselbe sein wie auf dem Rechner, auf dem
  echo bisher gebaut wurde - sonst erreicht Home Assistant die Geraete
  echo nicht mehr. Die Datei uebernehmen, nicht neu anlegen.
  echo.
  pause
  exit /b 1
)

echo ============================================================
echo  Firmware bauen
echo ============================================================
pushd "%ROOT%\esphome\level"
"%ESPHOME%" compile camperminder-level.yaml
set BUILD=%ERRORLEVEL%
popd

if not "%BUILD%"=="0" (
  echo.
  echo Der Build ist fehlgeschlagen. Meldung oben lesen.
  echo.
  pause
  exit /b %BUILD%
)

echo.
echo ============================================================
echo  Release-AnhÑnge erzeugen
echo ============================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_release.ps1"

echo.
echo Fertig. Die Dateien liegen in  release\
echo Zum Verîffentlichen:  veroeffentlichen.cmd
echo.
pause
