# CamperMinder Level — Selbstbau

Für ein **fertig gekauftes Gerät** ist diese Seite nicht nötig — dort führt
[docs/inbetriebnahme.md](docs/inbetriebnahme.md) durch drei Schritte.

Hier geht es um den Selbstbau: Hardware, Firmware, Home Assistant.

---

## 0. Was du brauchst

| Was | Wofür |
|---|---|
| ESP32-C3-Board mit 0,42″-OLED und MPU6050 | die Hardware — [docs/verkabelung.md](docs/verkabelung.md) |
| ESPHome | Firmware bauen (Add-on in Home Assistant oder `pip install esphome`) |
| HACS | Integration und Karte, nur für den Betrieb **mit** Home Assistant |

Ohne Home Assistant brauchst du nur die ersten beiden Zeilen.

---

## 1. Firmware bauen und aufspielen

Repository holen, dann eine `secrets.yaml` neben die Vorlage legen:

```
esphome/level/secrets.yaml    ← aus secrets.yaml.example
esphome/level/camperminder-level.yaml
```

Drei Einträge genügen: `camperminder_api_key`, `camperminder_ota_password`,
`camperminder_fallback_password`. Den API-Schlüssel erzeugt ESPHome auf Wunsch
selbst; das Passwort des Gerätenetzes brauchst du gleich am Handy.

```bash
cd esphome/level
esphome run camperminder-level.yaml
```

- ✔ Der Build läuft durch. **Bricht er mit `Killed signal terminated program
  cc1plus` ab**, ging der Arbeitsspeicher aus — `compile_process_limit: 1`
  steht bereits in der Datei; dann hilft nur ein Neustart des Bauwerkzeugs
  oder ein größerer Rechner.
- ✔ Im Log erscheint der I²C-Scan mit **0x3C** (OLED) und **0x68** (MPU6050).
  Fehlt 0x68, stimmt die Verkabelung nicht — erst
  [docs/verkabelung.md](docs/verkabelung.md), nicht weitersuchen.
- ✔ Auf dem OLED wandert die Blase, wenn du das Board kippst.

---

## 2. Gerät bedienen — ohne Home Assistant

Die Firmware bringt **kein WLAN** mit. Das Gerät öffnet beim ersten
Einschalten sein eigenes Netz.

1. Am Handy WLAN **CamperMinder** wählen — **ohne Passwort**.
2. Im Browser **`192.168.4.1`** öffnen.
3. Über *Zum Home-Bildschirm hinzufügen* landet ein Symbol auf dem Handy.

> **Das eigene Netz ist ab Werk offen.** Kein Aufkleber, kein Passwort, keine
> Rückfrage — man verbindet sich und ist da. Es besteht ohnehin nur, solange
> kein WLAN eingetragen ist.
>
> Wer nicht möchte, dass jeder in Funkreichweite die Einstellungen erreicht,
> vergibt unter *Technik → Eigenes Netz* ein eigenes Passwort (mindestens acht
> Zeichen). Leer speichern öffnet es wieder.
>
> Vergessen? *Zurücksetzen* am Ende derselben Seite öffnet das Netz wieder.
> Ausgesperrt ist damit niemand.

Dort stellst du unter **Fahrzeug** Fahrzeugart, Radstand, Spurweite, Toleranz,
Präzisionsmodus und Keilstufe ein — die Werte liegen im Gerät, nicht im Handy.

- ✔ Zwei Wasserwaagen, Draufsicht mit wandernder Blase, Seiten- und
  Heckansicht, Klartextanweisung.
- ✔ Unter *Technik → Software* steht die Firmware-Version.

Wer hier stehenbleibt, ist fertig. Alles Weitere ist freiwillig.

---

## 3. Home Assistant anbinden

**3.1 WLAN eintragen** — auf der Geräteseite unter *Technik → WLAN*. Das Gerät
startet neu und verbindet sich; das Netz `CamperMinder` verschwindet dabei.

**3.2 Gerät übernehmen** — Home Assistant findet es von selbst und fragt nach
dem API-Schlüssel aus deiner `secrets.yaml`.

**3.3 Integration installieren** — HACS → Dreipunktmenü → *Benutzerdefinierte
Repositories*:

| Feld | Wert |
|---|---|
| Repository | `https://github.com/rcdev67/camperminder` |
| Typ | **Integration** |

Danach **CamperMinder** herunterladen und Home Assistant neu starten.

**3.4 Einrichten** — Einstellungen → Geräte & Dienste → *Integration
hinzufügen* → **CamperMinder**. Die Sensorfelder sind vorausgefüllt, sofern die
mitgelieferte Firmware läuft.

- ✔ Es entsteht ein Gerät **CamperMinder** mit „Phase", „Steht eben",
  „Schwelle längs/quer", „Korrektur längs/quer" und „Ansageziel".
- ✔ Fahrzeugmaße, Ausrichtart und Präzisionsmodus erscheinen **nicht**
  doppelt — die liest die Integration vom Gerät. Die Karte bedient dann den
  Schalter des Geräts.

**3.5 Karte aufs Dashboard** — Dashboard → Bearbeiten → *Karte hinzufügen* →
„CamperMinder" suchen.

Erscheint sie nicht in der Auswahl, prüf unter Einstellungen → Dashboards → ⋮
→ *Ressourcen*, ob `/camperminder_static/camperminder-card.js` eingetragen ist.
Die Integration legt den Eintrag beim Start selbst an.

---

## 4. Kalibrieren

Zum Schluss einmal im Fahrzeug — wie und warum steht in
[docs/kalibrierung.md](docs/kalibrierung.md).

---

## Anhang: Ohne Bauen aufs Board

Wer nicht selbst bauen will, nimmt die fertige Firmware aus dem
[jüngsten Release](https://github.com/rcdev67/camperminder/releases/latest):
`level-firmware.factory.bin` enthält Bootloader und Partitionstabelle und geht
auf ein leeres Board — mit [ESPHome Web](https://web.esphome.io) oder
`esptool` an Adresse `0x0`.

Nicht zu verwechseln mit `level-firmware.ota.bin`: Die ist für Updates über das
Netz gedacht. Auf einen leeren Chip geschrieben ergibt sie ein Gerät, das nicht
startet.

Die Einstellungen machst du danach am Handy wie in Schritt 2. Ein eigener
API-Schlüssel entsteht dabei nicht — die Werksfirmware bringt ihren mit.
