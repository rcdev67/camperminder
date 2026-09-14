# CamperMinder Level — Anleitung für Testgeräte

Diese Anleitung ist für alle, die ein **Testgerät** bekommen haben: ein kleines
Gehäuse mit ESP32-C3 SuperMini und Lagesensor MPU6050, Firmware **3.9.2**.
Sie erklärt, was das Gerät kann, wie man es einbaut und einrichtet, welche
Einstellungen wichtig sind und wie es mit Home Assistant und MQTT
zusammenarbeitet.

> **Danke fürs Mittesten.** Das Gerät ist ein Prototyp. Alles, was dir
> auffällt — was nicht klappt, was unklar ist, was fehlt —, hilft. Am
> nützlichsten ist eine Rückmeldung mit Firmware-Version (steht unter
> *Technik → Software*) und einem Satz dazu, was du gerade gemacht hast.

## Auf einen Blick

| | |
|---|---|
| **WLAN des Geräts** | `CamperMinder` — ohne Passwort, nach etwa 20 s |
| **Geräteseite** | `192.168.4.1` im Browser eintippen |
| **Nach jeder Änderung** | eine Minute Strom lassen, dann ist sie gespeichert |
| **API-Schlüssel** (nur für Home Assistant) | <!--API-->liegt dem Gerät bei<!--/API--> |
| **Firmware** | 3.9.2 — Updates unter *Technik → Software* |

---

## Inhalt

1. [Was das Gerät kann](#1-was-das-gerät-kann)
2. [Was das Testgerät nicht hat](#2-was-das-testgerät-nicht-hat)
3. [Einbauen und Strom](#3-einbauen-und-strom)
4. [Erster Start: mit dem Handy verbinden](#4-erster-start-mit-dem-handy-verbinden)
5. [Die wichtigen Einstellungen](#5-die-wichtigen-einstellungen)
6. [Kalibrieren](#6-kalibrieren)
7. [Im Alltag: Ausrichten, Zielprofil, Wächter](#7-im-alltag-ausrichten-zielprofil-wächter)
8. [Heim-WLAN und Updates](#8-heim-wlan-und-updates)
9. [Home Assistant](#9-home-assistant)
10. [MQTT](#10-mqtt)
11. [Der API-Schlüssel für Home Assistant](#11-der-api-schlüssel-für-home-assistant)
12. [Wenn etwas nicht klappt](#12-wenn-etwas-nicht-klappt)
13. [Anhang für Selbstbauer: die `secrets.yaml`](#anhang-für-selbstbauer-die-secretsyaml)

---

## 1. Was das Gerät kann

CamperMinder Level misst dauerhaft die Neigung des Fahrzeugs und sagt dir,
**welche Ecke wie viele Zentimeter** hoch muss. Es arbeitet eigenständig —
Handy zum Gerät, fertig. Kein Router, keine App, kein Konto. Home Assistant
und MQTT sind freiwillige Zugaben auf derselben Firmware.

| Funktion | Was sie tut |
|---|---|
| **Ausrichten** | Zwei Wasserwaagen (quer, längs), Seiten- und Heckansicht, Anweisung im Klartext wie „Hinten links 4.5 cm hoch“, auf Wunsch in Keilstufen |
| **Wohnmobil und Wohnwagen** | Beim Wohnwagen rechnet es mit Achse und Stützrad statt mit vier Rädern |
| **Keile oder Hebesystem** | Anweisung passend zu Auffahrkeilen oder Hydraulik/Luftkissen |
| **Präzisionsmodus** | Toleranz in Grad statt Zentimetern, Winkel mit zwei Nachkommastellen |
| **Zielprofile** | *Schlafen* (z. B. Kopfende etwas höher) und *Ablassen* (Neigung zum Ablasspunkt), statt immer nur „eben“ |
| **Kühlschrank-Warnung** | Ein Absorberkühlschrank verträgt etwa 3° Schräglage nicht dauerhaft. Das Gerät zählt die Zeit und warnt in Stufen |
| **Wächter** | Scharf geschaltet merkt es sich die Lage. Wird das Fahrzeug angehoben, abgeschleppt oder aufgebockt, rastet ein Alarm ein, der auch einen Stromausfall übersteht |
| **Selbstüberwachung** | Meldet, wenn die Kalibrierung wegen Temperatur fraglich wird oder das Gehäuse sich gelöst hat. Dazu Innentemperatur und Frostwarnung |
| **Updates** | Neue Fassungen kommen von GitHub — über Home Assistant oder einen Knopf auf der Geräteseite, ohne Kabel |
| **Home Assistant** | Alle Werte und Einstellungen als Entitäten, dazu eine eigene Bedienkarte und Sprachansagen |
| **MQTT** | Neigung, Hubhöhen und Anweisung für Victron Cerbo GX, ioBroker, Node-RED usw. |

---

## 2. Was das Testgerät nicht hat

- **Kein Display.** Angezeigt wird alles auf dem Handy. Im Log steht eine
  Fehlermeldung zu einem fehlenden OLED an 0x3C — die ist bei diesem Gerät
  erwartet und harmlos.
- **Keine Status-LED-Meldungen und keinen Summer.** Beides gehört zur
  nächsten Gerätegeneration.
- **Kurze Funkreichweite.** Die verbaute Platine (ESP32-C3 SuperMini) hat eine
  schwache Antenne; die Sendeleistung ist deshalb bewusst gedrosselt. Im
  selben Raum und auf einige Meter geht es gut, **durch eine gemauerte Wand
  nicht**. Wie gut es durch eine Fahrzeugwand kommt, ist noch nicht gemessen —
  eine Rückmeldung dazu hilft. Das eigene Netz des Geräts ist für die Nähe
  gedacht — so, wie man es auf dem Stellplatz benutzt.

---

## 3. Einbauen und Strom

### Strom

Das Gerät bekommt **5 V über die USB-C-Buchse**. Ein übliches USB-Ladegerät
oder eine USB-Steckdose im Fahrzeug genügt.

> **Für den Wächter und die Kühlschrank-Warnung** muss das Gerät auch dann Strom
> haben, wenn die Zündung aus ist. Viele USB-Buchsen im Cockpit schalten mit
> der Zündung ab — dann besser eine Buchse am Aufbau-Stromkreis nehmen.

### Einbauort und Lage

1. **Fest** einbauen — geklebt oder geschraubt, nicht lose in eine Schublade.
   Ein Gehäuse, das rutscht oder klappert, misst Unsinn.
2. Möglichst **waagerecht**, an einer Stelle, die sich nicht verzieht
   (Möbelkorpus, Boden, stabiles Regal — keine dünne Klappe).
3. Der **Pfeil auf dem Gehäuse zeigt nach vorn** in Fahrtrichtung.
4. Nicht direkt an Heizung, Kühlschrank-Lüftungsgitter oder in die Sonne —
   Temperaturschwankungen verschieben den Nullpunkt.

Zwei Einbaulagen sind vorgesehen:

| Einbaulage | Bedeutung |
|---|---|
| **Deckel oben** | Gehäuse steht auf seiner Unterseite — der Normalfall |
| **Deckel unten** | Gehäuse klebt unter einem Regalbrett oder an der Decke; der Pfeil zeigt trotzdem nach vorn |

Welche du gewählt hast, stellst du nach dem ersten Start auf der Geräteseite
ein (Abschnitt 5).

---

## 4. Erster Start: mit dem Handy verbinden

Das Gerät bringt **kein WLAN** mit. Beim Einschalten öffnet es nach etwa
20 Sekunden sein eigenes Netz.

1. Gerät mit Strom versorgen, 20 Sekunden warten.
2. Am Handy in die WLAN-Liste gehen und **CamperMinder** wählen — **ohne
   Passwort**. Das Handy warnt, das Netz sei ungesichert; das ist so gewollt.
   Manche Handys fragen außerdem, ob sie im Netz ohne Internet bleiben
   sollen — mit *Ja* bestätigen.
3. Im Browser **`192.168.4.1`** eintippen. Die Seite öffnet sich *nicht* von
   selbst.
4. Im Browsermenü **Zum Startbildschirm hinzufügen** wählen. Dann öffnet ein
   Symbol die Seite künftig im Vollbild, wie eine App.

Die Seite hat zwei Reiter:

| Reiter | Inhalt |
|---|---|
| **Anzeige** | Wasserwaagen, Anweisung, Kalibrieren, Zielprofil, Wächter — und darunter alle Einstellungen |
| **Technik** | alle Messwerte als Liste, Software-Update, WLAN, eigenes Netz, MQTT, Zurücksetzen |

> **Wer das eigene Netz abschließen will:** *Technik → Eigenes Netz*, ein
> Passwort mit mindestens acht Zeichen eintragen. Leer speichern öffnet es
> wieder. Wer es vergessen hat, kommt über *Zurücksetzen* wieder heran (das
> löscht allerdings auch die Einstellungen).
>
> Ohne Passwort kann jeder in Funkreichweite die Geräteseite öffnen — und damit
> auch Einstellungen ändern oder eine Firmwaredatei aufspielen. Auf einem
> vollen Stellplatz ist ein Passwort deshalb eine gute Idee.

---

## 5. Die wichtigen Einstellungen

Alle Einstellungen stehen im Reiter **Anzeige**, unterhalb der Wasserwaagen.
Sie liegen **im Gerät**, nicht im Handy — jedes Handy sieht dieselben Werte.

> **Nach dem Ändern eine Minute Strom lassen.** Das Gerät schreibt geänderte
> Werte einmal pro Minute dauerhaft weg. Wer direkt danach den Stecker zieht,
> findet beim nächsten Start die alten Werte vor.

### Fahrzeug — zuerst einstellen

| Einstellung | Was eintragen |
|---|---|
| **Fahrzeugart** | *Wohnmobil* oder *Wohnwagen* |
| **Radstand (mm)** | Mitte Vorderachse bis Mitte Hinterachse. Beim Wohnwagen heißt das Feld *Achse → Stützrad* |
| **Spurweite (mm)** | Mitte linkes Rad bis Mitte rechtes Rad |
| **Womit ausrichten** | *Auffahrkeile* oder *Hydraulik/Luftkissen* (nur Wohnmobil) |
| **Toleranz (cm)** | Ab wie viel Höhenunterschied es dich stört. 5 cm ist ein guter Anfang |
| **Keilstufe (cm)** | Höhengewinn einer Stufe deiner Auffahrkeile. 0 = Anweisung in Zentimetern |
| **Präzisionsmodus** | Aus: Toleranz in cm, innerhalb davon steht alles in der Mitte. Ein: feste Gradtoleranz („Toleranz genau“), Blase an ihrer echten Stelle |

**Radstand und Spurweite sind wichtig**: Aus ihnen rechnet das Gerät aus einem
Winkel die Zentimeter an jeder Ecke — und ab wann „eben“ gilt. Falsche Maße
geben falsche Anweisungen, obwohl der Sensor richtig misst.

### Gerät

| Einstellung | Was eintragen |
|---|---|
| **Einbaulage** | *Deckel oben* oder *Deckel unten* — siehe Abschnitt 3. **Nach dem Umstellen neu kalibrieren** |
| **Driftwarnung ab (K)** | Wie weit die Temperatur von der beim Kalibrieren abweichen darf, bevor das Gerät zum Nachkalibrieren rät. Vorgabe 20 |
| **Temperatur Abgleich (K)** | Einmal gegen ein Thermometer im Fahrzeug ablesen und die Differenz eintragen. Nötig für eine brauchbare Frostwarnung |

### Anzeige

| Einstellung | Wirkung |
|---|---|
| **Anzeigeruhe (0–10)** | klein: folgt jeder Regung, zappelt mehr. Groß: steht ruhig, reagiert etwas später |
| **Haltebereich (%)** | Wie weit es über die Toleranz hinausgehen darf, bis „eben“ wieder verschwindet. Höher setzen, wenn die Anzeige an der Grenze hin und her springt |

### Ziele

Die Zahlen hinter den Zielprofilen (Abschnitt 7). Plus heißt **Front höher**
bzw. **rechte Seite höher**.

| Einstellung | Vorgabe |
|---|---|
| **Schlafen längs (cm)** | −2, also Heck etwas höher — für Betten hinten. Wer vorn schläft, dreht das Vorzeichen um |
| **Ablassen längs / quer (cm)** | 5 / 0 — je nachdem, wo dein Ablasspunkt sitzt |

### Warnungen

| Einstellung | Vorgabe / Bedeutung |
|---|---|
| **Schräglage ab (°)** | 3 — Grenze für den Absorberkühlschrank |
| **Kühlschrank kritisch nach (min)** | Warnung nach einem Drittel dieser Zeit, dringend nach der vollen |
| **Lageänderung ab (°)** | Ab wann der Wächter anschlägt. Wind und Einsteigen bleiben darunter |
| **Frostwarnung unter (°C)** | 3 — funktioniert nur ordentlich mit gesetztem Temperatur-Abgleich |
| **Karenzzeit Wächter (s)** | Zeit zum Aussteigen nach dem Scharfschalten |

---

## 6. Kalibrieren

Einmal nach dem Einbau, und immer nach Umstellen der Einbaulage.

1. Fahrzeug **so exakt wie möglich waagerecht** stellen — mit einer echten
   Wasserwaage, längs **und** quer, z. B. auf dem Kühlschrankboden oder dem
   Tisch. Das ist die größte Fehlerquelle: Was hier schief steht, steckt
   dauerhaft in allen späteren Zentimeterangaben.
2. Niemand bewegt sich im Fahrzeug.
3. Im Reiter *Anzeige* **Neigung kalibrieren** drücken, 5 Sekunden warten.
4. Beide Wasserwaagen stehen jetzt auf **EBEN**.
5. **Eine Minute Strom lassen**, damit der Nullpunkt dauerhaft gespeichert ist.

**Kurzer Richtungstest danach** — lohnt sich, weil ein falsch herum
eingebautes Gerät völlig plausible Zahlen zeigt:

- **Vorn anheben** (oder vorn auf einen Keil fahren) → die Anzeige verlangt
  **HECK hoch**.
- **Rechte Seite anheben** → die Anzeige verlangt **LINKE Seite hoch**.

Stimmt eine Richtung nicht: Pfeil wirklich nach vorn? Einbaulage richtig
eingestellt? Wenn beides passt, bitte melden — dann ist das Gerät intern
anders herum bestückt als erwartet.

---

## 7. Im Alltag: Ausrichten, Zielprofil, Wächter

### Ausrichten

Seite öffnen, der Anweisung folgen, bis **✅ EBEN – STOP** erscheint. Die
Farben: grün eben, gelb nah dran, rot weit weg.

### Zielprofil

Im Kasten **Zielprofil** auf der Hauptseite:

| Profil | Wofür |
|---|---|
| **Ausrichten** | eben, wie gewohnt |
| **Schlafen** | steht so, wie du es zum Schlafen willst — „EBEN“ heißt dann „am Ziel“ |
| **Ablassen** | neigt zum Ablasspunkt, damit Boiler und Tank leer laufen |

Das Profil wirkt nur aufs Ausrichten. Kühlschrank-Warnung und Wächter rechnen
immer mit der echten Neigung.

### Wächter

1. Fahrzeug abstellen, **Scharf schalten**.
2. Während der Karenzzeit aussteigen.
3. Ab dann meldet das Gerät, wenn das Fahrzeug seine Lage verlässt. Eine
   Erschütterung — jemand steigt ein, Wind — löst **nichts** aus, sie steht nur
   unter „Bewegung“.
4. Hat der Wächter ausgelöst, steht der Alarm ganz oben auf der Seite, bis du
   **Alarm quittieren** drückst. Das schaltet den Wächter nicht ab.

Ohne Internet kennt das Gerät keine Uhrzeit. Dann steht im Alarm „vor 3 h“
statt „um 03:14“ — das ist kein Fehler.

> Ohne Home Assistant erfährst du von einem Alarm erst, wenn du die Seite
> öffnest. Eine Benachrichtigung aufs Handy gibt es über Home Assistant.

---

## 8. Heim-WLAN und Updates

### WLAN eintragen (freiwillig)

Nötig nur für automatische Updates, Home Assistant oder MQTT.

*Technik → WLAN*: Netzwerkname und Passwort eintragen, **Speichern und
verbinden**. Das Gerät startet neu und wählt sich künftig dort ein. Ist das
WLAN nicht erreichbar — etwa auf dem Stellplatz —, öffnet es nach 20 Sekunden
wieder sein eigenes Netz `CamperMinder`.

> Im Heim-WLAN ist die Geräteseite unter **`http://camperminder-level.local`**
> oder unter der IP-Adresse erreichbar, die dein Router vergeben hat (steht
> unter *Technik* als „IP Adresse“, oder in der Geräteliste des Routers).
> Manche Android-Handys kennen `.local`-Adressen nicht — dann die IP nehmen.
> `192.168.4.1` gilt nur im eigenen Netz.

Reichweite beachten (Abschnitt 2): Steht das Fahrzeug vor dem Haus, reicht
das Signal des Geräts oft nicht bis zum Router. Das Gerät funktioniert dann
trotzdem, nur eben ohne Heim-WLAN.

### Updates

| Lage | So geht's |
|---|---|
| Gerät im Heim-WLAN mit Internet | *Technik → Software* → **Auf Updates prüfen und installieren** |
| mit Home Assistant | Einstellungen → System → **Updates**, meldet sich von selbst |
| ohne Internet | Datei `level-firmware.ota.bin` aufs Handy laden, dann *Technik → Software → Datei aufspielen* |

Testgeräte holen ihre Updates aus einem **eigenen Kanal** — sie bekommen nie
versehentlich die Firmware der nächsten Gerätegeneration, die zu diesem Sensor
nicht passt.

Bei einer Datei von Hand bitte nur Releases mit **`v3.…`** im Namen nehmen,
[hier aufgelistet](https://github.com/rcdev67/camperminder/releases). Eine
`v4.…` startet auf diesem Gerät, zeigt aber keine Werte.

Einstellungen, Kalibrierung und WLAN bleiben bei einem Update erhalten.

---

## 9. Home Assistant

### 9.1 Gerät übernehmen

1. WLAN auf dem Gerät eintragen (Abschnitt 8).
2. Home Assistant findet das Gerät von selbst: *Einstellungen → Geräte &
   Dienste*, unter **Entdeckt** steht **CamperMinder Level** (ESPHome).
3. **Konfigurieren** → Home Assistant fragt nach dem
   **Verschlüsselungsschlüssel**. Das ist der API-Schlüssel aus *Auf einen Blick* ganz oben
   (mehr dazu in Abschnitt 11).

Danach erscheinen alle Werte, Schalter und Einstellungen des Geräts als
Entitäten — Neigung, Hubhöhen, Anweisung, Wächter, Kühlschrank und so weiter.
Einstellungen, die du in Home Assistant änderst, gelten sofort auch auf der
Geräteseite und umgekehrt.

Erscheint das Gerät nicht unter *Entdeckt*: *Integration hinzufügen* →
**ESPHome** → als Adresse `camperminder-level.local` oder die IP eintragen.

### 9.2 Integration und Karte installieren (über HACS)

Die Integration **CamperMinder** bringt die Bedienkarte, eine Phasenanzeige
(„Linke Seite anheben“, „Fast eben“, „Eben“), die Sprachansagen und den
Kalibrier-Selbsttest.

1. HACS → Dreipunktmenü → **Benutzerdefinierte Repositories**. Als
   Repository `https://github.com/rcdev67/camperminder` eintragen, als Typ
   **Integration**.
2. **CamperMinder** suchen, **Herunterladen**. Im Download-Fenster als Version
   die neueste **`v3.…`** wählen — passend zur Firmware des Testgeräts.
3. Home Assistant neu starten.
4. *Einstellungen → Geräte & Dienste → Integration hinzufügen* →
   **CamperMinder**. Die Sensorfelder sind schon vorausgefüllt; kurz prüfen,
   Fahrzeugmaße ergänzen, fertig.

### 9.3 Karte aufs Dashboard

Dashboard → Bearbeiten → **Karte hinzufügen** → „CamperMinder“ suchen.

Fehlt sie in der Auswahl: *Einstellungen → Dashboards → ⋮ → Ressourcen* —
dort muss `/camperminder_static/camperminder-card.js` stehen. Die Integration
trägt das beim Start selbst ein; ein weiterer Neustart und ein Neuladen des
Browsers (Cache!) helfen meistens.

### 9.4 Sprachansagen und Benachrichtigungen

- **Sprachansage** und **Ansageziel** stellst du am Gerät CamperMinder in Home
  Assistant ein. Angesagt wird beim Wechsel der Phase („Heck anheben“ → „Fast
  eben“ → „Eben“), nur solange sich das Fahrzeug bewegt.
- **Text vorlesen lassen** (in der Konfiguration der Integration) liest die
  Meldung auf Android-Handys mit der Home-Assistant-App vor.
- Für Alarm aufs Handy eine Automation auf **Wächter Alarm** oder
  **Kühlschrank Warnung** legen.

---

## 10. MQTT

Für Systeme ohne Home Assistant — **Victron Cerbo GX**, ioBroker, openHAB,
Node-RED. **Mit Home Assistant brauchst du MQTT nicht**; dort läuft alles
über die ESPHome-Verbindung.

### Einrichten

*Technik → MQTT*: Broker-Adresse, Port (meist 1883), Benutzer und Passwort
eintragen, **MQTT speichern**. Das Gerät startet neu. Danach zeigt der Eintrag
**MQTT** den Zustand:

| Anzeige | Bedeutung |
|---|---|
| `aus` | keine Adresse eingetragen, MQTT ist abgeschaltet |
| `verbunden mit …` | läuft |
| `keine Verbindung zu …` | Adresse, Port, Benutzer oder Passwort prüfen |

Adresse leeren und speichern schaltet MQTT wieder ab.

### Die wichtigsten Themen

```
camperminder/level/status                              online / offline
camperminder/level/text_sensor/anweisung/state          Hinten links 4.5 cm hoch
camperminder/level/sensor/neigung_pitch/state           Grad, + = Front höher
camperminder/level/sensor/neigung_roll/state            Grad, + = rechts höher
camperminder/level/sensor/hub_vorne_links/state         cm   (ebenso vorne_rechts,
camperminder/level/sensor/hub_hinten_links/state        cm    hinten_rechts)
camperminder/level/binary_sensor/camper_steht_gerade/state   ON = eben
camperminder/level/binary_sensor/waechter_alarm/state        ON = Alarm
camperminder/level/binary_sensor/kuehlschrank_warnung/state  ON = zu lange schief
```

Die Hubhöhen sind fertig gerechnet — Fahrzeugmaße, Toleranz und Zielprofil
sind schon drin. Die vollständige Liste, Befehle zum Umschalten und der Weg
zum Cerbo GX stehen in der
[MQTT-Beschreibung](https://github.com/rcdev67/camperminder/blob/mpu6050/docs/mqtt.md).

Die automatische Erkennung (Discovery) ist abgeschaltet, sonst stünde in Home
Assistant jede Entität doppelt.

---

## 11. Der API-Schlüssel für Home Assistant

**Nur für Home Assistant** brauchst du den **API-Schlüssel** — eine Zeichenkette
aus 44 Zeichen, die auf `=` endet. Home Assistant fragt beim Übernehmen des
Geräts danach (Abschnitt 9.1).

<!--API-KASTEN-->

Am einfachsten ist es, den Schlüssel nicht abzutippen, sondern zu kopieren
und einzufügen: Groß- und Kleinbuchstaben zählen, und `l`, `I` und `1` sehen
sich in vielen Schriften zum Verwechseln ähnlich.

Ohne Home Assistant brauchst du den Schlüssel **nicht**. WLAN-Zugang,
Netz-Passwort und alle Einstellungen trägst du auf der Geräteseite ein.

Alle Testgeräte haben **denselben** Schlüssel. Er bleibt auch nach Updates
gleich — einmal in Home Assistant eingetragen, musst du ihn nie wieder
eingeben.

### Was er schützt — und was nicht

Er **verschlüsselt** den Datenverkehr zu Home Assistant: Wer im selben WLAN
mitliest, sieht keine Klartextwerte.

Er ist **kein Zugangsschutz**. Er steckt in jeder veröffentlichten
Firmwaredatei, und wer sich Mühe gibt, kann ihn dort herauslesen. Die
Geräteseite selbst ist im lokalen Netz ohne Passwort erreichbar — das ist
Absicht, damit auf dem Stellplatz niemand Zugangsdaten suchen muss. Wer das
eigene Netz schützen will, vergibt dafür auf der Geräteseite ein Passwort
(Abschnitt 4).

---

## 12. Wenn etwas nicht klappt

| Problem | Was tun |
|---|---|
| **Netz `CamperMinder` erscheint nicht** | 20–30 s warten. Handy näher ran, im selben Raum. Ist ein Heim-WLAN eingetragen und erreichbar, öffnet das Gerät sein eigenes Netz gar nicht — dann die Seite über das Heim-WLAN öffnen |
| **`192.168.4.1` lädt nicht** | Handy wirklich mit `CamperMinder` verbunden? Mobile Daten kurz ausschalten, damit das Handy nicht am Gerät vorbei ins Internet geht. `http://` statt `https://` |
| **„⚠️ Kein Sensorwert“** | Stecker kurz ziehen und wieder einstecken. Bleibt es dabei: bitte melden, vermutlich ein Kontakt im Gehäuse |
| **Gelbe Meldung „sitzt das Gehäuse noch fest?“** | Befestigung prüfen, dann neu kalibrieren |
| **Gelbe Meldung zur Kalibrierung** | Temperatur weit weg von der beim Kalibrieren. Bei nächster Gelegenheit auf ebenem Grund neu kalibrieren |
| **Anweisung zeigt in die falsche Richtung** | Pfeil nach vorn? Einbaulage richtig? Neu kalibrieren. Sonst melden (Abschnitt 6) |
| **Anzeige springt an der Grenze hin und her** | *Haltebereich* erhöhen oder *Anzeigeruhe* höher setzen |
| **Einstellungen nach Neustart weg** | Nach dem Ändern eine Minute Strom lassen |
| **Home Assistant: „nicht erreichbar“** | Gerät im WLAN? Signal zum Router reicht? API-Schlüssel richtig eingetragen? |
| **Update schlägt fehl** | Gerät braucht Internet über das Heim-WLAN. Sonst den Weg mit der Datei vom Handy nehmen |
| **Netz-Passwort vergessen** | *Technik → Zurücksetzen*. Achtung: löscht auch WLAN, Kalibrierung und Fahrzeugmaße |
| **Zwei Testgeräte im selben Heimnetz** | Beide heißen `camperminder-level` — das ist noch nicht vorgesehen. Bitte nur eins zur Zeit ins Heim-WLAN |

**Rückmeldung:** am liebsten mit Firmware-Version (*Technik → Software*),
Fahrzeugart und einem Satz, was du gerade gemacht hast. Ein Bildschirmfoto
der Geräteseite sagt oft mehr als eine lange Beschreibung.

---

## Anhang für Selbstbauer: die `secrets.yaml`

Dieser Teil ist nur für alle, die die Firmware **selbst bauen**. Wer ein
fertiges Testgerät bekommen hat, kann ihn überspringen.

### Was in der `secrets.yaml` steht

Die `secrets.yaml` liegt beim Bauen neben
`esphome/level/camperminder-level.yaml` und enthält genau **zwei** Einträge:

```yaml
camperminder_api_key: "…44 Zeichen Base64…"
camperminder_ota_password: "…"
```

| Eintrag | Wofür | Wer braucht ihn |
|---|---|---|
| `camperminder_api_key` | **verschlüsselt** die Verbindung zwischen Gerät und Home Assistant (ESPHome-API) | Home Assistant, einmal beim Übernehmen |
| `camperminder_ota_password` | erlaubt das Aufspielen **aus ESPHome heraus** über das Netz (`esphome run`, ESPHome-Dashboard) | nur wer selbst baut und flasht |

Beide werden beim Bauen **fest in die Firmware eingebaut**.

### Was ausdrücklich *nicht* darin steht

| Nicht in der Datei | Warum |
|---|---|
| **WLAN-Name und -Passwort** | Stünde hier ein WLAN, wäre es in jedem Gerät — und ESPHome behielte ein auf der Geräteseite eingetragenes WLAN nur, solange in der Konfiguration keins steht |
| **Passwort für das Netz `CamperMinder`** | Ein Passwort ab Werk wäre für alle Geräte gleich (und stünde bald in jedem Forum) oder bräuchte einen Aufkleber je Gerät, der nach dem Zurücksetzen nicht mehr stimmt. Deshalb offen ab Werk, eigenes Passwort auf der Geräteseite |

### Die wichtigste Regel: den Schlüssel nie neu erzeugen

Die Firmware, die ein Gerät über den Update-Knopf holt, ist **mit genau diesem
Schlüssel gebaut**. Alle Geräte einer Linie teilen sich also denselben
API-Schlüssel und dasselbe OTA-Passwort.

Wird eine Firmware mit einem **neuen** Schlüssel gebaut und veröffentlicht,
passiert Folgendes: Jedes Gerät, das dieses Update installiert, spricht danach
mit Home Assistant nur noch mit dem neuen Schlüssel. Bei jedem Tester steht es
dann als „nicht erreichbar“ da, bis er den neuen Schlüssel eingetragen hat —
und den müsste man jedem einzeln schicken.

Beim OTA-Passwort ähnlich: Wer es ändert, braucht zum nächsten Flashen aus
ESPHome heraus trotzdem noch das **alte** — das Gerät prüft gegen das Passwort
der Firmware, die gerade darauf läuft.

Deshalb:

- Die `secrets.yaml` **einmal** anlegen und von da an nur noch **kopieren** —
  in jeden Arbeitsordner, auf jeden Rechner, der Firmware baut.
- **Nicht** in ESPHome auf „Encryption key generieren“ drücken, wenn es schon
  Geräte gibt.
- Die Datei **nie ins Repository** legen; `.gitignore` schließt sie aus. Sicher
  aufbewahren (Passwortmanager). Ist sie weg, steckt der Schlüssel nur noch in
  den gespeicherten Daten einer Home-Assistant-Installation, in der ein Gerät
  schon eingebunden ist — das wieder herauszuholen ist mühsam.
