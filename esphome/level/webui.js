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

  var WHEEL_NAMES = {
    vorne_links: "Vorne links",
    vorne_rechts: "Vorne rechts",
    hinten_links: "Hinten links",
    hinten_rechts: "Hinten rechts",
    stuetzrad: "Stützrad"
  };

  /* Beim Wohnwagen heißen zwei Dinge anders, weil sie anderes bedeuten:
   * die Räder sitzen auf einer Achse, und das Längenmaß geht bis zum
   * Stützrad statt zur zweiten Achse. */
  var CARAVAN_WHEEL_NAMES = {
    hinten_links: "Linkes Rad",
    hinten_rechts: "Rechtes Rad",
    stuetzrad: "Stützrad"
  };

  /* Wenn zwei Räder derselben Seite dasselbe Maß brauchen, ist das EINE
   * Anweisung und nicht zwei. Dann steht hier der Name der Seite. */
  var SIDE_NAMES = {
    links: "Linke Seite",
    rechts: "Rechte Seite",
    vorne: "Vorne",
    hinten: "Hinten"
  };

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
    method: "keile", vehicle: "wohnmobil", mounting: "oben"
  };

  /* Objekt-Kennungen der Firmware. Die Schreibwege gehen über diese Namen,
   * gelesen wird über Teilstrings - so hält beides auch, wenn dem Gerät
   * ein anderer Name gegeben wird. */
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
    move_limit: "nderung_grenzwert"
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
      writeError = "Das Gerät kennt keine Einstellung „" + needle + "“. " +
        "Läuft die passende Firmware?";
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
      writeError = "Das Gerät kennt keinen Präzisionsmodus. " +
        "Läuft die passende Firmware?";
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

  function check(path) {
    return function (status) {
      writeError = (status >= 200 && status < 300)
        ? null
        : "Das Gerät hat die Einstellung nicht übernommen (Status " + status +
          " bei " + path + "). Sie steht nur auf diesem Handy.";
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

  function levelPitch() { return axisLevel("pitch", state.pitch, tolerance(cfg.wheelbase)); }
  function levelRoll() { return axisLevel("roll", state.roll, tolerance(cfg.track)); }

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
    if (!seite || !SIDE_NAMES[seite]) return list;
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
    var t = el('<div class="tabs"></div>');
    [["anzeige", "Anzeige"], ["technik", "Technik"]].forEach(function (pair) {
      var b = el("<button" + (page === pair[0] ? ' class="on"' : "") + ">" + pair[1] + "</button>");
      b.onclick = function () { page = pair[0]; render(); };
      t.appendChild(b);
    });
    return t;
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
    var pitch = ok ? state.pitch : 0;
    var roll = ok ? state.roll : 0;
    // Über axisLevel und nicht über den nackten Vergleich: nur so tragen
    // Text, Blase und Fahrzeugneigung dieselbe, ruhige Antwort.
    var levP = ok && levelPitch();
    var levR = ok && levelRoll();
    var level = levP && levR;
    // Angezeigte Winkel gerastet - siehe steady(). Der Rechenweg oben bleibt
    // am ungerasteten Messwert, gerastet wird nur, was zu lesen ist.
    var degP = ok ? steadyDeg("pitch_deg", pitch) : 0;
    var degR = ok ? steadyDeg("roll_deg", roll) : 0;

    var textR = !ok ? "⚠️ Kein Sensorwert"
      : levR ? "✅ EBEN – STOP"
        : (roll > 0 ? "LINKE Seite hoch" : "RECHTE Seite hoch");
    var textP = !ok ? "⚠️ Kein Sensorwert"
      : levP ? "✅ EBEN – STOP"
        : (pitch > 0 ? "HECK hoch" : "FRONT hoch");

    target.appendChild(bar("QUER", roll, tolR, levR, textR));
    target.appendChild(bar("LÄNGS", pitch, tolP, levP, textP));

    var plan = el('<div class="plan"></div>');
    var head = level ? "✅ EBEN – STOP" : ok ? "Ausrichten" : "⚠️ Kein Sensorwert";
    var html = "<h2>" + head + "</h2>";
    if (ok) {
      html += '<div class="muted">Längs ' + degP.toFixed(places()) + "° · Quer " +
        degR.toFixed(places()) + "°" +
        (state.motion ? " · in Bewegung" : "") + "</div>";
      var lifts = level ? [] : (wheelLifts() || []);
      var names = isCaravan() ? CARAVAN_WHEEL_NAMES : WHEEL_NAMES;
      var label = function (i) {
        return names[i.wheel] || WHEEL_NAMES[i.wheel] || SIDE_NAMES[i.wheel] || i.wheel;
      };
      // Auch die Zentimeter der Anweisung gerastet: ein Maß, das beim Lesen
      // zwischen 4,3 und 5,2 wechselt, ist keine Anweisung, sondern eine Frage.
      var planCm = function (i) { return steadyCm("plan_" + i.wheel, i.cm).toFixed(1); };

      if (lifts.length) {
        html += "<ul>";
        if (isCaravan()) {
          // Beide Schritte auf einmal, aber in fester Reihenfolge - und mit
          // Richtung, weil das Stützrad auch runter kann.
          lifts.forEach(function (i) {
            html += "<li><b>" + label(i) + "</b> " + i.direction + ", " +
              (i.steps ? "Keilstufe " + i.steps : planCm(i) + " cm") + "</li>";
          });
          html += "</ul>";
          html += '<div class="muted">' + (lifts.length > 1
            ? "Erst das Rad auf den Keil, dann das Stützrad – das Auffahren kippt den Wagen längs mit."
            : "Danach neu messen.") + "</div>";
        } else if (cfg.method === "hebesystem") {
          lifts.forEach(function (i) {
            html += "<li><b>" + label(i) + "</b> " + planCm(i) + " cm</li>";
          });
          // "Räder" im Plural: Bei einer zusammengezogenen Seitenanweisung
          // bleiben zwei stehen, nicht eines.
          html += '</ul><div class="muted">Alle Stützen auf einmal, höchste zuerst. Nicht genannte Räder bleiben stehen.</div>';
        } else {
          var first = lifts[0];
          html += "<li><b>" + label(first) + "</b> " +
            (first.steps ? "Keilstufe " + first.steps : planCm(first) + " cm") + "</li></ul>" +
            '<div class="muted">Eine Anweisung nach der anderen – nach dem Auffahren neu messen.</div>';
        }
      }
    } else {
      html += '<div class="muted">Das Nivelliergerät liefert gerade keine Werte – Anzeige nicht verwenden.</div>';
    }
    plan.innerHTML = html;
    target.appendChild(plan);

    // --- Draufsicht: beide Achsen in einer Blase ---------------------------
    var overall = !ok ? COLORS.off
      : level ? COLORS.ok
        : (Math.abs(pitch) > 2 * tolP || Math.abs(roll) > 2 * tolR) ? COLORS.bad : COLORS.warn;
    var top = el('<div class="top"><div class="cap">▲ VORNE</div></div>');
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
     * Sie kommen aus dem Gerät (Hub-Sensoren), nicht aus einer zweiten
     * Rechnung hier: Die Anweisung darunter und diese Zahlen müssen dasselbe
     * sagen, sonst sucht der Nutzer den Unterschied.
     *
     * Beim Wohnwagen tragen die beiden hinteren Werte die Räder der einen
     * Achse, und vorne steht mittig das Stützrad - deshalb dort nur ein Feld
     * statt zweier. */
    var hub = function (kennung) {
      var w = parseFloat(findStateOf("sensor", kennung));
      return isNaN(w) ? null : w;
    };
    var ecke = function (wert, oben, links, text) {
      var e = el('<div class="ecke"></div>');
      e.style.top = oben;
      e.style.left = links;
      e.style.transform = "translate(-50%,-50%)";
      if (wert === null) { e.textContent = "–"; e.className = "ecke fertig"; }
      else if (Math.abs(wert) < 1) { e.textContent = "0"; e.className = "ecke fertig"; }
      else {
        e.textContent = (text || "") + Math.abs(wert).toFixed(1).replace(".", ",");
        e.className = "ecke tun";
      }
      top.appendChild(e);
    };

    if (isCaravan()) {
      var st = hub("stuetzrad");
      ecke(st, "16%", "50%", st !== null && st < 0 ? "▼ " : "▲ ");
      ecke(hub("hub_hinten_links"), "78%", "22%");
      ecke(hub("hub_hinten_rechts"), "78%", "78%");
    } else {
      ecke(hub("hub_vorne_links"), "20%", "22%");
      ecke(hub("hub_vorne_rechts"), "20%", "78%");
      ecke(hub("hub_hinten_links"), "80%", "22%");
      ecke(hub("hub_hinten_rechts"), "80%", "78%");
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
    var schiefste = Math.max(Math.abs(degP), Math.abs(degR));

    var badges = el('<div class="badges"></div>');
    var badge = function (titel, text, klasse, hinweis) {
      var b = el('<div class="badge ' + klasse + '"><div class="bt"></div><div class="bs"></div></div>');
      b.querySelector(".bt").textContent = titel;
      b.querySelector(".bs").textContent = text;
      if (hinweis) b.title = hinweis;
      badges.appendChild(b);
    };

    if (!ok) {
      badge("Neigung", "–", "aus");
      badge("Bewegung", "–", "aus");
      badge("Lage", "–", "aus");
    } else {
      badge("Neigung",
        schiefste.toFixed(1).replace(".", ",") + "° · " + (schraeg ? "Kühlschrank!" : "ok"),
        schraeg ? "alarm" : "ok",
        schraeg
          ? "Über " + cfg.tilt_limit.toFixed(1).replace(".", ",") +
            "° arbeitet ein Absorberkühlschrank nicht mehr zuverlässig."
          : "Unter " + cfg.tilt_limit.toFixed(1).replace(".", ",") +
            "° – der Absorberkühlschrank arbeitet zuverlässig.");
      badge("Bewegung", bewegt ? "in Bewegung" : "steht ruhig",
        bewegt ? "achtung" : "ok",
        "Erschütterung – jemand steigt ein, Wind, der Nachbar rangiert. Kein Alarm.");
      badge("Lage", verrueckt ? "verändert!" : "unverändert",
        verrueckt ? "alarm" : "ok",
        "Weicht die Neigung um mehr als " + cfg.move_limit.toFixed(1).replace(".", ",") +
        "° von der Ruhelage ab, wurde das Fahrzeug bewegt.");
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
      "SEITE · längs — " + (ok ? degP.toFixed(places()) + "°" : "⚠️"),
      colorFor(pitch, tolP, levP), tilt(degP, levP)));
    target.appendChild(view(isCaravan() ? CARAVAN_REAR : CAMPER_REAR,
      "HECK · quer — " + (ok ? degR.toFixed(places()) + "°" : "⚠️"),
      colorFor(roll, tolR, levR), tilt(-degR, levR)));

    var cal = el('<button class="act">Neigung kalibrieren</button>');
    cal.onclick = function () {
      cal.disabled = true;
      cal.textContent = "Kalibriere …";
      press("neigung_kalibrieren", function () {
        window.setTimeout(function () { cal.disabled = false; cal.textContent = "Neigung kalibrieren"; }, 5000);
      });
    };
    target.appendChild(cal);
  }

  /* Wird einmal je Reiterwechsel aufgebaut. Die Verweise bleiben erhalten,
   * damit syncSettings() später nur die Werte nachziehen kann. */
  var settingInputs = {};
  var methodSelect = null;
  var vehicleSelect = null;
  var mountingSelect = null;
  var preciseBox = null;
  var mqttNote = null;
  var mqttBroker = null;
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

  function settings() {
    settingInputs = {};
    var box = el('<div class="plan"><h2>Fahrzeug</h2></div>');
    // Beim Wohnwagen misst dieselbe Zahl etwas anderes - deshalb die
    // Beschriftung mitführen statt sie fest hinzuschreiben.
    //
    // Und nur die Toleranz, die gerade gilt: Beide nebeneinander wären zwei
    // Felder für eine Frage, von denen eines wirkungslos ist - der Nutzer
    // stellt dann das falsche ein und wundert sich, dass nichts passiert.
    var rows = [
      ["wheelbase", isCaravan() ? "Achse → Stützrad (mm)" : "Radstand (mm)"],
      ["track", "Spurweite (mm)"],
      cfg.precise ? ["tolerance_deg", "Toleranz genau (°)"]
        : ["tolerance_cm", "Toleranz (cm)"],
      ["wedge_step", "Keilstufe (cm, 0 = aus)"]
    ];
    rows.forEach(function (r) { zahlZeile(box, r[0], r[1]); });

    /* Steht direkt unter der Toleranz, weil er ändert, was sie bedeutet.
     *
     * Der Kasten braucht eine eigene Breite: .set input ist 130 px breit,
     * das ergäbe ein Ankreuzfeld in der Größe eines Eingabefelds. */
    var prow = el('<div class="set"><span>Präzisionsmodus</span></div>');
    preciseBox = el('<input type="checkbox" style="width:26px;height:26px;padding:0">');
    preciseBox.checked = cfg.precise;
    preciseBox.onchange = function () { setPrecise(preciseBox.checked); };
    prow.appendChild(preciseBox);
    box.appendChild(prow);
    box.appendChild(el('<div class="muted" style="margin-bottom:6px">' +
      "Aus: die Toleranz gilt in Zentimetern, und innerhalb davon steht alles " +
      "in der Mitte – dort ist nichts mehr zu tun. Ein: feste Gradtoleranz für " +
      "beide Achsen, die Blase bleibt an ihrer echten Stelle, Winkel mit zwei " +
      "Nachkommastellen.</div>"));

    var vrow = el('<div class="set"><span>Fahrzeugart</span></div>');
    vehicleSelect = el('<select><option>Wohnmobil</option><option>' + VEHICLE_CARAVAN + "</option></select>");
    vehicleSelect.value = isCaravan() ? VEHICLE_CARAVAN : "Wohnmobil";
    vehicleSelect.onchange = function () { setVehicle(vehicleSelect.value); };
    vrow.appendChild(vehicleSelect);
    box.appendChild(vrow);

    var mrow = el('<div class="set"><span>Womit ausrichten</span></div>');
    methodSelect = el('<select><option>Auffahrkeile</option><option>' + METHOD_LIFT + "</option></select>");
    methodSelect.value = cfg.method === "hebesystem" ? METHOD_LIFT : "Auffahrkeile";
    methodSelect.onchange = function () { setMethod(methodSelect.value); };
    mrow.appendChild(methodSelect);
    // Beim Wohnwagen ohne Bedeutung: längs kurbelt man am Stützrad, quer
    // fährt man auf. Ein Hebesystem gibt es dort nicht.
    if (!isCaravan()) box.appendChild(mrow);

    settingsNote = el('<div class="muted" style="margin-top:8px"></div>');
    box.appendChild(settingsNote);

    /* Eigener Bereich, weil die Einbaulage das GERÄT beschreibt und nicht das
     * Fahrzeug. Sie wird einmal beim Ankleben gesetzt und danach nie wieder -
     * zwischen Radstand und Spurweite stünde sie an der falschen Stelle.
     *
     * Sie MUSS hier stehen: Achszuordnung und Vorzeichen sind Substitutions und
     * brauchen einen Flash, die Einbaulage entscheidet der Nutzer im Fahrzeug.
     * Ohne diese Auswahl gäbe es sie nur in Home Assistant, und wer das Gerät
     * ohne Zentrale betreibt, käme an eine Einstellung nicht heran, die über
     * richtig und falsch herum entscheidet. */
    var geraet = el('<div class="plan"><h2>Gerät</h2></div>');
    var erow = el('<div class="set"><span>Einbaulage</span></div>');
    mountingSelect = el('<select><option>Deckel oben</option><option>' +
      MOUNT_UNDER + "</option></select>");
    mountingSelect.value = cfg.mounting === "unten" ? MOUNT_UNDER : "Deckel oben";
    mountingSelect.onchange = function () { setMounting(mountingSelect.value); };
    erow.appendChild(mountingSelect);
    geraet.appendChild(erow);
    geraet.appendChild(el('<div class="muted" style="margin-top:8px">' +
      "„Deckel unten“ heißt: unter ein Regalbrett oder eine Decke geklebt, " +
      "der Pfeil zeigt weiterhin nach vorn. Nach dem Umstellen neu kalibrieren." +
      "</div>"));

    /* Eigener Kasten, weil diese beiden weder die Messung noch die Toleranz
     * anfassen - sie ändern, wie sich die Anzeige anfühlt. Und das empfindet
     * jeder anders: Der eine will, dass sie steht wie angenagelt, der andere
     * will jede Regung sehen. Ab Werk lässt sich das nicht entscheiden,
     * deshalb steht es hier und nicht in der Firmware. */
    var anzeige = el('<div class="plan"><h2>Anzeige</h2></div>');
    zahlZeile(anzeige, "calm", "Anzeigeruhe (0–10)");
    anzeige.appendChild(el('<div class="muted" style="margin-bottom:10px">' +
      "Klein: die Anzeige folgt jeder Regung, zappelt im Stand aber mehr. " +
      "Groß: sie steht im Stand still und reagiert dafür etwas später. " +
      "Die Genauigkeit ändert sich nicht – nur die Geduld." +
      "</div>"));
    zahlZeile(anzeige, "hold_percent", "Haltebereich (%)");
    anzeige.appendChild(el('<div class="muted">' +
      "Wie weit die Neigung über die Toleranz hinausgehen darf, bevor die " +
      "Anzeige „eben“ zurücknimmt. 100 % heißt sofort – dann springt sie an " +
      "der Grenze hin und her. Höher setzen, wenn genau das passiert." +
      "</div>"));

    /* Warnungen - eigener Kasten, weil sie nichts mit dem Ausrichten zu tun
     * haben. Der Rest dieser Seite hilft, gerade zu stehen; diese beiden
     * melden, dass etwas Schaden nimmt oder jemand am Fahrzeug war. */
    var warnungen = el('<div class="plan"><h2>Warnungen</h2></div>');
    zahlZeile(warnungen, "tilt_limit", "Schräglage ab (°)");
    warnungen.appendChild(el('<div class="muted" style="margin-bottom:10px">' +
      "Ein Absorberkühlschrank arbeitet über etwa 3° nicht mehr zuverlässig. " +
      "Das merkt niemand, bis das Essen warm ist – deshalb die eigene Warnung, " +
      "unabhängig von deiner Toleranz beim Ausrichten." +
      "</div>"));
    zahlZeile(warnungen, "move_limit", "Lageänderung ab (°)");
    warnungen.appendChild(el('<div class="muted">' +
      "Ab welcher Abweichung von der Ruhelage gemeldet wird, dass das Fahrzeug " +
      "bewegt wurde. Ein Grad sind bei 3500 mm Radstand rund 6 cm – Wind und " +
      "Einsteigen bleiben darunter, Anheben und Abschleppen darüber." +
      "</div>"));

    /* Vier Kästen, ein Rückgabewert: appendChild fügt bei einem Fragment alle
     * Kinder ein, der Aufrufer bleibt unverändert. */
    var beide = document.createDocumentFragment();
    beide.appendChild(box);
    beide.appendChild(anzeige);
    beide.appendChild(warnungen);
    beide.appendChild(geraet);
    return beide;
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
    if (mountingSelect && mountingSelect !== focused) {
      mountingSelect.value = cfg.mounting === "unten" ? MOUNT_UNDER : "Deckel oben";
    }
    if (preciseBox && preciseBox !== focused) preciseBox.checked = cfg.precise;
    // Nur, solange dort keine eigene Rueckmeldung steht - sonst ueberschriebe
    // der Zustand die Meldung "Gespeichert, das Geraet startet neu".
    if (mqttNote && !mqttNote.style.fontWeight) {
      mqttNote.textContent = findStateOf("text_sensor", "mqtt") || "";
    }
    /* Broker, Benutzer und Port zeigen, was im Gerät steht.
     *
     * Leere Felder bei laufender Verbindung sahen nicht nur nach "nichts
     * eingerichtet" aus, sie waren gefährlich: Wer nur den Benutzer ändern
     * wollte und speicherte, schickte ein leeres Brokerfeld mit - und leer
     * schaltet MQTT ab. Das Passwortfeld bleibt leer, dort heißt leer beim
     * Speichern "unverändert". */
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
        : state.ready ? "Diese Werte stehen im Gerät. Jedes Handy sieht dieselben."
          : "Warte auf das Gerät …";
      settingsNote.style.color = writeError ? "#ff7a7a" : "";
      settingsNote.style.fontWeight = writeError ? "700" : "";
    }
    if (versionNote) {
      versionNote.innerHTML = "Laufende Fassung: <b>" +
        (findState("firmware_version") || "unbekannt") + "</b>";
    }
  }

  /* Überschriften je Bereich. Das Gerät liefert seine Kennungen als
   * "<bereich>-<name>" (je nach Fassung auch mit Schrägstrich), sonst nichts
   * Gegliedertes - eine Liste aus 25 Zeilen ohne Ordnung liest niemand. */
  var DOMAIN_TITLES = {
    sensor: "Messwerte",
    binary_sensor: "Zustände",
    text_sensor: "Informationen",
    number: "Einstellwerte",
    select: "Auswahl",
    text: "Texteingaben",
    switch: "Schalter",
    button: "Tasten",
    update: "Software"
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

  /* Fehlt der Name, aus der Kennung einen lesbaren machen:
   * "neigung_pitch" wird zu "Neigung pitch". Besser als die rohe Kennung. */
  function prettify(objectId) {
    var t = objectId.replace(/_/g, " ").trim();
    return t.charAt(0).toUpperCase() + t.slice(1);
  }

  function renderTechTable(target) {
    var box = el('<div class="plan"><h2>Technik</h2></div>');
    var ids = Object.keys(state.seen);

    if (!ids.length) {
      box.appendChild(el('<div class="muted">Noch keine Daten empfangen.</div>'));
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
      box.appendChild(el('<div class="muted">Noch keine Messwerte empfangen.</div>'));
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
        (DOMAIN_TITLES[domain] || prettify(domain)) + "</div>"));
      var table = document.createElement("table");
      var body = document.createElement("tbody");
      groups[domain]
        .sort(function (a, b) { return String(a.label).localeCompare(String(b.label), "de"); })
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

  var versionNote = null;

  /* Aktualisierung von Hand - der Weg für die Betriebsart ohne Home
   * Assistant. Ausgelöst wird die Taste im Gerät, die ihrerseits die neue
   * Firmware von GitHub holt. Für Update-Entitäten gibt es keinen
   * dokumentierten REST-Endpunkt, für Tasten schon. */
  function softwareBox() {
    var up = el('<div class="plan"><h2>Software</h2></div>');
    versionNote = el('<div class="muted"></div>');
    up.appendChild(versionNote);

    var btn = el('<button class="act ghost" style="margin-top:10px">Auf Updates prüfen und installieren</button>');
    btn.onclick = function () {
      if (!window.confirm("Neue Firmware von GitHub laden und installieren?\n\nDas Gerät startet dabei neu. Nicht während der Fahrt.")) return;
      btn.disabled = true;
      btn.textContent = "Lade und installiere …";
      press("firmware_aktualisieren", function () {
        btn.textContent = "Läuft – das Gerät startet gleich neu.";
      });
    };
    up.appendChild(btn);
    up.appendChild(el('<div class="muted" style="margin-top:8px">Holt die neue Fassung von GitHub – das Gerät braucht dafür Internet. Steht es im eigenen Netz auf dem Stellplatz, gibt es keins; dann der Weg darunter.</div>'));

    /* Weg ohne Internet: Datei vom Handy hochladen. Möglich durch
     * "ota: platform: web_server" in der Firmware.
     *
     * ACHTUNG: ESPHome dokumentiert den Endpunkt dieses Formulars nicht -
     * /update mit dem Feldnamen "file" ist der übliche Weg, aber ungeprüft.
     * Schlägt es fehl, sagt die Seite das ausdrücklich statt stumm zu
     * bleiben, und nennt den Ausweg. Beim ersten echten Build prüfen. */
    var form = el('<div style="margin-top:14px"></div>');
    form.appendChild(el('<div class="muted">Oder Firmwaredatei vom Handy aufspielen:</div>'));
    var file = el('<input type="file" accept=".bin" style="margin-top:8px;width:100%">');
    var send = el('<button class="act ghost" style="margin-top:8px">Datei aufspielen</button>');
    var note = el('<div class="muted" style="margin-top:8px"></div>');
    send.onclick = function () {
      if (!file.files || !file.files.length) { note.textContent = "Erst eine Datei auswählen."; return; }
      send.disabled = true;
      note.textContent = "Übertrage …";
      var body = new FormData();
      body.append("file", file.files[0]);
      var req = new XMLHttpRequest();
      req.open("POST", "/update", true);
      req.onload = function () {
        note.textContent = req.status >= 200 && req.status < 300
          ? "Übertragen. Das Gerät startet neu."
          : "Fehlgeschlagen (Status " + req.status + "). Notfalls über das ESPHome-Dashboard aufspielen.";
        send.disabled = false;
      };
      req.onerror = function () {
        note.textContent = "Keine Verbindung zum Gerät.";
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
    var box = el('<div class="plan"><h2>WLAN</h2></div>');
    box.appendChild(el('<div class="muted">Nur nötig für automatische Updates und Home Assistant. Ohne WLAN läuft alles Übrige weiter.</div>'));

    var ssid = el('<input type="text" placeholder="Netzwerkname" style="width:100%;margin-top:10px">');
    var pass = el('<input type="password" placeholder="Passwort" style="width:100%;margin-top:8px">');
    var btn = el('<button class="act ghost" style="margin-top:10px">Speichern und verbinden</button>');
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
      if (!ssid.value) { say("Netzwerkname fehlt.", "bad"); return; }
      btn.disabled = true;
      say("Übertrage …");

      var pName = pathFor("text", "wlan_name");
      var pPass = pathFor("text", "wlan_pass");
      var pSave = pathFor("button", "wlan_speichern");

      if (!pName || !pPass || !pSave) {
        return fail("Das Gerät meldet keine WLAN-Eingabefelder. " +
          "Auf diesem Gerät läuft eine Firmware ohne diese Funktion.");
      }

      // Nacheinander, nicht gleichzeitig: der Knopf im Gerät liest beide
      // Felder, sie müssen also vorher angekommen sein.
      setText(pName, ssid.value, function (ok1) {
        if (!ok1) return fail("Das Gerät hat den Netzwerknamen nicht angenommen (" + pName + "/set).");
        setText(pPass, pass.value, function (ok2) {
          if (!ok2) return fail("Das Gerät hat das Passwort nicht angenommen (" + pPass + "/set).");
          say("Warte auf Bestätigung des Geräts …");
          awaitEcho(ssid.value, 5000, function (confirmed) {
            if (!confirmed) {
              return fail("Das Gerät bestätigt die Eingabe nicht. Nichts wurde gespeichert.");
            }
            post(pSave + "/press");
            say("Gespeichert. Das Gerät startet jetzt neu und verbindet sich mit „" +
              ssid.value + "“.\n\n" +
              "Achte auf die WLAN-Liste deines Handys: Verschwindet das Netz CamperMinder " +
              "innerhalb einer Minute, hat es geklappt. Bleibt es bestehen, stimmt " +
              "Name oder Passwort nicht – dann einfach erneut verbinden und korrigieren.", "good");
          });
        });
      });

      function fail(text) {
        say(text + " Notfalls über das ESPHome-Dashboard einrichten.", "bad");
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
    box.appendChild(el('<div class="grouphead" style="margin-top:22px">Eigenes Netz</div>'));
    var anote = el('<div class="muted"></div>');
    anote.textContent = "Das Netz „CamperMinder“ ist ohne Passwort erreichbar. " +
      "Es besteht nur, solange oben kein WLAN eingetragen ist. Wer es " +
      "abschließen möchte, vergibt hier eines – mindestens acht Zeichen. " +
      "Leer lassen und speichern öffnet es wieder.";
    box.appendChild(anote);

    var apPass = el('<input type="password" placeholder="Neues Passwort (leer = offen)" style="width:100%;margin-top:10px">');
    var apBtn = el('<button class="act ghost" style="margin-top:8px">Netz-Passwort speichern</button>');
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
        apSay("Mindestens acht Zeichen – so verlangt es WPA2. Oder leer lassen, dann bleibt das Netz offen.", "bad");
        return;
      }
      var offen = !apPass.value;
      var pText = pathFor("text", "netz_passwort_neu");
      var pSave = pathFor("button", "netz_passwort_speichern");
      if (!pText || !pSave) {
        apSay("Das Gerät kennt diese Einstellung nicht. Läuft die passende Firmware?", "bad");
        return;
      }
      apBtn.disabled = true;
      apSay("Übertrage …");
      setText(pText, apPass.value, function (ok) {
        if (!ok) {
          apSay("Das Gerät hat die Eingabe nicht angenommen.", "bad");
          apBtn.disabled = false;
          return;
        }
        post(pSave + "/press");
        apPass.value = "";
        apSay(offen
          ? "Gespeichert. Das Gerät startet neu – das Netz ist danach wieder ohne Passwort erreichbar."
          : "Gespeichert. Das Gerät startet neu.\n\nDanach fragt dein Handy nach dem neuen Passwort. " +
            "Merke es dir gut: Ohne WLAN und ohne dieses Passwort kommst du nur noch " +
            "über ein USB-Kabel an das Gerät – oder über Zurücksetzen weiter unten, " +
            "das es wieder öffnet.", "good");
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
    box.appendChild(el('<div class="muted">' +
      "Meldet Neigung, Hubhöhe je Ecke und Anweisung an einen MQTT-Broker – " +
      "für Victron Cerbo GX, ioBroker, openHAB, Node-RED oder was immer du " +
      "einsetzt. Für Home Assistant ist es nicht nötig, das läuft über die " +
      "eigene Schnittstelle. Themen unter <b>camperminder/level/…</b>" +
      "</div>"));

    var mBroker = el('<input type="text" placeholder="Broker, z. B. 192.168.1.10 (leer = aus)" style="width:100%;margin-top:10px">');
    var mPort = el('<input type="number" placeholder="Port" style="width:100%;margin-top:8px">');
    var mUser = el('<input type="text" placeholder="Benutzer (optional)" style="width:100%;margin-top:8px">');
    var mPass = el('<input type="password" placeholder="Passwort (leer = unverändert)" style="width:100%;margin-top:8px">');
    var mBtn = el('<button class="act ghost" style="margin-top:8px">MQTT speichern</button>');
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
    mSay(findStateOf("text_sensor", "mqtt") || "");

    mBtn.onclick = function () {
      var pB = pathFor("text", "mqtt_broker");
      var pU = pathFor("text", "mqtt_benutzer");
      var pP = pathFor("text", "mqtt_passwort");
      var pPort = pathFor("number", "mqtt_port");
      var pSave = pathFor("button", "mqtt_speichern");
      if (!pB || !pSave) {
        mSay("Das Gerät kennt MQTT nicht. Läuft die passende Firmware?", "bad");
        return;
      }
      mBtn.disabled = true;
      mSay("Übertrage …");

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
          mSay("Das Gerät hat die Eingabe nicht angenommen.", "bad");
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
        mSay(mBroker.value
          ? "Gespeichert. Das Gerät startet neu und meldet sich beim Broker.\n\nDanach steht der Zustand hier oben – bei einem Tippfehler „keine Verbindung“."
          : "Gespeichert. MQTT ist wieder aus.", "good");
      })(true);
    };

    box.appendChild(mBroker);
    box.appendChild(mPort);
    box.appendChild(mUser);
    box.appendChild(mPass);
    box.appendChild(mBtn);
    box.appendChild(mNote);

    /* Werksreset. Steht bewusst hier unten und nicht bei den Bedienelementen
     * oben - er löscht WLAN, Kalibrierung und Fahrzeugmaße auf einmal. */
    box.appendChild(el('<div class="grouphead" style="margin-top:22px">Zurücksetzen</div>'));
    var rnote = el('<div class="muted"></div>');
    rnote.textContent = "Löscht WLAN-Zugangsdaten, Kalibrierung, Fahrzeugmaße und ein " +
      "selbst vergebenes Netz-Passwort. Das Gerät startet danach neu und " +
      "öffnet wieder sein eigenes, offenes Netz.";
    box.appendChild(rnote);

    var reset = el('<button class="act ghost" style="margin-top:10px">Auf Werkseinstellungen zurücksetzen</button>');
    reset.onclick = function () {
      if (!window.confirm("Wirklich zurücksetzen?\n\nWLAN, Kalibrierung und Fahrzeugmaße gehen verloren. Das Gerät muss danach neu eingerichtet und neu kalibriert werden.\n\nEin selbst vergebenes Netz-Passwort wird ebenfalls gelöscht – das eigene Netz ist danach wieder offen.")) return;
      reset.disabled = true;
      reset.textContent = "Setze zurück …";
      press("werkseinstellungen", function () {
        rnote.textContent = "Zurückgesetzt. Das Gerät startet neu – verbinde dich anschließend wieder mit dem Netz CamperMinder.";
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
      if (id.indexOf(needle) >= 0) return state.seen[id].state;
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
      if (parts[1] === needle) { exact = { id: id, obj: parts[1] }; break; }
      if (parts[1].indexOf(needle) >= 0 && (!best || parts[1].length < best.obj.length)) {
        best = { id: id, obj: parts[1] };
      }
    }
    return exact || best;
  }

  function objectId(domain, needle, fallback) {
    var hit = findEntity(domain, needle);
    // Der Rückfallwert greift nur, solange noch nichts empfangen wurde.
    return hit ? hit.obj : fallback;
  }

  /* Den REST-Pfad einer Entität, wie das Gerät ihn selbst angibt.
   *
   * Rückgabe etwa "/number/radstand". Findet sich nichts, kommt null - dann
   * wird gar nicht erst geschrieben, statt auf gut Glück eine Adresse zu
   * bauen und den 404 zu verschlucken. */
  function pathFor(domain, needle) {
    var hit = findEntity(domain, needle);
    if (!hit) return null;
    var nid = state.seen[hit.id].name_id;
    return nid ? "/" + nid : "/" + domain + "/" + hit.obj;
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

      // Über Teilstrings statt die volle Kennung: dann hält die Seite auch,
      // wenn jemand dem Gerät einen anderen Namen gibt.
      var id = data.id;
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
      else if (id.indexOf(IDS.calm) >= 0) cfg.calm = num(data.value);
      else if (id.indexOf(IDS.hold_percent) >= 0) cfg.hold_percent = num(data.value);
      else if (id.indexOf(IDS.precise) >= 0) {
        // Wie bei der Fahrzeugart: Der Modus formt die Bedienelemente, da
        // reicht das Nachziehen der Messwerte nicht.
        var genau = data.value === true || data.state === "ON";
        if (genau !== cfg.precise) { cfg.precise = genau; render(); return; }
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
