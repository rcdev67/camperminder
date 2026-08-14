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
