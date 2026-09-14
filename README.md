<p align="center">
  <img src="brand/camperminder-wordmark-dark.png#gh-dark-mode-only" width="420" alt="CamperMinder">
  <img src="brand/camperminder-wordmark-light.png#gh-light-mode-only" width="420" alt="CamperMinder">
</p>

Offene Technik für Wohnmobil und Wohnwagen. Jedes Gerät arbeitet **eigenständig**
— Handy zum Gerät, fertig. Wer Home Assistant nutzt, bindet es zusätzlich ein.
Beides läuft auf derselben Firmware; niemand muss sich vorher entscheiden.

## Produkte

| | Was es tut | Stand |
|---|---|---|
| **CamperMinder Level** | Nivellieren mit Keilen oder Hebesystem, Wohnmobil und Wohnwagen | in Entwicklung |
| **CamperMinder Gas** | Gasflaschen wiegen, Füllstand bestimmen | geplant |
| **CamperMinder Base** | vorbereitete Home-Assistant-Zentrale | geplant |

> **Testgerät bekommen?** Alles zu Einbau, Einrichtung, Home Assistant und MQTT
> steht in [docs/anleitung-prototyp.md](docs/anleitung-prototyp.md).

## Zwei Zweige, zwei Sensoren

| Zweig | Lagesensor | Wofür |
|---|---|---|
| **`mpu6050`** — dieser hier | MPU6050 | die Geräte der Erprobung. Bekommt weiterhin Verbesserungen an Bedienung und Funktionen. |
| `main` | LSM6DS3TR-C | die Weiterentwicklung. Der MPU-6050 ist abgekündigt, der Nachfolger ist in laufender Produktion. |

Die beiden Firmwares sind **nicht austauschbar** — jede spricht nur mit ihrem
Sensor. Deshalb haben sie getrennte Update-Kanäle: Ein Gerät dieser Linie
bekommt nie versehentlich die Firmware der anderen.
Einzelheiten in [docs/firmware_update.md](docs/firmware_update.md).

Releases dieser Linie tragen Tags mit `v3.…`, die der anderen `v4.…`.

## Aufbau des Repositorys

```
custom_components/camperminder/   Home-Assistant-Integration (alle Produkte)
  brand/                          Icon der Marke
  www/                            Lovelace-Karte
esphome/
  common/                         geteilte Firmware-Bausteine
  level/                          Firmware CamperMinder Level
brand/                            Wort- und Bildmarke
tools/                            Bau- und Release-Skripte
docs/                           Anleitungen
```

**Eine** Integration für alle Produkte, nicht eine je Gerät: ein HACS-Eintrag,
ein Update, eine Antwort im Support.

## Lizenz

| | |
|---|---|
| Code | private Nutzung erlaubt, kommerzielle Verwertung nicht — [LICENSE](LICENSE) |
| ESPHome-Anteile der Firmware | GPLv3 |
| Marke und Gestaltung | alle Rechte vorbehalten — [brand/LICENSE](brand/LICENSE) |

Einzelheiten: [LICENSES.md](LICENSES.md)

## Sicherheit

Die Geräteseite ist im lokalen Netz ohne Passwort erreichbar — bewusst, damit
auf dem Stellplatz niemand nach Zugangsdaten sucht.

Der API-Schlüssel verschlüsselt die Verbindung zu Home Assistant. Er ist kein
Zugangsschutz.
