@echo off
rem Diese Datei ist in CP850 gespeichert - dort belegt jeder Umlaut genau
rem ein Byte. Nur deshalb ist das Umschalten gefahrlos: cmd.exe merkt sich die
rem Leseposition in Bytes, rechnet aber mit einem Zeichen je Byte. In einer
rem UTF-8-Datei verrutscht dadurch jede folgende Zeile.
chcp 850 >nul
rem ===========================================================================
rem  Anleitung fuer die Testgeraete als PDF - zum Doppelklicken.
rem
rem  Quelle ist docs\anleitung-prototyp.md. Das PDF entsteht daraus neu und
rem  wird nie von Hand bearbeitet - wer etwas aendern will, aendert die .md.
rem
rem  Ergebnis:  druck\CamperMinder-Level-Anleitung.pdf
rem
rem  Liegt esphome\level\secrets.yaml vor, steht der API-Schluessel im PDF
rem  (Kurzkarte auf Seite 1, QR-Code in Abschnitt 11). Deshalb ist druck\
rem  durch .gitignore ausgeschlossen: an Tester weitergeben ja, ins
rem  Repository oder oeffentlich ins Netz nein.
rem ===========================================================================

setlocal
set ROOT=%~dp0..
set PY=%ROOT%\.venv\Scripts\python.exe

call "%~dp0einrichten.cmd"
if errorlevel 1 exit /b 1

"%PY%" -c "import markdown, qrcode" >nul 2>nul
if not errorlevel 1 goto :drucken

echo.
echo Einmalig: Werkzeuge fuer das PDF einrichten ...
"%PY%" -m pip install --disable-pip-version-check -q markdown qrcode
if errorlevel 1 (
  echo.
  echo FEHLER: markdown und qrcode liessen sich nicht installieren.
  echo Besteht eine Internetverbindung?
  echo.
  pause
  exit /b 1
)

:drucken
echo.
echo ============================================================
echo  Anleitung als PDF erzeugen
echo ============================================================
"%PY%" "%~dp0anleitung_pdf.py"
if errorlevel 1 (
  echo.
  pause
  exit /b 1
)

start "" "%ROOT%\druck\CamperMinder-Level-Anleitung.pdf"
echo.
pause
