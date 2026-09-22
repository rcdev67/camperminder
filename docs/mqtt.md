# MQTT — CamperMinder an fremde Systeme anbinden

Level meldet Neigung, Hubhöhe je Ecke und die Anweisung im Klartext an einen
MQTT-Broker. Damit lässt es sich in Systeme einbinden, die keinen
Neigungssensor haben — **Victron Cerbo GX**, ioBroker, openHAB, Node-RED,
E1NFACH E1NS.

> **Für Home Assistant nicht nötig.** Dort läuft alles über die native
> ESPHome-Schnittstelle. MQTT ist der Weg zu allem anderen.

## Einrichten

Auf der Geräteseite unter **Technik → MQTT**, oder in Home Assistant über die
Entitäten `MQTT Broker`, `MQTT Port`, `MQTT Benutzer`, `MQTT Passwort` und den
Knopf `MQTT speichern`.

Danach startet das Gerät neu. Der Zustand steht anschließend in der Entität
**MQTT**:

| Anzeige | Bedeutung |
|---|---|
| `aus` | keine Adresse eingetragen — MQTT ist abgeschaltet |
| `verbunden mit …` | läuft |
| `keine Verbindung zu …` | Adresse erreichbar? Port? Benutzer und Passwort? |

**Adresse leeren und speichern schaltet MQTT wieder ab.** Ohne Eintrag baut das
Gerät keine Verbindung auf und schreibt nichts ins Log — wer MQTT nicht
benutzt, merkt nichts davon.

## Themen

```
camperminder/level/<art>/<name>/state
```

Erreichbarkeit meldet das Gerät unter `camperminder/level/status` mit `online`
bzw. `offline` (Last Will). Wer Werte weiterverarbeitet, sollte darauf hören —
sonst rechnet er nach einem Stromausfall mit dem letzten bekannten Stand
weiter.

### Was zum Ausrichten gebraucht wird

| Thema | Inhalt |
|---|---|
| `camperminder/level/sensor/neigung_pitch/state` | Längsneigung in Grad, `+` = Front höher |
| `camperminder/level/sensor/neigung_roll/state` | Querneigung in Grad, `+` = rechts höher |
| `camperminder/level/sensor/hub_vorne_links/state` | Hubhöhe in cm |
| `camperminder/level/sensor/hub_vorne_rechts/state` | Hubhöhe in cm |
| `camperminder/level/sensor/hub_hinten_links/state` | Hubhöhe in cm |
| `camperminder/level/sensor/hub_hinten_rechts/state` | Hubhöhe in cm |
| `camperminder/level/sensor/stuetzrad/state` | Wohnwagen: `+` hoch, `−` runter |
| `camperminder/level/text_sensor/anweisung/state` | `Hinten links 4.5 cm hoch` |

Beim **Wohnwagen** bedeuten „hinten links/rechts" die beiden Räder der einen
Achse; „vorne" bleibt auf 0, dort steht das Stützrad.

Die Hubhöhen sind **fertig gerechnet** — Fahrzeugmaße, Fahrzeugart und
Toleranz sind darin schon berücksichtigt. Ein anbindendes System muss nichts
nachrechnen und braucht die Fahrzeugmaße nicht zu kennen.

### Zustände

| Thema | Inhalt |
|---|---|
| `camperminder/level/binary_sensor/camper_steht_gerade/state` | `ON` = innerhalb der eingestellten Toleranz |
| `camperminder/level/binary_sensor/schraeglage/state` | `ON` = über dem Grenzwert, Vorgabe 3° (Absorberkühlschrank) |
| `camperminder/level/binary_sensor/lageaenderung/state` | `ON` = Fahrzeug hat seine Ruhelage verlassen |
| `camperminder/level/binary_sensor/in_bewegung/state` | `ON` = Erschütterung, also Anwesenheit |
| `camperminder/level/text_sensor/eigenes_netz/state` | `offen` oder `mit Passwort` |
| `camperminder/level/text_sensor/firmware_version/state` | z. B. `3.2.0` |

**`in_bewegung` ist kein Alarm.** Es meldet, dass jemand einsteigt, der Wind
drückt oder der Nachbar rangiert. Der Alarm ist `lageaenderung` — das Fahrzeug
hat seine Lage verlassen und ist nicht zurückgekommen.

### Selbstüberwachung

Ein fest verbautes Gerät kann sich selbst beobachten, ein Handgerät nicht.

| Thema | Inhalt |
|---|---|
| `camperminder/level/binary_sensor/kalibrierung_pruefen/state` | `ON` = Temperatur oder Sensorbetrag weit weg von der Kalibrierung |
| `camperminder/level/text_sensor/kalibrierung/state` | `am 22.08.2026 bei 21 °C` — mit Zusatz, wenn zu prüfen |
| `camperminder/level/binary_sensor/montage_pruefen/state` | `ON` = der Sensor liefert Unsinn, Gehäuse lose? |
| `camperminder/level/binary_sensor/frostgefahr/state` | `ON` = unter dem Grenzwert |
| `camperminder/level/sensor/innentemperatur/state` | °C, Chiptemperatur plus Abgleich |
| `camperminder/level/number/driftwarnung_ab/…` | 5 – 50 Kelvin, Vorgabe 20 |
| `camperminder/level/number/temperatur_abgleich/…` | −20 … 20 Kelvin |
| `camperminder/level/number/frostwarnung_unter/…` | −10 … 15 °C, Vorgabe 3 |

Nicht die Zeit verschiebt den Nullpunkt eines Neigungsmessers, sondern die
**Temperatur** — siehe `drift_messung.md`. Das Gerät merkt sich deshalb beim
Kalibrieren die Chiptemperatur und den Betrag des Beschleunigungsvektors und
vergleicht laufend dagegen.

**Die Innentemperatur ist kein Thermometer.** Der Chip erwärmt sich selbst und
sitzt dort, wo das Gehäuse klebt. Für eine Frostwarnung reicht sie, für eine
Klimaregelung nicht.

### Zielprofile

Eine Wasserwaage kennt ein Ziel: null. Dieses Gerät kennt Ziele — und richtet
danach aus. Das Profil wirkt **ausschließlich** auf das Ausrichten;
Schräglagenwarnung und Wächter rechnen weiter mit der echten Neigung.

| Thema | Inhalt |
|---|---|
| `camperminder/level/select/zielprofil/…` | `Ausrichten`, `Schlafen`, `Ablassen` |
| `camperminder/level/select/schlafrichtung/…` | `Kopf vorn`, `Kopf hinten`, `Kopf links`, `Kopf rechts` |
| `camperminder/level/number/kopfende_anheben/…` | 0 … 15 cm, Vorgabe 2 |
| `camperminder/level/select/ablasspunkt/…` | `vorn`, `hinten`, `links`, `rechts`, `vorn links`, `vorn rechts`, `hinten links`, `hinten rechts` |
| `camperminder/level/number/neigung_zum_ablasspunkt/…` | 0 … 15 cm, Vorgabe 5 |
| `camperminder/level/sensor/ziel_laengs/state` | geltende Zielneigung längs in cm |
| `camperminder/level/sensor/ziel_quer/state` | geltende Zielneigung quer in cm |

**Richtung und Betrag statt Vorzeichen.** Das Profil `Schlafen` fragt, wo der
Kopf liegt — in Fahrtrichtung gesehen —, und um wie viel das Kopfende höher
stehen soll. Das Profil `Ablassen` fragt nach dem **tiefsten** Punkt, also der
Ecke oder Seite, an der Boiler oder Tank ablaufen; angehoben wird die
Gegenseite. Welche Achse und welches Vorzeichen daraus folgt, rechnet das
Gerät. Bei `Kopf links`/`Kopf rechts` und bei einem seitlichen Ablasspunkt
entsteht eine **Quer**neigung, bei `Kopf vorn`/`Kopf hinten` und vorn/hinten
eine Längsneigung; eine Ecke neigt beide Achsen.

> **Geändert mit 4.0.0.** Die drei vorzeichenbehafteten Zahlen
> `schlafen_laengs`, `ablassen_laengs` und `ablassen_quer` gibt es nicht mehr.
> Wer sie abonniert hatte, nimmt jetzt die beiden `select`- und die beiden
> `number`-Themen darunter — oder einfacher die zwei `ziel_*`-Sensoren, die
> sich nicht geändert haben.

Die beiden `ziel_*`-Sensoren sind der bequeme Weg für ein anbindendes System:
Sie liefern fertig, was das gewählte Profil verlangt, ohne dass man die Regler
selbst auswerten muss. Vorzeichen wie überall im Gerät: **längs plus = Front
höher**, **quer plus = rechte Seite höher**. Die Hubhöhen je Ecke
berücksichtigen das Ziel bereits.

### Kühlschrank-Zeitkonto

`schraeglage` meldet den **Winkel**. Was einen Absorberkühlschrank beschädigt,
ist aber der Winkel **mal der Zeit** — kurz schief beim Rangieren ist
folgenlos. Wer eine Benachrichtigung schalten will, nimmt deshalb
`kuehlschrank_warnung` und nicht `schraeglage`.

| Thema | Inhalt |
|---|---|
| `camperminder/level/binary_sensor/kuehlschrank_warnung/state` | `ON` = lange genug schief, dass der Kühlschrank leidet |
| `camperminder/level/sensor/schraeglage_dauer/state` | Minuten über dem Grenzwert, `0` wenn gerade nicht |
| `camperminder/level/text_sensor/kuehlschrank/state` | `arbeitet normal`, `3.4° schief seit 42 min - die Kühlleistung fällt ab` |
| `camperminder/level/number/kuehlschrank_kritisch_nach/…` | 5 – 240 Minuten |

Drei Stufen, abgeleitet aus einem einzigen Regler: Hinweis ab dem
Überschreiten des Winkels, Warnung nach einem Drittel der eingestellten Zeit,
dringend nach der vollen Zeit.

### Wächter

`lageaenderung` ist ein Messwert: Kommt das Fahrzeug in seine Lage zurück, geht
es wieder aus. Als Alarm taugt das nicht — wer schläft, verpasst ihn. Der
Wächter macht daraus einen Zustand, der **einrastet** und stehen bleibt, bis er
quittiert wird.

| Thema | Inhalt |
|---|---|
| `camperminder/level/binary_sensor/waechter_alarm/state` | `ON` = hat ausgelöst und ist nicht quittiert |
| `camperminder/level/text_sensor/waechter/state` | `aus`, `scharf in 45 s`, `scharf seit 2 h 10 min`, `ALARM - Lage verändert am 22.08. um 03:14` |
| `camperminder/level/text_sensor/letzte_bewegung/state` | `gerade jetzt`, `22.08. um 21:40`, `vor 3 h 12 min` |
| `camperminder/level/switch/waechter/…` | `ON` / `OFF` — scharf schalten |
| `camperminder/level/number/waechter_karenzzeit/…` | 0 – 600 s |

Der Alarm übersteht einen Stromausfall: Wer die Versorgung kappt, löscht ihn
damit nicht. Fehlte beim Auslösen eine gültige Uhr — auf einem Stellplatz ohne
Internet der Normalfall —, nennt der Text eine Zeitspanne statt einer Uhrzeit.

Quittiert wird über `camperminder/level/button/alarm_quittieren/command`. Das
löscht den Alarm, **ohne** den Wächter abzuschalten, und nimmt die jetzige Lage
als neuen Bezugspunkt.

### Statuswerte

Die Klartextsätze oben (`waechter`, `kuehlschrank`, `kalibrierung`,
`letzte_bewegung`, `mqtt`, `eigenes_netz`) sind deutsch formuliert. Die
Geräteseite kann Deutsch und Englisch und bildet ihre Sätze deshalb selbst —
dafür gibt es dieselben sechs Auskünfte noch einmal als Werte:

| Thema | Inhalt |
|---|---|
| `camperminder/level/text_sensor/statuswerte/state` | `w=scharf:7830;k=2:2760:3.4;c=1758200000:21:27:1;b=vor:1200;m=getrennt;n=offen` |

Schlüssel=Wert, getrennt durch Semikolon. Zeitspannen in Sekunden, Zeitpunkte
als Unix-Zeit (`0` = es gab keine gültige Uhr).

| Schlüssel | Werte |
|---|---|
| `w` Wächter | `aus`, `karenz:REST`, `scharf:SEIT`, `alarm:ZEITPUNKT`, `alarm_vor:SEIT`, `alarm_unbekannt` |
| `k` Kühlschrank | `ok` oder `STUFE:DAUER:GRAD` mit Stufe 1 bis 3 |
| `c` Kalibrierung | `nie`, `ohne_werte` oder `ZEITPUNKT:TEMP:JETZT:PRUEFEN` |
| `b` Bewegung | `nie`, `jetzt`, `ZEITPUNKT` oder `vor:SEKUNDEN` |
| `m` MQTT | `aus`, `verbunden`, `getrennt` |
| `n` Eigenes Netz | `offen`, `passwort` |

Die Entität ist `diagnostic` und in Home Assistant standardmäßig eingeklappt.
Ein anbindendes System braucht sie nicht — die Klartextsätze und die
`binary_sensor` sind bequemer. Sie ist dokumentiert, weil sie im Thema
auftaucht und niemand rätseln soll, was dort steht.

### Einstellbar über MQTT

Diese Themen nehmen auch Befehle entgegen (`…/command`):

| Thema | Werte |
|---|---|
| `camperminder/level/number/schraeglage_grenzwert/…` | 1 – 10 Grad |
| `camperminder/level/number/lageaenderung_grenzwert/…` | 0,2 – 5 Grad |
| `camperminder/level/number/waechter_karenzzeit/…` | 0 – 600 Sekunden |
| `camperminder/level/switch/praezisionsmodus/…` | `ON` / `OFF` |
| `camperminder/level/switch/waechter/…` | `ON` / `OFF` |
| `camperminder/level/switch/status_led/…` | `ON` / `OFF` — die Leuchte am Gerät |
| `camperminder/level/switch/alarmton/…` | `ON` / `OFF` — der Summer beim Alarm |
| `camperminder/level/switch/auffahrton/…` | `ON` / `OFF` — die akustische Auffahrhilfe. Kommt nach einem Neustart immer **aus** zurück und schaltet sich selbst ab, sobald das Ziel erreicht ist |

Der Auffahrton taktet umso schneller, je kleiner der größte Hub einer Ecke
ist — 1000 ms ab zehn Zentimetern, 120 ms am Ziel, dann ein langer Ton. Er
folgt dabei dem **Zielprofil**: Wer im Profil „Schlafen“ auffährt, wird zu
dessen Ziel geführt, nicht nach null.

Die drei letzten gibt es seit 4.0.0. Sie ersetzen zusammen mit der
Blinkanzeige das Display des ersten Prototyps: Das ausgelieferte Gerät hat
keins. **Ein eingerasteter Alarm blinkt auch bei ausgeschalteter Status-LED** —
der Schalter nimmt die Betriebsanzeige weg, nicht die Meldung.

Fahrzeugmaße, Toleranz und Keilstufe erscheinen ebenfalls als `number` bzw.
`select` unter ihren jeweiligen Namen.

### Warum die Reihenfolge `<art>/<name>` ist

Sie kommt von ESPHome und ließe sich je Entität überschreiben. Sie bleibt aus
einem Grund: Neue Entitäten erscheinen von selbst am richtigen Platz. Ein von
Hand gepflegtes Thema vergisst man beim Hinzufügen — und dann fehlt es
ausgerechnet dem, der sich darauf verlassen hat.

Ausdrücklich festgelegt sind nur die Themen von Entitäten mit Umlaut im Namen:
Aus „Stützrad" würde sonst `st__tzrad`, aus „Schräglage" `schr__glage`, aus
„Wächter" `w__chter`. Der Anzeigename bleibt deutsch, das Thema wird lesbar.

## Erkennung ist ausgeschaltet

`discovery: false`. In Home Assistant stünde sonst jede Entität **doppelt** —
einmal über die native Schnittstelle, einmal über MQTT.

Fremde Systeme brauchen die Erkennung nicht; sie abonnieren die Themen oben
direkt. Wer sie doch will — etwa für eine zweite Home-Assistant-Instanz, die
das Gerät nicht selbst eingebunden hat —, setzt `discovery: true` in
`esphome/level/hardware.yaml` und baut neu.

## Victron Cerbo GX

Venus OS bringt einen eigenen Broker mit; in der **Large**-Fassung lassen sich
mit Node-RED *virtuelle Geräte* anlegen, die auf dem GX-Display und in VRM wie
echte Victron-Hardware erscheinen.

Der Weg:

1. In Venus OS unter *Settings → Services → MQTT on LAN* den Broker
   freischalten.
2. Auf der CamperMinder-Geräteseite die Adresse des Cerbo eintragen.
3. In Node-RED die Themen oben abonnieren und auf ein virtuelles Gerät legen.

Zum Ausrichten genügen `anweisung` und die vier `hub_*` — der Rest ist Zugabe.

## Kein Neustart mehr ohne Broker

`reboot_timeout: 0s`. ESPHome startet ein Gerät voreingestellt neu, wenn MQTT
15 Minuten lang nicht verbindet. Bei jedem Kunden ohne Broker wäre das ein
Neustart alle Viertelstunde — deshalb abgeschaltet.
