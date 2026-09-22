# Inbetriebnahme — was der Kunde tut

Das Gerät kommt **ohne hinterlegtes WLAN**. Es öffnet beim ersten Einschalten
sein eigenes Netz und ist damit sofort benutzbar — ohne Router, ohne App, ohne
Konto.

## Schritt 1: Verbinden (immer nötig)

1. Gerät einschalten.
2. Am Handy in die WLAN-Liste, **CamperMinder** auswählen — ohne Passwort.
3. Die Bedienseite öffnet sich meist von selbst. Falls nicht:
   **`192.168.4.1`** im Browser eingeben.
4. Über *Zum Home-Bildschirm hinzufügen* landet ein Symbol auf dem Handy,
   das die Seite im Vollbild öffnet — wie eine App.

Mehr ist für den Betrieb nicht nötig. Wasserwaagen, Anweisungen und
Kalibrierung stehen sofort zur Verfügung.

## Sprache

Die Bedienseite spricht **Deutsch und Englisch**. Ohne eigene Wahl richtet sie
sich nach der Spracheinstellung des Handys; umstellen unter Reiter **Technik**
→ **Sprache**.

Die Wahl gilt **je Handy**, nicht je Gerät — zwei Leute in einem Fahrzeug
lesen so jeder in seiner Sprache. Die Namen der Messwerte bleiben deutsch,
damit Home Assistant und MQTT bei einem Sprachwechsel weiter zusammenpassen.

## Schritt 2: Eigenes WLAN eintragen (freiwillig)

Nur nötig, wer automatische Software-Updates oder Home Assistant will. Ohne
diesen Schritt funktioniert alles Übrige unverändert.

Auf derselben Seite, Reiter **Technik** → Abschnitt **WLAN**: Netzwerkname und
Passwort eintragen, speichern. Das Gerät startet neu und wählt sich künftig
dort ein, sobald es in Reichweite ist — und öffnet unterwegs wieder sein
eigenes Netz.

Die Eingabe bleibt dauerhaft gespeichert.

> Danach ist das Gerät im Heimnetz unter seinem Namen erreichbar, nicht mehr
> unter `192.168.4.1`. Diese Adresse gilt wieder, sobald das Heimnetz außer
> Reichweite ist — also auf dem Stellplatz.

## Fernalarm einrichten (freiwillig)

Der Wächter meldet eine Lageänderung an alle, die das Gerät erreichen — im
eigenen Netz. Wer am Strand steht, während das Fahrzeug aufgebockt wird,
erfährt es damit erst bei der Rückkehr. Genau dafür gibt es den Fernalarm:
Das Gerät schickt die Meldung selbst an einen Push-Dienst, den **der Kunde**
betreibt oder benutzt.

**Kein Konto bei uns, keine Daten bei uns, keine Verfügbarkeitszusage.** Das
ist der Preis dafür, dass es nichts kostet und niemand mitliest.

Reiter **Technik** → Abschnitt **Fernalarm**: Adresse eintragen, speichern,
**Testmeldung senden**. Der letzte Schritt ist nicht freiwillig — ein
Alarmweg, den niemand ausprobiert hat, ist keiner.

### Was in das Feld gehört

Zwei Betriebsarten, unterschieden am Platzhalter `{text}`:

| | Adresse | Was das Gerät tut |
|---|---|---|
| **A** | ohne `{text}` | schickt die Meldung als Rumpf einer POST-Anfrage |
| **B** | mit `{text}` | setzt die Meldung kodiert in die Adresse ein und ruft sie ab |

### Dienste

| Dienst | Beispiel | Art | Kosten |
|---|---|---|---|
| **Telegram** | `https://api.telegram.org/bot<TOKEN>/sendMessage?chat_id=<Nr>&text={text}` | B | kostenlos |
| **Home Assistant Webhook** | `https://dein-ha/api/webhook/xyz` | A | kostenlos, wenn HA ohnehin läuft |
| **Node-RED, n8n, eigener Dienst** | Adresse des Ablaufs | A oder B | eigener Server |
| **ntfy selbst betrieben** | `https://ntfy.mein-server/mein-thema` | A | kostenlos, braucht einen Server |
| **ntfy.sh (gehostet)** | `https://ntfy.sh/mein-thema` | A | Grenzen im Gratisteil, Tarife darüber |
| **IFTTT Webhooks** | `https://maker.ifttt.com/trigger/<Ereignis>/with/key/<Schlüssel>?value1={text}` | B | Gratisteil begrenzt |

**Empfehlung für den Standardfall: Telegram.** Kein Server, kein Abo, kein
weiterer Dienst, den man kennenlernen muss — ein Bot bei @BotFather, und die
Meldung landet in einem Chat. Wer Home Assistant betreibt, nimmt besser den
Webhook: Dann entscheidet die Automatisierung, wohin die Meldung geht, und
kann auch Dienste bedienen, die das Gerät selbst nicht ansprechen kann.

**Pushover und Ähnliches gehen nicht direkt.** Sie verlangen eine POST-Anfrage
mit mehreren Formularfeldern; dafür passt keine der beiden Betriebsarten. Der
Weg dorthin führt über einen Webhook in Home Assistant oder Node-RED — der
nimmt die Meldung entgegen und schickt sie weiter, wohin er will.

### Telegram einrichten

Der empfohlene Weg für den Standardfall: kostenlos, kein Server, kein
weiterer Dienst.

**1. Bot anlegen.** In Telegram **@BotFather** anschreiben, `/newbot`,
Anzeigename eingeben (etwa `CamperMinder`), dann einen eindeutigen
Benutzernamen, der auf `bot` endet. BotFather antwortet mit dem **Token**:

```
8123456789:AAHxyz-abcDEF_ghiJKL1234567890mnop
```

**2. Den Chat starten.** Den eigenen Bot öffnen und **Start** drücken. Ein
Bot darf niemandem schreiben, der ihn nicht zuerst angeschrieben hat — ohne
diesen Schritt schlägt alles Weitere fehl.

**3. Chat-Nummer holen.** Im Browser aufrufen:

```
https://api.telegram.org/bot<TOKEN>/getUpdates
```

In der Antwort steht `"chat":{"id":123456789,...}` — diese Zahl ist die
Chat-Nummer. Kommt `{"ok":true,"result":[]}`, fehlt Schritt 2.

**4. Im Browser gegenprüfen**, bevor etwas ins Gerät getippt wird:

```
https://api.telegram.org/bot<TOKEN>/sendMessage?chat_id=<NUMMER>&text=Test
```

`{"ok":true,…}` und die Nachricht auf dem Handy heißt: passt. Bei `403`
fehlt Schritt 2, bei `401` stimmt der Token nicht.

**5. Ins Gerät eintragen** — dieselbe Adresse, statt `Test` der Platzhalter:

```
https://api.telegram.org/bot<TOKEN>/sendMessage?chat_id=<NUMMER>&text={text}
```

*Technik → Fernalarm*, eintragen, **speichern**, **Testmeldung senden**. Die
Adresse braucht rund 120 Zeichen, das Feld fasst 191.

### Wenn schon ein Bot vorhanden ist

Wer Telegram bereits mit Home Assistant oder einem anderen System benutzt,
braucht **keinen neuen Bot** — und muss nichts umstellen:

**Das Gerät schickt nur, es liest nie.** Es ruft ausschließlich `sendMessage`
auf. Mehrere Absender auf demselben Bot stören sich nicht. Ein bestehender
Webhook oder ein laufendes Abrufen durch Home Assistant bleibt unberührt.

- **Token:** steht in der Konfiguration des bestehenden Systems (bei Home
  Assistant unter `telegram_bot: api_key`). Sonst in Telegram bei
  **@BotFather** → `/mybots` → Bot auswählen → *API Token*.
- **Chat-Nummer:** ebenfalls aus der bestehenden Konfiguration (bei Home
  Assistant `allowed_chat_ids`).

> **`getUpdates` in diesem Fall nicht aufrufen.** Telegram lässt nur einen
> Abrufer gleichzeitig zu: Ist für den Bot ein Webhook gesetzt, antwortet
> `getUpdates` mit `409 Conflict`; ruft ein anderes System gerade ab, reisst
> man ihm die Meldung weg. Die Chat-Nummer kommt deshalb aus der vorhandenen
> Konfiguration — oder aus einem zweiten, eigenen Bot.

**Ein eigener Bot lohnt sich trotzdem**, wenn die Alarmmeldung anders klingen
oder in einem anderen Chat landen soll als der übrige Hausbetrieb. Beides
geht, es ist eine Frage des Geschmacks und nicht der Technik.

### Der Token ist ein Geheimnis

Wer sie hat, kann als dieser Bot schreiben. Sie steht im Gerät und ist auf
der Geräteseite lesbar — bei offenem eigenem Netz also für jeden in
Funkreichweite. **Wer den Fernalarm benutzt, vergibt unter *Technik → Eigenes
Netz* ein Passwort.** Und sie gehört auf kein Bildschirmfoto.

### Was der Fernalarm nicht kann

**Er braucht Internet am Fahrzeug.** Ohne eingetragenes WLAN mit Verbindung
nach draußen geht nichts hinaus — auf einem Stellplatz ohne Empfang bleibt
nur der Summer und die eingerastete Meldung im Gerät.

**Er weiß nicht, ob die Meldung ankommt.** Das Gerät erfährt vom Dienst nur,
ob dieser sie angenommen hat. Was danach passiert, liegt beim Dienst und beim
Handy des Kunden. Deshalb die Testmeldung.

**Eine Meldung je Alarm.** Der Alarm rastet im Gerät ein und bleibt stehen,
bis er quittiert wird — wiederholt verschickt wird er nicht.

## Software-Updates

| Lage | Weg |
|---|---|
| Gerät hat Internet | Reiter *Technik* → **Auf Updates prüfen und installieren** |
| Gerät im eigenen Netz | Reiter *Technik* → Firmwaredatei vom Handy aufspielen |

Die laufende Fassung steht im selben Reiter.

> **Für die Werkstatt:** Aktualisierungen nur über OTA einspielen. Ein
> serielles Aufspielen mit Löschen des Flash nimmt dem Kunden sein
> eingerichtetes WLAN wieder weg — die gespeicherten Zugangsdaten liegen dort.

## Mit Home Assistant

Sobald das Gerät im heimischen WLAN hängt, findet Home Assistant es über
ESPHome von selbst. Die Integration **CamperMinder** kommt über HACS und bringt
die Bedienkarte mit; Firmware-Updates meldet Home Assistant dann automatisch.

Beide Betriebsarten laufen auf derselben Firmware. Wer klein anfängt, kann
jederzeit umsteigen — ohne neue Software, ohne neues Gerät.
