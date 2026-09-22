# Produktentscheidungen Level — Markt, Positionierung, Firmware

Stand: 17. August 2026. Ergebnis einer Marktrecherche und der Entscheidung, die
geplante Basisstation zurückzustellen und Level zuerst an den Start zu bringen.

Diese Datei beschreibt **warum** die Firmware bestimmte Dinge können muss. Die
Konfiguration selbst steht in `esphome/level/`.

## Die Positionierung

**Level ist kein Nivelliergerät. Es ist ein fest verdrahteter Lage- und
Bewegungswächter.**

Das ist keine Wortklauberei, sondern folgt aus dem Markt. Als digitale
Wasserwaage ist Level teurer als der Wettbewerb und kann weniger:

| | EasyLevel (CaraTech) | LevelMatePRO (LogicBlue) |
|---|---|---|
| Preis | ~70 € | 99,98 $ · ~78 € über eBay.de |
| Anzeige | Neigung längs und quer, live | **Höhe je Ecke in cm oder Zoll**, eigene Anzeige fürs Stützrad |
| Wohnwagen | **ja**, Fahrzeugtyp in der App wählbar | **ja**, Hauptmarkt |
| Versorgung | CR2450, über ein Jahr | Batterie |
| Verbindung | Bluetooth zum Telefon | Bluetooth zum Telefon |

Dazu kostenlose Apps (Truma, motorhome-level.com) und eine veröffentlichte
ESPHome-Bauanleitung mit MPU6050 auf smarthomeundmore.de.

**Wichtig für jeden Verkaufstext:** Die Zentimeterangabe je Ecke ist **kein**
Alleinstellungsmerkmal — LevelMatePRO kann das. Wohnwagen sind **nicht**
ungedeckt — EasyLevel deckt sie ab, mit Auswahl des Fahrzeugtyps. Eine
widerlegbare Behauptung im ersten Satz kostet in einem Forum mehr, als sie
einbringt.

### Was Level wirklich kann und die anderen nicht

Beide Wettbewerber sind Batteriegeräte. EasyLevel läuft ein Jahr auf einer
Knopfzelle — das geht nur, weil es die meiste Zeit schläft und nur redet, wenn
ein Telefon in Reichweite ist.

**Level hängt an 7–36 V und ist immer an.** Daraus folgt alles:

| | |
|---|---|
| **Bewegungsmeldung aus der Ferne** | Der LSM6DS3TR-C hat eine Drehratenmessung. Wird das Fahrzeug angehoben, abgeschleppt oder betreten, meldet Level das über das Netz — nicht an ein Telefon in Bluetooth-Reichweite. |
| **Schräglagenwarnung** | Über etwa 3° arbeitet ein Absorberkühlschrank nicht mehr richtig. Niemand merkt das, bis das Essen warm ist. |
| **Verlauf und Automatisierung** | Ein Batteriegerät hat keine Historie. |
| **Kein Batteriewechsel** | — |

Das rechtfertigt 99–129 € gegen 70 €. „Zeigt die Neigung an" rechtfertigt sie
nicht.

Nebenbei ein Verkaufsargument, das im Hardware-Repository bereits begründet
ist: Die veröffentlichte Bauanleitung nutzt den MPU-6050, den TDK als
abgekündigt führt und von dem der Markt voller Fälschungen ist. Bei einem
Gerät, dessen Genauigkeit am Temperaturdrift des Sensors hängt, ist das die
schlechteste Stelle zum Sparen. Level nutzt den LSM6DS3TR-C in laufender
Produktion.

## Stand der Firmware — nachgesehen am 17.08.2026

| Merkmal | Stand |
|---|---|
| `wifi:` mit Zugangspunkt-Rückfall (`ap:`, SSID `CamperMinder`, 192.168.4.1, `ap_timeout: 20s`) | **vorhanden** |
| Eigene Einrichtung über die Geräteseite (`save_wifi_sta`, `set_ap` in `hardware.yaml`) | **vorhanden** — ersetzt `captive_portal` |
| `web_server:` — eigene Seite auf dem Gerät | **vorhanden** (`camperminder-level.yaml:321`, `hardware.yaml:224`) |
| `api:` — native Schnittstelle zu Home Assistant | **vorhanden** (`camperminder-level.yaml:90`) |
| **`mqtt:`** | **fehlt** |

Von den besprochenen Punkten fehlt damit **nur MQTT**. Die Einrichtung ohne
Home Assistant ist bereits gelöst, und zwar besser als über den
Standard-`captive_portal`.

## Was noch in die Firmware muss

### 1. MQTT — höchste Priorität

Der strategisch wichtigste Punkt. Die Basisstation ist gestrichen; Level soll
**vorhandene Systeme ergänzen statt gegen sie anzutreten**. MQTT ist die
einzige Schnittstelle, die das leistet:

| System | Anbindung über MQTT |
|---|---|
| **Victron Cerbo GX** | Venus OS hat einen lokalen MQTT-Broker. In der Large-Fassung legt man mit Node-RED *virtuelle Geräte* an, die sich auf dem GX-Display und in VRM wie echte Victron-Hardware verhalten. |
| **E1NFACH E1NS** | spricht ausdrücklich MQTT |
| **COMWORKS CIS 3** | läuft auf Home Assistant |
| ioBroker, openHAB, Node-RED | Standardweg |

Weder Victron noch COMWORKS haben einen Neigungssensor. Mit MQTT ist Level
deren Zubehör statt deren Wettbewerber — ein erheblich leichterer Verkauf als
ein eigenes System.

In ESPHome läuft MQTT parallel zur nativen Schnittstelle; Home-Assistant-Kunden
verlieren nichts.

### 2. Die Zentimeterrechnung gehört ins Gerät

**Nicht in ein Home-Assistant-Template.** Steht die Umrechnung von Winkel auf
Höhe je Ecke in HA, dann gibt es sie nur dort — nicht auf der Geräteseite,
nicht über MQTT, nicht auf einem Cerbo GX. Genau das Merkmal, mit dem Level
verkauft wird, wäre dann an die Plattform gefesselt, von der es unabhängig sein
soll.

Konkret:

- **Radstand**, **Spurweite** und **Fahrzeugtyp** als `number` bzw. `select`,
  vom Kunden einmalig gesetzt und dauerhaft gespeichert.
- Höhe je Ecke als `template`-Sensor aus Quer- und Längsneigung:
  - quer: `Spurweite · tan(Querneigung)`
  - längs: `Bezugslänge · tan(Längsneigung)`
- **Die Bezugslänge hängt vom Fahrzeugtyp ab** — beim Wohnmobil der Radstand,
  beim Wohnwagen der Abstand Achse–Kupplung. Der Fahrzeugtyp ist deshalb keine
  Kosmetik, sondern geht in die Rechnung ein. Wer das nicht trennt, rechnet für
  Wohnwagen falsch.
- Ausgabe: welche Seite wie viele Zentimeter hoch, beim Wohnwagen zusätzlich
  Stützrad hoch oder runter.

### 3. Bewegungserkennung

Über die Drehratenmessung des LSM6DS3TR-C. Zwei Meldungen sind zu unterscheiden:

- **kurze Erschütterung** — jemand steigt ein, Wind, Nachbar
- **anhaltende Lageänderung** — das Fahrzeug wird angehoben oder bewegt

Nur die zweite ist ein Alarm, die erste ist Anwesenheitserkennung. Als getrennte
Entitäten herausgeben, damit der Kunde selbst entscheidet.

### 4. Schräglagenwarnung

Binärer Sensor „Schräglage über Grenzwert", Grenzwert als `number` einstellbar,
Voreinstellung 3°. Begründung auf der Geräteseite und im Handbuch:
Absorberkühlschrank.

## Was ausdrücklich NICHT in die erste Serie kommt

**Kein aktives Bluetooth.** Also kein Improv über BLE, kein BTHome, kein
BLE-Rundsenden.

**Grund:** Die Bluetooth SIG — kein Amt, sondern ein Industriekonsortium —
verlangt für jedes Erzeugnis, das Bluetooth benutzt, eine Produkt-Deklaration:

| | USD |
|---|---|
| Adopter (Mitgliedschaft kostenlos) | 8.000 |
| Associate / Promoter | 4.000 |
| **Innovation Incentive Program, kleine Unternehmen, bis zu zwei Deklarationen** | **2.500** |

Stand 1. März 2026. Dass das ESP32-C3-WROOM-02 bereits qualifiziert ist (QDID
von Espressif), erspart die **Prüfung**, nicht die **Gebühr**.

**Praktische Regel:** Bluetooth in der Firmware aus. Weder das Wort „Bluetooth"
noch das Logo auf Verpackung, Gehäuse, Webseite oder Handbuch.

**WLAN ist davon nicht betroffen.** Die Zertifizierung der Wi-Fi Alliance ist
freiwillig; man darf 802.11 einbauen und verkaufen, nur der Schriftzug
„Wi-Fi CERTIFIED" ist geschützt.

Improv und BTHome selbst kosten nichts — beides sind offene Standards ohne
Organisation und ohne Gebühr. Sie scheitern allein daran, dass sie Bluetooth
voraussetzen. Sobald die Stückzahl die 2.500 $ trägt, kommen sie dazu, und die
Gebühr deckt dann zwei Geräte.

## Zulassung — was unabhängig davon anfällt

CE nach der Funkanlagenrichtlinie 2014/53/EU ist Pflicht, ohne Stückzahlgrenze.
Wer unter eigenem Namen in Verkehr bringt, ist Hersteller.

| Anforderung | Nachweis |
|---|---|
| Funkeigenschaften, Art. 3.2 | **geerbt** vom vorzertifizierten ESP32-C3-WROOM-02 |
| Elektrische Sicherheit, Art. 3.1(a) | bei Kleinspannung nahezu erledigt |
| **EMV, Art. 3.1(b)** | selbst, EN 301 489 und EN 55032/55035 |
| **Cybersicherheit, Art. 3.3(d/e/f)** | selbst, EN 18031 — seit 1. August 2025 verbindlich |

Realistisch **2.500–4.500 €** einmalig. Das wiegt bei einem 99-Euro-Gerät schwer
und erzwingt eine Entscheidung über die Seriengröße, bevor die erste
Serienbestellung rausgeht:

| Serie | Zulassung je Stück |
|---|---|
| 50 | 50–90 € |
| 150 | 17–30 € |
| **300** | **8–15 €** |

Empfehlung: **vor dem Prüftermin Vorbestellungen einsammeln.**

Cyber Resilience Act: Meldepflicht für aktiv ausgenutzte Schwachstellen ab
**11. September 2026** (24 h / 72 h über ENISA), vollständige Anwendung ab
**11. Dezember 2027**.

## Warum die Basisstation gestrichen ist

Geplant war eine eigene CM4-Trägerplatine mit serienmäßigem Home Assistant. Das
Lastenheft liegt im Hardware-Repository unter `basisstation/LASTENHEFT.md` und
bleibt als Nachschlagewerk bestehen.

Gestrichen, weil es das Produkt bereits gibt: **COMWORKS CIS 3**, seit Herbst
2024, angepasstes Home Assistant auf Linux, 10–30 V, unter 5 W, passiv gekühlt,
Zigbee an Bord, CI-Bus und CAN, eigene Plattform für den Fernzugriff
(DigiCamper) — für **649–795 €**. Daneben E1NFACH E1NS, Truma iNet X, CBE ONDA.
Und Victron Cerbo GX ab 173 € besitzt die Batteriedaten ohnehin.

Vorleistung für eine eigene Basisstation: 25.000–40.000 €, Kostendeckung erst
bei 120–190 Geräten.

**Der Schluss daraus ist die heutige Strategie:** Diese Systeme ergänzen statt
gegen sie antreten. Deshalb MQTT.

## Der Ausbau — beschlossen und gebaut am 22. August 2026

**Stand: alle vier Punkte sind umgesetzt und am laufenden Gerät geprüft.**

| | Fassung | Was am Gerät nachgewiesen wurde |
|---|---|---|
| Wächtermodus | 3.6.0 | Karenz-Countdown, Einrasten, Quittieren, Wiederscharfschalten |
| Kühlschrank-Zeitkonto | 3.7.0 | alle drei Stufen im Zeitverlauf durchlaufen |
| Zielprofile | 3.8.0 | alle drei Profile; Schräglage und Lageänderung blieben unberührt |
| Selbstüberwachung | 3.9.0 | keine Fehlalarme ohne Kalibrierdaten, Montagewarnung kam und ging |

Zwei Beobachtungen aus den Tests, die in den Verkaufstext bzw. ins Handbuch
gehören:

- **Das Schlafprofil wirkt nur unterhalb der Toleranz sichtbar.** Bei 3 cm
  Toleranz liegt ein Schlafziel von 2 cm innerhalb davon — das Gerät meldet
  dann folgerichtig „steht schon richtig". Wer das Profil nutzen will, wählt
  eine größere Zielneigung oder für die Nacht den Präzisionsmodus. Ob das
  Profil eine eigene, engere Toleranz bekommen soll, ist offen.
- **Die Driftnachführung kann eine sehr kleine, sehr langsame Lageänderung
  aufnehmen**, solange der Kreisel dabei keine Bewegung sieht. Beim echten
  Aufbocken tritt das nicht auf — dort setzt `In Bewegung` den Zähler zurück.



Die vier Punkte aus dem Abschnitt „Was noch in die Firmware muss" sind seit
3.5.2 erledigt. Die Frage war also, was danach kommt. Maßstab ist ein einziger
Prüfstein, der sich aus der Positionierung von selbst ergibt:

> **Könnte ein Knopfzellengerät mit Bluetooth das auch?**
> Wenn ja, ist es kein Unterscheidungsmerkmal, sondern Aufholen.

Der Prüfstein schließt aus, was naheliegt und nichts einbringt: mehr
Nachkommastellen, eine eigene Telefon-App, Bluetooth-Nähe. EasyLevel kann das
für 70 €; auf diesem Feld ist nichts zu gewinnen.

### 1. Wächtermodus

Level ist heute ein Gerät, das **fünf Minuten pro Reise** benutzt wird. Das
rechtfertigt keine 129 €. Scharf geschaltet meldet es dagegen rund um die Uhr,
wenn sich an der Lage etwas tut — angehoben, abgeschleppt, aufgebockt.

- scharf/unscharf mit Karenzzeit, damit der eigene Ausstieg nicht auslöst
- zwei Stufen: **Bewegung am Fahrzeug** (Anwesenheit) und **Lageänderung**
  (Alarm). Die Trennung stand schon oben, hier wird sie zum Produkt
- Ereignis mit Zeitstempel, nicht nur ein Zustand — damit morgens sichtbar ist,
  dass nachts um drei etwas war

Ein Batteriegerät kann das prinzipiell nicht: Es schläft und redet nur mit
einem Telefon in Reichweite.

### 2. Kühlschrank-Zeitkonto

Die Schräglagenwarnung ist bisher eine Wasserwaage mit Grenzwert. Was den
Absorber beschädigt, ist aber nicht der Winkel, sondern **Winkel mal Zeit**.
Kurz schräg beim Rangieren ist folgenlos, drei Stunden schräg im Betrieb nicht.

- Dauer über dem Grenzwert als eigener Wert
- Eskalation statt An/Aus: Hinweis, Warnung, dringend
- ~~Zähler über die ganze Standzeit~~ — beim Bauen gestrichen. Solange das
  Fahrzeug steht, ist er identisch mit der Dauer darüber; unterscheiden würden
  sich die beiden nur beim Flattern um die Schwelle, und genau das entfernt
  die Hysterese bereits. Ein zweiter Zähler hätte nur eine zweite Zahl mit
  derselben Aussage ergeben.

Nur ein Gerät, das die ganze Zeit hinsieht, kann das. Es beseitigt zugleich die
Fehlalarme beim Rangieren, die eine harte Grenze zwangsläufig erzeugt.

**Offen:** Grenzwinkel und kritische Dauer vor dem Druck aus den Handbüchern
von Dometic und Thetford belegen, nicht aus Forenwissen übernehmen.

### 3. Zielprofile statt „eben"

Der begriffliche Bruch mit der Wasserwaage. Die kennt **ein** Ziel: null.

| Profil | Ziel |
|---|---|
| Ausrichten | eben |
| Schlafen | Kopfende ein bis zwei Zentimeter höher |
| Ablassen | bewusst zur Ablassseite geneigt, damit Boiler und Tank leerlaufen |
| Kühlschrank | enger Grenzwert, Vorrang für die Querneigung |

Technisch eine Sollneigung je Achse in der Anzeigerechnung; Anweisung und
Ecken-Zentimeter laufen unverändert weiter.

### 4. Selbstüberwachung

Ein fest verbautes Gerät kann sich selbst beobachten, ein Handgerät nicht.

- Driftwarnung, aufbauend auf `docs/drift_messung.md`: „Kalibrierung
  empfohlen", bevor der Kunde falschen Werten vertraut
- gelöste Montage erkennen — springt der Wert im Stand um Grade, ist nicht das
  Fahrzeug schief, sondern das Gerät locker. Sonst begegnet einem dieses
  Fehlerbild als „misst falsch" in einer Rezension
- Temperatur für eine Frostwarnung; für Genauigkeit taugt sie nicht, das gehört
  dazugesagt

### Zurückgestellt

**Ausgabe für Hydraulik und Luftfederung.** Zielwerte je Ecke über MQTT
bereitstellen passt zur Ergänzungsstrategie — **selbst ansteuern nicht.** Wer
Stützen fahren lässt, haftet für ein absackendes Fahrzeug. Werte liefern ja,
Ventile schalten nein.

**Windwarnung.** Der Kreisel sieht das Schwingen des Aufbaus, „Markise
einfahren" wäre ein hübsches Argument. Wind ist von Menschen im Fahrzeug aber
schwer zu unterscheiden — erst angehen, wenn der LSM6DS3TR-C läuft und echte
Aufzeichnungen vorliegen. **Seit 4.0.0 läuft er**; die Aufzeichnungen fehlen
noch.

## Der Hardwarewechsel — gebaut am 31. August 2026, Fassung 4.0.0

Zwei Änderungen auf einmal, weil sie dieselbe Verkabelung anfassen.

### 1. LSM6DS3TR-C statt MPU6050

Der Grund steht oben unter „Was Level wirklich kann": Der MPU-6050 ist bei TDK
abgekündigt, der Markt ist voller Fälschungen, und bei einem Gerät, dessen
Genauigkeit am Temperaturdrift des Sensors hängt, ist das die schlechteste
Stelle zum Sparen. Bis 3.9.0 war das ein Vorsatz, seit 4.0.0 ist es gebaut.

ESPHome bringt den Chip seit 2026.6 selbst mit — als `motion`-Plattform. Ein
eigener Treiber war also nicht nötig; das war vor der Entscheidung nicht sicher
und hätte sie sonst teuer gemacht.

**Was dabei zu beachten war:**

| | |
|---|---|
| **Einheit** | Die neue Plattform liefert die Beschleunigung in **g**, der MPU6050 lieferte sie in **m/s²**. Betroffen sind der Diagnosewert „Betrag", die Montageprüfung und die Kalibrierprüfung. Pitch und Roll nicht — `atan2` rechnet mit Verhältnissen. |
| **Achsen** | Der Chip sitzt auf der Platine Rev B anders als der alte Sensor auf seinem Modul. Zuordnung und Vorzeichen sind aus dem Layout abgeleitet und **am ersten Muster zu bestätigen**, bevor etwas davon in eine Serie geht. |
| **Aufzeichnungen** | Die Driftmessreihe aus `docs/drift_messung.md` beginnt von vorn. Sie stammte von einem anderen Bauteil und sagt über dieses hier nichts. |

**Was der neue Sensor mitbringt:** rund viermal weniger Rauschen auf der
Beschleunigung (90 statt etwa 400 Mikro-g je Wurzel Hertz) und einen deutlich
kleineren Nullpunktversatz auf der Drehrate. Beides ist noch **nicht**
ausgenutzt — die Glättungsbeiwerte und die Bewegungsschwelle stehen weiter auf
den Werten, die am MPU6050 erprobt wurden. Sie werden erst nach einer Messreihe
am stehenden Fahrzeug gesenkt, nicht auf Verdacht: Eine zu niedrige
Bewegungsschwelle hat hier schon einmal drei Fehler auf einmal erzeugt.

Damit rückt auch die zurückgestellte **Windwarnung** in Reichweite. Ihre
Bedingung war „erst wenn der LSM6DS3TR-C läuft und echte Aufzeichnungen
vorliegen". Die erste Hälfte ist erfüllt, die zweite nicht.

### 2. Die Ausführung ohne Display

Die Serie bekommt kein OLED. Die Nivellieranzeige gehört aufs Handy — sie
braucht Größe, Farbe und einen Blickwinkel, den ein Feld von 72 x 40 Pixeln an
der Einbaustelle nicht hergibt. Wer Keile unterlegt, steht draußen und sieht es
ohnehin nicht.

Das Feld beantwortete aber drei Fragen, die sich **ohne** Handy stellen. Zwei
davon übernehmen jetzt eine Status-LED und ein Summer:

| Frage | vorher | jetzt |
|---|---|---|
| Läuft das Gerät? | Anzeige an | LED blinkt |
| Eigenes Netz oder Heimnetz? | stand da | zwei verschiedene Blinkmuster |
| Antwortet der Sensor? | „Sensor stumm" | eigenes Blinkmuster |
| Liegt ein Alarm an? | „ALARM" mit Uhrzeit | Blinkmuster **und Ton** |
| **Wie lautet die IP im Heimnetz?** | **stand da** | **nicht mehr** |

Die letzte Zeile ist ein echter Verlust und wird nicht schöngeredet: Eine LED
kann keine Adresse buchstabieren. Ersatz ist der Name
`camperminder-level.local` im Handbuch — das ist schlechter, aber es betrifft
nur den Fall „im Heimnetz **und** Adresse vergessen **und** kein Zugriff auf
den Router". Im eigenen Netz gilt weiterhin die feste 192.168.4.1.

Dafür kann der Summer etwas, was das Display nie konnte: Er erreicht jemanden,
der nicht hinsieht. Beim Wächteralarm tönt er alle zehn Sekunden, und nach
fünf Minuten ist Ruhe — wer ihn hört, ist entweder da, oder das Gerät
beschallt sonst eine halbe Nacht den Stellplatz, ohne dass es jemandem hilft.
Eine Sirene, die stundenlang läuft, schaltet der Nachbar ab, und dann ist die
Meldung weg.

Das OLED bleibt als **Werkstattvariante** bestehen (`anzeige-oled.yaml`, in der
Gerätedatei eine auskommentierte Zeile, Anschluss an der Stiftleiste J4 der
Platine). Es ist kein zweites Produkt, sondern das Werkzeug für Werkstatt und
Messplatz.

### 3. Das Board — entschieden am 14. September 2026: eigene Platine

Das Gerät läuft auf einer **eigenen Platine „CamperMinder Level"**, 90 × 45 mm,
mit einem **ESP32-C3-WROOM-02-N4** als Funkmodul und dem LSM6DS3TR-C direkt
bestückt. Dazu Versorgung 7–36 V über Schraubklemme mit Sicherung, Verpol- und
Überspannungsschutz, USB-C zum Flashen und für 5 V, Status-LED, Betriebs-LED
und ein magnetischer Summer. **Rev B** ist am 14. September 2026 bei PCBWay
bestellt, zehn Stück bestückt, als Prototypenreihe. **Rev C** ändert nur
Siebdruck und Sensor-Pads und wird später bestellt.

Warum ein Modul und kein nackter Chip: Das WROOM-02 ist mit seiner Antenne
funkzertifiziert, die Funkeigenschaften nach Artikel 3.2 werden geerbt — der
teuerste Posten der CE-Prüfung entfällt. Die Erfahrungen mit den lose
gekauften ESP32-C3-Boards des Prototyps waren außerdem schlecht: chargenweise
unsichtbare Netze, unklare Stiftbelegung.

**Alte Hardware gibt es nicht im Feld.** Kein Kunde hat ein Gerät mit MPU6050,
SuperMini oder aufgelötetem OLED. Firmware und Dokumentation beschreiben
deshalb nur noch die Platine; Migrationspfade von der alten Bestückung werden
nicht gepflegt.

Für die Firmware folgt daraus: Board-Profil `esp32-c3-devkitc-02`, Pins
unverändert (GPIO5/6 I²C, GPIO8 LED, GPIO10 Summer), Sendeleistung auf der
Voreinstellung, Achszuordnung aus dem Layout abgeleitet — siehe die offenen
Punkte.

## Die Geräteseite — gebaut am 22. September 2026, Fassung 4.0.0

Drei Entscheidungen, ausgelöst von einem Satz beim Durchsehen der
Einstellungen: *„Der Punkt mit der Neigung zum Schlafen war selbst für mich
nicht klar.“* Wenn der Entwickler seine eigene Einstellung nicht lesen kann,
kann sie niemand lesen.

### 1. Richtung und Betrag statt Vorzeichen

Bis 4.0.0 hieß die Einstellung fürs Schlafen `Schlafen längs = -2`. Das
bedeutete „Heck 2 cm höher“ — nachzulesen nirgends. Ersetzt durch **zwei
Fragen**: Wo liegt der Kopf (`Kopf vorn`, `Kopf hinten`, `Kopf links`,
`Kopf rechts`, in Fahrtrichtung gesehen), und um wie viel soll das Kopfende
höher stehen (`Kopfende anheben`, 0 … 15 cm). Dasselbe Muster beim Ablassen:
`Ablasspunkt` nennt den **tiefsten** Punkt — acht Optionen bis zur Ecke —,
`Neigung zum Ablasspunkt` den Betrag. Achse und Vorzeichen rechnet das Gerät.

Das räumt zugleich einen Denkfehler aus: Eine **Quer**neigung fürs Schlafen
galt als unsinnig („quer schief rollt man aus dem Bett“). Das gilt nur für ein
Längsbett. Wer quer schläft — im Alkoven, im Queensbett vieler Kastenwagen —,
hat seine Kopf-Fuß-Achse quer im Fahrzeug und braucht genau diese Neigung.

Dazu auf der Geräteseite eine **Skizze des Fahrzeugs von oben**: Bett bzw.
Ablasspunkt eingezeichnet, das angehobene Ende markiert, dazu ein Satz im
Klartext („Ziel im Profil ‚Schlafen‘: linke Seite 2,0 cm höher.“). Eine
Richtungsangabe, die man sich vorstellen muss, hat noch niemand richtig
verstanden.

### 2. Die Hilfetexte sind für den Kunden, nicht für den Entwickler

Die alten Erklärungen begründeten den technischen Hintergrund — warum ein
Wert so gerechnet wird, woher eine Grenze kommt. Das ist die Begründung einer
Entscheidung und gehört in diese Datei und in die Kommentare der Firmware, nicht
unter einen Regler. Unter dem Regler steht jetzt, **was der Kunde davon hat und
was passiert, wenn er die Zahl ändert**. Der technische Grund bleibt dort, wo
er hingehört.

### 3. Deutsch und Englisch, umschaltbar am Gerät

Unter **Technik → Sprache** lässt sich die Geräteseite auf Englisch stellen;
ohne Auswahl entscheidet die Spracheinstellung des Handys. Die Wahl liegt im
`localStorage` des Browsers, also **je Handy** — nicht im Gerät. Zwei Leute
mit einem Fahrzeug lesen so jeder in seiner Sprache, und die Einstellung
kostet keinen Flash-Platz.

**Die Entitätsnamen bleiben deutsch.** Sie sind zur Bauzeit festgelegt, und sie
sind in Home Assistant, in MQTT und in jeder Automatisierung des Kunden die
Kennung — wer sie übersetzt, zerschießt bestehende Installationen bei einem
Sprachwechsel. Übersetzt wird nur, was die Seite selbst schreibt.

Damit die Seite ihre Sätze selbst bilden kann, liefert die Firmware dieselben
sechs Auskünfte (Wächter, Kühlschrank, Kalibrierung, letzte Bewegung, MQTT,
eigenes Netz) zusätzlich als **Werte** statt als Satz: ein Diagnose-Textsensor
`Statuswerte` im Format `w=…;k=…;c=…;b=…;m=…;n=…`, dokumentiert in
`docs/mqtt.md`. Die deutschen Klartextsätze bleiben daneben stehen: Home
Assistant und MQTT benutzen sie unverändert weiter, und für den Support ist ein
Satz auf einem Bildschirmfoto mehr wert als ein Code.

### 4. Die Seite sagt, wenn sie veraltet ist

Aufgefallen beim ersten Aufspielen auf ein Muster: Nach dem Update zeigte die
Geräteseite weiter den alten Stand — der Browser hatte `/0.js` in seinem
Zwischenspeicher und holte sie nicht neu. Das ist kein Einzelfall am Muster,
sondern gilt für **jedes Update beim Kunden**: `handle_js_request` in ESPHomes
`web_server.cpp` liefert die Datei ohne `Cache-Control`, ohne `ETag` und ohne
`Last-Modified` aus. Der Browser darf seine Kopie also behalten, und niemand
merkt es — neue Firmware, alte Oberfläche, und die beiden passen nach einer
Änderung an den Entitäten nicht mehr zusammen.

Die Seite kennt deshalb ihre eigene Fassung (`SEITE_VERSION` in `webui.js`)
und vergleicht sie mit der, die das Gerät meldet. Weichen sie ab, steht oben
ein gelber Balken: *„Diese Seite ist älter als das Gerät … bitte neu laden.“*
Gelb wie die Selbstüberwachung, nicht rot wie der Alarm — es ist nichts
kaputt, es ist nur alt.

Damit die Nummern nicht auseinanderlaufen, prüft `tools/build_release.ps1`
sie hart und bricht bei Abweichung ab. Ohne diese Prüfung wäre der Balken
schlimmer als kein Balken: Eine vergessene Nummer ließe ihn bei **jedem**
Kunden erscheinen, und eine Warnung, die immer steht, liest nach der zweiten
Woche niemand mehr.

Nicht gemacht: ein automatischer Neuladeversuch der Seite. Wer gerade WLAN-
Zugangsdaten eintippt, verlöre sie dabei — und ein Gerät, das die Seite unter
den Händen des Kunden austauscht, ist schwerer zu erklären als ein Satz, den
er liest und dann selbst entscheidet.

Nicht gemacht: eine Sprachumstellung, die auch die Entitäten umbenennt, und
weitere Sprachen. Französisch und Niederländisch sind für den Markt
interessant, kosten aber je Sprache ein vollständiges Wörterbuch im Flash —
das entscheidet sich, wenn die ersten Geräte im Feld sind.

## ESPHome ist eine Abhängigkeit, kein Fundament — 22. September 2026

Die Geräteseite ist an ESPHomes Webserver angeschlossen, und diese
Schnittstelle ist **nicht zugesagt**. Am 22. September 2026 hat das einen Tag
gekostet: Mit 2026.8 bildet ESPHome die Entitätskennung im Ereignisstrom als
`sensor/Neigung Pitch` statt als `sensor-neigung_pitch` (`set_json_id` in
`web_server.cpp`), und Schreibzugriffe treffen die Entität seither über ihren
**Anzeigenamen** statt über eine Objektkennung; das Feld `name_id` entfiel.

Die Seite suchte weiter nach dem alten Format. Sie ist dabei nicht
abgestürzt — sie hat schlicht keine Entität wiedergefunden: keine Messwerte,
alle Schalter grau, die Technik-Liste nur beim Neuladen aktuell, keine
Fehlermeldung. **Ein stummer Ausfall ist der teuerste Fehler dieser Bauart**,
und er wäre beim Kunden nach einem OTA-Update auf dem Stellplatz aufgefallen.

Entschieden wurde daraufhin dreierlei:

1. **Die Fassung ist festgenagelt** (`requirements.txt`, `esphome==…`), und
   `tools/einrichten.cmd` installiert nur diese. Vorher stand dort ein
   `pip install esphome` ohne Angabe — die Fassung, gegen die wir bauen, war
   Zufall. Ein Wechsel ist jetzt eine Entscheidung mit eigenem Testlauf.
2. **Die Annahmen der Seite werden geprüft, nicht gehofft**
   (`tools/pruefe_esphome.py`). Das Skript liest den Quelltext der
   installierten Fassung und bricht ab, sobald Kennungsformat, Schreibziel,
   `set`/`value`, `/0.js`, `/events` oder die Adressdekodierung nicht mehr
   passen. Es hängt in `bauen.cmd` **und** in `build_release.ps1` — einmal
   für den täglichen Bau, einmal als letzter Halt vor dem Kunden. Geprüft
   wird der Quelltext und nicht nur die Versionsnummer: Eine Nummer sagt
   nichts über diese Schnittstelle.
3. **Der Prüfstand wird abgeleitet, nicht gepflegt**
   (`tools/stub_erzeugen.py` aus `esphome config`). Sein Entitätsbestand
   stand vorher von Hand im Quelltext, auf dem Stand eines Berichts vom
   Sommer. Er hat dreimal grünes Licht gegeben, während am Gerät nichts
   lief.

Dazu die Freigaberegel in `docs/firmware_update.md`: **kein OTA-Release ohne
einmal geöffnete Geräteseite auf echter Hardware**, mit mitlaufenden Werten
und einer Änderung, die ein Neuladen überlebt.

Nicht gemacht: die Geräteseite von ESPHomes Webserver lösen. Ein eigener
HTTP-Dienst im Gerät wäre unabhängig, kostet aber Flash, Wartung und eine
zweite Zulassungsbetrachtung — und die Prüfung oben fängt denselben Fehler
zu einem Bruchteil der Kosten. Die Abhängigkeit bleibt also, sie ist nur
nicht mehr unbemerkt.

## Fernalarm — entschieden am 22. August 2026

Der Wächter hat einen blinden Fleck: **Er erreicht den Kunden nur, solange
dieser sein Netz erreicht.** Wer am Strand steht, während das Fahrzeug
aufgebockt wird, findet den eingerasteten Alarm erst bei der Rückkehr — das
Gegenteil dessen, wofür er da ist.

Erwogen wurde ein **eigener Server mit Konten pro Kunde**. Zurückgestellt, und
zwar aus demselben Rechenweg, der schon die Basisstation gekippt hat: Der
Server kostet fünf Euro im Monat, alles daran hängende nicht.

- **Cyber Resilience Act** — heute ist Level ein Gerät im LAN ohne offenen
  Dienst. Mit Konten, Token und öffentlichem Endpunkt wächst die
  Angriffsfläche um Größenordnungen, und die Meldepflichten wachsen mit.
- **DSGVO** — Daten pro Account sind personenbezogene Daten. Löschkonzept,
  Auskunftsersuchen, 72-Stunden-Meldung. Dauerhafte Arbeit, kein einmaliger
  Aufwand.
- **Die Haftung kippt** — ein Alarm, der wegen eines ausgefallenen Servers
  nicht ankam, ist ein Versagen des eigenen Produkts, nicht der Einrichtung
  des Kunden. Das ist eine Verfügbarkeitszusage.
- **Ewigkeitsverpflichtung** — 300 verkaufte Geräte binden den Dienst
  dauerhaft, auch wenn der Verkauf endet.

**Eine Plattform ist ein Geschäft, kein Merkmal.**

Stattdessen der abgestufte Weg:

| Stufe | Inhalt | Kosten und Pflichten |
|---|---|---|
| 1 | MQTT auf einen aus dem Internet erreichbaren Broker — **geht heute schon** | keine, aber **TLS fehlt**, siehe offene Punkte |
| 2 | **Feld für einen Push-Dienst** (ntfy, Gotify, Pushover, Telegram): Der Kunde trägt sein eigenes Ziel ein, wie beim MQTT-Broker | keine Konten, keine Datenhaltung, keine Verfügbarkeitszusage |
| 3 | Konten, Verlauf über Reisen, Flottenansicht für Vermieter | Geschäftsmodell mit Abo |

**Beschlossen: Stufe 2, aber später.** Sie ist reine Firmware — keine
Platinenänderung, keine neue Zulassung — und lässt sich jederzeit über OTA
nachliefern, auch an bereits verkaufte Geräte. Sie gehört deshalb **nicht auf
den kritischen Pfad** vor der ersten Serie.

## Ideen für 4.x — gesammelt am 22. September 2026

Der Maßstab ist nicht „was wäre noch nett“, sondern: **Was können die
Wettbewerber strukturell nicht?** Beide sind Batteriegerate mit Bluetooth,
ohne Drehratenmessung und ohne Dauerstrom. Alles, was daraus folgt, ist
verteidigbar; alles andere ist Beiwerk.

Nichts davon ist beschlossen. Reihenfolge ist Vorschlag, nicht Plan.

### 1. Akustische Auffahrhilfe — gebaut am 22.09.2026

Beim Auffahren auf Keile schaut niemand aufs Handy — man sitzt am Lenkrad.
Der Summer ist verbaut: Takt schneller werdend, je näher am Ziel, Dauerton
bei „eben“. In einem Satz erklärt, in jedem Video zu zeigen, und von einem
Batteriegerät ohne Summer nicht nachzubauen.

Gebaut: Schalter *Auffahrton*, 50-ms-Takt, Abstand der Töne aus dem
größten Hub einer Ecke (1000 ms ab zehn Zentimetern, 120 ms am Ziel, dann
ein langer Ton). Drei Entscheidungen darin:

- **Er folgt dem Zielprofil.** Gemessen wird am Hub je Ecke, und der enthält
  Fahrzeugmaße, Fahrzeugart, Toleranz und Profil bereits. Wer im Profil
  „Schlafen“ auffährt, wird zu dessen Ziel geführt.
- **Er kommt nach einem Neustart immer aus** (`restore_mode: ALWAYS_OFF`) und
  schaltet sich ab, sobald das Ziel erreicht ist. Das Gerät hängt am Bordnetz
  und ist auch während der Fahrt an — ein Ton, der ungefragt losgeht, wäre
  auf der Autobahn unerträglich. Dazu eine Abschaltung nach zehn Minuten.
- **Der Alarm hat Vorrang.** Zwei Tonfolgen auf einem Summer sind keine
  Information mehr.

Offen: Lautstärke im Fahrerhaus — der MLT-8530 sitzt im Wohnraum, nicht in
der Kabine. Das entscheidet sich erst an der Platine im Gehäuse.

### 2. Push-Ziel für den Wächter

Siehe „Fernalarm“ oben, Stufe 2 — hier nur die Einordnung: Es ist der
größte offene Hebel. Ein Wächter, der nur im heimischen Netz meldet, nützt
genau dann nichts, wenn man ihn braucht. Ein Feld für ntfy, Gotify oder
Telegram, der Kunde trägt sein eigenes Ziel ein — keine Konten, keine
Datenhaltung, keine Verfügbarkeitszusage.

### 3. Wächter automatisch scharf

„Nach 20 Minuten Ruhe von selbst“. Wer Home Assistant hat, baut sich das;
wer keins hat, hat keinen Schutz, sobald er das Scharfschalten vergisst —
und genau das vergisst man.

Aufwand: klein. Ein Zahlenregler neben der Karenzzeit, 0 = aus.

### 4. Nachtruhe für die Status-LED

Eine rote LED im verdunkelten Wohnraum stört. Zeitfenster oder Helligkeit
über PWM. Kommt in Bewertungen vor, kostet fast nichts.

Aufwand: klein. Die LED hängt an GPIO8 und ist bereits schaltbar.

### 5. Windwarnung / „Markise einfahren“

Steht oben unter „Zurückgestellt“ mit dem Vermerk, dass Aufzeichnungen
fehlen. Seit 4.0.0 läuft der LSM6DS3TR-C, und sein Rauschen ist gemessen
(0,024°, siehe `docs/kalibrierung.md`) — die Aufzeichnungen lassen sich
also im laufenden Betrieb sammeln. Die eigentliche Schwierigkeit bleibt: Wind
von Menschen im Fahrzeug zu unterscheiden.

Aufwand: mittel, plus Feldaufzeichnungen.

### 6. Externer Temperaturfühler

In `docs/mqtt.md` steht ausdrücklich: *„Die Innentemperatur ist kein
Thermometer.“* Der Chip erwärmt sich selbst und sitzt dort, wo das Gehäuse
klebt. Die Frostwarnung ist damit grob, und die Kalibrierprüfung rechnet mit
einer Temperatur, die nicht die des Raums ist.

Ein DS18B20 an der bereits vorhandenen Stiftleiste J4 macht daraus eine echte
Frostwarnung — ein Bauteil unter einem Euro für ein Argument, das jeder
versteht: warnt, bevor die Wasserleitung platzt.

Aufwand: klein in der Firmware, ein Stecker am Gehäuse, Dokumentation. Die
Chiptemperatur bleibt daneben bestehen: Sie überwacht die Kalibrierung, und
dafür ist genau sie die richtige.

### Nicht auf der Liste

**Andere Produkte.** Die Gaswaage und alles Weitere stehen bis auf Weiteres
nicht zur Disposition — die Arbeit konzentriert sich auf Level, bis es
verkauft wird.

**Eigene App, Bluetooth, eigener Server, Aktoren schalten.** Begründet oben:
SIG-Gebühr, Plattformkosten, Haftung.

## Offene Punkte

1. ~~MQTT ergänzen~~ — erledigt in 3.2.0, Fehler behoben in 3.5.1/3.5.2. Die
   Gegenprobe an einem Cerbo GX mit Node-RED steht noch aus; sie ist der
   Nachweis für das wichtigste Verkaufsargument.
2. ~~Zentimeterrechnung ins Gerät~~ — erledigt, Fahrzeugtyp getrennt.
3. ~~Bewegungserkennung und Schräglagenwarnung~~ — erledigt, Ausbau siehe oben.
4. Verkaufstext ohne die zwei widerlegbaren Behauptungen (cm-Anzeige,
   Wohnwagen) fassen.
5. Prüflabor ansprechen, Paketpreis erfragen.
6. Seriengröße festlegen — sie entscheidet über die Zulassungskosten je Stück.
7. Grenzwinkel und kritische Dauer für den Absorberkühlschrank belegen.
8. **TLS für den MQTT-Client.** Der Client ist ohne Verschlüsselung
   konfiguriert (kein `certificate_authority` in `hardware.yaml`). Im
   Heimnetz ist das vertretbar; wer den Broker aber ins Internet legt — der
   Weg zum Fernalarm, siehe oben —, schickt Passwort und Daten im Klartext.
   Vor jeder Empfehlung in diese Richtung nachzurüsten, und dabei gegen den
   Flash-Verbrauch zu prüfen: Stand 3.9.0 sind 71,7 % belegt.
9. Push-Dienst als Fernalarm (Stufe 2), nach dem Verkaufsstart — siehe
   auch „Ideen für 4.x“, Punkt 2.
10. **Achszuordnung und Vorzeichen am ersten Rev-B-Muster bestätigen.** Die
    Werte in den Substitutions sind aus dem Platinenlayout und der Achsfigur
    des ST-Datenblatts abgeleitet, nicht gemessen. Verfahren in
    `docs/kalibrierung.md`, Schritte 2 und 3. Am selben Muster: I²C-Scan
    zeigt 0x6A, Status-LED blinkt, Summer tönt hörbar, eigenes Netz sichtbar.
11. **Glättung und Bewegungsschwelle am neuen Sensor nachmessen.** Am
    Handmuster am 22.09.2026 gemessen (673 Punkte, pitch σ 0,0242°): Die
    Rauschgrenze steht jetzt auf 0,11° statt 0,25°, Verfahren in
    `docs/kalibrierung.md`. **An Rev B zu wiederholen** — anderer Aufbau,
    möglicherweise ruhiger. Die Bewegungsschwelle `motion_deg_s` (3,0 °/s)
    ist noch unangetastet.
12. ~~Board für die Serie festlegen~~ — entschieden, siehe „Der
    Hardwarewechsel", Punkt 3: eigene Platine mit ESP32-C3-WROOM-02.
13. **Icon bei `home-assistant/brands` eintragen.** HACS und Home Assistant
    laden Integrations-Icons ausschließlich von `brands.home-assistant.io`;
    der Ordner `custom_components/camperminder/brand/` ist dafür unsichtbar
    und nur die Vorlage. Nötig ist ein Pull Request mit diesem Ordner unter
    `custom_integrations/camperminder/` — die Dateien haben bereits die
    geforderten Maße (icon 256², icon@2x 512², logo 256 hoch, logo@2x 512).
    Geht erst, wenn das Repository wieder öffentlich ist: Die Betreuer
    verlangen eine öffentlich installierbare Integration. Das gelegentlich
    fehlende ESPHome-Icon am Gerät hat dieselbe Quelle und fehlt ohne
    Internet im Camper; daran ändert der Eintrag nichts.
14. ~~**Home-Assistant-Blueprints.**~~ Gebaut am 22.09.2026, drei Stück in
    `blueprints/automation/camperminder/` mit frei wählbarer Benachrichtigung
    (Feld „Was soll passieren?“) — Kühlschrankwarnung, Wächteralarm,
    Frostwarnung. **In einer echten Home-Assistant-Instanz noch zu erproben**,
    und der Import über die Adresse geht erst, wenn das Repository öffentlich
    ist (siehe Punkt 13). Begründung der Auslöserwahl in
    `blueprints/README.md`. Ursprünglich notiert als — der
    Wert entsteht nicht durch neue Funktionen, sondern dadurch, dass die
    vorhandenen beim Kunden ohne Bastelei ankommen. Damit ist die Anbindung
    an Home Assistant abgeschlossen.
15. **Verschlüsselung der MQTT-Verbindung.** Dieselbe Sache wie Punkt 8, aber
    aus Kundensicht: Die Schnittstelle ist bewusst offen, damit jeder seinen
    eigenen Broker anbinden kann — genau deshalb gehört TLS dazu, bevor das
    beworben wird. Ohne sie gehen Passwort und Messwerte im Klartext über die
    Leitung, sobald der Broker nicht im Heimnetz steht.

## Marktumfeld, zur Einordnung

- Bestand Wohnmobile Deutschland: **über 1 Million** (KBA, April 2025), seit
  2017 mehr als verdoppelt
- Neuzulassungen Deutschland 2025: 75.368 Wohnmobile
- Halterwechsel Deutschland 2025: **111.034 Wohnmobile** — der Nachrüstmarkt
  hängt hieran, nicht an Neuzulassungen
- Aktive deutschsprachige Gemeinschaft mit sichtbaren Multiplikatoren:
  womo.blog, schleeh.de, smarthomeundmore.de, simon42, camper-bauen.de,
  my-pepper, viercampen.de
