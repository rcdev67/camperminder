# CamperMinder Level — Anleitung

Diese Anleitung gehört zu jedem Gerät, auch zu den ersten Prototypen. Sie
bringt dich in einer Minute zur Wasserwaage auf dem Handy: **ohne App, ohne
Konto, ohne Koppeln.** Alles, was danach kommt, ist freiwillig.

## In einer Minute zur Wasserwaage

![Aufkleber mit zwei QR-Codes. Code 1: Handy verbinden, Netz CamperMinder, 192.168.4.1. Code 2: Im Heim-WLAN, camperminder-level.local](bilder/aufkleber-qr.svg)

1. **Strom anschließen**, auf einem von zwei Wegen:
   - **USB-C**, 5 V: an eine USB-Steckdose im Fahrzeug, ein USB-Netzteil oder
     eine Powerbank.
   - **Schraubklemme**, 7 bis 36 V: **VIN** an Plus, **GND** an Minus der
     Aufbaubatterie, also 12 oder 24 V direkt aus dem Bordnetz. Falsch herum
     angeklemmt passiert nichts, es geht nur nichts.

   Beide dürfen auch gleichzeitig stecken, dann versorgt die stärkere Quelle.
   Die **grüne** Leuchte zeigt: Strom ist da.
2. **Handy verbinden.** In den WLAN-Einstellungen des Handys **CamperMinder**
   wählen. Das ist das eigene Netz des Geräts, nicht dein WLAN zu Hause; ab
   Werk hat es kein Passwort. Meldet das Handy, dieses Netz habe kein
   Internet: **verbunden bleiben.** Das Gerät braucht kein Internet.
3. **Code 1 scannen** oder im Browser **`192.168.4.1`** eingeben. Die
   Wasserwaage ist sofort da.

Mehr ist für den Betrieb nicht nötig. **Code 2** brauchst du erst, wenn das
Gerät in deinem WLAN zu Hause ist, siehe *Ins eigene WLAN*.

Die Codes hier in der Anleitung funktionieren genauso wie die auf dem Gerät.
Das iPhone liest sie mit der Kamera-App, Android mit der Kamera oder mit
Google Lens.

> **Ein Symbol wie eine App.** Auf dem iPhone in Safari *Teilen → Zum
> Home-Bildschirm*, auf Android in Chrome *⋮ → Zum Startbildschirm
> hinzufügen*. Das Symbol öffnet die Seite im Vollbild. Wo ein
> Bluetooth-Gerät eine App braucht, steckt hier die Seite im Gerät selbst,
> und jedes Update bringt sie mit.

## Einbauen

- **Der Pfeil zeigt nach vorn.** Er steht auf der Gehäusewand und zeigt in
  Fahrtrichtung, USB-Buchse und Klemme liegen hinten. Um 90 Grad verdreht
  eingebaut verwechselt das Gerät längs und quer.
- **Deckel oben** ist der Normalfall. Wer das Gehäuse unter ein Regalbrett
  klebt, stellt unter *Anzeige → Gerät → Einbaulage* auf **Deckel unten**.
- **Fest und flach.** Auf eine ebene, feste Fläche schrauben oder kleben. Ein
  Gerät, das wackelt, misst das Wackeln.

## Einmal einrichten

1. *Anzeige → Fahrzeug*: Fahrzeugart, Radstand und Spurweite. Aus den Maßen
   rechnet das Gerät, wie viele Zentimeter jede Ecke hoch muss.
2. Das Fahrzeug einmal wirklich waagerecht stellen, mit einer Wasserwaage
   längs und quer geprüft, und auf *Anzeige* unter den Ansichten **Neigung
   kalibrieren** tippen. Ab Werk ist der Sensor bereits kalibriert; dieser
   Schritt gleicht aus, wie das Gerät in deinem Fahrzeug sitzt. Mehr dazu in
   [kalibrierung.md](kalibrierung.md).

## Was die Leuchten sagen

| Leuchte | Bedeutung |
|---|---|
| **grün**, an | Strom ist da |
| **rot**, lang an, lang aus | Das eigene Netz ist offen: mit **CamperMinder** verbinden, dann Code 1 oder `192.168.4.1` |
| **rot**, ein kurzes Blinken alle drei Sekunden | Das Gerät ist in deinem WLAN |
| **rot**, gleichmäßig im Halbsekundentakt | Der Sensor antwortet nicht. Bitte melden. |
| **rot**, hektisches Doppelblinken, dazu drei Töne | Wächteralarm: Das Fahrzeug hat seine Lage verändert |
| **rot** aus | Die Leuchte ist mit dem Schalter *Status-LED* abgeschaltet. Ein Alarm blinkt trotzdem. |

## Sprache

Die Bedienseite spricht **Deutsch und Englisch**. Ohne eigene Wahl richtet sie
sich nach der Spracheinstellung des Handys; umstellen unter Reiter **Technik**
→ **Sprache**.

Die Wahl gilt **je Handy**, nicht je Gerät — zwei Leute in einem Fahrzeug
lesen so jeder in seiner Sprache. Die Namen der Messwerte bleiben deutsch,
damit Home Assistant und MQTT bei einem Sprachwechsel weiter zusammenpassen.

## Ins eigene WLAN (freiwillig)

Nur nötig für automatische Updates und Home Assistant. Ohne diesen Schritt
funktioniert alles andere unverändert, unterwegs sowieso.

1. Zu Hause, mit dem Handy im Netz **CamperMinder**: *Technik → WLAN*, Name
   und Passwort deines WLANs eintragen, **Speichern und verbinden**.
2. **Auf der Seite bleiben.** Das Gerät startet neu und meldet sich in deinem
   WLAN an. Das Netz CamperMinder verschwindet, und dein Handy kehrt von
   selbst in dein WLAN zurück. Die Seite sucht das Gerät dann dort und zeigt
   nach meist unter einer Minute: **Gefunden: Das Gerät ist in deinem WLAN
   unter 192.168.178.45 erreichbar** (die Zahl ist bei dir eine andere).
3. **Im Heimnetz öffnen** tippen und dort das Symbol neu auf den
   Home-Bildschirm legen.

Damit hast du zwei Symbole, und beide bleiben richtig. Zu Hause gilt die neue
Adresse. Unterwegs, wenn dein WLAN außer Reichweite ist, öffnet das Gerät nach
etwa 20 Sekunden wieder sein eigenes Netz, und es gilt `192.168.4.1`. Die
Zugangsdaten bleiben gespeichert.

**Code 2 auf dem Aufkleber** öffnet das Gerät zu Hause über seinen Namen,
`camperminder-level.local`, ganz gleich, welche Adresse dein Router ihm gibt.
Auf dem iPhone klappt das, auf Android nicht auf jedem Gerät. Öffnet Code 2
dort nichts, nimm das Symbol, das du dir in Schritt 3 angelegt hast.

**Kommt das Netz CamperMinder nach einer halben Minute wieder,** hat die
Anmeldung nicht geklappt, meist wegen eines Tippfehlers im Passwort. Die Seite
sagt das dann auch. Einfach wieder verbinden, berichtigen, speichern.

### Wenn die Seite das Gerät nicht findet

- **Im Router nachsehen.** In der Geräteliste deines Routers steht das Gerät
  unter seinem Namen, meist **camperminder-level**, bei der Fritzbox unter
  *Heimnetz → Netzwerk*. Die Adresse daneben im Browser aufrufen. Den genauen
  Namen nennt die Seite unter *Technik* als *Name im Netz*.
- **Code 2 scannen** oder `camperminder-level.local` im Browser eingeben. Auf
  dem iPhone klappt das fast immer, auf Android nicht auf jedem Gerät.
- **Beim nächsten Mal nachlesen.** Das Gerät merkt sich seine Adresse. Wenn du
  das nächste Mal im Netz CamperMinder bist, steht sie oben unter *Technik →
  WLAN*.

Die Suche findet nichts in Gäste-WLANs, die ihre Geräte voneinander
abschotten, und in ungewöhnlich eingerichteten Heimnetzen. Dann bleibt der
Blick in den Router.

## Fernalarm einrichten (freiwillig)

Der Wächter meldet eine Lageänderung an alle, die das Gerät erreichen — im
eigenen Netz. Wer am Strand steht, während das Fahrzeug aufgebockt wird,
erfährt es damit erst bei der Rückkehr. Genau dafür gibt es den Fernalarm:
Das Gerät schickt die Meldung selbst an einen Push-Dienst, den **du**
betreibst oder benutzt.

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
ob dieser sie angenommen hat. Was danach passiert, liegt beim Dienst und bei
deinem Handy. Deshalb die Testmeldung.

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

## Wenn etwas nicht klappt

| Was | Was hilft |
|---|---|
| Kein Netz **CamperMinder** in der Liste | Leuchtet die grüne Leuchte? Sonst fehlt Strom. Blinkt die rote kurz alle drei Sekunden, ist das Gerät in deinem WLAN, und das eigene Netz ist deshalb aus: siehe *Ins eigene WLAN*. Nach dem Einschalten bis zu 20 Sekunden warten. |
| Das Handy springt aus dem Netz CamperMinder zurück | Es sucht Internet. *Verbunden bleiben* bestätigen; hilft das nicht, kurz die mobilen Daten ausschalten. |
| `192.168.4.1` lädt nicht | Vollständig eingeben: `http://192.168.4.1`. Manche Browser machen sonst eine Suche daraus. Das Handy muss im Netz CamperMinder sein. |
| Längs und quer sind vertauscht | Das Gehäuse ist verdreht eingebaut. Der Pfeil muss nach vorn zeigen. |
| Die Blase springt bei der kleinsten Bewegung von Rand zu Rand | Kopfüber eingebaut, aber die *Einbaulage* steht auf *Deckel oben*. |
| Nach dem Eintragen des WLANs nicht mehr erreichbar | *Wenn die Seite das Gerät nicht findet*, oben. |
| Alles auf Anfang | *Technik → Zurücksetzen*. Löscht WLAN, Kalibrierung im Fahrzeug und Fahrzeugmaße; die Werkskalibrierung bleibt. |

## Für die Testerinnen und Tester der ersten Geräte

Du hast eines der ersten Geräte. Am meisten hilft uns, was **nicht** glatt
lief, und zwar so genau, wie du es noch weißt:

- **Dein Handy** mit Betriebssystem, etwa „iPhone 13, iOS 19" oder „Pixel 7,
  Android 15".
- **Die erste Minute**: Wie lange hat es vom Anschließen bis zur ersten
  Anzeige gedauert, und wo hast du gestockt?
- **Das eigene WLAN**: Hat die Seite das Gerät nach dem Eintragen gefunden?
  Welcher Router war es, etwa Fritzbox, Speedport oder ein Handy-Hotspot?
- **Jeder Satz auf der Seite, den du zweimal lesen musstest.**

Ein Bildschirmfoto sagt oft mehr als eine Beschreibung. Nur keines, auf dem
ein Telegram-Token zu sehen ist, siehe *Fernalarm*.
