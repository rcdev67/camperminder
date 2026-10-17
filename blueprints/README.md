# Blueprints für Home Assistant

Vier fertige Automatisierungen zum Importieren. Sie bringen Meldungen dorthin,
wo man sie liest — auf das Handy, an eine Sirene, an ein Licht. Drei kommen
vom Gerät, die vierte von der Integration: der Wetterwächter für die Markise.

| Blueprint | Meldet | Hängt an |
|---|---|---|
| [Kühlschrankwarnung](automation/camperminder/kuehlschrank_warnung.yaml) | Das Fahrzeug steht so lange schief, dass der Absorberkühlschrank leidet | `Kühlschrank Warnung` |
| [Wächteralarm](automation/camperminder/waechter_alarm.yaml) | Das Fahrzeug hat seine Lage verlassen — angehoben, aufgebockt, abgeschleppt | `Wächter Alarm` |
| [Frostwarnung](automation/camperminder/frostwarnung.yaml) | Es wird kalt im Fahrzeug | `Frostgefahr` |
| [Wetterwächter Markise](automation/camperminder/markise_wetter.yaml) | Böen, Gewitter, Hagel, Schnee oder Starkregen sind angesagt — oder so viel Regen, dass die Markise eine Seite tiefer braucht | `Markise Warnung` |

## Warum an diesen Entitäten und nicht an den naheliegenden

Das ist der eigentliche Wert der drei Geräte-Blueprints — die Wahl der Auslöser:

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

## Wetterwächter Markise

Die Vorhersage bewertet die Integration, nicht der Blueprint. Dafür unter
*Einstellungen → Geräte & Dienste → CamperMinder → Konfigurieren* eine
Wetter-Entität wählen, am besten **Open-Meteo mit der Zone „Zuhause“**: Sie
folgt dem Heimatort (siehe „Heimatort folgt dem Fahrzeug“ in der Anleitung)
und liefert Böen. Dann gibt es am Gerät *CamperMinder* den Melder
`Markise Warnung` und vier Regler: Böen ab, mittlerer Wind ab, Regen ab,
Vorlauf. Dieselbe Warnung zeigt die Karte als gelbe Leiste.

Halbstündlich liest die Integration die stündliche Vorhersage für die
nächsten Stunden (*Vorlauf*, Vorgabe 3). Bei Böen, mittlerem Wind über der
Grenze, Gewitter, Hagel, Schnee, Starkregen oder Unwetter heißt die Meldung
*Markise einfahren*, mit Uhrzeit:

> Markise einfahren: ab 15 Uhr Böen bis 55 km/h, ab 16 Uhr Gewitter.

Ist nur Regen angesagt, aber genug davon (Vorgabe 5 mm im Vorlauf), kommt der
Hinweis zum Absenken. Eine waagerechte Markise sammelt das Wasser in der
Mitte, und an diesem Wassersack brechen die meisten:

> 6,2 mm Regen in den nächsten 3 Stunden: Markise auf einer Seite absenken,
> damit das Wasser abläuft.

- **Zwei Windgrenzen, weil nicht jede Wetterquelle Böen meldet.** Die Vorgabe
  von Home Assistant (met.no) liefert nur den mittleren Wind, OpenWeatherMap
  auch Böen. Vorgaben: Böen 40 km/h, mittlerer Wind 25 km/h. Es reicht, dass
  eine von beiden erreicht ist.
- **Einheiten egal.** Wind in m/s, mph oder Knoten und Regen in Zoll werden
  umgerechnet; die Grenzen gelten immer in km/h und mm.
- **Mit Melder für die Markise** (freiwillig, ebenfalls unter
  *Konfigurieren*: ein Endschalter, ein Markisenantrieb, notfalls ein
  Schalter-Helfer, den man selbst umlegt) gibt es die Warnung nur, solange sie
  ausgefahren ist, und beim Ausfahren wird sofort nachgesehen. Ohne Melder gilt
  jede Warnung.
- **Eine Meldung je Wetterlage.** Der Melder bleibt an, solange die Gefahr
  angesagt ist, und der Blueprint meldet nur den Wechsel auf „an“. Fällt die
  Gefahr aus der Vorhersage, bleibt die Warnung noch eine Stunde stehen, damit
  Werte an der Grenze nicht bei jeder neuen Vorhersage eine neue Meldung
  auslösen. Wer einen Regler verstellt, sieht das Ergebnis sofort.
- **Die Vorhersage muss für den Stellplatz gelten.** Die Wetter-Entität
  kennt nur den Ort ihrer Integration. Läuft Home Assistant zu Hause, ist das
  ohne weitere Einrichtung das Wetter von zu Hause, nicht das am Stellplatz.

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
- [Wetterwächter Markise importieren](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Frcdev67%2Fcamperminder%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fcamperminder%2Fmarkise_wetter.yaml)

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
