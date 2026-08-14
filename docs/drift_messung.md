# Nullpunktdrift messen

Diese Seite beschreibt drei Diagnosewerte, die das Gerät mitführt, und wie man
sie auswertet. Für den normalen Betrieb sind sie ohne Bedeutung — sie sind der
Kategorie *Diagnose* zugeordnet und in der Übersicht standardmäßig eingeklappt.

## Worum es geht

Ein Grad Neigung entspricht rund 17 Milli-g Beschleunigung. Was einen
Neigungsmesser begrenzt, ist deshalb nicht sein Rauschen — das lässt sich
wegmitteln —, sondern das Wandern seines Nullpunkts mit der Temperatur.

Der Innenraum eines Wohnmobils schwankt zwischen Winternacht und Sommermittag
um 40 bis 50 Grad. Wandert der Nullpunkt dabei um mehr als ein Zehntelgrad,
stimmt die im Frühjahr vorgenommene Kalibrierung im August nicht mehr, und das
Fahrzeug steht schief, obwohl die Anzeige „eben" meldet.

Wie groß der Drift beim verbauten Sensor tatsächlich ist, lässt sich nicht aus
Datenblättern ablesen — dort stehen Grenzwerte, keine Messwerte. Deshalb misst
das Gerät es selbst.

## Die drei Werte

| Wert | Bedeutung |
|---|---|
| **Diagnose Pitch Mittel** | Längsneigung, geglättet und je Minute gemittelt, drei Nachkommastellen |
| **Diagnose Roll Mittel** | dasselbe quer |
| **Diagnose Betrag** | Betrag des Beschleunigungsvektors, vier Nachkommastellen |
| **MPU6050 Temperatur** | Temperatur im Sensor selbst, nicht der Raumluft |

Die beiden Neigungswerte gibt es zusätzlich zu den Live-Anzeigen, weil jene auf
eine Nachkommastelle gerundet sind. Ein Drift von wenigen Hundertstelgrad wäre
darin unsichtbar.

**Diagnose Betrag** ist der aussagekräftigste Wert der Reihe. Die
Erdbeschleunigung beträgt immer 9,81 m/s², ganz gleich wie das Fahrzeug steht —
Neigung verteilt sie nur anders auf die drei Achsen. Jede Abweichung, die mit
der Temperatur mitwandert, stammt deshalb zwingend vom Sensor. Reifendruck,
Federung, Beladung oder ein Umparken können diesen Wert nicht verfälschen.

## Auswerten

Die Werte tragen `state_class: measurement`. Home Assistant führt dafür
dauerhaft Langzeitstatistiken mit Stundenmittel, auch wenn der kurzfristige
Verlauf längst gelöscht ist. Für eine Messreihe über Wochen ist nichts weiter
einzurichten.

1. **Entwicklerwerkzeuge → Statistik** öffnen und die vier Werte auswählen.
2. Einen Zeitraum wählen, in dem das Fahrzeug **stand**. Der Binärsensor
   *In Bewegung* zeigt, wann das der Fall war. Am aussagekräftigsten ist eine
   Standzeit von mehreren Tagen mit deutlichem Tag-Nacht-Wechsel.
3. Neigung gegen Temperatur auftragen. Die Steigung der Punktwolke ist der
   Drift in Grad je Kelvin.

## Was die Ergebnisse bedeuten

Als Maßstab dient die Toleranz des Fahrzeugs. Bei 3350 mm Radstand entsprechen
5 cm Höhenunterschied etwa 0,85 Grad. Ein Messfehler von 0,2 Grad verbraucht
davon bereits ein Viertel.

| Drift über 40 Kelvin | Bewertung |
|---|---|
| unter 0,05 Grad | ohne Bedeutung, Sensor bleibt |
| 0,05 bis 0,15 Grad | grenzwertig; eine Temperaturkorrektur in der Firmware wäre möglich |
| über 0,15 Grad | der Sensor sollte gewechselt werden |

## Was die Messung verfälschen kann

Die beiden Neigungswerte messen **Sensor und Fahrzeug zusammen**. Ein
abgestelltes Fahrzeug bewegt sich nämlich durchaus:

- Der Reifendruck steigt mit der Temperatur, das hebt den Wagen leicht an.
  Betrifft alle Räder ähnlich und wirkt sich deshalb kaum auf die Neigung aus.
- Sonne auf einer Seite erwärmt eine Fahrzeugseite stärker als die andere.
- Weicher Untergrund gibt über Tage nach, besonders nach Regen.

Deshalb der Blick auf **Diagnose Betrag**: Wandert dieser Wert mit der
Temperatur, liegt es am Sensor. Bleibt er fest, während die Neigung wandert,
war es das Fahrzeug.

Ganz sauber trennen lässt sich beides nur auf einem Tisch in einem Raum mit
wechselnder Temperatur — dort steht das Gerät nachweislich still. Für eine
Vorentscheidung genügen die Daten aus dem Fahrzeug.
