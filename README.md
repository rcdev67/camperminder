<p align="center">
  <img src="brand/camperminder-wordmark-dark.png#gh-dark-mode-only" width="420" alt="CamperMinder">
  <img src="brand/camperminder-wordmark-light.png#gh-light-mode-only" width="420" alt="CamperMinder">
</p>

Technik für Wohnmobil und Wohnwagen. Das Gerät arbeitet **eigenständig**
— Handy zum Gerät, fertig. Wer Home Assistant nutzt, bindet es zusätzlich ein.
Beides läuft auf derselben Firmware; niemand muss sich vorher entscheiden.

## Produkt

| | Was es tut | Stand |
|---|---|---|
| **CamperMinder Level** | Nivellieren mit Keilen oder Hebesystem, Wohnmobil und Wohnwagen | in Entwicklung |

## Aufbau des Repositorys

```
custom_components/camperminder/   Home-Assistant-Integration
  brand/                          Icon der Marke
  www/                            Lovelace-Karte
esphome/
  level/                          Firmware CamperMinder Level
brand/                            Wort- und Bildmarke
tools/                            Bau- und Release-Skripte
docs/                           Anleitungen
```

Eine Integration, ein HACS-Eintrag, ein Update, eine Antwort im Support.

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
