# Blueprints für Home Assistant

Drei fertige Automatisierungen zum Importieren. Sie bringen die Meldungen des
Geräts dorthin, wo man sie liest — auf das Handy, an eine Sirene, an ein Licht.

| Blueprint | Meldet | Hängt an |
|---|---|---|
| [Kühlschrankwarnung](automation/camperminder/kuehlschrank_warnung.yaml) | Das Fahrzeug steht so lange schief, dass der Absorberkühlschrank leidet | `Kühlschrank Warnung` |
| [Wächteralarm](automation/camperminder/waechter_alarm.yaml) | Das Fahrzeug hat seine Lage verlassen — angehoben, aufgebockt, abgeschleppt | `Wächter Alarm` |
| [Frostwarnung](automation/camperminder/frostwarnung.yaml) | Es wird kalt im Fahrzeug | `Frostgefahr` |

## Warum an diesen Entitäten und nicht an den naheliegenden

Das ist der eigentliche Wert dieser drei Dateien — die Wahl der Auslöser:

- **Kühlschrank:** nicht `Schräglage`, sondern `Kühlschrank Warnung`. Ein
  Absorberkühlschrank nimmt keinen Schaden vom Winkel, sondern vom Winkel
  **mal der Zeit**. Das Gerät zählt die Zeit über dem Grenzwert
  ununterbrochen mit — auch wenn Home Assistant neu startet — und meldet erst,
  wenn es darauf ankommt. Wer an `Schräglage` hängt, wird beim Rangieren
  benachrichtigt.
- **Wächter:** nicht `Lageänderung`, sondern `Wächter Alarm`. Die
  Lageänderung ist ein Messwert und geht wieder aus, sobald das Fahrzeug in
  seine Lage zurückkommt; wer schläft, verpasst sie. Der Wächter rastet ein,
  bleibt stehen, bis er quittiert wird, und übersteht einen Stromausfall.
- **Frost:** der Grenzwert steht im Gerät und gilt auch ohne Home Assistant.
  Der Blueprint bringt die Meldung nur weiter.

## Benachrichtigung ist frei wählbar

Jeder Blueprint hat das Feld **„Was soll passieren?"**. Dort trägt man ein,
was man will: `notify.mobile_app_…`, eine anhaltende Meldung, ein Lautsprecher,
ein Licht, mehrere Dinge nacheinander. Der fertige Meldetext steht in der
Variablen `meldung` bereit — er kommt vom Gerät und nennt Winkel, Dauer oder
Uhrzeit.

Das ist mit Absicht kein festes Feld für einen Dienst: Was bei einem Kunden
die richtige Meldung ist, weiß niemand außer ihm.

## Einbauen

**Mit einem Klick** — der Link öffnet den Import im eigenen Home Assistant
(über my.home-assistant.io):

- [Kühlschrankwarnung importieren](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Frcdev67%2Fcamperminder%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fcamperminder%2Fkuehlschrank_warnung.yaml)
- [Wächteralarm importieren](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Frcdev67%2Fcamperminder%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fcamperminder%2Fwaechter_alarm.yaml)
- [Frostwarnung importieren](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Frcdev67%2Fcamperminder%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fcamperminder%2Ffrostwarnung.yaml)

**Von Hand** — *Einstellungen → Automatisierungen und Szenen → Blueprints →
Blueprint importieren*, dann die Adresse der gewünschten Datei aus diesem
Ordner einfügen (die `github.com`-Adresse, nicht die Rohdatei).

**Ohne Internet in Home Assistant** — Datei herunterladen und nach
`config/blueprints/automation/camperminder/` legen, dann *Entwicklerwerkzeuge
→ YAML → Automatisierungen neu laden*.

Danach *Automatisierung erstellen → Aus einem Blueprint*, die Entitäten
auswählen und die Benachrichtigung eintragen. Eine Handymeldung sieht etwa so
aus:

```yaml
action: notify.mobile_app_mein_handy
data:
  title: CamperMinder
  message: "{{ meldung }}"
```

Ein aktualisierter Blueprint kommt nicht von selbst: Im Menü ⋮ neben dem
Blueprint holt *erneut importieren* den neuen Stand, die eigenen
Automatisierungen bleiben dabei erhalten.

## Verhalten im Einzelnen

- **Kein Doppel nach einem Neustart.** Startet Home Assistant neu oder reißt
  die Verbindung zum Gerät kurz ab, springt ein Melder von „nicht verfügbar“
  auf „an“. Kühlschrank- und Frostwarnung melden das nicht noch einmal, wenn
  sie es in den letzten zwölf Stunden schon getan haben. Der Wächteralarm
  meldet dagegen jedes Mal — ein Alarm, der nicht quittiert ist, soll lieber
  einmal zu oft kommen.
- **Der Satz passt zum Alarm.** Den Meldetext schreibt das Gerät in einem
  eigenen Sensor, etwas später als der Melder umschaltet. Die Blueprints
  warten deshalb kurz (Wächter 2 s, Kühlschrank 6 s), damit nicht noch der
  Satz von vorher in der Meldung steht.
- **Wiederholen bis zum Quittieren** (nur Wächter): Wird quittiert, endet die
  Wiederholung sofort. Löst der Wächter danach erneut aus, kommt die Meldung
  sofort und nicht erst nach Ablauf der Wartezeit.

## Was diese Blueprints nicht können

**Sie erreichen dich nur, wenn Home Assistant dich erreicht.** Steht das
Fahrzeug auf einem Stellplatz und dein Telefon im Mobilfunknetz, hilft das nur
mit einem von außen erreichbaren Home Assistant. Für den Wächter gibt es einen
zweiten Weg ohne Home Assistant: Das Gerät schickt den Alarm selbst an einen
Push-Dienst (ntfy, Gotify, Telegram) — Geräteseite → Technik → Fernalarm.
