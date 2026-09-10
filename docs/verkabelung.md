# Verkabelung

Ab Version 4.0.0 besteht das Gerät aus zwei Teilen: einem **ESP32-C3 ohne
Display** und einem **LSM6DS3TR-C** auf einem Adafruit-Breakout. Sie hängen an
einem I²C-Bus.

Wer noch das Board des ersten Prototyps benutzt — ESP32-C3 mit aufgelötetem
0,42″-OLED und MPU6050 —, findet am Ende dieser Seite, was sich für ihn ändert.

---

## LSM6DS3TR-C (Adafruit 4503) → ESP32-C3

| Breakout | ESP32-C3 | Hinweis |
|----------|----------|---------|
| **VIN**  | **3V3**  | Der Breakout hat eigenen Regler und Pegelwandler und nähme auch 5 V. 3V3 ist trotzdem richtig: Der SuperMini führt an seinem 5-V-Pin nur dann Spannung, wenn er selbst über USB versorgt wird — im Fahrzeug hängt er am Wandler, und dort liegt dort nichts an. |
| **GND**  | GND      | gemeinsame Masse — zwingend |
| **SDA**  | **GPIO5** | |
| **SCL**  | **GPIO6** | |
| 3Vo      | offen lassen | Ausgang des Reglers auf dem Breakout, wird nicht gebraucht |
| INT1, INT2 | offen lassen | ESPHome fragt den Sensor im 100-ms-Takt ab; ein Interrupt ist nicht vorgesehen |
| Lötbrücke auf der Rückseite | **offen lassen** | offen → Adresse **0x6A**. Geschlossen → 0x6B, dann in `hardware.yaml` unter `motion:` die Adresse mitändern |

Die Pins stehen als Substitutionen in
[`esphome/level/hardware.yaml`](../esphome/level/hardware.yaml) unter
`i2c_sda_pin` und `i2c_scl_pin` — wer anders verdrahtet, ändert sie dort und
nicht im Code.

> **Löten ist nicht zwingend.** Der Breakout hat zwei STEMMA-QT-Buchsen
> (steckerkompatibel mit SparkFun Qwiic). Mit einem JST-SH-Kabel auf vier
> Einzeldrähte hängt der Sensor am Steckbrett, ohne dass an ihm eine
> Lötstelle entsteht. Für den Prototyp ist das der schnellere Weg; für den
> Einbau ins Fahrzeug ist gelötet oder gecrimpt besser — ein Steckverbinder,
> der sich über Jahre durchrüttelt, sieht als Fehlerbild aus wie ein defekter
> Sensor.

### Anschlüsse ohne weitere Aufgabe

| ESP32-C3 | Wofür |
|---|---|
| **GPIO8** | eingebaute LED des SuperMini, Betriebs- und Alarmanzeige — schon auf der Platine verbunden, nichts zu tun |
| **GPIO10** | Summer, passives Piezoelement gegen GND. Optional: Hängt nichts daran, passiert nichts. |

Ein **aktiver** Summer mit eigener Elektronik taugt hier nicht — der pfeift
stur auf seiner eigenen Frequenz und ignoriert die Tonfolge. Es muss ein
passives Piezoelement sein.

---

## ESP32-C3 — freie und gesperrte Pins (wichtig!)

Der C3 ist **nicht** wie ein klassischer ESP32:

- **GPIO0/1** = 32-kHz-Quarz → für I²C unbrauchbar
- **GPIO2/8/9** = Strapping (Boot) · **GPIO11** = VDD_SPI · **GPIO12–17** = Flash
- **GPIO18/19** = USB · **GPIO20/21** = UART0 (Log)
- **frei nutzbar:** GPIO4, 5, 6, 7, 10

**GPIO8 ist Strapping-Pin und trägt trotzdem die LED.** Das geht gut, weil der
Pin beim Start Eingang ist und der Widerstand der LED ihn dabei nach oben zieht
— genau in den Zustand, den der Bootlader erwartet. ESPHome warnt beim Bauen
trotzdem; die Warnung ist an dieser Stelle richtig verstanden und harmlos. Auf
einer eigenen Platine gehört die LED an einen Pin ohne Nebenaufgabe.

---

## Kontrolle per Log

Nach dem Flashen im ESPHome-Log auf den I²C-Scan achten:

```
Found device at address 0x6A   ← LSM6DS3TR-C
```

Beim Bausatz mit Display steht **0x3C** (OLED) zusätzlich da.

| Was im Log steht | Was es heißt |
|---|---|
| **0x6A fehlt ganz** | SDA/SCL testweise tauschen, GND prüfen, Versorgung am VIN messen |
| **0x6B statt 0x6A** | Die Lötbrücke auf der Rückseite ist geschlossen. Entweder öffnen oder in `hardware.yaml` unter `motion:` `address: 0x6B` eintragen. |
| **0x68 oder 0x69** | Das ist ein MPU6050, kein LSM6DS3TR-C — falsches Modul erwischt |
| **`Unknown WHO_AM_I value`** | Etwas antwortet auf 0x6A, ist aber nicht dieser Chip. Bei einem gekauften Adafruit-Modul praktisch ausgeschlossen; bei Ware aus unklarer Quelle der übliche Befund. |

Pull-Widerstände sind **keine** zu ergänzen: Der Breakout bringt je 10 kΩ auf
SDA und SCL mit, dazu schaltet die Firmware die des ESP32 hinzu.

---

## Umstieg vom ersten Prototyp

Wer das Board mit aufgelötetem OLED und MPU6050 weiterbenutzen will:

1. **Den MPU6050 abklemmen.** Zwei Sensoren gleichzeitig gehen nicht — die
   Firmware kennt nur noch den einen.
2. Den Breakout wie oben an dieselben zwei Leitungen hängen. Die Adressen
   beißen sich nicht (0x3C, 0x6A).
3. In [`esphome/level/camperminder-level.yaml`](../esphome/level/camperminder-level.yaml)
   unter `packages:` die Zeile `anzeige: !include anzeige-oled.yaml`
   einkommentieren, dann bleibt das Display in Betrieb.
4. **Neu kalibrieren.** Der neue Sensor sitzt anders herum auf seiner Platine
   als der alte — Achszuordnung, Vorzeichen und Nullpunkt gelten nicht mehr.
   Das Verfahren steht in [kalibrierung.md](kalibrierung.md).

Punkt 4 ist keine Formsache. Bis die Achsen geprüft sind, kann das Gerät
Längs- und Querneigung vertauschen oder mit falschem Vorzeichen anzeigen — und
das sieht auf der Anzeige völlig plausibel aus.
