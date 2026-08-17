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

## Offene Punkte

1. MQTT ergänzen und gegen einen Cerbo GX mit Node-RED gegenprobieren — das ist
   der Nachweis für das wichtigste Verkaufsargument.
2. Zentimeterrechnung ins Gerät verlagern, Fahrzeugtyp Wohnmobil/Wohnwagen
   trennen.
3. Bewegungserkennung und Schräglagenwarnung ergänzen.
4. Verkaufstext ohne die zwei widerlegbaren Behauptungen (cm-Anzeige,
   Wohnwagen) fassen.
5. Prüflabor ansprechen, Paketpreis erfragen.
6. Seriengröße festlegen — sie entscheidet über die Zulassungskosten je Stück.

## Marktumfeld, zur Einordnung

- Bestand Wohnmobile Deutschland: **über 1 Million** (KBA, April 2025), seit
  2017 mehr als verdoppelt
- Neuzulassungen Deutschland 2025: 75.368 Wohnmobile
- Halterwechsel Deutschland 2025: **111.034 Wohnmobile** — der Nachrüstmarkt
  hängt hieran, nicht an Neuzulassungen
- Aktive deutschsprachige Gemeinschaft mit sichtbaren Multiplikatoren:
  womo.blog, schleeh.de, smarthomeundmore.de, simon42, camper-bauen.de,
  my-pepper, viercampen.de
