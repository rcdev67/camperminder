@echo off
rem Diese Datei ist in CP850 gespeichert - dort belegt jeder Umlaut genau
rem ein Byte. Nur deshalb ist das Umschalten gefahrlos: cmd.exe merkt sich die
rem Leseposition in Bytes, rechnet aber mit einem Zeichen je Byte. In einer
rem UTF-8-Datei verrutscht dadurch jede folgende Zeile.
chcp 850 >nul
rem ===========================================================================
rem  Sorgt dafuer, dass ESPHome bereitsteht. Wird von bauen.cmd und
rem  veroeffentlichen.cmd aufgerufen - nicht von Hand.
rem
rem  WARUM ES DAS GIBT: Bisher brach der Bau ab und nannte zwei Befehle, die
rem  man in einer Konsole eintippen sollte. Genau dieser Umweg soll durch den
rem  Doppelklick entfallen - und beim ersten Mal auf einem neuen Rechner traf
rem  er einen zwangslaeufig. Seither zieht der Bau sein Werkzeug selbst nach.
rem
rem  Der Ordner .venv ist durch .gitignore ausgeschlossen. Er gehoert zum
rem  Rechner, nicht zum Projekt: Wer ihn loescht, bekommt beim naechsten
rem  Doppelklick einen neuen.
rem
rem  Rueckgabe: 0 wenn ESPHome bereitsteht, sonst 1.
rem ===========================================================================

setlocal
set ROOT=%~dp0..
set ESPHOME=%ROOT%\.venv\Scripts\esphome.exe

if exist "%ESPHOME%" exit /b 0

echo.
echo ============================================================
echo  Erster Start auf diesem Rechner
echo ============================================================
echo.
echo ESPHome fehlt noch und wird jetzt einmalig eingerichtet unter
echo   %ROOT%\.venv
echo.
echo Das dauert einige Minuten und braucht Internet. Beim naechsten
echo Mal entfaellt es.
echo.

rem Erst den Python-Starter, dann python.exe. "where" setzt errorlevel 1,
rem wenn nichts gefunden wurde.
set "PY="
where py >nul 2>nul
if not errorlevel 1 set "PY=py -3"
if defined PY goto :habe_python

where python >nul 2>nul
if not errorlevel 1 set "PY=python"
if defined PY goto :habe_python

echo FEHLER: Auf diesem Rechner ist kein Python zu finden.
echo.
echo Python von python.org installieren und bei der Installation
echo   "Add python.exe to PATH"
echo ankreuzen. Danach bauen.cmd erneut doppelklicken.
echo.
pause
exit /b 1

:habe_python
echo Python gefunden: %PY%
echo.
%PY% -m venv "%ROOT%\.venv"
if errorlevel 1 goto :fehlgeschlagen

"%ROOT%\.venv\Scripts\python.exe" -m pip install --upgrade pip
"%ROOT%\.venv\Scripts\python.exe" -m pip install esphome
if errorlevel 1 goto :fehlgeschlagen
if not exist "%ESPHOME%" goto :fehlgeschlagen

echo.
echo Eingerichtet:
"%ESPHOME%" version
echo.
exit /b 0

:fehlgeschlagen
echo.
echo FEHLER: Das Einrichten ist fehlgeschlagen - Meldung oben lesen.
echo.
echo Haeufigste Ursachen: kein Internet, oder ein Virenscanner haelt die
echo Installation auf. Der halbfertige Ordner .venv laesst sich gefahrlos
echo loeschen, dann faengt der naechste Versuch sauber an.
echo.
pause
exit /b 1
