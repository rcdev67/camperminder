/*
 * CamperMinder - Oberfläche auf dem Gerät selbst
 * ---------------------------------------------------------------------------
 * Wird über web_server.js_include in die Firmware eingebettet und als /0.js
 * ausgeliefert. Braucht weder Home Assistant noch Internet noch eine App: das
 * Handy verbindet sich mit dem Gerät und öffnet dessen Adresse.
 *
 * Die Rechnung ist absichtlich dieselbe wie in der Home-Assistant-Integration
 * (coordinator.py): Schwellen über den Arkustangens der Fahrzeugmaße,
 * Hubhöhe je Rad gegen das höchste Rad. Wer eine Formel ändert, muss beide
 * Stellen ändern - sonst sagen Gerät und Karte Verschiedenes, und das
 * merkt man erst im Fahrzeug.
 *
 * Vorzeichen wie in der Firmware: pitch > 0 = Front höher (Heck muss hoch),
 * roll > 0 = rechte Seite höher (linke Seite muss hoch).
 */

(function () {
  "use strict";

  var COLORS = { ok: "#37d67a", warn: "#ffb020", bad: "#ff5c5c", off: "#6b7280" };
  var CHIP = { "#37d67a": "#37d67a", "#ffb020": "#ffb020", "#ff5c5c": "#ff7a7a", "#6b7280": "#b0b7c3" };

  /* --- Sprache ---------------------------------------------------------------
   *
   * Zwei Sprachen, ein Woerterbuch: TEXTE.de und TEXTE.en. Jeder sichtbare
   * Satz steht dort und wird mit t("schluessel") geholt; Platzhalter in
   * geschweiften Klammern werden beim Holen ersetzt.
   *
   * WARUM DIE SEITE UND NICHT DIE FIRMWARE UEBERSETZT: Namen von Entitaeten
   * stehen in ESPHome beim Bauen fest und liessen sich im Betrieb nicht
   * umstellen. Die Seite dagegen baut jeden Satz selbst - sie bekommt vom
   * Geraet Zahlen und Zustaende (Sensor "Statuswerte", siehe hardware.yaml)
   * und formuliert daraus. Deutsch bleibt im Geraet nur, was Home Assistant
   * und MQTT lesen.
   *
   * Die Sprache kommt aus der Einstellung des Handys und laesst sich unter
   * Technik umstellen. Die Wahl liegt im Browser (localStorage), nicht im
   * Geraet: Sie gehoert zum Betrachter, nicht zum Fahrzeug - zwei Leute mit
   * verschiedenen Sprachen schauen sonst gegeneinander.
   */
  var TEXTE = {
    de: {
      achse_laengs: "LÄNGS",
      achse_quer: "QUER",
      acht_zeichen: "Mindestens acht Zeichen – so verlangt es WPA2. Oder leer lassen, dann bleibt das Netz offen.",
      alarm_quittieren: "Alarm quittieren",
      ansicht_heck: "HECK · quer",
      ansicht_seite: "SEITE · längs",
      bereich_auswahl: "Auswahl",
      bereich_einstellwerte: "Einstellwerte",
      bereich_informationen: "Informationen",
      bereich_messwerte: "Messwerte",
      bereich_schalter: "Schalter",
      bereich_software: "Software",
      bereich_tasten: "Tasten",
      bereich_texteingaben: "Texteingaben",
      bereich_zustaende: "Zustände",
      bewegung_jetzt: "gerade jetzt",
      bewegung_nie: "seit dem Einschalten nichts",
      bewegung_vor: "vor {dauer}",
      datei_aufspielen: "Datei aufspielen",
      datei_aufspielen_hinweis: "Oder Firmwaredatei vom Handy aufspielen:",
      eben_stop: "✅ EBEN – STOP",
      eingabe_nicht_angenommen: "Das Gerät hat die Eingabe nicht angenommen.",
      erst_datei: "Erst eine Datei auswählen.",
      gegen_hinten: "Front",
      gegen_hinten_links: "Front rechts",
      gegen_hinten_rechts: "Front links",
      gegen_links: "rechte Seite",
      gegen_rechts: "linke Seite",
      gegen_vorn: "Heck",
      gegen_vorn_links: "Heck rechts",
      gegen_vorn_rechts: "Heck links",
      hilfe_ablassen: "Der Tropfen in der Skizze sitzt am Ablass – dorthin soll das Wasser laufen. Das <b>+</b> markiert die Seite, die dafür angehoben wird. Links und rechts gelten <b>in Fahrtrichtung</b>.<br><br>{satz}",
      hilfe_alarmton: "Beim Wächteralarm tönt der Summer alle zehn Sekunden, fünf Minuten lang. Aus, wenn du scharf schaltest, während noch Leute im Fahrzeug sind.",
      hilfe_anzeigeruhe: "Klein: Die Anzeige folgt jeder Regung, zappelt im Stand aber mehr. Groß: Sie steht im Stand still und reagiert dafür etwas später. Die Genauigkeit ändert sich nicht, nur die Geduld.",
      hilfe_bewegung: "Erschütterung – jemand steigt ein, Wind, der Nachbar rangiert. Kein Alarm.",
      hilfe_driftwarnung: "Ändert sich die Temperatur so weit gegenüber der Kalibrierung, rät das Gerät zum Nachkalibrieren – Wärme verschiebt den Nullpunkt. 20 Kelvin sind ein guter Wert, kleiner meldet sich öfter.",
      hilfe_einbaulage: "„Deckel unten“ heißt: unter ein Regalbrett oder eine Decke geklebt, der Pfeil zeigt weiterhin nach vorn. Nach dem Umstellen einmal neu kalibrieren.",
      kopf_fernalarm: "Fernalarm",
      hilfe_fernalarm: "Der Wächter meldet sich sonst nur in dem Netz, in dem auch das Fahrzeug hängt – wer am Strand steht, während das Fahrzeug aufgebockt wird, erfährt es erst bei der Rückkehr. Trag hier die Adresse deines eigenen Push-Dienstes ein, dann schickt das Gerät die Meldung selbst dorthin. Kein Konto bei uns, keine Daten bei uns.<br><br><b>Telegram</b> – kostenlos und der einfachste Weg. Bot bei @BotFather anlegen, dann:<br><code>https://api.telegram.org/bot&lt;Kennung&gt;/sendMessage?chat_id=&lt;Nr&gt;&amp;text={text}</code><br><br><b>Home Assistant</b> – wenn du es ohnehin betreibst. Der Webhook löst eine Automatisierung aus, und die meldet, wohin du willst:<br><code>https://dein-ha/api/webhook/xyz</code><br><br><b>Eigener Dienst</b> – Node-RED, n8n, ntfy auf dem eigenen Server: einfach die Adresse deines Ablaufs.<br><br><b>Wichtig:</b> <code>{text}</code> bleibt wörtlich so stehen – dort setzt das Gerät seine Meldung selbst ein. Schreib dort nicht deinen eigenen Text hinein. Ohne <code>{text}</code> schickt das Gerät die Meldung als Text an die Adresse.<br><br>Dienste, die ein bestimmtes Formularformat verlangen (Pushover zum Beispiel), gehen nicht direkt – dafür ist der Umweg über einen Webhook der Weg. Leer lassen schaltet den Fernalarm ab.",
      platzhalter_fernalarm: "https://api.telegram.org/bot…/sendMessage?chat_id=…&text={text}",
      fernalarm_speichern: "Fernalarm speichern",
      fernalarm_testen: "Testmeldung senden",
      fernalarm_gespeichert: "Gespeichert. Schick jetzt eine Testmeldung – ein Alarmweg, den du nie ausprobiert hast, ist keiner.",
      fernalarm_aus: "Fernalarm abgeschaltet – es wird nichts verschickt.",
      fernalarm_test_laeuft: "Testmeldung wird verschickt …",
      fernalarm_test_gesendet: "Verschickt. Kommt sie nicht an, stimmt die Adresse nicht – das Gerät erfährt vom Dienst nur, ob er sie angenommen hat.",
      hilfe_frost: "Das Gerät misst seine eigene Temperatur, nicht die der Raumluft. Für eine Frostwarnung reicht das, sobald du den Abgleich unter „Gerät“ einmal gegen ein Thermometer gesetzt hast.",
      hilfe_haltebereich: "Wie weit die Neigung über die Toleranz hinausgehen darf, bevor die Anzeige „eben“ zurücknimmt. Höher setzen, wenn sie an der Grenze hin und her springt.",
      hilfe_karenzzeit: "So lange nach dem Scharfschalten meldet der Wächter nichts – Zeit zum Aussteigen.",
      hilfe_kuehlschrank: "Kurz schief beim Rangieren schadet nicht, eine Nacht schief schon. Das Gerät warnt nach einem Drittel dieser Zeit und wird nach der vollen Zeit dringend.",
      hilfe_lage: "Weicht die Neigung um mehr als {grenze}° von der Ruhelage ab, wurde das Fahrzeug bewegt.",
      hilfe_lageaenderung: "Ab welcher Abweichung von der Ruhelage der Wächter anschlägt. Bei 3500 mm Radstand ist ein Grad rund 6 cm: Wind und Einsteigen bleiben darunter, Anheben und Abschleppen liegen darüber.",
      hilfe_masse: "Aus diesen Maßen rechnet das Gerät Grad in Zentimeter um. <b>Radstand</b>: Mitte Vorderachse bis Mitte Hinterachse. <b>Spurweite</b>: Mitte linkes bis Mitte rechtes Rad. <b>Toleranz</b>: ab wie viel Höhenunterschied es dich stört – 5 cm ist ein guter Anfang. <b>Keilstufe</b>: Höhengewinn einer Stufe deiner Auffahrkeile; bei 0 wird in Zentimetern angesagt.",
      hilfe_masse_wagen: "Aus diesen Maßen rechnet das Gerät Grad in Zentimeter um. <b>Achse → Stützrad</b>: von der Achsmitte bis zum Stützrad – meist deutlich mehr als ein Radstand, also nachmessen. <b>Spurweite</b>: Mitte linkes bis Mitte rechtes Rad. <b>Toleranz</b>: ab wie viel Höhenunterschied es dich stört – 5 cm ist ein guter Anfang. <b>Keilstufe</b>: Höhengewinn einer Stufe deiner Auffahrkeile.",
      hilfe_mqtt: "Meldet Neigung, Hubhöhe je Ecke und die Anweisung an einen MQTT-Broker – für Victron Cerbo GX, ioBroker, openHAB, Node-RED oder was du sonst einsetzt. Für Home Assistant ist es nicht nötig. Themen unter <b>camperminder/level/…</b>",
      hilfe_netz_geschuetzt: "Das Netz „CamperMinder“ ist <b>mit Passwort</b> geschützt. Leer lassen und speichern öffnet es wieder.",
      hilfe_netz_offen: "Das Netz „CamperMinder“ ist derzeit <b>ohne Passwort</b> erreichbar. Es besteht nur, solange oben kein WLAN eingetragen ist. Wer es abschließen möchte, vergibt hier eines – mindestens acht Zeichen.",
      hilfe_praezision: "Aus: Die Toleranz gilt in Zentimetern, und was innerhalb liegt, zeigt die Anzeige als eben – dort ist nichts mehr zu tun. Ein: feste Gradtoleranz für beide Achsen, die Blase bleibt an ihrer echten Stelle, Winkel mit zwei Nachkommastellen. Für Werkstatt und Messplatz.",
      hilfe_schlafen: "Links und rechts gelten <b>in Fahrtrichtung</b>. Die Skizze zeigt das Fahrzeug von oben, vorn ist oben: die Fläche ist das Bett, das farbige Ende das Kopfende, und das <b>+</b> markiert die Seite, die höher kommt.<br><br>{satz}",
      hilfe_schraeglage: "Ein Absorberkühlschrank arbeitet über etwa 3° nicht mehr zuverlässig, und das merkt niemand, bis das Essen warm ist. Diese Warnung ist unabhängig von deiner Toleranz beim Ausrichten.",
      hilfe_sprache: "Vorausgewählt ist die Sprache deines Handys. Die Wahl gilt nur für dieses Handy – wer mit einem anderen Telefon auf dasselbe Gerät schaut, kann eine andere Sprache sehen. Die Namen in Home Assistant bleiben deutsch.",
      hilfe_status_led: "Die Leuchte zeigt, dass das Gerät läuft, und in welchem Netz es steckt: lang an und lang aus heißt eigenes Netz – dann gilt 192.168.4.1 –, ein kurzer Herzschlag alle drei Sekunden heißt Heimnetz. Aus, wenn sie nachts stört. <b>Ein Alarm blinkt trotzdem.</b>",
      hilfe_temp_abgleich: "Einmal gegen ein Thermometer im Fahrzeug ablesen und die Differenz hier eintragen. Danach taugt der Wert für die Frostwarnung – ein Thermometer wird daraus nicht.",
      hilfe_update: "Holt die neue Fassung von GitHub – dafür braucht das Gerät Internet. Im eigenen Netz auf dem Stellplatz gibt es keins; dann hilft der Weg darunter.",
      hilfe_waechter_aus: "Beim Einschalten merkt sich das Gerät die jetzige Lage. Ab dann meldet es, wenn das Fahrzeug sie verlässt. Eine Erschütterung – jemand steigt ein, Wind – löst nichts aus; die steht unter „Bewegung“.",
      hilfe_waechter_scharf: "Scharf gilt die Lage vom Einschalten. Wird das Fahrzeug angehoben, abgeschleppt oder aufgebockt, rastet der Alarm ein und bleibt stehen, bis du ihn quittierst – auch wenn längst wieder Ruhe ist.",
      hilfe_wlan: "Nur nötig für automatische Updates und Home Assistant. Ohne WLAN läuft alles Übrige weiter.",
      hilfe_womit: "<b>Auffahrkeile</b>: Das Gerät nennt eine Ecke nach der anderen – beim Auffahren kippt das Fahrzeug mit, deshalb lohnt kein zweiter Schritt im Voraus. <b>Hydraulik oder Luftkissen</b>: alle Stützen auf einmal, weil sie sich unabhängig voneinander ausfahren lassen.",
      hilfe_ziele: "Hier richtest du die beiden Profile ein. Gewählt werden sie oben auf der Anzeige unter „Zielprofil“.",
      hilfe_zuruecksetzen: "Löscht WLAN-Zugangsdaten, Kalibrierung, Fahrzeugmaße und ein selbst vergebenes Netz-Passwort. Das Gerät startet danach neu und öffnet wieder sein eigenes, offenes Netz.",
      hinweis_hebesystem: "Alle Stützen auf einmal, höchste zuerst. Nicht genannte Räder bleiben stehen.",
      hinweis_keile_einzeln: "Eine Anweisung nach der anderen – nach dem Auffahren neu messen.",
      hinweis_neu_messen: "Danach neu messen.",
      hinweis_wagen_reihenfolge: "Erst das Rad auf den Keil, dann das Stützrad – das Auffahren kippt den Wagen längs mit.",
      hoch_front: "FRONT hoch",
      hoch_heck: "HECK hoch",
      hoch_links: "LINKE Seite hoch",
      hoch_rechts: "RECHTE Seite hoch",
      in_bewegung: "in Bewegung",
      kal_gut: "{wann} bei {temp} °C",
      kal_nie: "noch nie kalibriert – einmal im Stand nachholen",
      kal_ohne_uhr: "Zeitpunkt unbekannt",
      kal_ohne_werte: "kalibriert, aber ohne Vergleichswerte – einmal neu kalibrieren, dann überwacht das Gerät den Drift",
      kal_pruefen: "{wann} bei {temp} °C – jetzt {jetzt} °C, bitte prüfen",
      kalibriere_laeuft: "Kalibriere …",
      kalibrieren: "Neigung kalibrieren",
      keilstufe: "Keilstufe {n}",
      kein_wert: "⚠️ Kein Sensorwert",
      keine_bestaetigung: "Das Gerät bestätigt die Eingabe nicht. Nichts wurde gespeichert.",
      keine_verbindung: "Keine Verbindung zum Gerät.",
      keine_werte_warnung: "Das Nivelliergerät liefert gerade keine Werte – Anzeige nicht verwenden.",
      keine_wlan_felder: "Das Gerät meldet keine WLAN-Eingabefelder. Auf diesem Gerät läuft eine Firmware ohne diese Funktion.",
      kennt_einstellung_nicht: "Das Gerät kennt diese Einstellung nicht. Läuft die passende Firmware?",
      kennt_mqtt_nicht: "Das Gerät kennt MQTT nicht. Läuft die passende Firmware?",
      kennt_praezision_nicht: "Das Gerät kennt keinen Präzisionsmodus. Läuft die passende Firmware?",
      kennt_wert_nicht: "Das Gerät kennt keine Einstellung „{was}“. Läuft die passende Firmware?",
      kennzeichen_bewegung: "Bewegung",
      kennzeichen_lage: "Lage",
      kennzeichen_neigung: "Neigung",
      kopf_ablassen: "Ablassen",
      kopf_anzeige: "Anzeige",
      kopf_ausrichten: "Ausrichten",
      kopf_eigenes_netz: "Eigenes Netz",
      kopf_fahrzeug: "Fahrzeug",
      kopf_geraet: "Gerät",
      kopf_schlafen: "Schlafen",
      kopf_software: "Software",
      kopf_sprache: "Sprache",
      kopf_technik: "Technik",
      kopf_waechter: "Wächter",
      kopf_warnungen: "Warnungen",
      kopf_wlan: "WLAN",
      kopf_ziele: "Ziele",
      kopf_zielprofil: "Zielprofil",
      kopf_zuruecksetzen: "Zurücksetzen",
      kuehl_ok: "Unter {grenze}° – der Absorberkühlschrank arbeitet zuverlässig.",
      kuehl_stufe_1: "{grad}° schief seit {dauer} – noch unkritisch.",
      kuehl_stufe_2: "{grad}° schief seit {dauer} – die Kühlleistung fällt ab.",
      kuehl_stufe_3: "{grad}° schief seit {dauer} – bitte ausrichten.",
      kurz_kuehlschrank: "Kühlschrank!",
      kurz_ok: "ok",
      kurz_schief: "schief",
      label_ablassneigung: "Neigung zum Ablass (cm)",
      label_ablasspunkt: "Wo sitzt der Ablass?",
      label_achse_stuetzrad: "Achse → Stützrad (mm)",
      label_auffahrton: "Auffahrton",
      hilfe_auffahrton: "Beim Auffahren auf die Keile sitzt du am Lenkrad und kannst nicht aufs Handy schauen. Eingeschaltet tönt der Summer, und zwar umso schneller, je näher du am Ziel bist – ein langer Ton heißt: steht. Danach schaltet er sich selbst wieder aus, damit er auf der Weiterfahrt still bleibt.",
      label_alarmton: "Alarmton",
      label_anzeigeruhe: "Anzeigeruhe (0–10)",
      label_driftwarnung: "Driftwarnung ab (K)",
      label_einbaulage: "Einbaulage",
      label_fahrzeugart: "Fahrzeugart",
      label_frost: "Frostwarnung unter (°C)",
      label_haltebereich: "Haltebereich (%)",
      label_karenzzeit: "Karenzzeit Wächter (s)",
      label_keilstufe: "Keilstufe (cm, 0 = aus)",
      label_kopfende: "Kopfende anheben (cm)",
      label_kuehlschrank: "Kühlschrank kritisch nach (min)",
      label_lageaenderung: "Lageänderung ab (°)",
      label_praezision: "Präzisionsmodus",
      label_radstand: "Radstand (mm)",
      label_schlafrichtung: "Wo liegt der Kopf?",
      label_schraeglage: "Schräglage ab (°)",
      label_sprache: "Sprache",
      label_spurweite: "Spurweite (mm)",
      label_status_led: "Status-LED",
      label_temp_abgleich: "Temperatur Abgleich (K)",
      label_toleranz_cm: "Toleranz (cm)",
      label_toleranz_grad: "Toleranz genau (°)",
      label_womit: "Womit ausrichten",
      lage_unveraendert: "unverändert",
      lage_veraendert: "verändert!",
      laufende_fassung: "Laufende Fassung: {version}",
      letzte_bewegung: "Letzte Bewegung am Fahrzeug: {wann}",
      mqtt_aus: "Gespeichert. MQTT ist wieder aus.",
      mqtt_gespeichert: "Gespeichert. Das Gerät startet neu und meldet sich beim Broker.\n\nDanach steht der Zustand hier oben – bei einem Tippfehler „keine Verbindung“.",
      mqtt_speichern: "MQTT speichern",
      mqtt_zustand_aus: "MQTT ist aus – keine Adresse eingetragen.",
      mqtt_zustand_getrennt: "Keine Verbindung zu {broker} – Adresse, Port, Benutzer und Passwort prüfen.",
      mqtt_zustand_verbunden: "Verbunden mit {broker}.",
      name_nicht_angenommen: "Das Gerät hat den Netzwerknamen nicht angenommen ({pfad}/set).",
      netz_jetzt_geschuetzt: "Gespeichert. Das Gerät startet neu.\n\nDanach fragt dein Handy nach dem neuen Passwort. Merke es dir gut: Ohne WLAN und ohne dieses Passwort kommst du nur noch über ein USB-Kabel an das Gerät – oder über Zurücksetzen weiter unten, das es wieder öffnet.",
      netz_passwort_speichern: "Netz-Passwort speichern",
      netz_wieder_offen: "Gespeichert. Das Gerät startet neu – das Netz ist danach wieder ohne Passwort erreichbar.",
      netzname_fehlt: "Netzwerkname fehlt.",
      nicht_uebernommen: "Das Gerät hat die Einstellung nicht übernommen (Status {status} bei {pfad}). Sie steht nur auf diesem Handy.",
      noch_keine_daten: "Noch keine Daten empfangen.",
      noch_keine_messwerte: "Noch keine Messwerte empfangen.",
      notfalls_dashboard: "Notfalls über das ESPHome-Dashboard einrichten.",
      opt_ablass_hinten: "hinten",
      opt_ablass_hinten_links: "hinten links",
      opt_ablass_hinten_rechts: "hinten rechts",
      opt_ablass_links: "links",
      opt_ablass_rechts: "rechts",
      opt_ablass_vorn: "vorn",
      opt_ablass_vorn_links: "vorn links",
      opt_ablass_vorn_rechts: "vorn rechts",
      opt_fahrzeug_wohnmobil: "Wohnmobil",
      opt_fahrzeug_wohnwagen: "Wohnwagen",
      opt_lage_deckel_oben: "Deckel oben",
      opt_lage_deckel_unten: "Deckel unten",
      opt_methode_auffahrkeile: "Auffahrkeile",
      opt_methode_hydraulik_oder_luftkissen: "Hydraulik oder Luftkissen",
      opt_profil_ablassen: "Ablassen",
      opt_profil_ausrichten: "Ausrichten",
      opt_profil_schlafen: "Schlafen",
      opt_schlaf_kopf_hinten: "hinten – Füße zur Front",
      opt_schlaf_kopf_links: "links – quer im Fahrzeug",
      opt_schlaf_kopf_rechts: "rechts – quer im Fahrzeug",
      opt_schlaf_kopf_vorn: "vorn – Füße zum Heck",
      passwort_nicht_angenommen: "Das Gerät hat das Passwort nicht angenommen ({pfad}/set).",
      platzhalter_benutzer: "Benutzer (optional)",
      platzhalter_broker: "Broker, z. B. 192.168.1.10 (leer = aus)",
      platzhalter_mqtt_passwort: "Passwort (leer = unverändert)",
      platzhalter_netz_passwort: "Neues Passwort (leer = offen)",
      platzhalter_netzname: "Netzwerkname",
      platzhalter_passwort: "Passwort",
      platzhalter_port: "Port",
      profil_ablassen_erklaerung: "Das Fahrzeug neigt sich zum Ablasspunkt, damit Boiler und Tank wirklich leer laufen. Wer eben steht, behält einen Rest drin – und der friert im Winter.",
      profil_ausrichten_erklaerung: "Eben ausrichten, wie gewohnt.",
      profil_schlafen_erklaerung: "Das Kopfende liegt etwas höher – das schläft sich für viele besser. Die Anzeige rechnet ab jetzt gegen dieses Ziel: „EBEN“ heißt dann „steht, wie du es wolltest“. Eingerichtet wird es weiter unten in den Einstellungen, Abschnitt „Ziele“.",
      rad_hinten: "Hinten",
      rad_hinten_links: "Hinten links",
      rad_hinten_rechts: "Hinten rechts",
      rad_links: "Linke Seite",
      rad_rechts: "Rechte Seite",
      rad_stuetzrad: "Stützrad",
      rad_vorne: "Vorne",
      rad_vorne_links: "Vorne links",
      rad_vorne_rechts: "Vorne rechts",
      reiter_anzeige: "Anzeige",
      reiter_technik: "Technik",
      richtung_hoch: "hoch",
      richtung_runter: "runter",
      satz_ablassen: "Ziel im Profil „Ablassen“: {gegen} {cm} cm höher, damit es zum Ablass {punkt} läuft.",
      satz_ablassen_null: "Neigung steht auf 0 – im Profil „Ablassen“ richtet das Gerät dann eben aus.",
      satz_schlafen: "Ziel im Profil „Schlafen“: {seite} {cm} cm höher.",
      satz_schlafen_null: "Höhe steht auf 0 – im Profil „Schlafen“ richtet das Gerät dann eben aus.",
      scharf_schalten: "Scharf schalten",
      seite_front: "Front",
      seite_heck: "Heck",
      seite_links: "linke Seite",
      seite_rechts: "rechte Seite",
      steht_ruhig: "steht ruhig",
      uebertrage: "Übertrage …",
      uebertragen_fehler: "Fehlgeschlagen (Status {status}). Notfalls über das ESPHome-Dashboard aufspielen.",
      uebertragen_neustart: "Übertragen. Das Gerät startet neu.",
      unbekannt: "unbekannt",
      unscharf_schalten: "Unscharf schalten",
      update_frage: "Neue Firmware von GitHub laden und installieren?\n\nDas Gerät startet dabei neu. Nicht während der Fahrt.",
      update_laeuft: "Lade und installiere …",
      update_neustart: "Läuft – das Gerät startet gleich neu.",
      update_pruefen: "Auf Updates prüfen und installieren",
      vorne: "VORNE",
      vorne_kurz: "VORN",
      wache_alarm_um: "ALARM – Lage verändert am {zeit}",
      wache_alarm_unbekannt: "ALARM – Zeitpunkt unbekannt",
      wache_alarm_vor: "ALARM – Lage verändert vor {dauer}",
      wache_aus: "aus",
      wache_karenz: "scharf in {s} s",
      wache_scharf: "scharf seit {dauer}",
      wagen_rad_hinten_links: "Linkes Rad",
      wagen_rad_hinten_rechts: "Rechtes Rad",
      wagen_rad_stuetzrad: "Stützrad",
      warnung_kalibrierung: "Kalibrierung: {satz}",
      seite_wird_geholt: "Seite wird neu geladen …",
      warnung_seite_alt: "Diese Seite ist älter als das Gerät (Seite {seite}, Gerät {geraet}). Zum Neuladen hier tippen.",
      warnung_montage: "Der Sensor liefert unglaubwürdige Werte – sitzt das Gehäuse noch fest? Solange das so ist, stimmt die Anzeige nicht.",
      warte_auf_geraet: "Warte auf das Gerät …",
      warte_bestaetigung: "Warte auf Bestätigung des Geräts …",
      werte_im_geraet: "Diese Werte stehen im Gerät. Jedes Handy sieht dieselben.",
      winkel_zeile: "Längs {laengs}° · Quer {quer}°",
      wlan_gespeichert: "Gespeichert. Das Gerät startet jetzt neu und verbindet sich mit „{netz}“.\n\nAchte auf die WLAN-Liste deines Handys: Verschwindet das Netz CamperMinder innerhalb einer Minute, hat es geklappt. Bleibt es bestehen, stimmt Name oder Passwort nicht – dann einfach erneut verbinden und korrigieren.",
      wlan_speichern: "Speichern und verbinden",
      zentimeter: "{n} cm",
      ziel: "Ziel",
      ziel_front_hoeher: "Front {cm} cm höher",
      ziel_heck_hoeher: "Heck {cm} cm höher",
      ziel_ist: "Ziel: {was}",
      ziel_ist_eben: "Ziel: <b>eben</b> – die Höhe dieses Profils steht auf 0.",
      ziel_links_hoeher: "linke Seite {cm} cm höher",
      ziel_rechts_hoeher: "rechte Seite {cm} cm höher",
      zurueckgesetzt: "Zurückgesetzt. Das Gerät startet neu – verbinde dich anschließend wieder mit dem Netz CamperMinder.",
      zuruecksetzen: "Auf Werkseinstellungen zurücksetzen",
      zuruecksetzen_frage: "Wirklich zurücksetzen?\n\nWLAN, Kalibrierung und Fahrzeugmaße gehen verloren. Das Gerät muss danach neu eingerichtet und neu kalibriert werden.\n\nEin selbst vergebenes Netz-Passwort wird ebenfalls gelöscht – das eigene Netz ist danach wieder offen.",
      zuruecksetzen_laeuft: "Setze zurück …"
    },
    en: {
      achse_laengs: "ALONG",
      achse_quer: "ACROSS",
      acht_zeichen: "At least eight characters – that is what WPA2 requires. Or leave it empty and the network stays open.",
      alarm_quittieren: "Acknowledge alarm",
      ansicht_heck: "REAR · across",
      ansicht_seite: "SIDE · along",
      bereich_auswahl: "Selections",
      bereich_einstellwerte: "Settings",
      bereich_informationen: "Information",
      bereich_messwerte: "Readings",
      bereich_schalter: "Switches",
      bereich_software: "Software",
      bereich_tasten: "Buttons",
      bereich_texteingaben: "Text fields",
      bereich_zustaende: "States",
      bewegung_jetzt: "right now",
      bewegung_nie: "nothing since power-on",
      bewegung_vor: "{dauer} ago",
      datei_aufspielen: "Upload file",
      datei_aufspielen_hinweis: "Or upload a firmware file from your phone:",
      eben_stop: "✅ LEVEL – STOP",
      eingabe_nicht_angenommen: "The device did not accept the entry.",
      erst_datei: "Pick a file first.",
      gegen_hinten: "the front",
      gegen_hinten_links: "the front right",
      gegen_hinten_rechts: "the front left",
      gegen_links: "the right side",
      gegen_rechts: "the left side",
      gegen_vorn: "the rear",
      gegen_vorn_links: "the rear right",
      gegen_vorn_rechts: "the rear left",
      hilfe_ablassen: "The drop in the sketch marks the drain – that is where the water should run. The <b>+</b> marks the side that gets raised for it. Left and right are <b>seen facing forwards</b>.<br><br>{satz}",
      hilfe_alarmton: "On a guard alarm the buzzer sounds every ten seconds for five minutes. Switch it off if you arm the guard while people are still in the vehicle.",
      hilfe_anzeigeruhe: "Low: the display follows every movement, but jitters more when parked. High: it stands still when parked and reacts a little later. Accuracy does not change, only patience.",
      hilfe_bewegung: "A shake – someone getting in, wind, the neighbour manoeuvring. Not an alarm.",
      hilfe_driftwarnung: "If the temperature moves this far from the one at calibration, the device suggests calibrating again – heat shifts the zero point. 20 kelvin is a good value, lower means more reminders.",
      hilfe_einbaulage: "“Lid facing down” means: stuck under a shelf or a ceiling, with the arrow still pointing forwards. Calibrate once after changing it.",
      kopf_fernalarm: "Remote alert",
      hilfe_fernalarm: "Otherwise the guard only reaches you inside the same network as the vehicle – if you are on the beach while it gets jacked up, you find out when you come back. Enter the address of your own push service here and the device sends the message there itself. No account with us, no data with us.<br><br><b>Telegram</b> – free and the simplest route. Create a bot with @BotFather, then:<br><code>https://api.telegram.org/bot&lt;token&gt;/sendMessage?chat_id=&lt;id&gt;&amp;text={text}</code><br><br><b>Home Assistant</b> – if you run it anyway. The webhook triggers an automation and that notifies wherever you like:<br><code>https://your-ha/api/webhook/xyz</code><br><br><b>Your own service</b> – Node-RED, n8n, a self-hosted ntfy: just the address of your flow.<br><br><b>Important:</b> leave <code>{text}</code> exactly as it is – that is where the device inserts its own message. Do not put your own text there. Without <code>{text}</code> the device sends the message as the body.<br><br>Services that require a particular form format (Pushover, for example) do not work directly – a webhook is the way for those. Leave it empty to switch the remote alert off.",
      platzhalter_fernalarm: "https://api.telegram.org/bot…/sendMessage?chat_id=…&text={text}",
      fernalarm_speichern: "Save remote alert",
      fernalarm_testen: "Send a test message",
      fernalarm_gespeichert: "Saved. Send a test message now – an alert path you have never tried is not an alert path.",
      fernalarm_aus: "Remote alert switched off – nothing will be sent.",
      fernalarm_test_laeuft: "Sending a test message …",
      fernalarm_test_gesendet: "Sent. If it does not arrive, the address is wrong – the device only learns whether the service accepted it.",
      hilfe_frost: "The device measures its own temperature, not the air in the room. That is good enough for a frost warning once you have set the offset under “Device” against a thermometer.",
      hilfe_haltebereich: "How far the tilt may go beyond the tolerance before the display takes back “level”. Set it higher if the display flips back and forth at the limit.",
      hilfe_karenzzeit: "For this long after arming, the guard stays quiet – time to get out.",
      hilfe_kuehlschrank: "A moment off level while manoeuvring does no harm, a whole night does. The device warns after a third of this time and becomes urgent after the full time.",
      hilfe_lage: "If the tilt differs from the resting position by more than {grenze}°, the vehicle has been moved.",
      hilfe_lageaenderung: "How far the vehicle may deviate from its resting position before the guard reacts. On a 3500 mm wheelbase one degree is about 6 cm: wind and people getting in stay below that, lifting and towing are above it.",
      hilfe_masse: "The device turns degrees into centimetres using these dimensions. <b>Wheelbase</b>: centre of the front axle to centre of the rear axle. <b>Track width</b>: centre of the left wheel to centre of the right wheel. <b>Tolerance</b>: how much height difference still feels fine to you – 5 cm is a good start. <b>Ramp step</b>: height gained per step of your levelling ramps; at 0 the distance is given in centimetres.",
      hilfe_masse_wagen: "The device turns degrees into centimetres using these dimensions. <b>Axle → jockey wheel</b>: from the centre of the axle to the jockey wheel – usually much more than a wheelbase, so measure it. <b>Track width</b>: centre of the left wheel to centre of the right wheel. <b>Tolerance</b>: how much height difference still feels fine to you – 5 cm is a good start. <b>Ramp step</b>: height gained per step of your levelling ramps.",
      hilfe_mqtt: "Publishes tilt, lift height per corner and the instruction to an MQTT broker – for Victron Cerbo GX, ioBroker, openHAB, Node-RED or whatever you use. Not needed for Home Assistant. Topics under <b>camperminder/level/…</b>",
      hilfe_netz_geschuetzt: "The “CamperMinder” network is <b>protected with a password</b>. Leaving the field empty and saving opens it again.",
      hilfe_netz_offen: "The “CamperMinder” network is currently open <b>without a password</b>. It only exists while no Wi-Fi is entered above. If you want to lock it, set a password here – at least eight characters.",
      hilfe_praezision: "Off: the tolerance counts in centimetres, and anything inside it shows as level – nothing left to do there. On: a fixed tolerance in degrees for both axes, the bubble stays where it really is, angles with two decimals. For the workshop and the test bench.",
      hilfe_schlafen: "Left and right are <b>seen facing forwards</b>. The sketch shows the vehicle from above with the front at the top: the panel is the bed, the coloured end is the head end, and the <b>+</b> marks the side that will be raised.<br><br>{satz}",
      hilfe_schraeglage: "An absorber fridge stops working reliably above roughly 3°, and nobody notices until the food is warm. This warning is independent of your levelling tolerance.",
      hilfe_sprache: "Preselected is the language of your phone. The choice applies to this phone only – someone looking at the same device with another phone may see a different language. The entity names in Home Assistant stay German.",
      hilfe_status_led: "The light shows that the device is running and which network it is on: long on and long off means its own network – then 192.168.4.1 applies – while a short heartbeat every three seconds means your home network. Switch it off if it disturbs you at night. <b>An alarm still flashes.</b>",
      hilfe_temp_abgleich: "Compare the reading with a thermometer in the vehicle once and enter the difference here. After that the value is good enough for the frost warning – it does not turn into a thermometer.",
      hilfe_update: "Fetches the new version from GitHub – the device needs internet for that. On its own network at the pitch there is none; then use the way below.",
      hilfe_waechter_aus: "When you arm it, the device remembers the current position. From then on it reports when the vehicle leaves it. A shake – someone getting in, wind – does not trigger anything; that is shown under “Motion”.",
      hilfe_waechter_scharf: "While armed, the position at switch-on counts. If the vehicle is lifted, towed or jacked up, the alarm latches and stays on until you acknowledge it – even if all has been quiet again for hours.",
      hilfe_wlan: "Only needed for automatic updates and Home Assistant. Everything else works without Wi-Fi.",
      hilfe_womit: "<b>Levelling ramps</b>: the device names one corner at a time – driving up tilts the vehicle as well, so a second step planned ahead would be wrong anyway. <b>Hydraulics or air suspension</b>: all jacks at once, because they extend independently of each other.",
      hilfe_ziele: "Set the two profiles up here. You pick them at the top of the display page under “Target profile”.",
      hilfe_zuruecksetzen: "Deletes the Wi-Fi credentials, the calibration, the vehicle dimensions and any network password you set. The device then restarts and opens its own, open network again.",
      hinweis_hebesystem: "All jacks at once, the highest first. Wheels not listed stay where they are.",
      hinweis_keile_einzeln: "One step at a time – measure again after driving up.",
      hinweis_neu_messen: "Then measure again.",
      hinweis_wagen_reihenfolge: "Drive the wheel onto the ramp first, then crank the jockey wheel – driving up tilts the caravan lengthwise as well.",
      hoch_front: "Raise the FRONT",
      hoch_heck: "Raise the REAR",
      hoch_links: "Raise the LEFT side",
      hoch_rechts: "Raise the RIGHT side",
      in_bewegung: "moving",
      kal_gut: "{wann} at {temp} °C",
      kal_nie: "never calibrated – do it once while parked",
      kal_ohne_uhr: "time unknown",
      kal_ohne_werte: "calibrated, but without reference values – calibrate once more and the device will watch for drift",
      kal_pruefen: "{wann} at {temp} °C – now {jetzt} °C, please check",
      kalibriere_laeuft: "Calibrating …",
      kalibrieren: "Calibrate level",
      keilstufe: "ramp step {n}",
      kein_wert: "⚠️ No sensor reading",
      keine_bestaetigung: "The device does not confirm the entry. Nothing was saved.",
      keine_verbindung: "No connection to the device.",
      keine_werte_warnung: "The levelling device is not delivering readings – do not rely on this display.",
      keine_wlan_felder: "The device reports no Wi-Fi input fields. It is running firmware without this function.",
      kennt_einstellung_nicht: "The device does not have this setting. Is the matching firmware running?",
      kennt_mqtt_nicht: "The device does not know about MQTT. Is the matching firmware running?",
      kennt_praezision_nicht: "The device has no precision mode. Is the matching firmware running?",
      kennt_wert_nicht: "The device has no setting “{was}”. Is the matching firmware running?",
      kennzeichen_bewegung: "Motion",
      kennzeichen_lage: "Position",
      kennzeichen_neigung: "Tilt",
      kopf_ablassen: "Draining",
      kopf_anzeige: "Display",
      kopf_ausrichten: "Levelling",
      kopf_eigenes_netz: "Own network",
      kopf_fahrzeug: "Vehicle",
      kopf_geraet: "Device",
      kopf_schlafen: "Sleeping",
      kopf_software: "Software",
      kopf_sprache: "Language",
      kopf_technik: "System",
      kopf_waechter: "Guard",
      kopf_warnungen: "Warnings",
      kopf_wlan: "Wi-Fi",
      kopf_ziele: "Targets",
      kopf_zielprofil: "Target profile",
      kopf_zuruecksetzen: "Factory reset",
      kuehl_ok: "Below {grenze}° – the absorber fridge works reliably.",
      kuehl_stufe_1: "{grad}° off level for {dauer} – still harmless.",
      kuehl_stufe_2: "{grad}° off level for {dauer} – cooling performance is dropping.",
      kuehl_stufe_3: "{grad}° off level for {dauer} – please level the vehicle.",
      kurz_kuehlschrank: "Fridge!",
      kurz_ok: "ok",
      kurz_schief: "tilted",
      label_ablassneigung: "Tilt towards the drain (cm)",
      label_ablasspunkt: "Where is the drain?",
      label_achse_stuetzrad: "Axle → jockey wheel (mm)",
      label_auffahrton: "Ramp guidance tone",
      hilfe_auffahrton: "While driving onto the ramps you are at the wheel and cannot look at your phone. Switched on, the buzzer beeps – faster the closer you get, and one long tone means you are there. It then switches itself off so it stays quiet as you drive on.",
      label_alarmton: "Alarm sound",
      label_anzeigeruhe: "Display steadiness (0–10)",
      label_driftwarnung: "Drift warning above (K)",
      label_einbaulage: "Mounting",
      label_fahrzeugart: "Vehicle type",
      label_frost: "Frost warning below (°C)",
      label_haltebereich: "Hold range (%)",
      label_karenzzeit: "Guard grace period (s)",
      label_keilstufe: "Ramp step (cm, 0 = off)",
      label_kopfende: "Raise head end (cm)",
      label_kuehlschrank: "Fridge critical after (min)",
      label_lageaenderung: "Position change above (°)",
      label_praezision: "Precision mode",
      label_radstand: "Wheelbase (mm)",
      label_schlafrichtung: "Where is your head?",
      label_schraeglage: "Tilt warning above (°)",
      label_sprache: "Language",
      label_spurweite: "Track width (mm)",
      label_status_led: "Status LED",
      label_temp_abgleich: "Temperature offset (K)",
      label_toleranz_cm: "Tolerance (cm)",
      label_toleranz_grad: "Precise tolerance (°)",
      label_womit: "How you level",
      lage_unveraendert: "unchanged",
      lage_veraendert: "changed!",
      laufende_fassung: "Running version: {version}",
      letzte_bewegung: "Last movement of the vehicle: {wann}",
      mqtt_aus: "Saved. MQTT is switched off again.",
      mqtt_gespeichert: "Saved. The device is restarting and will report to the broker.\n\nThe state then shows up here – with a typo it says “no connection”.",
      mqtt_speichern: "Save MQTT",
      mqtt_zustand_aus: "MQTT is off – no address entered.",
      mqtt_zustand_getrennt: "No connection to {broker} – check address, port, user and password.",
      mqtt_zustand_verbunden: "Connected to {broker}.",
      name_nicht_angenommen: "The device did not accept the network name ({pfad}/set).",
      netz_jetzt_geschuetzt: "Saved. The device is restarting.\n\nAfter that your phone will ask for the new password. Remember it well: without Wi-Fi and without this password the only way in is a USB cable – or the factory reset further down, which opens the network again.",
      netz_passwort_speichern: "Save network password",
      netz_wieder_offen: "Saved. The device is restarting – afterwards the network is open again without a password.",
      netzname_fehlt: "The network name is missing.",
      nicht_uebernommen: "The device did not accept the setting (status {status} at {pfad}). It now only exists on this phone.",
      noch_keine_daten: "No data received yet.",
      noch_keine_messwerte: "No readings received yet.",
      notfalls_dashboard: "If all else fails, set it up through the ESPHome dashboard.",
      opt_ablass_hinten: "rear",
      opt_ablass_hinten_links: "rear left",
      opt_ablass_hinten_rechts: "rear right",
      opt_ablass_links: "left",
      opt_ablass_rechts: "right",
      opt_ablass_vorn: "front",
      opt_ablass_vorn_links: "front left",
      opt_ablass_vorn_rechts: "front right",
      opt_fahrzeug_wohnmobil: "Motorhome",
      opt_fahrzeug_wohnwagen: "Caravan",
      opt_lage_deckel_oben: "Lid facing up",
      opt_lage_deckel_unten: "Lid facing down",
      opt_methode_auffahrkeile: "Levelling ramps",
      opt_methode_hydraulik_oder_luftkissen: "Hydraulics or air suspension",
      opt_profil_ablassen: "Draining",
      opt_profil_ausrichten: "Levelling",
      opt_profil_schlafen: "Sleeping",
      opt_schlaf_kopf_hinten: "at the rear – feet towards the front",
      opt_schlaf_kopf_links: "on the left – bed across the vehicle",
      opt_schlaf_kopf_rechts: "on the right – bed across the vehicle",
      opt_schlaf_kopf_vorn: "at the front – feet towards the rear",
      passwort_nicht_angenommen: "The device did not accept the password ({pfad}/set).",
      platzhalter_benutzer: "User (optional)",
      platzhalter_broker: "Broker, e.g. 192.168.1.10 (empty = off)",
      platzhalter_mqtt_passwort: "Password (empty = unchanged)",
      platzhalter_netz_passwort: "New password (empty = open)",
      platzhalter_netzname: "Network name",
      platzhalter_passwort: "Password",
      platzhalter_port: "Port",
      profil_ablassen_erklaerung: "The vehicle tilts towards the drain point so boiler and tank really run empty. Standing level leaves a remainder behind – and that freezes in winter.",
      profil_ausrichten_erklaerung: "Level as usual.",
      profil_schlafen_erklaerung: "The head end sits a little higher, which many people find more comfortable. The display now works towards that target: “LEVEL” then means “standing the way you wanted”. You set it up in the settings below, section “Targets”.",
      rad_hinten: "Rear",
      rad_hinten_links: "Rear left",
      rad_hinten_rechts: "Rear right",
      rad_links: "Left side",
      rad_rechts: "Right side",
      rad_stuetzrad: "Jockey wheel",
      rad_vorne: "Front",
      rad_vorne_links: "Front left",
      rad_vorne_rechts: "Front right",
      reiter_anzeige: "Display",
      reiter_technik: "System",
      richtung_hoch: "up",
      richtung_runter: "down",
      satz_ablassen: "Target in the “Draining” profile: {gegen} {cm} cm higher, so the water runs to the drain at the {punkt}.",
      satz_ablassen_null: "The tilt is 0 – with that the “Draining” profile levels the vehicle as usual.",
      satz_schlafen: "Target in the “Sleeping” profile: {seite} {cm} cm higher.",
      satz_schlafen_null: "The height is 0 – with that the “Sleeping” profile levels the vehicle as usual.",
      scharf_schalten: "Arm",
      seite_front: "front",
      seite_heck: "rear",
      seite_links: "left side",
      seite_rechts: "right side",
      steht_ruhig: "at rest",
      uebertrage: "Sending …",
      uebertragen_fehler: "Failed (status {status}). If needed, upload it through the ESPHome dashboard.",
      uebertragen_neustart: "Uploaded. The device is restarting.",
      unbekannt: "unknown",
      unscharf_schalten: "Disarm",
      update_frage: "Download and install new firmware from GitHub?\n\nThe device will restart. Not while driving.",
      update_laeuft: "Downloading and installing …",
      update_neustart: "Running – the device will restart in a moment.",
      update_pruefen: "Check for updates and install",
      vorne: "FRONT",
      vorne_kurz: "FRONT",
      wache_alarm_um: "ALARM – position changed on {zeit}",
      wache_alarm_unbekannt: "ALARM – time unknown",
      wache_alarm_vor: "ALARM – position changed {dauer} ago",
      wache_aus: "off",
      wache_karenz: "arming in {s} s",
      wache_scharf: "armed for {dauer}",
      wagen_rad_hinten_links: "Left wheel",
      wagen_rad_hinten_rechts: "Right wheel",
      wagen_rad_stuetzrad: "Jockey wheel",
      warnung_kalibrierung: "Calibration: {satz}",
      seite_wird_geholt: "Reloading the page …",
      warnung_seite_alt: "This page is older than the device (page {seite}, device {geraet}). Tap here to reload.",
      warnung_montage: "The sensor is delivering implausible readings – is the housing still firmly in place? Until that is fixed, the display is not trustworthy.",
      warte_auf_geraet: "Waiting for the device …",
      warte_bestaetigung: "Waiting for the device to confirm …",
      werte_im_geraet: "These values live in the device. Every phone sees the same ones.",
      winkel_zeile: "Along {laengs}° · Across {quer}°",
      wlan_gespeichert: "Saved. The device is restarting now and will connect to “{netz}”.\n\nWatch the Wi-Fi list on your phone: if the CamperMinder network disappears within a minute, it worked. If it stays, the name or password is wrong – just connect again and correct it.",
      wlan_speichern: "Save and connect",
      zentimeter: "{n} cm",
      ziel: "Target",
      ziel_front_hoeher: "front {cm} cm higher",
      ziel_heck_hoeher: "rear {cm} cm higher",
      ziel_ist: "Target: {was}",
      ziel_ist_eben: "Target: <b>level</b> – the height of this profile is set to 0.",
      ziel_links_hoeher: "left side {cm} cm higher",
      ziel_rechts_hoeher: "right side {cm} cm higher",
      zurueckgesetzt: "Reset done. The device is restarting – connect to the CamperMinder network again afterwards.",
      zuruecksetzen: "Reset to factory settings",
      zuruecksetzen_frage: "Really reset?\n\nWi-Fi, calibration and vehicle dimensions will be lost. The device has to be set up and calibrated again afterwards.\n\nAny network password you set is deleted as well – the own network is open again after that.",
      zuruecksetzen_laeuft: "Resetting …"
    }
  };

  var sprache = (function () {
    try {
      var gewaehlt = window.localStorage.getItem("cm_sprache");
      if (gewaehlt === "de" || gewaehlt === "en") return gewaehlt;
    } catch (e) {
      /* Privates Fenster oder blockierte Website-Daten: dann eben die
       * Handy-Einstellung. Kein Grund, die Seite anzuhalten. */
    }
    var b = String(navigator.language || navigator.userLanguage || "de").toLowerCase();
    return b.indexOf("de") === 0 ? "de" : "en";
  })();

  /* Ein fehlender Schluessel faellt auf Deutsch zurueck und zuletzt auf den
   * Schluessel selbst. Eine leere Stelle in der Oberflaeche waere der
   * schlechteste Ausgang: Sie sieht aus wie ein Fehler des Geraets. */
  function t(schluessel, werte) {
    var wort = TEXTE[sprache][schluessel];
    if (wort === undefined) wort = TEXTE.de[schluessel];
    if (wort === undefined) return schluessel;
    if (werte) {
      for (var k in werte) {
        if (Object.prototype.hasOwnProperty.call(werte, k)) {
          wort = wort.split("{" + k + "}").join(String(werte[k]));
        }
      }
    }
    return wort;
  }

  /* Zahlen: Deutsch schreibt das Komma, Englisch den Punkt. An EINER Stelle,
   * weil sonst die Haelfte der Anzeige das eine und die andere Haelfte das
   * andere tut - und genau so war es vorher. */
  function zahl(wert, stellen) {
    var s = Number(wert).toFixed(stellen === undefined ? 1 : stellen);
    return sprache === "de" ? s.replace(".", ",") : s;
  }

  function spracheSetzen(neu) {
    if (neu !== "de" && neu !== "en") return;
    sprache = neu;
    try {
      window.localStorage.setItem("cm_sprache", neu);
    } catch (e) { /* siehe oben */ }
    document.documentElement.lang = neu;
    render();
  }

  /* Werte, die das GERAET fuehrt, bleiben deutsch: Sie stehen so in Home
   * Assistant, in MQTT und in den Auswahlen der Firmware. Angezeigt wird die
   * Uebersetzung, geschrieben wird der Wert des Geraets.
   *
   * Aus "Kopf vorn" wird der Schluessel "opt_schlaf_kopf_vorn". */
  function kennung(wert) {
    return String(wert).toLowerCase()
      .replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
  }

  function auswahl(werte, gruppe, aktuell, beiWechsel) {
    var sel = el("<select></select>");
    werte.forEach(function (wert) {
      var opt = el("<option></option>");
      opt.value = wert;
      opt.textContent = t("opt_" + gruppe + "_" + kennung(wert));
      sel.appendChild(opt);
    });
    sel.value = aktuell;
    sel.onchange = function () { beiWechsel(sel.value); };
    return sel;
  }

  /* Rad-, Seiten- und Richtungsnamen kommen aus dem Woerterbuch. Beim
   * Wohnwagen heissen zwei Dinge anders, weil sie anderes bedeuten: Die
   * Raeder sitzen auf einer Achse, und das Laengenmass geht bis zum Stuetzrad
   * statt zur zweiten Achse. Brauchen zwei Raeder derselben Seite dasselbe
   * Mass, ist das EINE Anweisung - dann steht dort der Name der Seite. */
  function radName(kennung) {
    var schluessel = (isCaravan() ? "wagen_" : "") + "rad_" + kennung;
    return TEXTE[sprache][schluessel] !== undefined || TEXTE.de[schluessel] !== undefined
      ? t(schluessel) : t("rad_" + kennung);
  }

  var VEHICLE_CARAVAN = "Wohnwagen";

  /* Die Fahrzeugmaße liegen im Gerät, nicht im Browser: sie beschreiben das
   * Fahrzeug, nicht den Betrachter. Dadurch sehen alle Mitfahrer dieselben
   * Zahlen, und ein neues Handy bringt sie nicht durcheinander.
   *
   * Die Werte kommen über denselben Ereignisstrom wie die Messwerte und
   * werden über die REST-Schnittstelle zurückgeschrieben. Die Vorgaben hier
   * gelten nur, solange noch nichts empfangen wurde - eine leere Anzeige wäre
   * schlimmer als eine plausible Zahl. */
  var cfg = {
    wheelbase: 3500, track: 1800, tolerance_cm: 5, wedge_step: 0,
    tolerance_deg: 0.4, precise: false, calm: 5, hold_percent: 125,
    tilt_limit: 3,
    move_limit: 1,
    fridge_minutes: 30,
    guard_grace: 120,
    profile: "Ausrichten",
    target_long: 0, target_lat: 0,
    sleep_dir: "Kopf hinten", sleep_height: 2,
    drain_point: "hinten", drain_amount: 5,
    drift_limit: 20, temp_offset: 0, frost_limit: 3,
    /* Beide ab Werk an. Ein Geraet ohne Display, das nicht blinkt und nicht
     * toent, ist von einem defekten nicht zu unterscheiden. */
    status_led: true, alarm_sound: true, ramp_sound: false,
    method: "keile", vehicle: "wohnmobil", mounting: "oben"
  };

  /* Objekt-Kennungen der Firmware. Die Schreibwege gehen über diese Namen,
   * gelesen wird über Teilstrings - so hält beides auch, wenn dem Gerät
   * ein anderer Name gegeben wird. */
  /* Die Fassung DIESER Datei. Muss zeichengleich mit firmware_version in
   * hardware.yaml sein; tools/build_release.ps1 bricht sonst ab - dieselbe
   * Pruefung, die schon die manifest.json der Integration abdeckt.
   *
   * Wofuer: Das Geraet liefert /0.js ohne Cache-Control, ohne ETag und ohne
   * Last-Modified aus. Der Browser darf seine alte Kopie also behalten, und
   * nach einem Update laeuft neue Firmware mit alter Oberflaeche - stumm.
   * Die Seite vergleicht deshalb ihre eigene Fassung mit der, die das Geraet
   * meldet, und sagt es, wenn sie auseinanderlaufen. */
  var SEITE_VERSION = "4.0.2";

  var IDS = {
    wheelbase: "radstand",
    track: "spurweite",
    tolerance_cm: "toleranz",
    tolerance_deg: "toleranz_genau",
    wedge_step: "keilstufe",
    /* Die Anzeigeruhe braucht hier keinen Eintrag zum Lesen - sie wirkt
     * ausschließlich im Filter der Firmware. Geschrieben wird sie trotzdem
     * von dieser Seite, deshalb steht sie in der Liste. */
    calm: "anzeigeruhe",
    hold_percent: "haltebereich",
    method: "ausrichtart",
    vehicle: "fahrzeugart",
    mounting: "einbaulage",
    /* Der Anfang fehlt mit Absicht. Die Firmware nennt den Schalter
     * „Präzisionsmodus"; ESPHome bildet die Kennung daraus Byte für Byte und
     * ersetzt alles außerhalb von a-z0-9_- durch einen Unterstrich - aus dem
     * „ä" werden zwei. Die Kennung lautet deshalb "pr__zisionsmodus". Der Rest
     * des Wortes ist eindeutig und überlebt jede Schreibweise, die ein
     * Umlaut sonst noch annehmen könnte. */
    precise: "zisionsmodus",
    /* Der Grenzwert der Schraeglagenwarnung. Der Umlaut in "Schraeglage"
     * wird zu zwei Unterstrichen - deshalb der Teilstring ab "glage",
     * der jede Schreibweise ueberlebt. */
    tilt_limit: "glage_grenzwert",
    /* Ebenfalls mit Umlaut in der Kennung ("Lage__nderung") - deshalb
     * der Teilstring ab "nderung". */
    move_limit: "nderung_grenzwert",
    /* Das Zeitkonto des Kuehlschranks. "K__hlschrank kritisch nach" - der
     * Umlaut steht am Anfang, deshalb hier das Teilstueck ab "hlschrank". */
    fridge_minutes: "hlschrank_kritisch_nach",
    /* Zielprofile. Die geltende Zielneigung liest die Seite als fertigen
     * Wert vom Geraet - sie wertet das Profil NICHT selbst aus. Zwei Stellen,
     * die aus Profil und drei Reglern dieselbe Zahl ableiten, laufen
     * auseinander, sobald ein Profil dazukommt. */
    profile: "zielprofil",
    target_long: "ziel_l",
    target_lat: "ziel_quer",
    sleep_dir: "schlafrichtung",
    sleep_height: "kopfende_anheben",
    /* ACHTUNG, Reihenfolge: "ablasspunkt" steckt auch in
     * "neigung_zum_ablasspunkt". Beim Auswerten des Ereignisstroms wird
     * deshalb erst die Zahl und dann die Auswahl geprueft. */
    drain_amount: "neigung_zum_ablasspunkt",
    drain_point: "ablasspunkt",
    /* Selbstueberwachung. Ein fest verbautes Geraet kann sich selbst
     * beobachten - ein Handgeraet nicht. */
    drift_limit: "driftwarnung_ab",
    temp_offset: "temperatur_abgleich",
    frost_limit: "frostwarnung_unter",
    /* Der Waechter. "W__chter" - derselbe Umlaut, dieselbe Loesung. Das
     * Teilstueck ab "chter" ist in jedem Bereich eindeutig: Im Schalter- wie
     * im Textbereich gibt es nur diese eine Entitaet, die darauf endet. */
    guard: "chter",
    guard_alarm: "chter_alarm",
    guard_grace: "chter_karenzzeit",
    guard_ack: "quittieren",
    last_motion: "letzte_bewegung",
    /* Ohne Umlaut und ohne Doppeldeutigkeit - hier braucht es keinen Trick
     * mit Teilstuecken. "status_led" steckt in keiner anderen Kennung, und
     * "alarmton" ist von "waechter_alarm" verschieden genug, dass indexOf sie
     * nicht verwechselt. */
    status_led: "status_led",
    alarm_sound: "alarmton",
    /* Die akustische Auffahrhilfe. "auffahrton" steckt in keiner anderen
     * Kennung - der Alarmton heisst schlicht "alarmton". */
    ramp_sound: "auffahrton"
  };

  var METHOD_LIFT = "Hydraulik oder Luftkissen";
  var MOUNT_UNDER = "Deckel unten";

  var state = { pitch: null, roll: null, motion: false, seen: {}, ready: false };

  /* Jeder Schreibzugriff wird geprüft.
   *
   * Vorher wurden Werte lokal gesetzt und blind abgeschickt. Antwortete das
   * Gerät mit 404, sah der Nutzer trotzdem seine Eingabe stehen und durfte
   * annehmen, sie sei gespeichert. Eine Einstellung, die stillschweigend
   * nicht ankommt, ist schlimmer als eine, die sichtbar scheitert. */
  var writeError = null;

  function write(domain, needle, query) {
    var base = pathFor(domain, needle);
    if (!base) {
      writeError = t("kennt_wert_nicht", { was: needle });
      syncSettings();
      return;
    }
    post(base + "/set?" + query, check(base + "/set"));
  }

  function setNumber(key, value) {
    cfg[key] = value;
    write("number", IDS[key], "value=" + encodeURIComponent(value));
  }

  function setMethod(option) {
    cfg.method = option === METHOD_LIFT ? "hebesystem" : "keile";
    write("select", IDS.method, "option=" + encodeURIComponent(option));
  }

  /* Einbaulage kehrt das Vorzeichen von Quer- und Hochachse um. Der gespeicherte
   * Nullpunkt gilt danach nicht mehr - deshalb steht der Hinweis auf neu
   * Kalibrieren unter der Auswahl und nicht nur im Log des Geräts, das ohne
   * Home Assistant niemand liest. */
  function setMounting(option) {
    cfg.mounting = option === MOUNT_UNDER ? "unten" : "oben";
    write("select", IDS.mounting, "option=" + encodeURIComponent(option));
  }

  /* Schalter gehen nicht über /set, sondern über /turn_on bzw. /turn_off -
   * eigener Weg, gleiche Prüfung. Danach neu aufbauen: Der Modus entscheidet,
   * ob unter „Fahrzeug" die Zentimeter- oder die Gradtoleranz steht, und das
   * ist ein Bedienelement und kein Messwert. */
  function setPrecise(on) {
    cfg.precise = on;
    var base = pathFor("switch", IDS.precise);
    if (!base) {
      writeError = t("kennt_praezision_nicht");
      syncSettings();
      return;
    }
    post(base + (on ? "/turn_on" : "/turn_off"), check(base));
    render();
  }

  function setVehicle(option) {
    cfg.vehicle = option === VEHICLE_CARAVAN ? "wohnwagen" : "wohnmobil";
    write("select", IDS.vehicle, "option=" + encodeURIComponent(option));
    // Beschriftungen und Bedienfelder hängen davon ab - hier reicht das
    // Nachziehen der Werte nicht, der feste Bereich muss neu entstehen.
    render();
  }

  /* Schlafrichtung und Ablasspunkt: Wert ins Geraet, Seite neu aufbauen -
   * die Skizze und der Satz darunter haengen daran. */
  function setSchlafrichtung(option) {
    cfg.sleep_dir = option;
    write("select", IDS.sleep_dir, "option=" + encodeURIComponent(option));
    render();
  }

  function setAblasspunkt(option) {
    cfg.drain_point = option;
    write("select", IDS.drain_point, "option=" + encodeURIComponent(option));
    render();
  }

  function check(path) {
    return function (status) {
      writeError = (status >= 200 && status < 300)
        ? null
        : t("nicht_uebernommen", { status: status, pfad: path });
      syncSettings();
    };
  }

  function post(path, done) {
    var req = new XMLHttpRequest();
    req.open("POST", path, true);
    req.onloadend = function () { if (done) done(req.status); };
    req.send();
  }

  // -- Rechnen --------------------------------------------------------------

  var MIN_TOLERANCE_DEG = 0.05;
  var IMPLAUSIBLE_DEG = 45;
  var WHEEL_LIFT_IGNORE_CM = 1;

  /* Rückfallwert für den Haltebereich, solange das Gerät seinen noch nicht
   * gemeldet hat. Muss mit LEVEL_RELEASE in const.py übereinstimmen. */
  var LEVEL_RELEASE = 1.25;

  function levelRelease() {
    var f = cfg.hold_percent / 100;
    // Unter 1 wäre es keine Hysterese mehr, sondern eine Anzeige, die "eben"
    // schon vor der Toleranz zurücknimmt.
    return f >= 1 ? f : LEVEL_RELEASE;
  }

  /* Im Präzisionsmodus eine feste Gradzahl für beide Achsen, sonst die
   * Zentimeterangabe über das jeweilige Fahrzeugmaß umgerechnet.
   *
   * Der Unterschied ist kein Feinschliff: In Zentimetern sind längs und quer
   * gleich streng bewertet, in Grad nicht - bei 3500 mm Radstand und 1800 mm
   * Spurweite bedeuten 0,4° längs 2,4 cm, quer aber nur 1,3 cm. Zentimeter
   * sind das Maß der Wirklichkeit, Grad das Maß des Sensors.
   *
   * MUSS mit _tolerance() in coordinator.py und der Rechnung im Binärsensor
   * "Camper steht gerade" übereinstimmen. */
  function tolerance(dimensionMm) {
    if (cfg.precise) return Math.max(cfg.tolerance_deg, MIN_TOLERANCE_DEG);
    var deg = Math.atan((cfg.tolerance_cm * 10) / dimensionMm) * 180 / Math.PI;
    return Math.max(deg, MIN_TOLERANCE_DEG);
  }

  /* Die Zielneigung in Grad. Dieselbe Umrechnung wie tolerance() darueber -
   * und wie im Geraet. Bei "Ausrichten" ist sie null, dann ist alles wie
   * frueher.
   *
   * Der Zentimeterwert kommt fertig vom Geraet; hier wird nur noch ueber das
   * Fahrzeugmass in einen Winkel gerechnet. */
  function zielGradP() {
    return Math.atan((cfg.target_long * 10) / cfg.wheelbase) * 180 / Math.PI;
  }
  function zielGradR() {
    return Math.atan((cfg.target_lat * 10) / cfg.track) * 180 / Math.PI;
  }

  /* Die ABWEICHUNG vom Ziel - das ist es, was die Anzeige zeigt und was noch
   * zu tun ist. Der echte Winkel bleibt in state.pitch/state.roll: Die
   * Kuehlschrankwarnung braucht ihn, und die interessiert sich nicht dafuer,
   * wie jemand schlafen moechte. */
  function abwP() { return state.pitch === null ? null : state.pitch - zielGradP(); }
  function abwR() { return state.roll === null ? null : state.roll - zielGradR(); }

  function available() {
    return state.pitch !== null && state.roll !== null &&
      Math.abs(state.pitch) <= IMPLAUSIBLE_DEG && Math.abs(state.roll) <= IMPLAUSIBLE_DEG;
  }

  /* Ob eine Achse eben steht - EINE Antwort für Text, Blase, Fahrzeugneigung
   * und Anweisung.
   *
   * Ohne Hysterese entscheidet sich das an einem einzigen Punkt, und genau auf
   * diesem Punkt rauscht der Messwert: Bei 5 cm Toleranz stand deshalb
   * abwechselnd "EBEN - STOP" und "noch 5,2 cm", mehrmals in der Sekunde. Der
   * Rückweg ist bewusst deutlich größer als das Rauschen, sonst verschiebt die
   * Hysterese das Flattern nur um ein paar Zehntel. */
  var hold = { pitch: false, roll: false };

  function axisLevel(key, value, tol) {
    if (value === null || !available()) {
      hold[key] = false;
      return false;
    }
    var deviation = Math.abs(value);
    if (hold[key]) {
      if (deviation > tol * levelRelease()) hold[key] = false;
    } else if (deviation <= tol) {
      hold[key] = true;
    }
    return hold[key];
  }

  function levelPitch() { return axisLevel("pitch", abwP(), tolerance(cfg.wheelbase)); }
  function levelRoll() { return axisLevel("roll", abwR(), tolerance(cfg.track)); }

  /* Der Maßstab der Anzeige ist die TOLERANZ, nicht das Grad.
   *
   * Vorher wanderte die Blase mit festen 16 px je Grad, und die grüne Mitte
   * der Skala war ein fester Streifen - beide wussten nichts von der
   * eingestellten Toleranz. Bei 5 cm Toleranz stand die Blase deshalb weit
   * neben der Mitte, während der Text daneben "EBEN - STOP" meldete. Zwei
   * Aussagen über einen Zustand, und die auffälligere war die falsche.
   *
   * Jetzt gilt: Toleranzgrenze = Rand der grünen Zone. Das stimmt für beide
   * Achsen zugleich, obwohl 5 cm längs (0,82°) und quer (1,59°) verschiedene
   * Winkel sind. Wer es genauer will, stellt die Toleranz kleiner - dann wird
   * derselbe Maßstab schärfer, ohne dass es eine zweite Darstellung braucht.
   *
   * Zahlen zur Skala: .track steht 6 % vom Rand, seine grüne Mitte liegt bei
   * 45-55 % - das sind ±4,4 % der Kachelbreite. Wer den Verlauf im CSS ändert,
   * muss BAR_TOLERANCE mitziehen. Das Zielfeld der Draufsicht ist 56 px groß,
   * also ±28 px.
   *
   * Jenseits der Toleranz staucht sich der Maßstab: bei doppelter Toleranz ist
   * ein Drittel des Restwegs verbraucht, bei fünffacher zwei Drittel, den Rand
   * erreicht die Blase nie ganz. So bleibt auch eine grobe Schieflage im Bild
   * und zeigt weiter Veränderung, statt am Anschlag zu kleben. */
  var BAR_FULL = 40, BAR_TOLERANCE = 4.4;
  var TOP_TOLERANCE = 28, TOP_FULL_X = 64, TOP_FULL_Y = 118;
  var OUTSIDE_K = 2;

  function deflect(value, tol, atTolerance, full) {
    if (!(tol > 0)) return 0;
    var units = Math.abs(value) / tol;
    var out = units <= 1
      ? units * atTolerance
      : atTolerance + (full - atTolerance) * ((units - 1) / (units - 1 + OUTSIDE_K));
    return value < 0 ? -out : out;
  }

  /* Eine Zahl, die stehen bleibt.
   *
   * Der Messwert rauscht um wenige Hundertstelgrad; über den Radstand
   * gerechnet werden daraus Zehntel Zentimeter. Nackt angezeigt wechselt die
   * Zahl mehrmals je Sekunde zwischen zwei Werten, obwohl das Fahrzeug still
   * steht - eine zappelnde Zahl liest niemand, sie beunruhigt nur.
   *
   * Die Anzeige rastet deshalb auf ein Raster und verlässt es erst, wenn der
   * Messwert um 0,75 Rasterschritte weiterwandert. Keine Glättung über die
   * Zeit: Der angezeigte Wert weicht nie weiter ab als diese 0,75 Schritte,
   * und einer echten Änderung hinkt er nicht hinterher. */
  var shown = {};
  /* Das Raster ist bewusst so fein wie die angezeigte Stelle - nicht gröber.
   *
   * Vorher stand hier ein halber Zentimeter, mit der Begründung, feiner lasse
   * sich ohnehin kein Keil legen. Das stimmt für die ANWEISUNG, war für die
   * ANZEIGE aber ein Fehler: Seit es den Regler "Anzeigeruhe" gibt, tut das
   * Raster dieselbe Arbeit ein zweites Mal - und es gewann. Das Restrauschen
   * liegt über den gesamten Regelbereich zwischen 0,03 und 0,11 cm, die
   * Umschaltschwelle des Rasters lag bei 0,375 cm. Der Regler konnte sich
   * damit gar nicht auswirken; jede Einstellung sah gleich aus.
   *
   * Jetzt bremst das Raster nur noch das Flackern der letzten angezeigten
   * Stelle. Wie ruhig es darüber hinaus zugeht, entscheidet der Regler - und
   * das ist auch die Stelle, an der der Nutzer es erwartet.
   */
  var STEP_CM = 0.1, STEP_CM_FEIN = 0.1;
  var STEP_DEG = 0.1, STEP_DEG_FEIN = 0.05;

  function steady(key, value, step) {
    if (value === null || value === undefined || isNaN(value)) return null;
    var last = shown[key];
    if (last === undefined || Math.abs(value - last) >= step * 0.75) {
      shown[key] = Math.round(value / step) * step;
    }
    return shown[key];
  }

  function steadyCm(key, value) {
    return steady(key, value, cfg.precise ? STEP_CM_FEIN : STEP_CM);
  }
  function steadyDeg(key, value) {
    var v = steady(key, value, cfg.precise ? STEP_DEG_FEIN : STEP_DEG);
    return v === null ? 0 : v;
  }
  function places() { return cfg.precise ? 2 : 1; }

  /* Innerhalb der Toleranz zeigt die Anzeige die Mitte - im Präzisionsmodus
   * nicht, dort ist die Feinlage genau das Gesuchte. */
  function centred(level) { return level && !cfg.precise; }

  function isCaravan() { return cfg.vehicle === "wohnwagen"; }

  /* Wohnwagen: zwei Räder auf einer Achse plus Stützrad.
   *
   * Quer wie beim Wohnmobil über die Spurweite - ein Keil unter das tiefere
   * Rad. Längs dagegen über das Stützrad, und das kurbelt in BEIDE
   * Richtungen; "nur anheben" wäre hier eine künstliche Einschränkung.
   *
   * Reihenfolge ist Absicht: erst quer, dann längs. Das Auffahren auf den
   * Keil kippt den Wagen längs mit - eine vorher berechnete Stützradhöhe
   * wäre danach falsch. */
  function caravanPlan() {
    if (!available()) return null;
    var out = [];

    /* Eine Achse innerhalb der Toleranz ist fertig und kommt nicht in die
     * Anweisung - dieselbe Regel wie beim Wohnmobil in wheelLifts(). Ohne sie
     * stünde "Stützrad hoch, 3 cm" unter einer Anzeige, die für dieselbe Achse
     * gerade "EBEN - STOP" meldet. */
    var across = levelRoll()
      ? 0
      : Math.round(cfg.track * Math.tan(Math.abs(state.roll) * Math.PI / 180) / 10 * 10) / 10;
    if (across >= WHEEL_LIFT_IGNORE_CM) {
      out.push({
        wheel: state.roll > 0 ? "hinten_links" : "hinten_rechts",
        cm: across,
        steps: cfg.wedge_step > 0 ? Math.max(Math.round(across / cfg.wedge_step), 1) : null,
        direction: "hoch"
      });
    }

    var along = levelPitch()
      ? 0
      : Math.round(cfg.wheelbase * Math.tan(Math.abs(state.pitch) * Math.PI / 180) / 10 * 10) / 10;
    if (along >= WHEEL_LIFT_IGNORE_CM) {
      out.push({
        wheel: "stuetzrad",
        cm: along,
        steps: null,                       // gekurbelt wird stufenlos
        direction: state.pitch > 0 ? "runter" : "hoch"
      });
    }
    return out;
  }

  function wheelLifts() {
    if (isCaravan()) return caravanPlan();
    if (!available()) return null;
    /* Eine Achse, die innerhalb ihrer Toleranz steht, ist FERTIG - ihr
     * Restwinkel darf die Anweisung nicht mehr formen.
     *
     * Ohne das nützt der Zusammenzug weiter unten nichts. Von Hand kippt
     * niemand exakt auf einer Achse: Schon 0,3 Grad Rest längs - ein Drittel
     * der Toleranz - erzeugen aus einer reinen Querneigung wieder drei
     * verschiedene Eckmaße, und die Anweisung nennt eine Längsrichtung, die
     * nach den eigenen Maßstäben des Nutzers gar nicht korrigiert werden muss.
     *
     * Bezugsgröße ist dieselbe Toleranz, die auch über "steht eben" entscheidet.
     * Damit kann die Anweisung nichts verlangen, was die Anzeige darüber
     * bereits als erledigt ausweist - vorher konnte sie genau das. */
    var pitch = levelPitch() ? 0 : state.pitch;
    var roll = levelRoll() ? 0 : state.roll;
    var halfLong = cfg.wheelbase * Math.tan(pitch * Math.PI / 180) / 20;
    var halfLat = cfg.track * Math.tan(roll * Math.PI / 180) / 20;
    // pitch > 0 = Front höher, roll > 0 = rechts höher.
    var ground = {
      vorne_links: +halfLong - halfLat,
      vorne_rechts: +halfLong + halfLat,
      hinten_links: -halfLong - halfLat,
      hinten_rechts: -halfLong + halfLat
    };
    var highest = -Infinity;
    for (var k in ground) { if (ground[k] > highest) highest = ground[k]; }
    var out = [];
    for (var w in ground) {
      var cm = Math.round((highest - ground[w]) * 10) / 10;
      if (cm >= WHEEL_LIFT_IGNORE_CM) {
        out.push({ wheel: w, cm: cm, steps: cfg.wedge_step > 0 ? Math.max(Math.round(cm / cfg.wedge_step), 1) : null });
      }
    }
    out.sort(function (a, b) { return b.cm - a.cm; });
    return mergeSide(out);
  }

  /* Zwei Räder mit demselben Maß, die eine Seite teilen, zu einer Anweisung
   * zusammenziehen.
   *
   * Steht das Fahrzeug nur quer schief, brauchen beide linken Räder exakt
   * dasselbe. Die Rechnung liefert dafür zwei Einträge, und die lasen sich als
   * "Vorne links 4,0 cm" und "Hinten links 4,0 cm" - zwei Handgriffe, wo einer
   * gemeint ist, und beide nennen eine Längsrichtung, die gar nicht korrigiert
   * wird. Wer nach Anweisung arbeitet, sucht dann nach einem Unterschied
   * zwischen den beiden Zeilen, den es nicht gibt.
   *
   * Nur bei GENAU zwei Einträgen: Sobald beide Achsen schief stehen, entstehen
   * drei mit verschiedenen Maßen, und dann ist jede Ecke wirklich einzeln
   * gemeint. Ein zufälliges Zusammenfallen kann es dabei nicht geben - die
   * beiden gleich großen Einträge lägen dann über Kreuz und teilten sich keine
   * Seite. */
  function mergeSide(list) {
    if (list.length !== 2 || list[0].cm !== list[1].cm) return list;
    var a = list[0].wheel.split("_");
    var b = list[1].wheel.split("_");
    if (a.length !== 2 || b.length !== 2) return list;
    var seite = a[0] === b[0] ? a[0] : (a[1] === b[1] ? a[1] : null);
    if (!seite || TEXTE.de["rad_" + seite] === undefined) return list;
    return [{ wheel: seite, cm: list[0].cm, steps: list[0].steps }];
  }

  // -- Aufbau ---------------------------------------------------------------

  var CAMPER_REAR =
    '<svg viewBox="0 0 220 200" id="svgRear"><defs><linearGradient id="bR" x1="0" y1="0" x2="1" y2="0">' +
    '<stop offset="0" stop-color="#d3dae1"/><stop offset="0.5" stop-color="#eef2f6"/><stop offset="1" stop-color="#d3dae1"/>' +
    '</linearGradient></defs>' +
    '<rect x="34" y="24" width="152" height="140" rx="16" fill="url(#bR)" stroke="#aab3bd" stroke-width="2"/>' +
    '<rect x="60" y="40" width="100" height="34" rx="5" fill="#38506a"/>' +
    '<rect x="86" y="82" width="48" height="78" rx="4" fill="#dbe1e7" stroke="#aab3bd" stroke-width="2"/>' +
    '<rect x="92" y="90" width="36" height="24" rx="3" fill="#38506a"/>' +
    '<rect x="44" y="120" width="16" height="30" rx="3" fill="#e0544e"/>' +
    '<rect x="160" y="120" width="16" height="30" rx="3" fill="#e0544e"/>' +
    '<rect x="34" y="150" width="152" height="9" fill="#2fb6c9" opacity="0.85"/>' +
    '<rect x="40" y="164" width="140" height="12" rx="4" fill="#c2cad2"/>' +
    '<rect x="40" y="176" width="30" height="16" rx="6" fill="#20242b"/>' +
    '<rect x="150" y="176" width="30" height="16" rx="6" fill="#20242b"/></svg>';

  /* Draufsicht mit wandernder Blase - die Hauptanzeige. Sie zeigt beide
   * Achsen zugleich, während die Wasserwaagen darüber jede für sich
   * stehen. Deshalb steht sie zwischen Klartext und Seitenansichten und
   * nicht am Rand. */
  var CAMPER_TOP =
    '<svg viewBox="0 0 300 380" id="svgTop"><defs><linearGradient id="bT" x1="0" y1="0" x2="1" y2="0">' +
    '<stop offset="0" stop-color="#eef2f6"/><stop offset="0.5" stop-color="#e2e7ed"/><stop offset="1" stop-color="#cdd4dc"/>' +
    '</linearGradient></defs><g fill="#20242b">' +
    '<rect x="44" y="72" width="16" height="34" rx="6"/><rect x="240" y="72" width="16" height="34" rx="6"/>' +
    '<rect x="44" y="276" width="16" height="34" rx="6"/><rect x="240" y="276" width="16" height="34" rx="6"/></g>' +
    '<rect x="58" y="16" width="184" height="348" rx="40" fill="url(#bT)" stroke="#aab3bd" stroke-width="2"/>' +
    '<path d="M92 40 Q150 18 208 40 L208 70 Q150 58 92 70 Z" fill="#38506a"/>' +
    '<rect x="74" y="82" width="4" height="268" rx="2" fill="#b7c0c9"/>' +
    '<rect x="222" y="82" width="4" height="268" rx="2" fill="#b7c0c9"/>' +
    '<rect x="96" y="96" width="108" height="70" rx="4" fill="#24507a" stroke="#3d6a99"/>' +
    '<rect x="120" y="184" width="60" height="46" rx="6" fill="#f3f6f9" stroke="#aab3bd" stroke-width="2"/>' +
    '<rect x="112" y="252" width="76" height="52" rx="8" fill="#dfe5ea" stroke="#aab3bd" stroke-width="2"/>' +
    '<rect x="58" y="320" width="184" height="10" fill="#2fb6c9" opacity="0.85"/></svg>';

  var CAMPER_SIDE =
    '<svg viewBox="0 0 380 170" id="svgSide"><defs><linearGradient id="bS" x1="0" y1="0" x2="0" y2="1">' +
    '<stop offset="0" stop-color="#eef2f6"/><stop offset="1" stop-color="#d3dae1"/></linearGradient></defs>' +
    '<path d="M20 128 L20 98 Q20 88 34 86 L58 64 Q62 44 88 44 L344 44 Q356 44 356 60 L356 122 Q356 128 348 128 Z" fill="url(#bS)" stroke="#aab3bd" stroke-width="2"/>' +
    '<path d="M44 84 L60 64 Q64 52 84 52 L84 84 Z" fill="#38506a"/>' +
    '<rect x="96" y="52" width="30" height="20" rx="3" fill="#38506a"/>' +
    '<rect x="150" y="58" width="60" height="34" rx="5" fill="#38506a"/>' +
    '<rect x="288" y="58" width="48" height="34" rx="5" fill="#38506a"/>' +
    '<rect x="20" y="112" width="336" height="9" fill="#2fb6c9" opacity="0.85"/>' +
    '<circle cx="86" cy="138" r="20" fill="#20242b"/><circle cx="300" cy="138" r="20" fill="#20242b"/></svg>';

  /* Wohnwagen: Deichsel mit Kupplung, EINE Achse, Stützrad vorn. Gleiche
   * viewBox wie die Wohnmobilfassungen, damit nichts umgerechnet werden muss. */
  var CARAVAN_SIDE =
    '<svg viewBox="0 0 380 170" id="svgSide"><defs><linearGradient id="bCS" x1="0" y1="0" x2="0" y2="1">' +
    '<stop offset="0" stop-color="#eef2f6"/><stop offset="1" stop-color="#d3dae1"/></linearGradient></defs>' +
    '<path d="M96 104 L30 113 L30 123 L96 126 Z" fill="#8d97a3"/>' +
    '<rect x="8" y="106" width="26" height="22" rx="6" fill="#20242b"/>' +
    '<rect x="56" y="108" width="10" height="34" rx="3" fill="#5a626b"/>' +
    '<rect x="48" y="100" width="26" height="7" rx="3" fill="#8d97a3"/>' +
    '<circle cx="61" cy="149" r="10" fill="#20242b"/><circle cx="61" cy="149" r="4" fill="#5a626b"/>' +
    '<path d="M96 128 L96 66 Q98 48 118 46 L344 44 Q356 44 356 60 L356 122 Q356 128 348 128 Z" fill="url(#bCS)" stroke="#aab3bd" stroke-width="2"/>' +
    '<rect x="108" y="58" width="34" height="26" rx="4" fill="#38506a"/>' +
    '<rect x="158" y="58" width="62" height="34" rx="5" fill="#38506a"/>' +
    '<rect x="298" y="58" width="42" height="34" rx="5" fill="#38506a"/>' +
    '<rect x="236" y="56" width="46" height="72" rx="4" fill="#dbe1e7" stroke="#aab3bd" stroke-width="2"/>' +
    '<rect x="96" y="112" width="260" height="9" fill="#2fb6c9" opacity="0.85"/>' +
    '<circle cx="238" cy="138" r="20" fill="#20242b"/><circle cx="238" cy="138" r="9" fill="#5a626b"/></svg>';

  var CARAVAN_REAR =
    '<svg viewBox="0 0 220 200" id="svgRear"><defs><linearGradient id="bCR" x1="0" y1="0" x2="1" y2="0">' +
    '<stop offset="0" stop-color="#d3dae1"/><stop offset="0.5" stop-color="#eef2f6"/><stop offset="1" stop-color="#d3dae1"/>' +
    '</linearGradient></defs>' +
    '<rect x="38" y="22" width="144" height="142" rx="24" fill="url(#bCR)" stroke="#aab3bd" stroke-width="2"/>' +
    '<rect x="62" y="40" width="96" height="38" rx="8" fill="#38506a"/>' +
    '<rect x="86" y="90" width="48" height="34" rx="4" fill="#dbe1e7" stroke="#aab3bd" stroke-width="2"/>' +
    '<rect x="46" y="122" width="18" height="26" rx="4" fill="#e0544e"/>' +
    '<rect x="156" y="122" width="18" height="26" rx="4" fill="#e0544e"/>' +
    '<rect x="38" y="150" width="144" height="9" fill="#2fb6c9" opacity="0.85"/>' +
    '<rect x="46" y="164" width="128" height="12" rx="5" fill="#c2cad2"/>' +
    '<rect x="44" y="176" width="30" height="16" rx="6" fill="#20242b"/>' +
    '<rect x="146" y="176" width="30" height="16" rx="6" fill="#20242b"/></svg>';

  var CARAVAN_TOP =
    '<svg viewBox="0 0 300 380" id="svgTop"><defs><linearGradient id="bCT" x1="0" y1="0" x2="1" y2="0">' +
    '<stop offset="0" stop-color="#eef2f6"/><stop offset="0.5" stop-color="#e2e7ed"/><stop offset="1" stop-color="#cdd4dc"/>' +
    '</linearGradient></defs>' +
    '<path d="M112 96 L150 32" stroke="#aab3bd" stroke-width="10" stroke-linecap="round" fill="none"/>' +
    '<path d="M188 96 L150 32" stroke="#aab3bd" stroke-width="10" stroke-linecap="round" fill="none"/>' +
    '<rect x="139" y="12" width="22" height="22" rx="7" fill="#20242b"/>' +
    '<g fill="#20242b"><rect x="36" y="176" width="26" height="44" rx="7"/>' +
    '<rect x="238" y="176" width="26" height="44" rx="7"/></g>' +
    '<rect x="58" y="80" width="184" height="284" rx="34" fill="url(#bCT)" stroke="#aab3bd" stroke-width="2"/>' +
    '<path d="M92 96 Q150 86 208 96 L208 118 Q150 110 92 118 Z" fill="#38506a"/>' +
    '<rect x="118" y="144" width="64" height="48" rx="6" fill="#f3f6f9" stroke="#aab3bd" stroke-width="2"/>' +
    '<rect x="96" y="212" width="108" height="60" rx="6" fill="#24507a" stroke="#3d6a99"/>' +
    '<rect x="112" y="292" width="76" height="52" rx="8" fill="#dfe5ea" stroke="#aab3bd" stroke-width="2"/>' +
    '<rect x="58" y="352" width="184" height="10" fill="#2fb6c9" opacity="0.85"/></svg>';

  var CSS =
    'body{margin:0;background:#11151b;color:#e8ecf1;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;' +
    '-webkit-text-size-adjust:100%}' +
    '.wrap{max-width:560px;margin:0 auto;padding:12px;display:flex;flex-direction:column;gap:12px}' +
    '.tabs{display:flex;gap:8px}' +
    '.tabs button{flex:1;padding:10px;border:0;border-radius:10px;background:#1c222b;color:#9aa4b2;font-size:1rem;font-weight:700}' +
    '.tabs button.on{background:#2fb6c9;color:#08252a}' +
    '.bar{position:relative;height:104px;border-radius:16px;background:#1b2029;border:1px solid rgba(255,255,255,.08);overflow:hidden}' +
    '.bar .lab{position:absolute;top:10px;left:0;right:0;text-align:center;font-size:.78rem;letter-spacing:.18em;opacity:.6}' +
    '.bar .val{position:absolute;top:30px;left:0;right:0;text-align:center;font-weight:800;font-size:1.05rem}' +
    '.track{position:absolute;left:6%;right:6%;top:76px;height:16px;margin-top:-8px;border-radius:8px;' +
    'background:linear-gradient(90deg,rgba(127,127,127,.18) 0,rgba(127,127,127,.18) 45%,rgba(55,214,122,.35) 45%,rgba(55,214,122,.35) 55%,rgba(127,127,127,.18) 55%)}' +
    '.bub{position:absolute;top:76px;width:26px;height:26px;margin:-13px 0 0 -13px;border-radius:50%;transition:left .25s,background .25s}' +
    '.top{position:relative;height:320px;border-radius:20px;background:#1b2029;' +
    'border:1px solid rgba(255,255,255,.08);overflow:hidden}' +
    '.top .cap{position:absolute;left:0;right:0;top:10px;text-align:center;font-size:.78rem;' +
    'letter-spacing:.2em;opacity:.6}' +
    '.top svg{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);height:272px}' +
    /* Zielfeld, kein Kreis: Die Toleranz gilt je Achse. Der erlaubte Bereich
       ist damit ein Rechteck - bei einem Kreis läge die Blase mit beiden
       Achsen knapp innerhalb der Toleranz trotzdem außerhalb der Markierung. */
    /* Eckwerte in der Draufsicht - die Zahl steht dort, wo der Keil hin muss.
       Das ist der Unterschied zu einer Liste unter dem Bild: Man muss nicht
       uebersetzen, welche Zeile welche Ecke meint. */
    /* Drei Badges: Neigung, Bewegung, Lage.
       Drei Themen, die NICHT das Ausrichten betreffen und deshalb eine eigene
       Zeile bekommen - und drei Farben, die auf einen Blick sagen, ob etwas
       zu tun ist. Bewusst andere Farbwerte als die Nivellieranzeige: Dort
       heisst Gruen "innerhalb der Toleranz", hier "alles in Ordnung". */
    '.badges{display:flex;gap:8px}' +
    '.badge{flex:1;min-width:0;padding:9px 8px;border-radius:12px;text-align:center;' +
    'background:#1b2029;border:1px solid rgba(255,255,255,.10)}' +
    '.badge .bt{font-size:.66rem;letter-spacing:.14em;font-weight:800;opacity:.75;' +
    'text-transform:uppercase;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
    '.badge .bs{margin-top:3px;font-size:.9rem;font-weight:800;' +
    'white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
    '.badge.ok{background:#1e3326;border-color:#2f6b45}.badge.ok .bs{color:#9fe3b8}' +
    '.badge.achtung{background:#4a3410;border-color:#ffb020}.badge.achtung .bs{color:#ffd48a}' +
    '.badge.alarm{background:#4a1d1d;border-color:#b3564f}.badge.alarm .bs{color:#ffd9d6}' +
    '.badge.aus .bs{color:#6f7885}' +
    '.ecke{position:absolute;min-width:52px;text-align:center;padding:3px 6px;border-radius:8px;' +
    'font-size:.82rem;font-weight:800;font-variant-numeric:tabular-nums;' +
    'background:rgba(12,16,22,.82);border:1px solid rgba(255,255,255,.14);color:#cfd6de}' +
    '.ecke.tun{background:#4a3410;border-color:#ffb020;color:#ffd48a}' +
    '.ecke.fertig{color:#6f7885}' +
    '.ring{position:absolute;left:50%;top:50%;width:56px;height:56px;margin:-28px 0 0 -28px;' +
    'border-radius:14px;border:2px dashed rgba(127,127,127,.5)}' +
    '.top .bub{width:42px;height:42px;margin:-21px 0 0 -21px;top:auto;transition:all .3s}' +
    '.view{position:relative;height:210px;border-radius:16px;background:#1b2029;border:1px solid rgba(255,255,255,.08);overflow:hidden}' +
    '.view .cap{position:absolute;left:50%;top:10px;transform:translateX(-50%);padding:5px 14px;border-radius:999px;' +
    'font-size:1rem;font-weight:800;color:#10141a;white-space:nowrap}' +
    '.view .ground{position:absolute;left:8%;right:8%;bottom:28px;border-top:2px dashed rgba(127,127,127,.35)}' +
    '.view svg{position:absolute;left:50%;bottom:28px;transform-origin:50% 100%;transition:transform .3s}' +
    '#svgSide{width:100%;max-width:300px}#svgRear{width:49.2%;max-width:148px}' +
    '.plan{background:#1b2029;border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:14px;font-size:1rem;line-height:1.5}' +
    '.plan h2{margin:0 0 6px;font-size:1.2rem}.plan ul{margin:8px 0 0;padding-left:1.1rem}.plan li{margin:3px 0}' +
    '.muted{color:#9aa4b2;font-size:.85rem}' +
    /* Warnfläche: kräftig, aber nicht in der Farbe der Nivellieranzeige.
       Rot dort heißt "noch weit weg", hier heißt es "hier nimmt etwas
       Schaden" - zwei verschiedene Aussagen dürfen nicht gleich aussehen. */
    '.warn{background:#4a1d1d;border:1px solid #b3564f;border-radius:12px;' +
    'padding:12px 14px;font-size:.95rem;line-height:1.45;color:#ffd9d6;font-weight:600}' +
    'button.act{width:100%;padding:14px;border:0;border-radius:12px;background:#2fb6c9;color:#08252a;font-size:1.05rem;font-weight:800}' +
    'button.act.ghost{background:#1c222b;color:#cfd6de}' +
    '.set{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid rgba(255,255,255,.07)}' +
    '.set input,.set select{width:130px;padding:8px;border-radius:8px;border:1px solid #2d3542;background:#141920;color:#e8ecf1;font-size:1rem}' +
    '.plan input{padding:10px;border-radius:8px;border:1px solid #2d3542;background:#141920;color:#e8ecf1;font-size:1rem;box-sizing:border-box}' +
    'table{width:100%;border-collapse:collapse;font-size:.95rem;table-layout:fixed}' +
    'td{padding:7px 4px;border-bottom:1px solid rgba(255,255,255,.06);' +
    'overflow:hidden;text-overflow:ellipsis;white-space:nowrap}' +
    'td.v{text-align:right;color:#cfd6de;font-variant-numeric:tabular-nums;width:42%}' +
    '.grouphead{margin:16px 0 4px;font-size:.75rem;font-weight:800;letter-spacing:.14em;' +
    'text-transform:uppercase;color:#2fb6c9}' +
    '.grouphead:first-of-type{margin-top:10px}';

  function el(html) {
    var d = document.createElement("div");
    d.innerHTML = html;
    return d.firstChild;
  }

  /* Tabellenteile MÜSSEN so gebaut werden, nicht über el().
   *
   * Der HTML-Parser verwirft <tr> und <td>, wenn sie in einem <div> stehen -
   * das ist Absicht der Spezifikation, nicht ein Fehler des Browsers. el()
   * lieferte daher für "<tr>..." nur die nackten Textknoten (die Technik-
   * liste sah dadurch unformatiert aus) und für "<tr></tr>" gar nichts,
   * worauf das Anhängen mit einem Fehler abbrach und die ganze Liste leer
   * blieb. Zwei Symptome, eine Ursache. */
  function cell(text, className) {
    var td = document.createElement("td");
    if (className) td.className = className;
    // textContent, nicht innerHTML: die Namen kommen vom Gerät, spitze
    // Klammern darin sollen Text bleiben.
    td.textContent = text;
    return td;
  }

  var root, page = "anzeige";

  function build() {
    document.title = "CamperMinder";
    var style = document.createElement("style");
    style.textContent = CSS;
    document.head.appendChild(style);

    var meta = document.createElement("meta");
    meta.name = "viewport";
    meta.content = "width=device-width,initial-scale=1,viewport-fit=cover";
    document.head.appendChild(meta);

    document.body.innerHTML = "";
    root = el('<div class="wrap"></div>');
    document.body.appendChild(root);
    render();
  }

  function tabs() {
    var leiste = el('<div class="tabs"></div>');
    [["anzeige", t("reiter_anzeige")], ["technik", t("reiter_technik")]].forEach(function (pair) {
      var b = el("<button" + (page === pair[0] ? ' class="on"' : "") + ">" + pair[1] + "</button>");
      b.onclick = function () { page = pair[0]; render(); };
      leiste.appendChild(b);
    });
    return leiste;
  }

  /*
   * Zwei Bereiche, und der Unterschied ist der wichtigste in dieser Datei:
   *
   *   live   - Messwerte. Wird bei jeder Meldung des Geräts neu gezeichnet,
   *            also mehrmals pro Sekunde.
   *   fest   - Bedienelemente. Wird nur beim Wechsel des Reiters aufgebaut.
   *
   * Vorher lag beides zusammen. Jede Messwertänderung hat damit auch die
   * Eingabefelder zerstört und neu angelegt - wer tippte, verlor den Text
   * nach Sekundenbruchteilen. Eingabefelder dürfen nie im Takt der Messwerte
   * neu entstehen.
   */
  var liveEl = null;
  var fixedEl = null;

  function render() {
    if (!root) return;
    root.innerHTML = "";
    root.appendChild(tabs());

    liveEl = el("<div></div>");
    fixedEl = el("<div></div>");
    root.appendChild(liveEl);
    root.appendChild(fixedEl);

    if (page === "technik") {
      fixedEl.appendChild(spracheBox());
      fixedEl.appendChild(softwareBox());
      fixedEl.appendChild(wifiSetup());
    } else {
      fixedEl.appendChild(settings());
    }
    update();
  }

  /* Nur der Messwertbereich - hier gibt es keine Eingabefelder. */
  function update() {
    if (!liveEl) return;
    liveEl.innerHTML = "";
    // Vor allem anderen und auf JEDEM Reiter: Ein Alarm, den man erst nach
    // einem Reiterwechsel sieht, ist ein halber Alarm.
    waechterAlarm(liveEl);
    seiteVeraltet(liveEl);
    geraetWarnung(liveEl);
    if (page === "technik") renderTechTable(liveEl);
    else renderMain(liveEl);
    syncSettings();
  }

  function colorFor(value, tol, level) {
    if (!available()) return COLORS.off;
    if (level) return COLORS.ok;
    return Math.abs(value) > 2 * tol ? COLORS.bad : COLORS.warn;
  }

  /* Steht die Achse innerhalb der Toleranz, zeigt die Anzeige die Mitte -
   * Blase mittig, Fahrzeug waagerecht. Denn genau das ist die Aussage: Hier
   * ist nichts mehr zu tun. Eine Blase, die dabei sichtbar neben der Mitte
   * steht, widerspricht dem Text daneben. */
  function bar(label, value, tol, level, text) {
    var color = colorFor(value, tol, level);
    var out = centred(level) ? 0 : deflect(value, tol, BAR_TOLERANCE, BAR_FULL);
    var b = el(
      '<div class="bar"><div class="lab">' + label + '</div>' +
      '<div class="val"></div><div class="track"></div><div class="bub"></div></div>'
    );
    var v = b.querySelector(".val");
    v.textContent = text;
    v.style.color = color;
    var bub = b.querySelector(".bub");
    bub.style.left = "calc(50% + " + out.toFixed(2) + "%)";
    bub.style.background = "radial-gradient(circle at 34% 30%,#fff," + color + " 62%)";
    bub.style.boxShadow = "0 3px 8px rgba(0,0,0,.45),0 0 12px " + color;
    return b;
  }

  function view(svg, capText, color, rotation) {
    var v = el('<div class="view"><div class="cap"></div><div class="ground"></div></div>');
    var cap = v.querySelector(".cap");
    cap.textContent = capText;
    cap.style.background = CHIP[color];
    v.appendChild(el(svg));
    var s = v.querySelector("svg");
    s.style.transform = "translateX(-50%) rotate(" + rotation.toFixed(1) + "deg)";
    return v;
  }

  function renderMain(target) {
    var ok = available();
    var tolP = tolerance(cfg.wheelbase);
    var tolR = tolerance(cfg.track);
    var pitch = ok ? abwP() : 0;
    var roll = ok ? abwR() : 0;
    // Über axisLevel und nicht über den nackten Vergleich: nur so tragen
    // Text, Blase und Fahrzeugneigung dieselbe, ruhige Antwort.
    var levP = ok && levelPitch();
    var levR = ok && levelRoll();
    var level = levP && levR;
    // Angezeigte Winkel gerastet - siehe steady(). Der Rechenweg oben bleibt
    // am ungerasteten Messwert, gerastet wird nur, was zu lesen ist.
    var degP = ok ? steadyDeg("pitch_deg", pitch) : 0;
    var degR = ok ? steadyDeg("roll_deg", roll) : 0;

    var textR = !ok ? t("kein_wert")
      : levR ? t("eben_stop")
        : (roll > 0 ? t("hoch_links") : t("hoch_rechts"));
    var textP = !ok ? t("kein_wert")
      : levP ? t("eben_stop")
        : (pitch > 0 ? t("hoch_heck") : t("hoch_front"));

    target.appendChild(bar(t("achse_quer"), roll, tolR, levR, textR));
    target.appendChild(bar(t("achse_laengs"), pitch, tolP, levP, textP));

    var plan = el('<div class="plan"></div>');
    var head = level ? t("eben_stop") : ok ? t("kopf_ausrichten") : t("kein_wert");
    var html = "<h2>" + head + "</h2>";
    if (ok) {
      html += '<div class="muted">' + t("winkel_zeile", {
        laengs: zahl(degP, places()), quer: zahl(degR, places())
      }) + (state.motion ? " · " + t("in_bewegung") : "") + "</div>";
      var lifts = level ? [] : (wheelLifts() || []);
      var label = function (i) { return radName(i.wheel); };
      // Auch die Zentimeter der Anweisung gerastet: ein Maß, das beim Lesen
      // zwischen 4,3 und 5,2 wechselt, ist keine Anweisung, sondern eine Frage.
      var planCm = function (i) { return steadyCm("plan_" + i.wheel, i.cm).toFixed(1); };

      if (lifts.length) {
        html += "<ul>";
        if (isCaravan()) {
          // Beide Schritte auf einmal, aber in fester Reihenfolge - und mit
          // Richtung, weil das Stützrad auch runter kann.
          lifts.forEach(function (i) {
            html += "<li><b>" + label(i) + "</b> " + t("richtung_" + i.direction) + ", " +
              (i.steps ? t("keilstufe", { n: i.steps }) : t("zentimeter", { n: planCm(i) })) + "</li>";
          });
          html += "</ul>";
          html += '<div class="muted">' + (lifts.length > 1
            ? t("hinweis_wagen_reihenfolge") : t("hinweis_neu_messen")) + "</div>";
        } else if (cfg.method === "hebesystem") {
          lifts.forEach(function (i) {
            html += "<li><b>" + label(i) + "</b> " + t("zentimeter", { n: planCm(i) }) + "</li>";
          });
          // "Räder" im Plural: Bei einer zusammengezogenen Seitenanweisung
          // bleiben zwei stehen, nicht eines.
          html += '</ul><div class="muted">' + t("hinweis_hebesystem") + "</div>";
        } else {
          var first = lifts[0];
          html += "<li><b>" + label(first) + "</b> " +
            (first.steps ? t("keilstufe", { n: first.steps }) : t("zentimeter", { n: planCm(first) })) +
            "</li></ul><div class=\"muted\">" + t("hinweis_keile_einzeln") + "</div>";
        }
      }
    } else {
      html += '<div class="muted">' + t("keine_werte_warnung") + "</div>";
    }
    plan.innerHTML = html;
    target.appendChild(plan);

    // --- Draufsicht: beide Achsen in einer Blase ---------------------------
    var overall = !ok ? COLORS.off
      : level ? COLORS.ok
        : (Math.abs(pitch) > 2 * tolP || Math.abs(roll) > 2 * tolR) ? COLORS.bad : COLORS.warn;
    var top = el('<div class="top"><div class="cap">▲ ' + t("vorne") + '</div></div>');
    top.appendChild(el(isCaravan() ? CARAVAN_TOP : CAMPER_TOP));
    top.appendChild(el('<div class="ring"></div>'));
    var bubTop = el('<div class="bub"></div>');
    bubTop.style.position = "absolute";
    bubTop.style.borderRadius = "50%";
    // Jede Achse an ihrer eigenen Toleranz: innerhalb steht die Blase im
    // Zielfeld, außerhalb daneben - obwohl 5 cm längs und quer verschiedene
    // Winkel sind.
    bubTop.style.left = "calc(50% + " +
      (centred(levR) ? 0 : deflect(-roll, tolR, TOP_TOLERANCE, TOP_FULL_X)).toFixed(1) + "px)";
    bubTop.style.top = "calc(50% + " +
      (centred(levP) ? 0 : deflect(pitch, tolP, TOP_TOLERANCE, TOP_FULL_Y)).toFixed(1) + "px)";
    bubTop.style.background = "radial-gradient(circle at 34% 30%,#fff," + overall + " 62%)";
    bubTop.style.boxShadow = "0 4px 12px rgba(0,0,0,.45),0 0 16px " + overall;
    /* Vier Eckwerte, an ihrem Platz im Bild.
     *
     * Sie kommen aus dem Gerät, nicht aus einer zweiten Rechnung hier. Orange
     * steht der Hub-Wert, den auch die Anweisung darunter nennt - beide müssen
     * dasselbe sagen, sonst sucht der Nutzer den Unterschied. Verlangt eine
     * Ecke nichts, steht dort grau der echte Höhenunterschied bis ganz
     * waagerecht (Sensoren "Abweichung ..."): Eine Achse in der Toleranz ist
     * fertig, ihre Abweichung bleibt aber sichtbar. Vorher stand dort "0", und
     * im Stand sah man nur noch Grad.
     *
     * Beim Wohnwagen tragen die beiden hinteren Werte die Räder der einen
     * Achse, und vorne steht mittig das Stützrad - deshalb dort nur ein Feld
     * statt zweier. Gesucht wird es mit dem Teilstück ab dem Umlaut wie in
     * IDS ("tzrad", "abweichung_st"): Aus "Stützrad" wird "st_tzrad" oder
     * "st__tzrad", je nach ESPHome-Fassung - "stuetzrad" traf nie. Der
     * kürzeste Teiltreffer gewinnt, "tzrad" findet also das Stützrad selbst
     * und nicht seine Abweichung. */
    var hub = function (kennung) {
      var w = parseFloat(findStateOf("sensor", kennung));
      return isNaN(w) ? null : w;
    };
    var pfeil = function (wert) { return wert < 0 ? "▼ " : "▲ "; };
    var ecke = function (tun, rest, oben, links, mitPfeil) {
      var e = el('<div class="ecke"></div>');
      e.style.top = oben;
      e.style.left = links;
      e.style.transform = "translate(-50%,-50%)";
      if (tun !== null && Math.abs(tun) >= 1) {
        e.textContent = (mitPfeil ? pfeil(tun) : "") + zahl(Math.abs(tun), 1);
        e.className = "ecke tun";
      } else if (rest !== null) {
        e.textContent = (mitPfeil && Math.abs(rest) >= 0.05 ? pfeil(rest) : "") +
          zahl(Math.abs(rest), 1);
        e.className = "ecke fertig";
      } else if (tun !== null) {
        e.textContent = "0";
        e.className = "ecke fertig";
      } else {
        e.textContent = "–";
        e.className = "ecke fertig";
      }
      top.appendChild(e);
    };

    if (isCaravan()) {
      ecke(hub("tzrad"), hub("abweichung_st"), "16%", "50%", true);
      ecke(hub("hub_hinten_links"), hub("abweichung_hinten_links"), "78%", "22%");
      ecke(hub("hub_hinten_rechts"), hub("abweichung_hinten_rechts"), "78%", "78%");
    } else {
      ecke(hub("hub_vorne_links"), hub("abweichung_vorne_links"), "20%", "22%");
      ecke(hub("hub_vorne_rechts"), hub("abweichung_vorne_rechts"), "20%", "78%");
      ecke(hub("hub_hinten_links"), hub("abweichung_hinten_links"), "80%", "22%");
      ecke(hub("hub_hinten_rechts"), hub("abweichung_hinten_rechts"), "80%", "78%");
    }

    top.appendChild(bubTop);
    target.appendChild(top);

    /* Drei Badges: Neigung, Bewegung, Lage.
     *
     * Sie beantworten drei Fragen, die mit dem Ausrichten nichts zu tun haben
     * und die man sonst aus einer Liste zusammensuchen müsste: Leidet der
     * Kühlschrank? Ist gerade jemand am Fahrzeug? Steht es noch, wo es stand?
     *
     * Alle drei Zustände entscheidet das GERÄT - hier werden sie nur gelesen.
     * Die Schwellen tragen dort ihre Hysterese; zwei Stellen, die dieselbe
     * Grenze auswerten, driften auseinander. */
    var schraeg = findStateOf("binary_sensor", "glage") === "ON";
    var bewegt = findStateOf("binary_sensor", "in_bewegung") === "ON";
    var verrueckt = findStateOf("binary_sensor", "nderung") === "ON";
    var schiefste = ok ? Math.max(Math.abs(state.pitch), Math.abs(state.roll)) : 0;

    var badges = el('<div class="badges"></div>');
    var badge = function (titel, text, klasse, hinweis) {
      var b = el('<div class="badge ' + klasse + '"><div class="bt"></div><div class="bs"></div></div>');
      b.querySelector(".bt").textContent = titel;
      b.querySelector(".bs").textContent = text;
      if (hinweis) b.title = hinweis;
      badges.appendChild(b);
    };

    if (!ok) {
      badge(t("kennzeichen_neigung"), "–", "aus");
      badge(t("kennzeichen_bewegung"), "–", "aus");
      badge(t("kennzeichen_lage"), "–", "aus");
    } else {
      /* Die Neigungskachel kennt drei Stufen statt an und aus.
       *
       * Was einen Absorberkühlschrank beschädigt, ist der Winkel MAL DER
       * ZEIT. Eine Kachel, die beim Rangieren rot wird, ist deshalb doppelt
       * falsch: Sie warnt, wo nichts ist, und wer sie kennt, sieht über sie
       * hinweg, wenn es ernst wird.
       *
       * Gelb heißt "steht schief, noch folgenlos", rot heißt "jetzt leidet
       * er". Die Grenze dazwischen zieht das Gerät, nicht diese Seite. */
      var kuehlWarn = findStateOf("binary_sensor", "hlschrank_warnung") === "ON";
      /* Stufe und Dauer kommen als Werte, nicht als Satz - siehe
       * statusWerte(). Die Stufe zieht das Gerät, nicht diese Seite: Sonst
       * gäbe es zwei Stellen, die dieselbe Grenze auswerten. */
      var kuehl = String(statusWerte().k || "ok").split(":");
      var wieLang = kuehl.length > 1 ? " " + spanne(kuehl[1]) : "";

      badge(t("kennzeichen_neigung"),
        zahl(schiefste, 1) + "° · " +
          (kuehlWarn ? t("kurz_kuehlschrank") + wieLang
            : schraeg ? t("kurz_schief") + wieLang
              : t("kurz_ok")),
        kuehlWarn ? "alarm" : schraeg ? "achtung" : "ok",
        kuehl.length > 2
          ? t("kuehl_stufe_" + kuehl[0], { grad: zahl(kuehl[2], 1), dauer: spanne(kuehl[1]) })
          : t("kuehl_ok", { grenze: zahl(cfg.tilt_limit, 1) }));
      badge(t("kennzeichen_bewegung"), bewegt ? t("in_bewegung") : t("steht_ruhig"),
        bewegt ? "achtung" : "ok", t("hilfe_bewegung"));
      badge(t("kennzeichen_lage"), verrueckt ? t("lage_veraendert") : t("lage_unveraendert"),
        verrueckt ? "alarm" : "ok",
        t("hilfe_lage", { grenze: zahl(cfg.move_limit, 1) }));
    }
    target.appendChild(badges);

    /* Anders als die Blasen bleiben diese beiden am echten Winkel: Sie zeigen
     * das Fahrzeug, nicht eine Skala. Nur innerhalb der Toleranz stehen sie
     * waagerecht - sonst kippelte das Bild um Zehntelgrad weiter, während
     * daneben "EBEN - STOP" steht. */
    var tilt = function (value, lev) {
      return !ok || centred(lev) ? 0 : Math.max(-30, Math.min(30, value));
    };
    target.appendChild(view(isCaravan() ? CARAVAN_SIDE : CAMPER_SIDE,
      t("ansicht_seite") + " — " + (ok ? zahl(degP, places()) + "°" : "⚠️"),
      colorFor(pitch, tolP, levP), tilt(degP, levP)));
    target.appendChild(view(isCaravan() ? CARAVAN_REAR : CAMPER_REAR,
      t("ansicht_heck") + " — " + (ok ? zahl(degR, places()) + "°" : "⚠️"),
      colorFor(roll, tolR, levR), tilt(-degR, levR)));

    var cal = el('<button class="act"></button>');
    cal.textContent = t("kalibrieren");
    cal.onclick = function () {
      cal.disabled = true;
      cal.textContent = t("kalibriere_laeuft");
      press("neigung_kalibrieren", function () {
        window.setTimeout(function () {
          cal.disabled = false;
          cal.textContent = t("kalibrieren");
        }, 5000);
      });
    };
    target.appendChild(cal);

    zielBox(target);
    waechterBox(target);
  }


  /* --- Statuswerte des Geraets ----------------------------------------------
   *
   * Das Geraet liefert die sechs Auskuenfte doppelt: als deutschen Satz (fuer
   * Home Assistant und MQTT) und als Werte im Sensor "Statuswerte". Die Seite
   * nimmt die Werte und formuliert selbst - nur so kann sie Englisch.
   *
   * Format siehe hardware.yaml: "w=...;k=...;c=...;b=...;m=...;n=..."
   */
  function statusWerte() {
    var roh = findStateOf("text_sensor", "statuswerte") || "";
    var raus = {};
    roh.split(";").forEach(function (paar) {
      var i = paar.indexOf("=");
      if (i > 0) raus[paar.slice(0, i)] = paar.slice(i + 1);
    });
    return raus;
  }

  /* Zeitspanne in Worten. Die Einheiten sind in beiden Sprachen dieselben
   * Abkuerzungen, deshalb eine Funktion fuer beide. */
  function spanne(sek) {
    var s = Math.max(0, Math.round(Number(sek) || 0));
    if (s < 60) return s + " s";
    if (s < 3600) return Math.floor(s / 60) + " min";
    if (s < 86400) return Math.floor(s / 3600) + " h " + Math.floor((s % 3600) / 60) + " min";
    return Math.floor(s / 86400) + " d " + Math.floor((s % 86400) / 3600) + " h";
  }

  /* Zeitpunkt in der Schreibweise der gewaehlten Sprache. Das Geraet liefert
   * Unix-Zeit; die Umrechnung macht das Handy, und das kennt seine Zeitzone
   * besser als das Geraet ohne Internet. */
  function zeitpunkt(unix) {
    var d = new Date(Number(unix) * 1000);
    try {
      return d.toLocaleString(sprache === "de" ? "de-DE" : "en-GB",
        { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
    } catch (e) {
      return d.toISOString().slice(5, 16).replace("T", " ");
    }
  }

  /* Der Satz zum Waechter, aus dem Wert "w". */
  function wacheSatz(wert) {
    var teil = String(wert || "").split(":");
    if (teil[0] === "alarm") return t("wache_alarm_um", { zeit: zeitpunkt(teil[1]) });
    if (teil[0] === "alarm_vor") return t("wache_alarm_vor", { dauer: spanne(teil[1]) });
    if (teil[0] === "alarm_unbekannt") return t("wache_alarm_unbekannt");
    if (teil[0] === "karenz") return t("wache_karenz", { s: Math.round(Number(teil[1]) || 0) });
    if (teil[0] === "scharf") return t("wache_scharf", { dauer: spanne(teil[1]) });
    return t("wache_aus");
  }

  /* Der Satz zur letzten Bewegung, aus dem Wert "b". */
  function bewegungSatz(wert) {
    var teil = String(wert || "").split(":");
    if (teil[0] === "jetzt") return t("bewegung_jetzt");
    if (teil[0] === "vor") return t("bewegung_vor", { dauer: spanne(teil[1]) });
    if (teil[0] === "nie" || !teil[0]) return t("bewegung_nie");
    return zeitpunkt(teil[0]);
  }

  /* Der Satz zur MQTT-Verbindung, aus dem Wert "m" - die Adresse steht im
   * Eingabefeld des Geraets, das Passwort nirgends. */
  function mqttSatz() {
    var zustand = statusWerte().m;
    var broker = findStateOf("text", "mqtt_broker") || "";
    if (!zustand || zustand === "aus") return t("mqtt_zustand_aus");
    return t(zustand === "verbunden" ? "mqtt_zustand_verbunden" : "mqtt_zustand_getrennt",
      { broker: broker });
  }

  /* Der Satz zur Kalibrierung, aus dem Wert "c". */
  function kalibrierSatz(wert) {
    var teil = String(wert || "").split(":");
    if (teil[0] === "nie") return t("kal_nie");
    if (teil[0] === "ohne_werte") return t("kal_ohne_werte");
    if (teil.length < 4) return t("kal_nie");
    var wann = Number(teil[0]) > 0 ? zeitpunkt(teil[0]) : t("kal_ohne_uhr");
    return teil[3] === "1"
      ? t("kal_pruefen", { wann: wann, temp: zahl(teil[1], 0), jetzt: zahl(teil[2], 0) })
      : t("kal_gut", { wann: wann, temp: zahl(teil[1], 0) });
  }

  /* Zielprofil.
   *
   * Steht auf der Hauptseite und nicht in den Einstellungen, weil man es
   * BENUTZT und nicht einrichtet: abends aufs Schlafprofil, im Herbst einmal
   * aufs Ablassen. Die Zahlen dahinter richtet man einmal ein, die stehen
   * folgerichtig unter Einstellungen.
   *
   * Solange "Ausrichten" gewählt ist, sieht die Seite darüber aus wie immer -
   * das Ziel ist dann null. */
  function zielBox(target) {
    var pfad = pathFor("select", IDS.profile);
    if (!pfad) return;   // ältere Firmware ohne Profile

    var box = el('<div class="plan" style="margin-top:12px"><h2>' + t("kopf_zielprofil") + "</h2></div>");
    var row = el('<div class="set" style="border-bottom:0"><span>' + t("ziel") + "</span></div>");
    profileSelect = auswahl(["Ausrichten", "Schlafen", "Ablassen"], "profil", cfg.profile,
      function (wert) {
        cfg.profile = wert;
        write("select", IDS.profile, "option=" + encodeURIComponent(wert));
        render();
      });
    row.appendChild(profileSelect);
    box.appendChild(row);

    var erklaerung = cfg.profile === "Schlafen" ? t("profil_schlafen_erklaerung")
      : cfg.profile === "Ablassen" ? t("profil_ablassen_erklaerung")
        : t("profil_ausrichten_erklaerung");

    /* Was das Profil verlangt, in einem Satz - und zwar in der Sprache des
     * Nutzers, nicht als Vorzeichen. "Ziel: Front 2,0 cm höher" ist die
     * Antwort auf "was stellt das Gerät hier eigentlich ein?". */
    var ziel = "";
    if (cfg.profile !== "Ausrichten") {
      var teile = [];
      if (cfg.target_long) {
        teile.push(t(cfg.target_long > 0 ? "ziel_front_hoeher" : "ziel_heck_hoeher",
          { cm: zahl(Math.abs(cfg.target_long), 1) }));
      }
      if (cfg.target_lat) {
        teile.push(t(cfg.target_lat > 0 ? "ziel_rechts_hoeher" : "ziel_links_hoeher",
          { cm: zahl(Math.abs(cfg.target_lat), 1) }));
      }
      ziel = "<br><br>" + (teile.length
        ? t("ziel_ist", { was: "<b>" + teile.join(", ") + "</b>" })
        : t("ziel_ist_eben"));
    }

    box.appendChild(el('<div class="muted" style="margin-top:10px;line-height:1.5">' +
      erklaerung + ziel + "</div>"));
    target.appendChild(box);
  }

  /* Der Wächter.
   *
   * Steht bewusst UNTER dem Ausrichten und nicht dazwischen: Beim Ankommen
   * geht es ums Geradestehen, der Wächter ist der Handgriff danach. Die
   * Ausnahme ist der Alarm - der steht ganz oben, siehe waechterAlarm().
   *
   * Alles hier liest nur ab und drückt Knöpfe des Geräts. Es gibt bewusst
   * keine zweite Zustandshaltung auf dieser Seite: Ein Wachdienst, dessen
   * Anzeige etwas anderes behauptet als das Gerät, ist schlimmer als keiner. */
  function waechterBox(target) {
    var pfad = pathFor("switch", IDS.guard);
    if (!pfad) return;   // ältere Firmware ohne Wächter - dann fehlt der Kasten

    var scharf = findStateOf("switch", IDS.guard) === "ON";
    var alarm = findStateOf("binary_sensor", IDS.guard_alarm) === "ON";
    var werte = statusWerte();
    var satz = wacheSatz(werte.w);
    var zuletzt = werte.b ? bewegungSatz(werte.b) : "";

    var box = el('<div class="plan" style="margin-top:12px"><h2>' + t("kopf_waechter") + "</h2></div>");

    var zeile = el('<div class="set" style="border-bottom:0"><span></span></div>');
    zeile.firstChild.textContent = satz;
    zeile.firstChild.style.fontWeight = "800";
    if (alarm) zeile.firstChild.style.color = "#ffd9d6";
    box.appendChild(zeile);

    var knopf = el('<button class="act' + (scharf ? " ghost" : "") + '"></button>');
    knopf.textContent = scharf ? t("unscharf_schalten") : t("scharf_schalten");
    knopf.onclick = function () {
      knopf.disabled = true;
      post(pfad + (scharf ? "/turn_off" : "/turn_on"), check(pfad));
    };
    box.appendChild(knopf);

    if (alarm) {
      var quitt = el('<button class="act ghost" style="margin-top:8px"></button>');
      quitt.textContent = t("alarm_quittieren");
      quitt.onclick = function () {
        quitt.disabled = true;
        press(IDS.guard_ack);
      };
      box.appendChild(quitt);
    }

    box.appendChild(el('<div class="muted" style="margin-top:10px;line-height:1.5">' +
      t(scharf ? "hilfe_waechter_scharf" : "hilfe_waechter_aus") +
      (zuletzt ? "<br><br>" + t("letzte_bewegung", { wann: "<b>" + zuletzt + "</b>" }) : "") +
      "</div>"));

    target.appendChild(box);
  }

  /* Selbstüberwachung: Meldungen, die sagen „traue der Anzeige gerade
   * nicht“. Die gehören nach oben und nicht in eine Diagnoseliste, die
   * niemand öffnet – wer einer verschobenen Kalibrierung vertraut, richtet
   * sein Fahrzeug falsch aus und merkt es nie.
   *
   * Gelb und nicht rot: Hier nimmt nichts Schaden, hier stimmt nur eine Zahl
   * womöglich nicht mehr. Rot bleibt dem Wächteralarm vorbehalten. */
  function geraetWarnung(target) {
    var montage = findStateOf("binary_sensor", "montage_pr") === "ON";
    var kalib = findStateOf("binary_sensor", "kalibrierung_pr") === "ON";
    if (!montage && !kalib) return;

    var text = montage
      ? t("warnung_montage")
      : t("warnung_kalibrierung", { satz: kalibrierSatz(statusWerte().c) });

    var w = el('<div style="background:#4a3410;border:1px solid #ffb020;' +
      'border-radius:12px;padding:10px 12px;margin-bottom:12px;' +
      'font-size:.9rem;line-height:1.45;color:#ffd48a;font-weight:600"></div>');
    w.textContent = "⚠️ " + text;
    target.appendChild(w);
  }

  /* Veraltete Seite im Browser.
   *
   * Der Vergleich laeuft erst, wenn das Geraet seine Fassung gemeldet hat -
   * vorher ist nichts bekannt, und eine Warnung auf Verdacht waere schlimmer
   * als keine.
   *
   * Gelb und nicht rot: Es ist nichts kaputt, es ist nur alt. Dieselbe Farbe
   * wie bei der Selbstueberwachung, aus demselben Grund. */
  function seiteVeraltet(target) {
    var geraet = findState("firmware_version");
    if (!geraet || geraet === SEITE_VERSION) return;

    var w = el('<button style="display:block;width:100%;text-align:left;' +
      'background:#4a3410;border:1px solid #ffb020;' +
      'border-radius:12px;padding:10px 12px;margin-bottom:12px;' +
      'font:inherit;font-size:.9rem;line-height:1.45;color:#ffd48a;' +
      'font-weight:600;cursor:pointer"></button>');
    w.textContent = "⚠️ " + t("warnung_seite_alt",
      { seite: SEITE_VERSION, geraet: geraet });

    /* Auf Fingertipp, nicht von allein: Wer gerade WLAN-Zugangsdaten
     * eintippt, verloere sie bei einem Neuladen aus heiterem Himmel.
     *
     * Erst die Datei erzwungen neu holen, dann laden - ein blosses
     * reload() nimmt sonst wieder die alte Kopie aus dem Zwischenspeicher.
     * Schlaegt das Holen fehl, wird trotzdem geladen: schlimmstenfalls
     * aendert sich nichts, und der Balken steht wieder da. */
    w.onclick = function () {
      w.textContent = t("seite_wird_geholt");
      var fertig = function () { location.reload(); };
      try {
        fetch("/0.js", { cache: "reload" }).then(fertig, fertig);
      } catch (e) {
        fertig();
      }
    };
    target.appendChild(w);
  }

  /* Der Alarm gehört an den Anfang der Seite, nicht ans Ende.
   *
   * Wer morgens aufs Telefon schaut, soll ihn sehen, bevor er irgendetwas
   * anderes liest - und ohne zu scrollen. Solange nichts ist, entsteht hier
   * auch nichts: Die gewohnte Anzeige bleibt unverändert. */
  function waechterAlarm(target) {
    if (findStateOf("binary_sensor", IDS.guard_alarm) !== "ON") return;
    var satz = wacheSatz(statusWerte().w);
    var w = el('<div class="warn" style="margin-bottom:12px"></div>');
    w.textContent = "🚨 " + satz;
    target.appendChild(w);
  }

  /* Wird einmal je Reiterwechsel aufgebaut. Die Verweise bleiben erhalten,
   * damit syncSettings() später nur die Werte nachziehen kann. */
  var settingInputs = {};
  var methodSelect = null;
  var vehicleSelect = null;
  var mountingSelect = null;
  var schlafSelect = null;
  var ablassSelect = null;
  var preciseBox = null;
  var schalterBoxen = {};
  var profileSelect = null;
  var mqttNote = null;
  var mqttBroker = null;
  var pushZiel = null;
  var mqttUser = null;
  var mqttPort = null;
  var settingsNote = null;

  /* Eine Zahlenzeile. Der Verweis auf das Eingabefeld bleibt in
   * settingInputs, damit syncSettings() den Wert später nachziehen kann, ohne
   * das Feld neu anzulegen - wer gerade tippt, verlöre sonst den Text. */
  function zahlZeile(ziel, key, label) {
    var row = el('<div class="set"><span>' + label + "</span></div>");
    var input = el('<input type="number" step="any">');
    input.value = cfg[key];
    input.onchange = function () {
      var v = parseFloat(input.value);
      if (!isNaN(v)) setNumber(key, v);
    };
    settingInputs[key] = input;
    row.appendChild(input);
    ziel.appendChild(row);
    return input;
  }

  /* Eine Schalterzeile mit Ankreuzfeld - wie setPrecise, aber ohne render().
   * Diese Schalter formen keine Bedienelemente, sie schalten nur etwas am
   * Geraet; ein Neuaufbau der Seite waere hier nur Flackern. */
  function schalterZeile(ziel, key, label) {
    var row = el('<div class="set"><span>' + label + "</span></div>");
    var kasten = el('<input type="checkbox" style="width:26px;height:26px;padding:0">');
    kasten.checked = cfg[key];
    kasten.onchange = function () {
      cfg[key] = kasten.checked;
      var base = pathFor("switch", IDS[key]);
      if (!base) {
        writeError = t("kennt_wert_nicht", { was: label });
        syncSettings();
        return;
      }
      post(base + (kasten.checked ? "/turn_on" : "/turn_off"), check(base));
    };
    schalterBoxen[key] = kasten;
    row.appendChild(kasten);
    ziel.appendChild(row);
    return kasten;
  }

  /* --- Skizzen ---------------------------------------------------------------
   *
   * Zwei kleine Draufsichten: Wo liegt der Kopf, wo sitzt der Ablasspunkt.
   *
   * WARUM SIE DA SIND: "Schlafen laengs -2 cm" war nicht zu verstehen - auch
   * fuer den nicht, der es gebaut hat. Eine Zeichnung beantwortet ohne Worte,
   * was "links" heisst (in Fahrtrichtung) und welche Seite hoeher kommt.
   *
   * Bewusst schematisch: ein Rechteck mit Front oben, das Bett als Flaeche,
   * das Kopfende farbig. Ein maßstäbliches Bild waere eine Behauptung ueber
   * einen Grundriss, den wir nicht kennen. */
  var SK_ACCENT = "#2fb6c9";
  var SK_LINIE = "#6b7280";
  var SK_FLAECHE = "#243447";

  /* Das Fahrzeug von oben: Rechteck von (34,20) bis (126,100) im Feld
   * 160 x 120. Aussen bleibt Platz fuer die Marke, damit sie nie auf dem Bett
   * oder dem Tropfen liegt. Die Fahrtrichtung steht links oben, sonst kaeme
   * sie der Marke an der Frontkante in den Weg. */
  function skizzeRahmen(inhalt) {
    /* Die Fahrtrichtung steht als kleines Dreieck INNEN an der Oberkante und
     * nicht als Wort daneben: Aussen braucht jede Kante Platz fuer die Marke,
     * und ein Wort an der Frontkante lag genau darunter. Dass vorn oben ist,
     * sagt zusaetzlich der Hilfetext. */
    return '<svg viewBox="0 0 160 120" style="width:100%;max-width:260px;height:auto;' +
      'display:block;margin:8px auto 2px">' +
      '<rect x="34" y="20" width="92" height="80" rx="10" fill="#1b2430" stroke="' +
      SK_LINIE + '" stroke-width="2"/>' +
      '<polygon points="74,28 86,28 80,21" fill="#8b96a5"/>' + inhalt + "</svg>";
  }

  /* Die Marke sitzt AUSSERHALB des Fahrzeugs an der Kante, die hoeher kommt. */
  function skizzeMarke(x, y) {
    return '<circle cx="' + x + '" cy="' + y + '" r="9" fill="' + SK_ACCENT + '"/>' +
      '<text x="' + x + '" y="' + (y + 4) + '" text-anchor="middle" fill="#0d1117" ' +
      'font-size="13" font-weight="700">+</text>';
  }

  /* Wo eine Kante liegt: vorn oben, hinten unten, links links, rechts rechts.
   * Fehlt eine Richtung, bleibt die Mitte. */
  function skizzeOrt(text, aussen) {
    var x = 80, y = 60;
    if (text.indexOf("links") >= 0) x = aussen ? 18 : 48;
    if (text.indexOf("rechts") >= 0) x = aussen ? 142 : 112;
    if (text.indexOf("vorn") >= 0) y = aussen ? 10 : 30;
    if (text.indexOf("hinten") >= 0) y = aussen ? 112 : 90;
    return [x, y];
  }

  function bettSkizze(richtung) {
    var quer = richtung === "Kopf links" || richtung === "Kopf rechts";
    var bett = quer
      ? '<rect x="44" y="46" width="72" height="32" rx="6" fill="' + SK_FLAECHE +
        '" stroke="#37516b" stroke-width="1.5"/>'
      : '<rect x="58" y="32" width="44" height="56" rx="6" fill="' + SK_FLAECHE +
        '" stroke="#37516b" stroke-width="1.5"/>';
    var kissen =
      richtung === "Kopf vorn" ? '<rect x="58" y="32" width="44" height="15" rx="6" fill="' + SK_ACCENT + '"/>'
      : richtung === "Kopf hinten" ? '<rect x="58" y="73" width="44" height="15" rx="6" fill="' + SK_ACCENT + '"/>'
      : richtung === "Kopf links" ? '<rect x="44" y="46" width="15" height="32" rx="6" fill="' + SK_ACCENT + '"/>'
      : '<rect x="101" y="46" width="15" height="32" rx="6" fill="' + SK_ACCENT + '"/>';
    var ort = skizzeOrt(richtung, true);
    return skizzeRahmen(bett + kissen + skizzeMarke(ort[0], ort[1]));
  }

  /* Der Ablasspunkt ist der TIEFSTE Punkt - der Tropfen sitzt dort, die Marke
   * auf der Gegenseite. */
  function ablassSkizze(punkt) {
    var tief = skizzeOrt(punkt, false);
    var gegen = skizzeOrt(punkt
      .replace("vorn", "H").replace("hinten", "vorn").replace("H", "hinten")
      .replace("links", "R").replace("rechts", "links").replace("R", "rechts"), true);
    return skizzeRahmen(
      '<text x="' + tief[0] + '" y="' + (tief[1] + 6) + '" text-anchor="middle" ' +
      'font-size="18">💧</text>' + skizzeMarke(gegen[0], gegen[1]));
  }

  function settings() {
    settingInputs = {};
    schalterBoxen = {};

    // --- Fahrzeug ----------------------------------------------------------
    // Beim Wohnwagen misst dieselbe Zahl etwas anderes - deshalb die
    // Beschriftung mitfuehren statt sie fest hinzuschreiben.
    //
    // Und nur die Toleranz, die gerade gilt: Beide nebeneinander waeren zwei
    // Felder fuer eine Frage, von denen eines wirkungslos ist.
    var box = el('<div class="plan"><h2>' + t("kopf_fahrzeug") + "</h2></div>");
    var rows = [
      ["wheelbase", isCaravan() ? t("label_achse_stuetzrad") : t("label_radstand")],
      ["track", t("label_spurweite")],
      cfg.precise ? ["tolerance_deg", t("label_toleranz_grad")]
        : ["tolerance_cm", t("label_toleranz_cm")],
      ["wedge_step", t("label_keilstufe")]
    ];
    rows.forEach(function (r) { zahlZeile(box, r[0], r[1]); });
    box.appendChild(el('<div class="muted" style="margin-bottom:6px">' +
      (isCaravan() ? t("hilfe_masse_wagen") : t("hilfe_masse")) + "</div>"));

    /* Steht direkt unter der Toleranz, weil er aendert, was sie bedeutet.
     *
     * Der Kasten braucht eine eigene Breite: .set input ist 130 px breit,
     * das ergaebe ein Ankreuzfeld in der Groesse eines Eingabefelds. */
    var prow = el('<div class="set"><span>' + t("label_praezision") + "</span></div>");
    preciseBox = el('<input type="checkbox" style="width:26px;height:26px;padding:0">');
    preciseBox.checked = cfg.precise;
    preciseBox.onchange = function () { setPrecise(preciseBox.checked); };
    prow.appendChild(preciseBox);
    box.appendChild(prow);
    box.appendChild(el('<div class="muted" style="margin-bottom:6px">' +
      t("hilfe_praezision") + "</div>"));

    var vrow = el('<div class="set"><span>' + t("label_fahrzeugart") + "</span></div>");
    vehicleSelect = auswahl(["Wohnmobil", VEHICLE_CARAVAN], "fahrzeug",
      isCaravan() ? VEHICLE_CARAVAN : "Wohnmobil", setVehicle);
    vrow.appendChild(vehicleSelect);
    box.appendChild(vrow);

    var mrow = el('<div class="set"><span>' + t("label_womit") + "</span></div>");
    methodSelect = auswahl(["Auffahrkeile", METHOD_LIFT], "methode",
      cfg.method === "hebesystem" ? METHOD_LIFT : "Auffahrkeile", setMethod);
    mrow.appendChild(methodSelect);
    // Beim Wohnwagen ohne Bedeutung: laengs kurbelt man am Stuetzrad, quer
    // faehrt man auf. Ein Hebesystem gibt es dort nicht.
    if (!isCaravan()) {
      box.appendChild(mrow);
      box.appendChild(el('<div class="muted" style="margin-bottom:6px">' +
        t("hilfe_womit") + "</div>"));
    }

    settingsNote = el('<div class="muted" style="margin-top:8px"></div>');
    box.appendChild(settingsNote);

    // --- Anzeige -----------------------------------------------------------
    var anzeige = el('<div class="plan"><h2>' + t("kopf_anzeige") + "</h2></div>");
    zahlZeile(anzeige, "calm", t("label_anzeigeruhe"));
    anzeige.appendChild(el('<div class="muted" style="margin-bottom:10px">' +
      t("hilfe_anzeigeruhe") + "</div>"));
    zahlZeile(anzeige, "hold_percent", t("label_haltebereich"));
    anzeige.appendChild(el('<div class="muted">' + t("hilfe_haltebereich") + "</div>"));

    // --- Ziele -------------------------------------------------------------
    /* Die Zahlen hinter den Zielprofilen. Sie stehen hier und nicht bei der
     * Profilwahl auf der Hauptseite: Man richtet sie einmal ein und waehlt
     * danach nur noch.
     *
     * Eingestellt wird die RICHTUNG, nicht das Vorzeichen - siehe die
     * Begruendung bei den Skizzen weiter oben. */
    var ziele = el('<div class="plan"><h2>' + t("kopf_ziele") + "</h2></div>");
    ziele.appendChild(el('<div class="muted" style="margin-bottom:10px">' +
      t("hilfe_ziele") + "</div>"));

    ziele.appendChild(el('<div class="grouphead">' + t("kopf_schlafen") + "</div>"));
    var srow = el('<div class="set"><span>' + t("label_schlafrichtung") + "</span></div>");
    schlafSelect = auswahl(["Kopf vorn", "Kopf hinten", "Kopf links", "Kopf rechts"],
      "schlaf", cfg.sleep_dir, setSchlafrichtung);
    srow.appendChild(schlafSelect);
    ziele.appendChild(srow);
    zahlZeile(ziele, "sleep_height", t("label_kopfende"));
    ziele.appendChild(el(bettSkizze(cfg.sleep_dir)));
    ziele.appendChild(el('<div class="muted" style="margin-bottom:10px">' +
      t("hilfe_schlafen", { satz: schlafSatz() }) + "</div>"));

    ziele.appendChild(el('<div class="grouphead">' + t("kopf_ablassen") + "</div>"));
    var arow = el('<div class="set"><span>' + t("label_ablasspunkt") + "</span></div>");
    ablassSelect = auswahl(["vorn", "hinten", "links", "rechts",
      "vorn links", "vorn rechts", "hinten links", "hinten rechts"],
      "ablass", cfg.drain_point, setAblasspunkt);
    arow.appendChild(ablassSelect);
    ziele.appendChild(arow);
    zahlZeile(ziele, "drain_amount", t("label_ablassneigung"));
    ziele.appendChild(el(ablassSkizze(cfg.drain_point)));
    ziele.appendChild(el('<div class="muted">' +
      t("hilfe_ablassen", { satz: ablassSatz() }) + "</div>"));

    // --- Warnungen ---------------------------------------------------------
    var warnungen = el('<div class="plan"><h2>' + t("kopf_warnungen") + "</h2></div>");
    zahlZeile(warnungen, "tilt_limit", t("label_schraeglage"));
    warnungen.appendChild(el('<div class="muted" style="margin-bottom:10px">' +
      t("hilfe_schraeglage") + "</div>"));
    zahlZeile(warnungen, "fridge_minutes", t("label_kuehlschrank"));
    warnungen.appendChild(el('<div class="muted" style="margin-bottom:10px">' +
      t("hilfe_kuehlschrank") + "</div>"));
    zahlZeile(warnungen, "move_limit", t("label_lageaenderung"));
    warnungen.appendChild(el('<div class="muted" style="margin-bottom:10px">' +
      t("hilfe_lageaenderung") + "</div>"));
    zahlZeile(warnungen, "frost_limit", t("label_frost"));
    warnungen.appendChild(el('<div class="muted" style="margin-bottom:10px">' +
      t("hilfe_frost") + "</div>"));
    zahlZeile(warnungen, "guard_grace", t("label_karenzzeit"));
    warnungen.appendChild(el('<div class="muted">' + t("hilfe_karenzzeit") + "</div>"));

    // --- Gerät -------------------------------------------------------------
    /* Eigener Bereich, weil die Einbaulage das GERAET beschreibt und nicht das
     * Fahrzeug. Sie wird einmal beim Ankleben gesetzt und danach nie wieder.
     *
     * Sie MUSS hier stehen: Achszuordnung und Vorzeichen sind Substitutions
     * und brauchen einen Flash, die Einbaulage entscheidet der Nutzer im
     * Fahrzeug. Ohne diese Auswahl gaebe es sie nur in Home Assistant, und wer
     * das Geraet ohne Zentrale betreibt, kaeme an eine Einstellung nicht
     * heran, die ueber richtig und falsch herum entscheidet. */
    var geraet = el('<div class="plan"><h2>' + t("kopf_geraet") + "</h2></div>");
    var erow = el('<div class="set"><span>' + t("label_einbaulage") + "</span></div>");
    mountingSelect = auswahl(["Deckel oben", MOUNT_UNDER], "lage",
      cfg.mounting === "unten" ? MOUNT_UNDER : "Deckel oben", setMounting);
    erow.appendChild(mountingSelect);
    geraet.appendChild(erow);
    geraet.appendChild(el('<div class="muted" style="margin-top:8px;margin-bottom:10px">' +
      t("hilfe_einbaulage") + "</div>"));

    /* Selbstueberwachung. Steht hier, weil beides das GERAET betrifft und
     * nicht das Fahrzeug. */
    zahlZeile(geraet, "drift_limit", t("label_driftwarnung"));
    geraet.appendChild(el('<div class="muted" style="margin-bottom:10px">' +
      t("hilfe_driftwarnung") + "</div>"));
    zahlZeile(geraet, "temp_offset", t("label_temp_abgleich"));
    geraet.appendChild(el('<div class="muted" style="margin-bottom:10px">' +
      t("hilfe_temp_abgleich") + "</div>"));

    /* Leuchte und Summer. Sie stehen hier, weil sie das GERAET beschreiben,
     * und sie stehen UEBERHAUPT hier, weil dieses Geraet kein Display hat:
     * Wer es ohne Home Assistant betreibt, kaeme sonst an zwei Dinge nicht
     * heran, die im Wohnraum blinken und laermen. */
    schalterZeile(geraet, "status_led", t("label_status_led"));
    geraet.appendChild(el('<div class="muted" style="margin-bottom:10px">' +
      t("hilfe_status_led") + "</div>"));
    schalterZeile(geraet, "alarm_sound", t("label_alarmton"));
    geraet.appendChild(el('<div class="muted" style="margin-bottom:10px">' +
      t("hilfe_alarmton") + "</div>"));
    schalterZeile(geraet, "ramp_sound", t("label_auffahrton"));
    geraet.appendChild(el('<div class="muted">' + t("hilfe_auffahrton") + "</div>"));

    /* Mehrere Kaesten, ein Rueckgabewert: appendChild fuegt bei einem Fragment
     * alle Kinder ein, der Aufrufer bleibt unveraendert. */
    var beide = document.createDocumentFragment();
    beide.appendChild(box);
    beide.appendChild(anzeige);
    beide.appendChild(ziele);
    beide.appendChild(warnungen);
    beide.appendChild(geraet);
    return beide;
  }

  /* Was die Einstellung bedeutet, in einem Satz - unter der Skizze. Hier
   * steckt die Uebersetzung von Richtung in "welche Seite kommt hoch". */
  function schlafSatz() {
    var hoch = zahl(cfg.sleep_height, 1);
    var kopf = cfg.sleep_dir;
    var seite = kopf === "Kopf vorn" ? t("seite_front")
      : kopf === "Kopf hinten" ? t("seite_heck")
        : kopf === "Kopf links" ? t("seite_links") : t("seite_rechts");
    return Number(cfg.sleep_height) > 0
      ? t("satz_schlafen", { kopf: t("opt_schlaf_" + kennung(kopf)), seite: seite, cm: hoch })
      : t("satz_schlafen_null");
  }

  function ablassSatz() {
    var neig = zahl(cfg.drain_amount, 1);
    return Number(cfg.drain_amount) > 0
      ? t("satz_ablassen", {
        punkt: t("opt_ablass_" + kennung(cfg.drain_point)),
        gegen: t("gegen_" + kennung(cfg.drain_point)), cm: neig
      })
      : t("satz_ablassen_null");
  }

  /* Werte nachziehen, ohne die Felder anzufassen, in denen gerade getippt
   * wird. Sonst spränge der Text während der Eingabe zurück - genau der
   * Fehler, den die Trennung in live und fest beseitigen soll. */
  function syncSettings() {
    var focused = document.activeElement;
    for (var key in settingInputs) {
      var input = settingInputs[key];
      if (input !== focused) input.value = cfg[key];
    }
    if (methodSelect && methodSelect !== focused) {
      methodSelect.value = cfg.method === "hebesystem" ? METHOD_LIFT : "Auffahrkeile";
    }
    if (vehicleSelect && vehicleSelect !== focused) {
      vehicleSelect.value = isCaravan() ? VEHICLE_CARAVAN : "Wohnmobil";
    }
    if (schlafSelect && schlafSelect !== focused) schlafSelect.value = cfg.sleep_dir;
    if (ablassSelect && ablassSelect !== focused) ablassSelect.value = cfg.drain_point;
    if (mountingSelect && mountingSelect !== focused) {
      mountingSelect.value = cfg.mounting === "unten" ? MOUNT_UNDER : "Deckel oben";
    }
    if (preciseBox && preciseBox !== focused) preciseBox.checked = cfg.precise;
    for (var sk in schalterBoxen) {
      var sb = schalterBoxen[sk];
      if (sb !== focused) sb.checked = cfg[sk];
    }
    if (profileSelect && profileSelect !== focused) profileSelect.value = cfg.profile;
    // Nur, solange dort keine eigene Rueckmeldung steht - sonst ueberschriebe
    // der Zustand die Meldung "Gespeichert, das Geraet startet neu".
    if (mqttNote && !mqttNote.style.fontWeight) {
      mqttNote.textContent = mqttSatz();
    }
    /* Broker, Benutzer und Port zeigen, was im Gerät steht.
     *
     * Leere Felder bei laufender Verbindung sahen nicht nur nach "nichts
     * eingerichtet" aus, sie waren gefährlich: Wer nur den Benutzer ändern
     * wollte und speicherte, schickte ein leeres Brokerfeld mit - und leer
     * schaltet MQTT ab. Das Passwortfeld bleibt leer, dort heißt leer beim
     * Speichern "unverändert". */
    if (pushZiel && pushZiel !== focused) {
      pushZiel.value = findStateOf("text", "fernalarm_adresse") || "";
    }
    if (mqttBroker && mqttBroker !== focused) {
      mqttBroker.value = findStateOf("text", "mqtt_broker") || "";
    }
    if (mqttUser && mqttUser !== focused) {
      mqttUser.value = findStateOf("text", "mqtt_benutzer") || "";
    }
    if (mqttPort && mqttPort !== focused) {
      mqttPort.value = findStateOf("number", "mqtt_port") || "";
    }
    if (settingsNote) {
      settingsNote.textContent = writeError ? writeError
        : state.ready ? t("werte_im_geraet") : t("warte_auf_geraet");
      settingsNote.style.color = writeError ? "#ff7a7a" : "";
      settingsNote.style.fontWeight = writeError ? "700" : "";
    }
    if (versionNote) {
      versionNote.innerHTML = t("laufende_fassung",
        { version: "<b>" + (findState("firmware_version") || t("unbekannt")) + "</b>" });
    }
  }

  /* Überschriften je Bereich. Das Gerät liefert seine Kennungen als
   * "<bereich>-<name>" (je nach Fassung auch mit Schrägstrich), sonst nichts
   * Gegliedertes - eine Liste aus 25 Zeilen ohne Ordnung liest niemand. */
  var DOMAIN_KEYS = {
    sensor: "bereich_messwerte",
    binary_sensor: "bereich_zustaende",
    text_sensor: "bereich_informationen",
    number: "bereich_einstellwerte",
    select: "bereich_auswahl",
    text: "bereich_texteingaben",
    switch: "bereich_schalter",
    button: "bereich_tasten",
    update: "bereich_software"
  };
  var DOMAIN_ORDER = ["sensor", "binary_sensor", "text_sensor", "number",
    "select", "text", "switch", "button", "update"];

  /*
   * Technik zeigt Ablesewerte, keine Bedienelemente. Drei Gründe:
   *
   *   button - Aktionen, keine Werte. Als Zeile mit Zustand sinnlos, und
   *            jede davon gibt es an der passenden Stelle als echten Knopf.
   *   text   - hier stünde das WLAN-Passwort im Klartext in einer Liste.
   *   update - meldet "unknown", solange nicht geprüft wurde. Direkt unter
   *            unserer korrekten Versionsanzeige gelesen wirkt das wie ein
   *            Widerspruch, obwohl beides stimmt.
   *
   * number und select sind die Fahrzeugmaße - die stehen auf der Anzeige
   * und wären hier eine zweite Darstellung derselben Sache.
   */
  var TECH_DOMAINS = ["sensor", "binary_sensor", "text_sensor"];

  function splitId(id) {
    var cut = id.search(/[-\/]/);
    return cut < 0 ? ["", id] : [id.slice(0, cut), id.slice(cut + 1)];
  }

  /* Aus dem Anzeigenamen die Kennung bilden, mit der diese Seite sucht.
   *
   * Das Geraet nennt seine Entitaeten seit ESPHome 2026.8 beim NAMEN:
   * "sensor/Neigung Pitch" statt "sensor-neigung_pitch" (set_json_id in
   * web_server.cpp). Gesucht wird hier aber weiter mit Teilstuecken wie
   * "neigung_pitch" - die stehen in IDS und sind gegen Umlaute abgesichert.
   *
   * Die Umrechnung ist dieselbe, die ESPHome frueher selbst gemacht hat:
   * klein schreiben, alles ausser a-z, 0-9 und _ zu _ machen. Aus "Wächter"
   * wird "w_chter", und das Teilstueck "chter" trifft weiterhin.
   *
   * Kommt schon das alte Format herein, aendert sich dabei nichts - es
   * besteht ohnehin nur aus erlaubten Zeichen. Die Seite versteht damit
   * beide Faelle, ohne sie unterscheiden zu muessen. */
  function objektKennung(text) {
    return String(text || "").toLowerCase().replace(/[^a-z0-9_]/g, "_");
  }

  /* Fehlt der Name, aus der Kennung einen lesbaren machen:
   * "neigung_pitch" wird zu "Neigung pitch". Besser als die rohe Kennung. */
  function prettify(objectId) {
    var wort = objectId.replace(/_/g, " ").trim();
    return wort.charAt(0).toUpperCase() + wort.slice(1);
  }

  function renderTechTable(target) {
    var box = el('<div class="plan"><h2>' + t("kopf_technik") + "</h2></div>");
    var ids = Object.keys(state.seen);

    if (!ids.length) {
      box.appendChild(el('<div class="muted">' + t("noch_keine_daten") + "</div>"));
      target.appendChild(box);
      return;
    }

    var groups = {};
    ids.forEach(function (id) {
      var parts = splitId(id);
      var domain = parts[0];
      if (TECH_DOMAINS.indexOf(domain) < 0) return;
      (groups[domain] = groups[domain] || []).push({
        label: state.seen[id].name || prettify(parts[1]),
        value: state.seen[id].state
      });
    });

    if (!Object.keys(groups).length) {
      box.appendChild(el('<div class="muted">' + t("noch_keine_messwerte") + "</div>"));
      target.appendChild(box);
      return;
    }

    // Bekannte Bereiche in fester Reihenfolge, alles Übrige hinten dran.
    var order = DOMAIN_ORDER.filter(function (d) { return groups[d]; });
    Object.keys(groups).sort().forEach(function (d) {
      if (order.indexOf(d) < 0) order.push(d);
    });

    order.forEach(function (domain) {
      box.appendChild(el('<div class="grouphead">' +
        (DOMAIN_KEYS[domain] ? t(DOMAIN_KEYS[domain]) : prettify(domain)) + "</div>"));
      var table = document.createElement("table");
      var body = document.createElement("tbody");
      groups[domain]
        .sort(function (a, b) { return String(a.label).localeCompare(String(b.label), sprache); })
        .forEach(function (row) {
          var tr = document.createElement("tr");
          tr.appendChild(cell(row.label, null));
          tr.appendChild(cell(
            row.value === "" || row.value === undefined || row.value === null
              ? "–" : row.value, "v"));
          body.appendChild(tr);
        });
      table.appendChild(body);
      box.appendChild(table);
    });

    target.appendChild(box);
  }

  /* Sprache. Steht unter Technik, weil sie einmal gesetzt wird und danach
   * nicht mehr - und weil sie zum Betrachter gehoert, nicht zum Fahrzeug.
   * Vorausgewaehlt ist, was das Handy meldet. */
  function spracheBox() {
    var box = el('<div class="plan"><h2>' + t("kopf_sprache") + "</h2></div>");
    var row = el('<div class="set" style="border-bottom:0"><span>' +
      t("label_sprache") + "</span></div>");
    var sel = el('<select><option value="de">Deutsch</option>' +
      '<option value="en">English</option></select>');
    sel.value = sprache;
    sel.onchange = function () { spracheSetzen(sel.value); };
    row.appendChild(sel);
    box.appendChild(row);
    box.appendChild(el('<div class="muted" style="margin-top:8px">' +
      t("hilfe_sprache") + "</div>"));
    return box;
  }

  var versionNote = null;

  /* Aktualisierung von Hand - der Weg für die Betriebsart ohne Home
   * Assistant. Ausgelöst wird die Taste im Gerät, die ihrerseits die neue
   * Firmware von GitHub holt. Für Update-Entitäten gibt es keinen
   * dokumentierten REST-Endpunkt, für Tasten schon. */
  function softwareBox() {
    var up = el('<div class="plan"><h2>' + t("kopf_software") + "</h2></div>");
    versionNote = el('<div class="muted"></div>');
    up.appendChild(versionNote);

    var btn = el('<button class="act ghost" style="margin-top:10px"></button>');
    btn.textContent = t("update_pruefen");
    btn.onclick = function () {
      if (!window.confirm(t("update_frage"))) return;
      btn.disabled = true;
      btn.textContent = t("update_laeuft");
      press("firmware_aktualisieren", function () {
        btn.textContent = t("update_neustart");
      });
    };
    up.appendChild(btn);
    up.appendChild(el('<div class="muted" style="margin-top:8px">' +
      t("hilfe_update") + "</div>"));

    /* Weg ohne Internet: Datei vom Handy hochladen. Möglich durch
     * "ota: platform: web_server" in der Firmware.
     *
     * ACHTUNG: ESPHome dokumentiert den Endpunkt dieses Formulars nicht -
     * /update mit dem Feldnamen "file" ist der übliche Weg, aber ungeprüft.
     * Schlägt es fehl, sagt die Seite das ausdrücklich statt stumm zu
     * bleiben, und nennt den Ausweg. Beim ersten echten Build prüfen. */
    var form = el('<div style="margin-top:14px"></div>');
    form.appendChild(el('<div class="muted">' + t("datei_aufspielen_hinweis") + "</div>"));
    var file = el('<input type="file" accept=".bin" style="margin-top:8px;width:100%">');
    var send = el('<button class="act ghost" style="margin-top:8px"></button>');
    send.textContent = t("datei_aufspielen");
    var note = el('<div class="muted" style="margin-top:8px"></div>');
    send.onclick = function () {
      if (!file.files || !file.files.length) { note.textContent = t("erst_datei"); return; }
      send.disabled = true;
      note.textContent = t("uebertrage");
      var body = new FormData();
      body.append("file", file.files[0]);
      var req = new XMLHttpRequest();
      req.open("POST", "/update", true);
      req.onload = function () {
        note.textContent = req.status >= 200 && req.status < 300
          ? t("uebertragen_neustart")
          : t("uebertragen_fehler", { status: req.status });
        send.disabled = false;
      };
      req.onerror = function () {
        note.textContent = t("keine_verbindung");
        send.disabled = false;
      };
      req.send(body);
    };
    form.appendChild(file);
    form.appendChild(send);
    form.appendChild(note);
    up.appendChild(form);
    return up;
  }

  /* WLAN-Einrichtung. Übernimmt die Aufgabe des Captive Portals, das dafür
   * entfällt: Es hätte im eigenen Netz jede Seitenanfrage abgefangen und
   * die Wasserwaage unerreichbar gemacht.
   *
   * Freiwillig - ohne WLAN funktioniert alles außer den automatischen
   * Updates. Deshalb steht es unter Technik und nicht auf der Anzeige. */
  function wifiSetup() {
    var box = el('<div class="plan"><h2>' + t("kopf_wlan") + "</h2></div>");
    box.appendChild(el('<div class="muted">' + t("hilfe_wlan") + "</div>"));

    var ssid = el('<input type="text" style="width:100%;margin-top:10px">');
    ssid.placeholder = t("platzhalter_netzname");
    var pass = el('<input type="password" style="width:100%;margin-top:8px">');
    pass.placeholder = t("platzhalter_passwort");
    var btn = el('<button class="act ghost" style="margin-top:10px"></button>');
    btn.textContent = t("wlan_speichern");
    // white-space: pre-line, damit der Absatz im Erfolgstext wirkt.
    var note = el('<div class="muted" style="margin-top:10px;line-height:1.5;white-space:pre-line"></div>');

    /* Rückmeldung deutlich, nicht als graue Randnotiz: Nach dem Neustart
     * verschwindet dieses Netz, und die Seite kann dann nichts mehr sagen.
     * Was hier steht, ist das Letzte, was der Nutzer sieht. */
    function say(text, kind) {
      note.textContent = text;
      note.style.color = kind === "bad" ? "#ff7a7a" : kind === "good" ? "#37d67a" : "#cfd6de";
      note.style.fontWeight = kind ? "700" : "400";
    }

    /* Wartet, bis das Gerät den gespeicherten Namen über den Ereignisstrom
     * zurückmeldet. Das ist der einzige echte Beweis, dass die Eingabe
     * angekommen ist - eine erfolgreiche HTTP-Antwort sagt nur, dass die
     * Anfrage entgegengenommen wurde. */
    function awaitEcho(expected, timeoutMs, done) {
      var waited = 0;
      var timer = window.setInterval(function () {
        // Auch hier über Teilstring statt fester Kennung - siehe objectId().
        if (findState("wlan_name") === expected) {
          window.clearInterval(timer);
          done(true);
          return;
        }
        waited += 300;
        if (waited >= timeoutMs) { window.clearInterval(timer); done(false); }
      }, 300);
    }

    btn.onclick = function () {
      if (!ssid.value) { say(t("netzname_fehlt"), "bad"); return; }
      btn.disabled = true;
      say(t("uebertrage"));

      var pName = pathFor("text", "wlan_name");
      var pPass = pathFor("text", "wlan_pass");
      var pSave = pathFor("button", "wlan_speichern");

      if (!pName || !pPass || !pSave) {
        return fail(t("keine_wlan_felder"));
      }

      // Nacheinander, nicht gleichzeitig: der Knopf im Gerät liest beide
      // Felder, sie müssen also vorher angekommen sein.
      setText(pName, ssid.value, function (ok1) {
        if (!ok1) return fail(t("name_nicht_angenommen", { pfad: pName }));
        setText(pPass, pass.value, function (ok2) {
          if (!ok2) return fail(t("passwort_nicht_angenommen", { pfad: pPass }));
          say(t("warte_bestaetigung"));
          awaitEcho(ssid.value, 5000, function (confirmed) {
            if (!confirmed) return fail(t("keine_bestaetigung"));
            post(pSave + "/press");
            say(t("wlan_gespeichert", { netz: ssid.value }), "good");
          });
        });
      });

      function fail(text) {
        say(text + " " + t("notfalls_dashboard"), "bad");
        btn.disabled = false;
      }
    };

    box.appendChild(ssid);
    box.appendChild(pass);
    box.appendChild(btn);
    box.appendChild(note);

    /* Eigenes Netz abschließen - freiwillig.
     *
     * Ab Werk ist das Netz offen, damit niemand vor einem Gerät steht, in das
     * er nicht hineinkommt. Wer nicht will, dass jeder in Funkreichweite die
     * Einstellungen erreicht, vergibt hier ein Passwort. */
    box.appendChild(el('<div class="grouphead" style="margin-top:22px">' +
      t("kopf_eigenes_netz") + "</div>"));
    var anote = el('<div class="muted"></div>');
    /* Der Zustand kommt aus den Statuswerten, nicht aus dem deutschen Satz
     * des Geraets - siehe statusWerte(). */
    anote.innerHTML = t(statusWerte().n === "passwort"
      ? "hilfe_netz_geschuetzt" : "hilfe_netz_offen");
    box.appendChild(anote);

    var apPass = el('<input type="password" style="width:100%;margin-top:10px">');
    apPass.placeholder = t("platzhalter_netz_passwort");
    var apBtn = el('<button class="act ghost" style="margin-top:8px"></button>');
    apBtn.textContent = t("netz_passwort_speichern");
    var apNote = el('<div class="muted" style="margin-top:10px;line-height:1.5;white-space:pre-line"></div>');

    function apSay(text, kind) {
      apNote.textContent = text;
      apNote.style.color = kind === "bad" ? "#ff7a7a" : kind === "good" ? "#37d67a" : "#cfd6de";
      apNote.style.fontWeight = kind ? "700" : "400";
    }

    apBtn.onclick = function () {
      /* Dieselbe Grenze wie im Gerät, hier nur früher: WPA2 kennt nichts
       * zwischen offen und acht Zeichen. Wer es hier erfährt, muss nicht
       * erst einen Neustart abwarten, um zu merken, dass nichts passiert
       * ist. */
      if (apPass.value && apPass.value.length < 8) {
        apSay(t("acht_zeichen"), "bad");
        return;
      }
      var offen = !apPass.value;
      var pText = pathFor("text", "netz_passwort_neu");
      var pSave = pathFor("button", "netz_passwort_speichern");
      if (!pText || !pSave) {
        apSay(t("kennt_einstellung_nicht"), "bad");
        return;
      }
      apBtn.disabled = true;
      apSay(t("uebertrage"));
      setText(pText, apPass.value, function (ok) {
        if (!ok) {
          apSay(t("eingabe_nicht_angenommen"), "bad");
          apBtn.disabled = false;
          return;
        }
        post(pSave + "/press");
        apPass.value = "";
        apSay(t(offen ? "netz_wieder_offen" : "netz_jetzt_geschuetzt"), "good");
      });
    };

    box.appendChild(apPass);
    box.appendChild(apBtn);
    box.appendChild(apNote);

    /* MQTT - die Tür zu fremden Systemen.
     *
     * Steht hier und nicht unter "Anzeige", weil es eine Netzsache ist: Wer
     * hier landet, sucht Verbindungen. Leer lassen und speichern schaltet es
     * wieder ab; wer MQTT nicht braucht, merkt nichts davon. */
    box.appendChild(el('<div class="grouphead" style="margin-top:22px">MQTT</div>'));
    box.appendChild(el('<div class="muted">' + t("hilfe_mqtt") + "</div>"));

    var mBroker = el('<input type="text" style="width:100%;margin-top:10px">');
    mBroker.placeholder = t("platzhalter_broker");
    var mPort = el('<input type="number" style="width:100%;margin-top:8px">');
    mPort.placeholder = t("platzhalter_port");
    var mUser = el('<input type="text" style="width:100%;margin-top:8px">');
    mUser.placeholder = t("platzhalter_benutzer");
    var mPass = el('<input type="password" style="width:100%;margin-top:8px">');
    mPass.placeholder = t("platzhalter_mqtt_passwort");
    var mBtn = el('<button class="act ghost" style="margin-top:8px"></button>');
    mBtn.textContent = t("mqtt_speichern");
    var mNote = el('<div class="muted" style="margin-top:10px;line-height:1.5;white-space:pre-line"></div>');

    function mSay(text, kind) {
      mNote.textContent = text;
      mNote.style.color = kind === "bad" ? "#ff7a7a" : kind === "good" ? "#37d67a" : "#cfd6de";
      mNote.style.fontWeight = kind ? "700" : "400";
    }

    /* Den aktuellen Zustand zeigen, statt den Nutzer raten zu lassen. Das
     * Gerät meldet ihn als Textwert - Adresse ja, Passwort nein.
     *
     * Der Verweis bleibt in mqttNote stehen, damit syncSettings() ihn bei
     * jeder Meldung des Geräts nachziehen kann: Nach dem Speichern und
     * Neustart soll dort von selbst "verbunden" erscheinen. */
    mqttNote = mNote;
    mqttBroker = mBroker;
    mqttUser = mUser;
    mqttPort = mPort;
    mSay(mqttSatz());

    mBtn.onclick = function () {
      var pB = pathFor("text", "mqtt_broker");
      var pU = pathFor("text", "mqtt_benutzer");
      var pP = pathFor("text", "mqtt_passwort");
      var pPort = pathFor("number", "mqtt_port");
      var pSave = pathFor("button", "mqtt_speichern");
      if (!pB || !pSave) {
        mSay(t("kennt_mqtt_nicht"), "bad");
        return;
      }
      mBtn.disabled = true;
      mSay(t("uebertrage"));

      /* Der Reihe nach, nicht gleichzeitig: Das Gerät nimmt die Felder
       * einzeln entgegen, und der Knopf darf erst drücken, wenn alle
       * angekommen sind - sonst speichert er einen halben Stand. */
      var offen = [];
      offen.push([pB, mBroker.value]);
      if (pU) offen.push([pU, mUser.value]);
      if (pP) offen.push([pP, mPass.value]);

      var i = 0;
      (function weiter(ok) {
        if (ok === false) {
          mSay(t("eingabe_nicht_angenommen"), "bad");
          mBtn.disabled = false;
          return;
        }
        if (i < offen.length) {
          var f = offen[i++];
          setText(f[0], f[1], weiter);
          return;
        }
        if (pPort && mPort.value) post(pPort + "/set?value=" + encodeURIComponent(mPort.value));
        post(pSave + "/press");
        mPass.value = "";
        mSay(t(mBroker.value ? "mqtt_gespeichert" : "mqtt_aus"), "good");
      })(true);
    };

    box.appendChild(mBroker);
    box.appendChild(mPort);
    box.appendChild(mUser);
    box.appendChild(mPass);
    box.appendChild(mBtn);
    box.appendChild(mNote);

    /* Fernalarm.
     *
     * Steht hinter MQTT, weil beides dieselbe Frage beantwortet: Wie kommt
     * eine Meldung aus dem Fahrzeug heraus? MQTT ist der Weg fuer die, die
     * ohnehin ein System betreiben - der Fernalarm ist der Weg fuer alle
     * anderen.
     *
     * Ohne ihn stimmt der wichtigste Satz ueber den Waechter nur mit
     * Einschraenkung: Er erreicht sonst nur, wer im selben Netz ist - und
     * das ist genau der, der nicht gewarnt werden muss. */
    box.appendChild(el('<div class="grouphead" style="margin-top:22px">' +
      t("kopf_fernalarm") + "</div>"));
    box.appendChild(el('<div class="muted" style="line-height:1.5">' +
      t("hilfe_fernalarm") + "</div>"));

    var pZiel = el('<input type="text" style="width:100%;margin-top:10px">');
    pZiel.placeholder = t("platzhalter_fernalarm");
    var pBtn = el('<button class="act ghost" style="margin-top:8px"></button>');
    pBtn.textContent = t("fernalarm_speichern");
    var pTestBtn = el('<button class="act ghost" style="margin-top:8px"></button>');
    pTestBtn.textContent = t("fernalarm_testen");
    var pNote = el('<div class="muted" style="margin-top:10px;line-height:1.5;white-space:pre-line"></div>');

    function pSay(text, kind) {
      pNote.textContent = text;
      pNote.style.color = kind === "bad" ? "#ff7a7a" : kind === "good" ? "#37d67a" : "#cfd6de";
      pNote.style.fontWeight = kind ? "700" : "400";
    }

    pushZiel = pZiel;
    pZiel.value = findStateOf("text", "fernalarm_adresse") || "";

    pBtn.onclick = function () {
      var pfad = pathFor("text", "fernalarm_adresse");
      var pSpeichern = pathFor("button", "fernalarm_speichern");
      if (!pfad || !pSpeichern) {
        pSay(t("kennt_einstellung_nicht"), "bad");
        return;
      }
      pBtn.disabled = true;
      pSay(t("uebertrage"));
      setText(pfad, pZiel.value, function (ok) {
        if (!ok) { pBtn.disabled = false; pSay(t("eingabe_nicht_angenommen"), "bad"); return; }
        press("fernalarm_speichern", function (status) {
          pBtn.disabled = false;
          if (status < 200 || status >= 300) { pSay(t("eingabe_nicht_angenommen"), "bad"); return; }
          pSay(t(pZiel.value ? "fernalarm_gespeichert" : "fernalarm_aus"), "good");
        });
      });
    };

    /* Der Test ist kein Beiwerk: Ein Alarmweg, den niemand ausprobiert hat,
     * ist keiner. Wer sich darauf verlaesst und erst im Ernstfall merkt, dass
     * die Adresse einen Tippfehler hat, ist schlechter dran als ohne.
     *
     * ERST SPEICHERN, DANN SENDEN. Das Geraet testet die GESPEICHERTE
     * Adresse - wer im Feld etwas korrigiert und gleich auf Test drueckt,
     * pruefte sonst den alten Stand und bekaeme ein Ergebnis, das nichts mit
     * dem zu tun hat, was er vor sich sieht. Genau das ist am 23.09.2026
     * passiert und hat eine Runde gekostet. */
    pTestBtn.onclick = function () {
      var pfad = pathFor("text", "fernalarm_adresse");
      var pSpeichern = pathFor("button", "fernalarm_speichern");
      var pTesten = pathFor("button", "fernalarm_testen");
      if (!pfad || !pSpeichern || !pTesten) {
        pSay(t("kennt_einstellung_nicht"), "bad");
        return;
      }
      pTestBtn.disabled = true;
      pSay(t("fernalarm_test_laeuft"));
      setText(pfad, pZiel.value, function (ok) {
        if (!ok) { pTestBtn.disabled = false; pSay(t("eingabe_nicht_angenommen"), "bad"); return; }
        press("fernalarm_speichern", function (gespeichert) {
          if (gespeichert < 200 || gespeichert >= 300) {
            pTestBtn.disabled = false;
            pSay(t("eingabe_nicht_angenommen"), "bad");
            return;
          }
          press("fernalarm_testen", function (status) {
            pTestBtn.disabled = false;
            pSay(t(status >= 200 && status < 300
              ? "fernalarm_test_gesendet" : "eingabe_nicht_angenommen"),
              status >= 200 && status < 300 ? "good" : "bad");
          });
        });
      });
    };

    box.appendChild(pZiel);
    box.appendChild(pBtn);
    box.appendChild(pTestBtn);
    box.appendChild(pNote);

    /* Werksreset. Steht bewusst hier unten und nicht bei den Bedienelementen
     * oben - er löscht WLAN, Kalibrierung und Fahrzeugmaße auf einmal. */
    box.appendChild(el('<div class="grouphead" style="margin-top:22px">' +
      t("kopf_zuruecksetzen") + "</div>"));
    var rnote = el('<div class="muted"></div>');
    rnote.textContent = t("hilfe_zuruecksetzen");
    box.appendChild(rnote);

    var reset = el('<button class="act ghost" style="margin-top:10px"></button>');
    reset.textContent = t("zuruecksetzen");
    reset.onclick = function () {
      /* Die Absaetze der Rueckfrage standen hier als "\n" im Quelltext und
       * erschienen deshalb als Zeichen im Dialog. Die Uebersetzung bringt sie
       * als echte Zeilenumbrueche mit. */
      if (!window.confirm(t("zuruecksetzen_frage"))) return;
      reset.disabled = true;
      reset.textContent = t("zuruecksetzen_laeuft");
      press("werkseinstellungen", function () {
        rnote.textContent = t("zurueckgesetzt");
      });
    };
    box.appendChild(reset);
    return box;
  }

  /* Erwartet den fertigen Pfad aus pathFor(), nicht die Kennung - der Pfad
   * kommt vom Gerät und wird hier nicht mehr zusammengesetzt. */
  function setText(path, value, done) {
    var req = new XMLHttpRequest();
    req.open("POST", path + "/set?value=" + encodeURIComponent(value), true);
    req.onload = function () { done(req.status >= 200 && req.status < 300); };
    req.onerror = function () { done(false); };
    req.send();
  }

  function findState(needle) {
    for (var id in state.seen) {
      if (objektKennung(splitId(id)[1]).indexOf(needle) >= 0) {
        return state.seen[id].state;
      }
    }
    return null;
  }

  /* Wie findState, aber auf einen Bereich eingegrenzt und mit Vorrang für den
   * exakten Treffer.
   *
   * Nötig, seit "mqtt" in fünf Kennungen steckt: mqtt_broker, mqtt_benutzer,
   * mqtt_passwort, mqtt_port und der Zustandssensor mqtt selbst. findState
   * gäbe das erstbeste zurück - also mit einiger Wahrscheinlichkeit den Inhalt
   * eines Eingabefelds statt des gesuchten Zustands. */
  function findStateOf(domain, needle) {
    var hit = findEntity(domain, needle);
    return hit ? state.seen[hit.id].state : null;
  }

  /* Die tatsächliche Entität aus dem Ereignisstrom holen, statt ihre Kennung
   * fest hinzuschreiben.
   *
   * ESPHome bildet sie aus dem Namen ("WLAN Name" -> "wlan_name"), aber die
   * Regel hat sich zwischen Fassungen schon geändert, und ein falscher Name
   * scheitert stumm mit 404. Das Gerät meldet seine Kennungen ohnehin - also
   * fragen wir es, statt zu raten.
   *
   * Ein exakter Treffer geht vor. Das ist keine Feinheit: "toleranz" steckt
   * auch in "toleranz_genau", und ein Schreibzugriff, der im falschen Feld
   * landet, verstellt stillschweigend eine andere Einstellung. Gibt es keinen
   * exakten Treffer, gewinnt der KÜRZESTE Teiltreffer - das ist der Name, der
   * am wenigsten über die gesuchte Kennung hinaus enthält. */
  function findEntity(domain, needle) {
    var exact = null, best = null;
    for (var id in state.seen) {
      var parts = splitId(id);
      if (parts[0] !== domain) continue;
      // obj ist der ROHE zweite Teil - er geht in die Schreibadresse.
      // kennung ist die normalisierte Form, mit der hier gesucht wird.
      var treffer = { id: id, obj: parts[1], kennung: objektKennung(parts[1]) };
      if (treffer.kennung === needle) { exact = treffer; break; }
      if (treffer.kennung.indexOf(needle) >= 0 &&
          (!best || treffer.kennung.length < best.kennung.length)) {
        best = treffer;
      }
    }
    return exact || best;
  }

  function objectId(domain, needle, fallback) {
    var hit = findEntity(domain, needle);
    // Der Rückfallwert greift nur, solange noch nichts empfangen wurde.
    return hit ? hit.kennung : fallback;
  }

  /* Den REST-Pfad einer Entität, wie das Gerät ihn selbst angibt.
   *
   * Rückgabe etwa "/number/radstand". Findet sich nichts, kommt null - dann
   * wird gar nicht erst geschrieben, statt auf gut Glück eine Adresse zu
   * bauen und den 404 zu verschlucken. */
  function pathFor(domain, needle) {
    var hit = findEntity(domain, needle);
    if (!hit) return null;
    /* name_id gab es bis 2026.7 und war der fertige Pfad. Faellt es weg,
     * bauen wir ihn selbst: Bereich und Anzeigename, wie match_entity ihn
     * vergleicht (this->id == entity->get_name()). Kodieren ist Pflicht -
     * die Namen enthalten Leerzeichen und Umlaute; das Geraet dekodiert
     * sie (url_decode in web_server_idf). */
    var nid = state.seen[hit.id].name_id;
    return nid ? "/" + nid : "/" + domain + "/" + encodeURIComponent(hit.obj);
  }

  // -- Gerät ---------------------------------------------------------------

  /* Auch hier der Pfad vom Gerät. Kennt es die Taste nicht, wird nicht
   * blind gedrückt - der Aufrufer erfährt es über einen Status 0. */
  function press(needle, done) {
    var path = pathFor("button", needle);
    if (!path) { if (done) done(0); return; }
    post(path + "/press", done);
  }

  function connect() {
    var src = new EventSource("/events");
    src.addEventListener("state", function (ev) {
      var data;
      try { data = JSON.parse(ev.data); } catch (e) { return; }
      if (!data || !data.id) return;
      /* ZUSAMMENFÜHREN, NICHT ERSETZEN - und das ist der ganze Punkt.
       *
       * Das Gerät schickt beim Verbinden einen vollständigen Bericht MIT
       * "name" und danach nur noch knappe Aktualisierungen OHNE. Wer den
       * Eintrag bei jeder Aktualisierung neu anlegt, verliert den Namen mit
       * dem ersten Messwert - und die Technik-Liste fiel auf prettify()
       * zurück, das aus "wlan_signal" ein "Wlan signal" macht und aus
       * "st__tzrad" ein "St tzrad". Was wie ein Haufen Tippfehler aussah,
       * war genau das.
       *
       * name_id ist der REST-Pfad, den das Gerät selbst nennt - etwa
       * "sensor/accel_z" für /sensor/accel_z. Genau so übernehmen, nicht aus
       * dem Namen bilden: Beide bisherigen Versuche, ihn zu erraten, endeten
       * in 404. Auch er kommt nur im ersten Bericht und muss bleiben. */
      var bekannt = state.seen[data.id] || {};
      state.seen[data.id] = {
        name_id: data.name_id || bekannt.name_id || null,
        name: data.name || bekannt.name || null,
        state: data.state
      };

      /* Über Teilstrings statt die volle Kennung: dann hält die Seite auch,
       * wenn jemand dem Gerät einen anderen Namen gibt.
       *
       * Verglichen wird die NORMALISIERTE Kennung. Das Gerät schickt seit
       * ESPHome 2026.8 "sensor/Neigung Pitch"; ohne die Umrechnung trifft
       * hier kein einziges Teilstück, und die Seite bleibt vollständig
       * leer - ohne Fehlermeldung, weil nichts abstürzt. Genau das ist am
       * 22.09.2026 stundenlang passiert. */
      var id = objektKennung(splitId(data.id)[1]);
      if (id.indexOf("neigung_pitch") >= 0) state.pitch = num(data.value);
      else if (id.indexOf("neigung_roll") >= 0) state.roll = num(data.value);
      else if (id.indexOf("in_bewegung") >= 0) state.motion = data.value === true || data.state === "ON";
      else if (id.indexOf(IDS.wheelbase) >= 0) { cfg.wheelbase = num(data.value); state.ready = true; }
      else if (id.indexOf(IDS.track) >= 0) cfg.track = num(data.value);
      // Die Gradtoleranz MUSS vor der Zentimetertoleranz stehen: "toleranz"
      // steckt auch in "toleranz_genau", die umgekehrte Reihenfolge schriebe
      // den Gradwert in die Zentimeterangabe.
      else if (id.indexOf(IDS.tolerance_deg) >= 0) cfg.tolerance_deg = num(data.value);
      else if (id.indexOf(IDS.tolerance_cm) >= 0) cfg.tolerance_cm = num(data.value);
      else if (id.indexOf(IDS.wedge_step) >= 0) cfg.wedge_step = num(data.value);
      else if (id.indexOf(IDS.tilt_limit) >= 0) cfg.tilt_limit = num(data.value);
      else if (id.indexOf(IDS.move_limit) >= 0) cfg.move_limit = num(data.value);
      else if (id.indexOf(IDS.guard_grace) >= 0) cfg.guard_grace = num(data.value);
      else if (id.indexOf(IDS.fridge_minutes) >= 0) cfg.fridge_minutes = num(data.value);
      // Erst die Zahl, dann die Auswahl: "ablasspunkt" steckt auch in
      // "neigung_zum_ablasspunkt".
      else if (id.indexOf(IDS.sleep_height) >= 0) cfg.sleep_height = num(data.value);
      else if (id.indexOf(IDS.drain_amount) >= 0) cfg.drain_amount = num(data.value);
      else if (id.indexOf(IDS.target_long) >= 0) cfg.target_long = num(data.value);
      else if (id.indexOf(IDS.target_lat) >= 0) cfg.target_lat = num(data.value);
      else if (id.indexOf(IDS.drift_limit) >= 0) cfg.drift_limit = num(data.value);
      else if (id.indexOf(IDS.temp_offset) >= 0) cfg.temp_offset = num(data.value);
      else if (id.indexOf(IDS.frost_limit) >= 0) cfg.frost_limit = num(data.value);
      else if (id.indexOf(IDS.profile) >= 0) {
        // Wie bei der Fahrzeugart: Das Profil formt die Bedienelemente, da
        // reicht das Nachziehen der Messwerte nicht.
        if (data.state !== cfg.profile) { cfg.profile = data.state; render(); return; }
      }
      else if (id.indexOf(IDS.status_led) >= 0) cfg.status_led = data.value === true || data.state === "ON";
      else if (id.indexOf(IDS.alarm_sound) >= 0) cfg.alarm_sound = data.value === true || data.state === "ON";
      else if (id.indexOf(IDS.ramp_sound) >= 0) cfg.ramp_sound = data.value === true || data.state === "ON";
      else if (id.indexOf(IDS.calm) >= 0) cfg.calm = num(data.value);
      else if (id.indexOf(IDS.hold_percent) >= 0) cfg.hold_percent = num(data.value);
      else if (id.indexOf(IDS.precise) >= 0) {
        // Wie bei der Fahrzeugart: Der Modus formt die Bedienelemente, da
        // reicht das Nachziehen der Messwerte nicht.
        var genau = data.value === true || data.state === "ON";
        if (genau !== cfg.precise) { cfg.precise = genau; render(); return; }
      }
      else if (id.indexOf(IDS.sleep_dir) >= 0) {
        // Richtung und Ablasspunkt formen die Skizze - hier reicht das
        // Nachziehen der Messwerte nicht.
        if (data.state !== cfg.sleep_dir) { cfg.sleep_dir = data.state; render(); return; }
      }
      else if (id.indexOf(IDS.drain_point) >= 0) {
        if (data.state !== cfg.drain_point) { cfg.drain_point = data.state; render(); return; }
      }
      else if (id.indexOf(IDS.method) >= 0) cfg.method = data.state === METHOD_LIFT ? "hebesystem" : "keile";
      else if (id.indexOf(IDS.mounting) >= 0) cfg.mounting = data.state === MOUNT_UNDER ? "unten" : "oben";
      else if (id.indexOf(IDS.vehicle) >= 0) {
        var kind = data.state === VEHICLE_CARAVAN ? "wohnwagen" : "wohnmobil";
        if (kind !== cfg.vehicle) { cfg.vehicle = kind; render(); return; }
      }
      else return;
      // Nur der Messwertbereich - render() würde die Eingabefelder mitsamt
      // Inhalt neu anlegen, und zwar mehrmals pro Sekunde.
      update();
    });
    src.onerror = function () {
      // Verbindung weg: keine Werte mehr behaupten. Lieber "kein Sensorwert"
      // als eine eingefrorene Blase, die fälschlich eben anzeigt.
      //
      // Auch hier nur update(): ein Aussetzer während der WLAN-Eingabe darf
      // die halb getippten Zugangsdaten nicht wegwerfen.
      state.pitch = null;
      state.roll = null;
      update();
    };
  }

  function num(v) {
    var f = parseFloat(v);
    return isNaN(f) ? null : f;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { build(); connect(); });
  } else {
    build();
    connect();
  }
})();
