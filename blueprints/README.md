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

**Über die Benutzeroberfläche** — *Einstellungen → Automatisierungen und
Szenen → Blueprints → Blueprint importieren*, dann die Adresse der
gewünschten Datei aus diesem Ordner einfügen (die `github.com`-Adresse, nicht
die Rohdatei).

> Solange das Repository nicht öffentlich ist, funktioniert der Import über
> die Adresse nicht. Bis dahin: Datei herunterladen und nach
> `config/blueprints/automation/camperminder/` legen, dann in Home Assistant
> *Entwicklerwerkzeuge → YAML → Automatisierungen neu laden*.

Danach *Automatisierung erstellen → Aus einem Blueprint*, die Entitäten
auswählen und die Benachrichtigung eintragen.

## Was diese Blueprints nicht können

**Sie erreichen dich nur im eigenen Netz.** Home Assistant meldet dorthin, wo
es hinkommt; steht das Fahrzeug auf einem Stellplatz und dein Telefon im
Mobilfunknetz, hilft das nur mit einem von außen erreichbaren Home Assistant.
Der Weg dafür steht in `docs/produktentscheidungen.md` unter „Fernalarm" — er
ist bewusst noch nicht gebaut.
