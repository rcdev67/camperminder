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

### Einstellbar über MQTT

Diese Themen nehmen auch Befehle entgegen (`…/command`):

| Thema | Werte |
|---|---|
| `camperminder/level/number/schraeglage_grenzwert/…` | 1 – 10 Grad |
| `camperminder/level/number/lageaenderung_grenzwert/…` | 0,2 – 5 Grad |
| `camperminder/level/switch/praezisionsmodus/…` | `ON` / `OFF` |

Fahrzeugmaße, Toleranz und Keilstufe erscheinen ebenfalls als `number` bzw.
`select` unter ihren jeweiligen Namen.

### Warum die Reihenfolge `<art>/<name>` ist

Sie kommt von ESPHome und ließe sich je Entität überschreiben. Sie bleibt aus
einem Grund: Neue Entitäten erscheinen von selbst am richtigen Platz. Ein von
Hand gepflegtes Thema vergisst man beim Hinzufügen — und dann fehlt es
ausgerechnet dem, der sich darauf verlassen hat.

Ausdrücklich festgelegt sind nur sechs Themen, nämlich die von Entitäten mit
Umlaut im Namen: Aus „Stützrad" würde sonst `st__tzrad`, aus „Schräglage"
`schr__glage`. Der Anzeigename bleibt deutsch, das Thema wird lesbar.

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
