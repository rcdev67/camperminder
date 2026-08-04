@echo off
rem Diese Datei ist in CP850 gespeichert - dort belegt jeder Umlaut genau
rem ein Byte. Nur deshalb ist das Umschalten gefahrlos: cmd.exe merkt sich die
rem Leseposition in Bytes, rechnet aber mit einem Zeichen je Byte. In einer
rem UTF-8-Datei verrutscht dadurch jede folgende Zeile.
chcp 850 >nul
rem ===========================================================================
rem  Bauen und auf GitHub verîffentlichen - zum Doppelklicken.
rem
rem  Macht alles, was bauen.cmd macht, und legt danach das Release an.
rem  Bewusst mit RÅckfrage: Ein Release ist îffentlich und wird von jedem
rem  GerÑt mit Internet innerhalb von zwîlf Stunden abgeholt.
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
echo  2/3  Release-AnhÑnge erzeugen
echo ============================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_release.ps1"
if not "%ERRORLEVEL%"=="0" ( echo. & pause & exit /b 1 )

echo.
echo ============================================================
echo  3/3  Auf GitHub verîffentlichen
echo ============================================================
echo.
echo Die Versionsnummer entscheidet, was daraus wird:
echo.
echo   mit Bindestrich  (2.0.4-rc1)  interne Vorabfassung, kein GerÑt
echo                                 und kein HACS holt sie sich
echo   ohne Bindestrich (2.0.4)      Auslieferung an alle GerÑte
echo.
echo Das Skript meldet gleich noch einmal, welcher Fall vorliegt.
echo.
set /p WEITER="Wirklich verîffentlichen? (j/n) "
if /i not "%WEITER%"=="j" ( echo Abgebrochen. & pause & exit /b 0 )

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0github_release.ps1"

echo.
pause
