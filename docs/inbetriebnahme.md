# Inbetriebnahme — was der Kunde tut

Das Gerät kommt **ohne hinterlegtes WLAN**. Es öffnet beim ersten Einschalten
sein eigenes Netz und ist damit sofort benutzbar — ohne Router, ohne App, ohne
Konto.

## Schritt 1: Verbinden (immer nötig)

1. Gerät einschalten.
2. Am Handy in die WLAN-Liste, **CamperMinder** auswählen — **ohne Passwort**.
   Das Netz ist ab Werk offen; das Handy warnt deshalb, dass es ungesichert
   sei. Das ist so gewollt.
3. Im Browser **`192.168.4.1`** eingeben. Die Seite öffnet sich **nicht** von
   selbst — die Adresse muss man eintippen.
4. Über *Zum Home-Bildschirm hinzufügen* landet ein Symbol auf dem Handy,
   das die Seite im Vollbild öffnet — wie eine App.

> **Warum ohne Passwort:** Ein Passwort ab Werk wäre entweder für alle Geräte
> gleich — dann stünde es nach dem ersten ausgegebenen Gerät in jedem Forum —
> oder je Gerät verschieden, dann bräuchte es einen Aufkleber, der nach einem
> Zurücksetzen nicht mehr stimmt. Das Netz besteht ohnehin nur, solange kein
> WLAN eingetragen ist.
>
> Wer nicht möchte, dass jeder in Funkreichweite die Einstellungen erreicht,
> vergibt unter *Technik → Eigenes Netz* ein eigenes Passwort (mindestens acht
> Zeichen). Leer speichern öffnet es wieder, und *Zurücksetzen* am Ende
> derselben Seite hilft, wenn man es vergessen hat.

Mehr ist für den Betrieb nicht nötig. Wasserwaagen, Anweisungen und
Kalibrierung stehen sofort zur Verfügung.

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

## Software-Updates

| Lage | Weg |
|---|---|
| Gerät hat Internet | Reiter *Technik* → **Auf Updates prüfen und installieren** |
| Gerät im eigenen Netz | Reiter *Technik* → Firmwaredatei vom Handy aufspielen |

Die laufende Fassung steht im selben Reiter.

> **Für Testgeräte:** Diese Firmware ist die Ausführung mit MPU6050 und holt
> sich ihre Aktualisierungen aus einem eigenen Kanal. Sie bekommt damit auch
> künftig Verbesserungen, die aus dem Feedback der Erprobung entstehen — und
> zwar über dasselbe Gerät, ohne Kabel und ohne Rückgabe. Einzelheiten in
> [firmware_update.md](firmware_update.md).

> **Für die Werkstatt:** Aktualisierungen nur über OTA einspielen. Ein
> serielles Aufspielen mit Löschen des Flash nimmt dem Kunden sein
> eingerichtetes WLAN wieder weg — die gespeicherten Zugangsdaten liegen dort.

## Mit Home Assistant

Sobald das Gerät im heimischen WLAN hängt, findet Home Assistant es über
ESPHome von selbst. Die Integration **CamperMinder** kommt über HACS und bringt
die Bedienkarte mit; Firmware-Updates meldet Home Assistant dann automatisch.

Beide Betriebsarten laufen auf derselben Firmware. Wer klein anfängt, kann
jederzeit umsteigen — ohne neue Software, ohne neues Gerät.
