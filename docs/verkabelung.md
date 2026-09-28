# Platine und Anschlüsse

Ab Version 4.0.0 läuft die Firmware auf der eigenen Platine **CamperMinder
Level** (Rev B, 90 × 45 mm). Funkmodul, Sensor, Versorgung, LEDs und Summer
sitzen darauf — zu verkabeln ist nur noch die Stromversorgung.

Diese Seite beschreibt, was die Firmware auf der Platine vorfindet und woran
man erkennt, dass es stimmt.

---

## Anschlüsse nach außen

| Anschluss | Was | Hinweis |
|---|---|---|
| **J2** Schraubklemme | **VIN** 7–36 V, **GND** | Bordnetz 12 V oder 24 V. Dahinter Sicherung (0,5 A, selbstrückstellend), Überspannungsschutz und Verpolschutz — falsch herum angeklemmt passiert nichts, es geht nur nichts. |
| **J1** USB-C | Flashen, Log, 5 V | Dieselbe Buchse für alles; ein Seriellwandler ist nicht nötig, der ESP32-C3 spricht USB selbst. Darf gleichzeitig mit der Klemme stecken: Die höhere Quelle versorgt, nichts fließt zurück. |

Beide Anschlüsse sitzen an derselben Stirnkante. Das ist **hinten** — der Pfeil
auf der Platine und auf der Gehäusewand zeigt von ihnen weg nach vorn, die
Kabel laufen nach hinten ab.

## Was die Firmware benutzt

| GPIO | Bauteil | In `hardware.yaml` |
|---|---|---|
| **5** | SDA — Sensor U5 und Stiftleiste J4 | `i2c_sda_pin` |
| **6** | SCL — Sensor U5 und Stiftleiste J4 | `i2c_scl_pin` |
| **8** | Status-LED **D10** (rot), über 470 Ω gegen 3V3, leuchtet bei LOW | `status_led_pin`, `status_led_inverted` |
| **10** | Summer **BZ1** über Transistor Q1 | `buzzer_pin` |
| 4 | INT1 des Sensors — verdrahtet, von der Firmware nicht benutzt | — |
| 20 / 21 | UART RX / TX an J5 — Notzugang | — |
| 18 / 19 | USB | — |

GPIO8 ist ein Strapping-Pin und trägt trotzdem die LED. Das geht, weil R10 den
Pin beim Start auf HIGH zieht und die LED dabei dunkel bleibt — genau der
Zustand, den der Bootlader erwartet. ESPHome warnt beim Bauen; die Warnung ist
hier verstanden und harmlos.

### Sensor

**U5 LSM6DS3TR-C**, direkt auf der Platine. SDO/SA0 liegt fest an Masse, die
Adresse ist damit **0x6A** und nicht umschaltbar. CS liegt an 3V3, der Chip
arbeitet über I²C. Die Hilfsschnittstelle SDx/SCx ist nach Datenblatt auf
Masse gelegt, INT2 offen. Pull-ups für SDA und SCL bringt die Platine mit.

Die Achszuordnung der Firmware ist aus dem Layout abgeleitet — Herleitung bei
den Substitutions in [`hardware.yaml`](../esphome/level/hardware.yaml) — und
wird am ersten bestückten Muster bestätigt, siehe unten.

### LEDs

| | Farbe | Bedeutung |
|---|---|---|
| **D8** | grün | Betrieb: hängt fest an 3V3, leuchtet, sobald Strom da ist. Die Firmware kann sie nicht schalten. |
| **D10** | rot | Status: die Blinkmuster der Firmware (eigenes Netz, Heimnetz, Sensor stumm, Alarm) |

Beide sitzen nebeneinander an der Längskante gegenüber dem Summer.

### Summer

**BZ1 MLT-8530**, magnetisch, Resonanz 2700 Hz, an +5 V. Q1 schaltet ihn nach
Masse, GPIO10 steuert die Basis über 470 Ω. Die Firmware steuert den Pin **nicht
invertiert** an: Im Ruhezustand LOW, Q1 gesperrt, kein Strom durch die Spule.
Die Alarmtöne liegen auf e7 (2637 Hz), dicht an der Resonanz.

Der Summer ist nicht dicht — seine Schallöffnung zeigt zur Platinenkante, das
Schallloch im Gehäuse gehört seitlich daneben, nicht darüber.

### Taster

**SW1 BOOT** und **SW2 RESET**. Im Betrieb braucht sie niemand; sie sind für
den Fall, dass ein Modul nicht mehr über USB in den Bootlader findet: BOOT
halten, RESET tippen, BOOT loslassen.

### Stiftleisten — unbestückt

| | Belegung | Wofür |
|---|---|---|
| **J4** I²C | 3V3, GND, SDA, SCL | weitere I²C-Teilnehmer; für Werkstatt und Messplatz ein 0,42"-OLED (`anzeige-oled.yaml`) |
| **J5** UART | 3V3, GND, TX (GPIO21), RX (GPIO20) | Notzugang, falls USB einmal nicht geht |

---

## Ausrichtung im Fahrzeug

Der Pfeil **VORN** auf der Platine zeigt in Fahrtrichtung, von USB-Buchse und
Klemme weg. Der Pfeil auf der Gehäusewand zeigt in dieselbe Richtung. Um 90
Grad verdreht eingebaut vertauscht das Gerät Längs- und Querneigung, und das
sieht auf der Anzeige plausibel aus — deshalb der Pfeil.

Kopfüber montiert, etwa unter einem Regalbrett, hilft der Pfeil nicht; dafür
gibt es in der Firmware die Einstellung **Einbaulage** — siehe
[kalibrierung.md](kalibrierung.md), Schritt 1.

---

## Kontrolle per Log

Nach dem Flashen im ESPHome-Log auf den I²C-Scan achten:

```
Found device at address 0x6A   ← LSM6DS3TR-C
```

Mit einem OLED an J4 steht **0x3C** zusätzlich da.

| Was im Log steht | Was es heißt |
|---|---|
| **0x6A fehlt ganz** | Der Sensor antwortet nicht. Bei einem LGA-Gehäuse ist das fast immer eine Lötstelle unter dem Chip — mit der Lupe ist da nichts zu sehen. Erst prüfen, ob 3V3 am Sensor anliegt (FB1 sitzt in der Zuleitung), dann Nacharbeit oder Austausch der Platine. |
| **`Unknown WHO_AM_I value`** | Etwas antwortet auf 0x6A, ist aber kein LSM6DS3TR-C. Ein anderes Bauteil bestückt — Reklamation beim Bestücker. |
| **0x6B statt 0x6A** | Kann auf dieser Platine nicht vorkommen; SA0 liegt fest an Masse. |

---

## Das erste bestückte Muster

Was maschinell prüfbar war, ist am Entwurf geprüft. Sechs Dinge sind es nur
am Aufbau, und sie gehören an das erste Muster jeder Revision:

1. **I²C-Scan zeigt 0x6A**, die rote LED blinkt, das eigene Netz
   `CamperMinder` ist am Handy sichtbar.
2. **Achszuordnung und Vorzeichen** nach [kalibrierung.md](kalibrierung.md),
   Schritte 2 und 3: vorn anheben gibt positiven Pitch, rechts anheben
   positiven Roll. Stimmt es nicht, die Substitutionen in `hardware.yaml`
   anpassen — dort steht die Herleitung, an der man sieht, welche Annahme
   nicht gestimmt hat.
3. **Summer** — Wächter scharf schalten, Gerät kippen: drei kurze Töne,
   deutlich hörbar. Ein magnetischer Summer arbeitet auch verpolt, nur leiser;
   klingt er dünn, die Polung von BZ1 gegen das Datenblatt prüfen.
4. **Sendeleistung** — das eigene Netz muss durch eine Fahrzeugwand hindurch
   auf dem Stellplatz sichtbar sein. Die Firmware lässt das Modul auf seiner
   Voreinstellung.
5. **QR-Aufkleber und Anmeldeseite** — mit einem iPhone und einem
   Android-Handy: Code 1 scannen, das Handy muss dem Netz CamperMinder
   beitreten. Notieren, ob sich die Wasserwaage danach **von selbst** öffnet
   (iPhone: Fenster *Anmelden*). Dann Code 2: Die Seite muss im Browser
   normal laufen, nicht umgeleitet werden. Code 3 mit dem Gerät im
   Heim-WLAN: das Ergebnis je Handy notieren, auf Android ist `.local`
   nicht überall verfügbar.
6. **Suche im Heimnetz** — mit iPhone und Android je einmal das WLAN
   eintragen und die Seite offen lassen. Sie muss das Gerät nach dem
   Netzwechsel finden und „Gefunden: …" zeigen. Am Prüfstand ist das
   belegt; ob die Handys die offene Seite beim Wechsel weiterlaufen lassen,
   zeigt nur dieser Versuch.

---

## Der QR-Aufkleber

Drei Codes, damit niemand etwas tippen muss:

| Code | Inhalt | Wann |
|---|---|---|
| **1** Handy verbinden | `WIFI:T:nopass;S:CamperMinder;;` — das Handy tritt dem Netz bei | erster Start, unterwegs; immer zuerst |
| **2** Wasserwaage öffnen | `http://192.168.4.1/` | direkt nach Code 1 |
| **3** Im Heim-WLAN | `http://camperminder-level.local/` | Gerät im WLAN zu Hause, unter welcher Adresse auch immer |

Netzbeitritt und Adresse lassen sich nicht in einem Code vereinen: Das
WLAN-Format kennt kein Feld für eine Adresse. Den zweiten Scan erspart nur
die Anmeldeseite der Firmware (`esphome/level/anmeldeseite.h`, seit 4.2.0):
Im eigenen Netz beantwortet das Gerät die Internetprüfung des Handys mit
einer Weiterleitung auf `192.168.4.1`, dazu nennt es die Seite per
DHCP-Option 114 (seit 4.2.1). Vom iPhone ist bekannt, dass es sie dann von
selbst öffnet; am Muster geprüft ist das noch nicht. Das Samsung des Nutzers
tat es am 28.09.2026 nicht, obwohl das Protokoll die
Umleitung seiner Prüfanfrage zeigte (`connectivitycheck.gstatic.com`) —
deshalb Code 2.

Code 3 geht über den Namen, weil die Adresse im Heim-WLAN in jedem Haushalt
eine andere ist. Auf dem iPhone trägt das, auf Android nicht auf jedem Gerät;
dafür nennt die Anleitung die Suche der Geräteseite und den Router.

Jedes Gerät bekommt denselben Aufkleber: Adresse und Name stehen in der
Firmware und nicht im einzelnen Gerät. Das gilt auch für das Handmuster, es
heißt seit 28.09.2026 ebenfalls `camperminder-level`.

| | |
|---|---|
| Druckvorlage | [`bilder/aufkleber-qr.pdf`](bilder/aufkleber-qr.pdf), 90 × 52 mm, **bei 100 % drucken**, nicht „an Seite anpassen" |
| Vorlage für Anleitung und Etikettendienst | [`bilder/aufkleber-qr.svg`](bilder/aufkleber-qr.svg) |
| Material | wetterfeste Etikettenfolie, matt — ein glänzender Aufkleber spiegelt im Licht der Handykamera |
| Ort | auf den Deckel, gut erreichbar mit dem Handy; nicht dort, wo das Gerät später verbaut unsichtbar ist |

Erzeugt wird er von `tools/qr_aufkleber.py`, nicht von Hand. Das Skript liest
Netzname, Adresse und Gerätenamen aus `esphome/level/camperminder-level.yaml`,
bricht ab, wenn dort mDNS abgeschaltet wäre, und prüft die Ruhezone von vier
Modulen um jeden Code. Ändert sich eines davon in der Firmware, gilt der alte
Aufkleber nicht mehr — dann neu erzeugen und neu drucken.

---

## Handmuster auf ESP32-C3 SuperMini

Bis die bestellten Platinen da sind, läuft dieselbe Firmware auf einem
handgelöteten Aufbau: **ESP32-C3 SuperMini** plus Adafruit-Breakout mit dem
LSM6DS3TR-C an I²C. Dafür gibt es `esphome/level/muster-supermini.yaml` —
diese Datei bindet die Produktfirmware unverändert als Paket ein und ändert
nur, was der Handaufbau anders braucht.

| Punkt | Platine Rev B | Handmuster |
|---|---|---|
| Sendeleistung | Voreinstellung 20 dB, das WROOM-02 ist mit seiner Antenne zertifiziert | **8,5 dB** — bei 20 dB erscheint das eigene Netz des SuperMini gar nicht, Keramikantenne und USB-Versorgung tragen die Leistung nicht |
| Gerätename | `camperminder-level` | ebenfalls `camperminder-level`, damit Code 3 des Aufklebers auch am Muster prüfbar ist. Muster und Platine deshalb nie gleichzeitig im selben Netz betreiben |
| I²C, LED | GPIO5/6, LED an GPIO8 gegen 3V3 | gleich — die blaue LED des SuperMini hängt ebenfalls an GPIO8 und leuchtet bei LOW |
| Summer | BZ1 über Q1 an GPIO10 | nicht bestückt; der Pin bleibt unbenutzt |

**Was sich damit prüfen lässt:** Anzeige, Zielprofile, Wächter,
Kühlschrank-Zeitkonto, MQTT, Home Assistant, Sprachumschaltung, OTA — also
alles, was Software ist.

**Was sich damit NICHT prüfen lässt:** die Achszuordnung. Die Vorgaben in
`hardware.yaml` sind aus dem Layout der Platine abgeleitet; auf dem Muster
liegt das Breakout anders. Die Zuordnung für das Muster steht auskommentiert
in `muster-supermini.yaml`, das Ergebnis gilt aber **nur dort**. Punkt 2 der
Liste oben bleibt am ersten bestückten Board zu erledigen.

