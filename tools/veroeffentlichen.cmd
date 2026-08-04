@echo off
rem ===========================================================================
rem  Bauen und auf GitHub veroeffentlichen - zum Doppelklicken.
rem
rem  Macht alles, was bauen.cmd macht, und legt danach das Release an.
rem  Bewusst mit Rueckfrage: Ein Release ist oeffentlich und wird von jedem
rem  Geraet mit Internet innerhalb von zwoelf Stunden abgeholt.
rem ===========================================================================

setlocal
set ROOT=%~dp0..
set ESPHOME=%ROOT%\.venv\Scripts\esphome.exe

if not exist "%ESPHOME%" (
  echo FEHLER: ESPHome nicht gefunden. Siehe bauen.cmd.
  pause & exit /b 1
)
if not exist "%ROOT%\esphome\level\secrets.yaml" (
  echo FEHLER: esphome\level\secrets.yaml fehlt.
  pause & exit /b 1
)

echo ============================================================
echo  1/3  Firmware bauen
echo ============================================================
pushd "%ROOT%\esphome\level"
"%ESPHOME%" compile campermaid-level.yaml
set BUILD=%ERRORLEVEL%
popd
if not "%BUILD%"=="0" ( echo. & echo Build fehlgeschlagen. & pause & exit /b %BUILD% )

echo.
echo ============================================================
echo  2/3  Release-Anhaenge erzeugen
echo ============================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_release.ps1"
if not "%ERRORLEVEL%"=="0" ( echo. & pause & exit /b 1 )

echo.
echo ============================================================
echo  3/3  Auf GitHub veroeffentlichen
echo ============================================================
echo.
echo Dies legt ein oeffentliches Release an. Geraete mit Internet
echo holen es sich anschliessend selbst.
echo.
set /p WEITER="Wirklich veroeffentlichen? (j/n) "
if /i not "%WEITER%"=="j" ( echo Abgebrochen. & pause & exit /b 0 )

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0github_release.ps1"

echo.
pause
