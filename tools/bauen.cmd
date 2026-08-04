@echo off
rem Konsole auf UTF-8, sonst zeigt cmd.exe die Umlaute falsch an.
chcp 65001 >nul
rem ===========================================================================
rem  CamperMaid Level bauen - zum Doppelklicken.
rem
rem  Ruft esphome direkt aus der virtuellen Umgebung auf. Ein "Aktivieren" der
rem  Umgebung wäre hier nicht nur unnötig, sondern scheitert auf vielen
rem  Rechnern an der PowerShell-Ausführungsrichtlinie.
rem
rem  Erzeugt danach die Release-Anhänge in  release/  - fertig zum Hochladen,
rem  aber ohne etwas zu veröffentlichen. Das macht veroeffentlichen.cmd.
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
echo  Release-Anhänge erzeugen
echo ============================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_release.ps1"

echo.
echo Fertig. Die Dateien liegen in  release\
echo Zum Veröffentlichen:  veroeffentlichen.cmd
echo.
pause
