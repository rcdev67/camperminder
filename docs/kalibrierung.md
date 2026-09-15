# Kalibrierung

Vier Dinge, in dieser Reihenfolge: **Einbaulage** (wie herum klebt das
Gehäuse?), **Achszuordnung** (welche Achse ist längs?), **Vorzeichen** (welche
Richtung ist positiv?), dann der **Nullpunkt**.

Einbaulage und Nullpunkt werden im Betrieb gesetzt. Achszuordnung und
Vorzeichen hängen an der Bestückung des Geräts, stehen damit einmalig fest und
erfordern einen neuen Flash.

---

## 1. Einbaulage angeben

Die Einstellung **„Einbaulage"** steht an zwei Orten und meint dieselbe: in Home
Assistant als Helfer, und auf der Geräteseite unter *Einstellungen → Gerät*.
Zwei Stellungen:

| Stellung | Bedeutung |
|----------|-----------|
| **Deckel oben** | Gehäuse steht auf seiner Unterseite — der Normalfall |
| **Deckel unten** | Gehäuse klebt unter einem Regalbrett oder einer Decke |

Der Pfeil auf der Seitenwand zeigt in beiden Fällen nach vorn. Die Umstellung
wirkt sofort, ein Flash ist nicht nötig.

> **Warum das nicht optional ist:** Kopfüber montiert liefert die Roll-Rechnung
> in Ruhelage nicht 0, sondern 180 Grad. Wer das übersieht, merkt zunächst
> nichts — die Kalibrierung speichert die 180 als Nullpunkt weg und die Anzeige
> sieht danach korrekt aus. Sie steht dann aber genau auf dem Punkt, an dem der
> Winkel zwischen +180 und −180 umspringt, und kippt bei minimaler Bewegung
> zwischen zwei Extremwerten. Das sieht nach einem defekten Sensor aus und ist
> keiner.

**Nach dem Umstellen neu kalibrieren** (Schritt 4) — der alte Nullpunkt gilt
für die alte Lage. Das Gerät schreibt beim Umschalten einen entsprechenden
Hinweis ins Log.

## 2. Achszuordnung prüfen (bei anderem Einbau)

Der Sensor misst auf drei Achsen. Welche davon die Längsneigung trägt, hängt
davon ab, **wie herum das Board eingebaut ist** — das lässt sich nicht durch ein
Vorzeichen korrigieren.

> **Für die Platine Rev B sind Zuordnung und Vorzeichen aus dem Layout
> abgeleitet** (Herleitung bei den Substitutions in `hardware.yaml`) und am
> ersten bestückten Muster **einmal zu bestätigen** — dieser und der nächste
> Schritt. Danach gelten sie für jede Platine dieser Revision; ein Kunde muss
> hier nichts tun. Wer die Prüfung überspringt, riskiert eine Anzeige, die
> plausibel aussieht und Längs mit Quer verwechselt.

Test: Fahrzeug (oder Board) **vorne anheben**.

- Ändert sich **„Neigung Pitch"** → Zuordnung stimmt.
- Ändert sich stattdessen **„Neigung Roll"** → längs und quer sind vertauscht.
  In `esphome/level/camperminder-level.yaml` die beiden Werte tauschen und neu
  flashen:

```yaml
substitutions:
  axis_pitch: "y"   # vorher "x"
  axis_roll: "x"    # vorher "y"
```

Erlaubt sind nur `x` und `y` — `z` ist immer die Schwerkraftachse.

> Diese Zuordnung wird an **drei** Stellen benutzt (Pitch-Sensor, Roll-Sensor,
> Kalibrier-Button). Deshalb steht sie in den Substitutions und nicht im Code:
> würde eine der drei Stellen abweichen, liefen Anzeige und gespeicherter Offset
> auseinander — ein Fehler, der erst auf dem Stellplatz auffällt. Der Selbsttest
> in Schritt 4 schlägt genau dann an.

## 3. Vorzeichen prüfen

Die Konvention ist:

- **pitch > 0 = Front hoch**
- **roll > 0 = rechte Seite hoch**

Prüfen:

- **Vorne anheben** → Pitch muss **positiv** werden, die Blase Richtung „VORNE"
  wandern.
- **Rechte Seite anheben** → Roll muss **positiv** werden, Blase nach rechts.

Stimmt eine Richtung nicht, das jeweilige Vorzeichen umstellen und neu flashen:

```yaml
substitutions:
  pitch_sign: "-1"   # falls vorne/hinten vertauscht
  roll_sign: "-1"    # falls links/rechts vertauscht
```

Nach jeder Änderung an Einbaulage, Zuordnung oder Vorzeichen **erneut
kalibrieren**.

## 4. Nullpunkt setzen — mit Selbsttest

1. Fahrzeug so exakt wie möglich waagerecht stellen (Wasserwaage längs **und**
   quer). Alternativ eine bekannt ebene Fläche nutzen.
   → **Das ist in der Praxis die größte Fehlerquelle, nicht der Sensor.**
   Alles, was hier schiefsteht, steckt dauerhaft in allen späteren cm-Angaben.
2. Während des Drückens **nicht** im Fahrzeug bewegen.
3. Button **„Auf eben kalibrieren"** drücken.
4. **5 Sekunden warten.** Home Assistant prüft automatisch, ob beide Achsen
   danach wirklich bei ~0 stehen:
   - ✔ `Zuletzt kalibriert` zeigt **heute, HH:MM Uhr**, keine Meldung → fertig.
   - ✘ Meldung **„Kalibrierung hat nicht gegriffen"** → entweder wurde während
     des Drückens bewegt (einfach wiederholen), oder die Achszuordnung aus
     Schritt 2 passt nicht.
5. Danach noch ~1 Minute Strom lassen — die Offsets werden erst nach dem
   `flash_write_interval` dauerhaft gespeichert und überleben dann Neustarts.

---

## 5. Fahrzeugmaße eintragen

In den HA-Helfern:

- **Radstand** = Abstand Vorder-/Hinterachse (mm)
- **Spurweite** = Abstand linkes/rechtes Rad (mm)

Diese Maße bestimmen **zweierlei**:

1. die Anhebehöhe in der Anweisung — `Höhe = Maß × tan(Winkel)`;
2. **ab wann „eben" gilt.** Im Realitätsmodus wird die Toleranz in Zentimetern
   angegeben und über diese Maße in eine Gradzahl je Achse umgerechnet. Bei
   5 cm Toleranz, 3500 mm Radstand und 1800 mm Spurweite ergibt das 0,82° längs
   und 1,59° quer.

Grob falsche Maße verschieben also auch den Punkt, an dem das System „steht
eben, Stopp" sagt. Auf ±5 cm genau reicht völlig, geschätzte Fantasiewerte
nicht.

> Wer stattdessen mit einer festen Gradtoleranz arbeiten will, schaltet den
> **Präzisionsmodus** ein; dann gilt `Toleranz genau` für beide Achsen und die
> Fahrzeugmaße wirken nur noch auf die cm-Angabe. Beides — Schalter und
> Gradtoleranz — liegt im Gerät und ist auch ohne Home Assistant erreichbar.

## Die Toleranz ist auch der Maßstab der Anzeige

Nicht nur die Grenze zwischen „eben" und „nicht eben", sondern der Maßstab
selbst: **Toleranzgrenze = Rand der grünen Zone.** Steht das Fahrzeug innerhalb
der Toleranz, steht die Blase in der Mitte, die Wasserwaagen stehen mittig und
die Seitenansichten waagerecht — in jeder Ansicht und auf beiden Achsen.

Das ist der Grund, warum die Anzeige mit 5 cm Toleranz gröber aussieht als mit
1 cm. Sie zeigt dieselbe Messung, nur an dem Maßstab, den du vorgegeben hast:
Wer 5 cm erlaubt, will bei 4 cm nicht sehen, dass 4 cm fehlen — er will sehen,
dass er fertig ist.

Zwei Dinge halten die Anzeige zusätzlich ruhig, wenn das Fahrzeug längere Zeit
steht:

- **Die Firmware glättet adaptiv.** Kleine Änderungen gelten als Rauschen und
  wirken nur träge, große als echte Lageänderung und wirken sofort. Beim
  Auffahren auf den Keil bleibt die Anzeige deshalb live, im Stand steht sie
  still. Verloren geht dabei nichts — der geglättete Wert läuft jeder echten
  Änderung vollständig nach, nur langsamer.
- **Einmal „eben" bleibt „eben"**, bis die Neigung deutlich über die Toleranz
  hinausgeht. Ohne das entscheidet sich an einem einzigen Punkt, ob das
  Fahrzeug steht — und genau auf diesem Punkt rauscht jeder Messwert.

### Beides ist einstellbar

Wie ruhig eine Anzeige sein *soll*, ist Geschmack. Der eine will, dass sie steht
wie angenagelt, der andere will jede Regung sehen. Deshalb sind es Regler und
keine einkompilierten Zahlen — auf der Geräteseite unter **Anzeige**, in Home
Assistant beim Gerät unter *Konfiguration*:

| Was du beobachtest | Regler | Richtung |
|---|---|---|
| zappelt im Stand noch | **Anzeigeruhe** | höher |
| hinkt beim Auffahren hinterher | **Anzeigeruhe** | niedriger |
| folgt beim Rangieren zu ruckelig | **Anzeigeruhe** | höher |
| springt an der Toleranzgrenze hin und her | **Haltebereich** | höher |

**Anzeigeruhe** geht von 0 bis 10, Vorgabe 5. Sie ändert nichts an der Messung
und nichts an der Toleranz — nur die Geduld. Ein Regler und nicht vier, weil die
vier Beiwerte des Filters dieselbe Eigenschaft aus vier Richtungen beschreiben;
einzeln verstellbar könnte man sie gegeneinander stellen und bekäme eine
Anzeige, die weder ruhig ist noch reagiert.

Was du bei welcher Stellung siehst:

| Ruhe | Zeitkonstante | Restrauschen | woran man es merkt |
|---|---|---|---|
| 0 | 0,1 s | ~0,5 cm | die Zahl lebt, jede Regung sofort |
| 2 | 1 s | ~0,1 cm | leichtes Wandern der letzten Stelle |
| **5** | **6 s** | **~0,04 cm** | **steht im Stand still** |
| 10 | 24 s | ~0,02 cm | steht ebenso still, folgt aber träger |

**Wichtig für den Vergleich:** Oberhalb von etwa 3 wird die Anzeige nicht mehr
sichtbar *ruhiger* — das Rauschen liegt dann schon unter der angezeigten
Stelle. Was sich weiter ändert, ist die **Reaktionszeit**. Der Unterschied
zwischen 5 und 10 zeigt sich deshalb nicht im Stillstand, sondern wenn du dich
ans Fahrzeug lehnst: Bei 10 dauert es spürbar länger, bis die Anzeige folgt.
Zum Ausprobieren also nach unten drehen, nicht nach oben.

**Haltebereich** in Prozent, Vorgabe 125: Wie weit die Neigung über die
Toleranz hinausgehen darf, bevor „eben" zurückgenommen wird. 100 % heißt
sofort — dann springt die Anzeige an der Grenze hin und her, genau das soll die
Hysterese verhindern.

Beide wirken sofort, ohne Neustart. Zum Ausprobieren im Fahrzeug ist das der
Sinn der Sache.

Wem das zu grob ist, der schaltet den **Präzisionsmodus** ein: Dort steht die
Blase auch innerhalb der Toleranz an ihrer echten Stelle, die Winkel stehen mit
zwei Nachkommastellen da, und statt der Zentimeter gilt `Toleranz genau` in
Grad — dieselbe Zahl für beide Achsen.

Der Schalter sitzt auf der Geräteseite unter *Fahrzeug* und auf der Karte unten
bei den Bedienelementen. Beide legen denselben Schalter um: Er liegt im Gerät,
damit er auch ohne Home Assistant erreichbar ist. Die Integration legt deshalb
keinen zweiten daneben — genau wie bei Radstand, Spurweite und Toleranz.

Auch der Binärsensor **Camper steht gerade** im Gerät folgt jetzt dieser
Rechnung. Vorher galt dort eine feste Gradzahl, und er meldete „nicht gerade",
während die Geräteseite daneben „EBEN – STOP" zeigte. Wer ihn in einer
Automation benutzt, bekommt jetzt genau das, was auf dem Handy steht.

## Wie lange hält eine Kalibrierung?

Solange das Gerät nicht bewegt wird, gilt sie unbegrenzt — der Nullpunkt liegt
im Flash und übersteht Stromausfall und Firmware-Update.

Eine Einschränkung gibt es dennoch: Der Nullpunkt eines Beschleunigungssensors
wandert mit der Temperatur, und ein Wohnmobil erlebt zwischen Winternacht und
Sommermittag 40 bis 50 Grad Unterschied. Wie stark sich das beim verbauten
Sensor auswirkt, misst das Gerät selbst mit — siehe
[drift_messung.md](drift_messung.md). Wer den Verdacht hat, dass die Anzeige
über die Jahreszeit wandert, findet dort die Werte, um es nachzuprüfen statt zu
vermuten.
