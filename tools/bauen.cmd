@echo off
rem ===========================================================================
rem  CamperMaid Level bauen - zum Doppelklicken.
rem
rem  Ruft esphome direkt aus der virtuellen Umgebung auf. Ein "Aktivieren" der
rem  Umgebung waere hier nicht nur unnoetig, sondern scheitert auf vielen
rem  Rechnern an der PowerShell-Ausfuehrungsrichtlinie.
rem
rem  Erzeugt danach die Release-Anhaenge in  release/  - fertig zum Hochladen,
rem  aber ohne etwas zu veroeffentlichen. Das macht veroeffentlichen.cmd.
rem ===========================================================================

setlocal
set ROOT=%~dp0..
set ESPHOME=%ROOT%\.venv\Scripts\esphome.exe

if not exist "%ESPHOME%" (
  echo.
  echo FEHLER: ESPHome nicht gefunden unter
  echo   %ESPHOME%
  echo.
  echo Einmalig einrichten:
  echo   python -m venv "%ROOT%\.venv"
  echo   "%ROOT%\.venv\Scripts\python.exe" -m pip install esphome
  echo.
  pause
  exit /b 1
)

if not exist "%ROOT%\esphome\level\secrets.yaml" (
  echo.
  echo FEHLER: esphome\level\secrets.yaml fehlt.
  echo Vorlage: esphome\level\secrets.yaml.example
  echo.
  pause
  exit /b 1
)

echo ============================================================
echo  Firmware bauen
echo ============================================================
pushd "%ROOT%\esphome\level"
"%ESPHOME%" compile campermaid-level.yaml
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
echo  Release-Anhaenge erzeugen
echo ============================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_release.ps1"

echo.
echo Fertig. Die Dateien liegen in  release\
echo Zum Veroeffentlichen:  veroeffentlichen.cmd
echo.
pause
