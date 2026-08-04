/*
 * CamperMaid - Oberflaeche auf dem Geraet selbst
 * ---------------------------------------------------------------------------
 * Wird ueber web_server.js_include in die Firmware eingebettet und als /0.js
 * ausgeliefert. Braucht weder Home Assistant noch Internet noch eine App: das
 * Handy verbindet sich mit dem Geraet und oeffnet dessen Adresse.
 *
 * Die Rechnung ist absichtlich dieselbe wie in der Home-Assistant-Integration
 * (coordinator.py): Schwellen ueber den Arkustangens der Fahrzeugmasse,
 * Hubhoehe je Rad gegen das hoechste Rad. Wer eine Formel aendert, muss beide
 * Stellen aendern - sonst sagen Geraet und Karte Verschiedenes, und das
 * merkt man erst im Fahrzeug.
 *
 * Vorzeichen wie in der Firmware: pitch > 0 = Front hoeher (Heck muss hoch),
 * roll > 0 = rechte Seite hoeher (linke Seite muss hoch).
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

  /* Beim Wohnwagen heissen zwei Dinge anders, weil sie anderes bedeuten:
   * die Raeder sitzen auf einer Achse, und das Laengenmass geht bis zum
   * Stuetzrad statt zur zweiten Achse. */
  var CARAVAN_WHEEL_NAMES = {
    hinten_links: "Linkes Rad",
    hinten_rechts: "Rechtes Rad",
    stuetzrad: "Stützrad"
  };

  var VEHICLE_CARAVAN = "Wohnwagen";

  /* Die Fahrzeugmasse liegen im Geraet, nicht im Browser: sie beschreiben das
   * Fahrzeug, nicht den Betrachter. Dadurch sehen alle Mitfahrer dieselben
   * Zahlen, und ein neues Handy bringt sie nicht durcheinander.
   *
   * Die Werte kommen ueber denselben Ereignisstrom wie die Messwerte und
   * werden ueber die REST-Schnittstelle zurueckgeschrieben. Die Vorgaben hier
   * gelten nur, solange noch nichts empfangen wurde - eine leere Anzeige waere
   * schlimmer als eine plausible Zahl. */
  var cfg = {
    wheelbase: 3500, track: 1800, tolerance_cm: 5, wedge_step: 0,
    method: "keile", vehicle: "wohnmobil"
  };

  /* Objekt-Kennungen der Firmware. Die Schreibwege gehen ueber diese Namen,
   * gelesen wird ueber Teilstrings - so haelt beides auch, wenn dem Geraet
   * ein anderer Name gegeben wird. */
  var IDS = {
    wheelbase: "radstand",
    track: "spurweite",
    tolerance_cm: "toleranz",
    wedge_step: "keilstufe",
    method: "ausrichtart",
    vehicle: "fahrzeugart"
  };

  var METHOD_LIFT = "Hydraulik oder Luftkissen";

  var state = { pitch: null, roll: null, motion: false, seen: {}, ready: false };

  /* Jeder Schreibzugriff wird geprueft.
   *
   * Vorher wurden Werte lokal gesetzt und blind abgeschickt. Antwortete das
   * Geraet mit 404, sah der Nutzer trotzdem seine Eingabe stehen und durfte
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

  function setVehicle(option) {
    cfg.vehicle = option === VEHICLE_CARAVAN ? "wohnwagen" : "wohnmobil";
    write("select", IDS.vehicle, "option=" + encodeURIComponent(option));
    // Beschriftungen und Bedienfelder haengen davon ab - hier reicht das
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

  function tolerance(dimensionMm) {
    var deg = Math.atan((cfg.tolerance_cm * 10) / dimensionMm) * 180 / Math.PI;
    return Math.max(deg, MIN_TOLERANCE_DEG);
  }

  function available() {
    return state.pitch !== null && state.roll !== null &&
      Math.abs(state.pitch) <= IMPLAUSIBLE_DEG && Math.abs(state.roll) <= IMPLAUSIBLE_DEG;
  }

  function isCaravan() { return cfg.vehicle === "wohnwagen"; }

  /* Wohnwagen: zwei Raeder auf einer Achse plus Stuetzrad.
   *
   * Quer wie beim Wohnmobil ueber die Spurweite - ein Keil unter das tiefere
   * Rad. Laengs dagegen ueber das Stuetzrad, und das kurbelt in BEIDE
   * Richtungen; "nur anheben" waere hier eine kuenstliche Einschraenkung.
   *
   * Reihenfolge ist Absicht: erst quer, dann laengs. Das Auffahren auf den
   * Keil kippt den Wagen laengs mit - eine vorher berechnete Stuetzradhoehe
   * waere danach falsch. */
  function caravanPlan() {
    if (!available()) return null;
    var out = [];

    var across = Math.round(cfg.track * Math.tan(Math.abs(state.roll) * Math.PI / 180) / 10 * 10) / 10;
    if (across >= WHEEL_LIFT_IGNORE_CM) {
      out.push({
        wheel: state.roll > 0 ? "hinten_links" : "hinten_rechts",
        cm: across,
        steps: cfg.wedge_step > 0 ? Math.max(Math.round(across / cfg.wedge_step), 1) : null,
        direction: "hoch"
      });
    }

    var along = Math.round(cfg.wheelbase * Math.tan(Math.abs(state.pitch) * Math.PI / 180) / 10 * 10) / 10;
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
    var halfLong = cfg.wheelbase * Math.tan(state.pitch * Math.PI / 180) / 20;
    var halfLat = cfg.track * Math.tan(state.roll * Math.PI / 180) / 20;
    // pitch > 0 = Front hoeher, roll > 0 = rechts hoeher.
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
    return out;
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
   * Achsen zugleich, waehrend die Wasserwaagen darueber jede fuer sich
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

  /* Wohnwagen: Deichsel mit Kupplung, EINE Achse, Stuetzrad vorn. Gleiche
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
    '.ring{position:absolute;left:50%;top:50%;width:56px;height:56px;margin:-28px 0 0 -28px;' +
    'border-radius:50%;border:2px dashed rgba(127,127,127,.5)}' +
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

  /* Tabellenteile MUESSEN so gebaut werden, nicht ueber el().
   *
   * Der HTML-Parser verwirft <tr> und <td>, wenn sie in einem <div> stehen -
   * das ist Absicht der Spezifikation, nicht ein Fehler des Browsers. el()
   * lieferte daher fuer "<tr>..." nur die nackten Textknoten (die Technik-
   * liste sah dadurch unformatiert aus) und fuer "<tr></tr>" gar nichts,
   * worauf das Anhaengen mit einem Fehler abbrach und die ganze Liste leer
   * blieb. Zwei Symptome, eine Ursache. */
  function cell(text, className) {
    var td = document.createElement("td");
    if (className) td.className = className;
    // textContent, nicht innerHTML: die Namen kommen vom Geraet, spitze
    // Klammern darin sollen Text bleiben.
    td.textContent = text;
    return td;
  }

  var root, page = "anzeige";

  function build() {
    document.title = "CamperMaid";
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
   *   live   - Messwerte. Wird bei jeder Meldung des Geraets neu gezeichnet,
   *            also mehrmals pro Sekunde.
   *   fest   - Bedienelemente. Wird nur beim Wechsel des Reiters aufgebaut.
   *
   * Vorher lag beides zusammen. Jede Messwertaenderung hat damit auch die
   * Eingabefelder zerstoert und neu angelegt - wer tippte, verlor den Text
   * nach Sekundenbruchteilen. Eingabefelder duerfen nie im Takt der Messwerte
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

  function colorFor(value, tol) {
    if (!available()) return COLORS.off;
    if (Math.abs(value) <= tol) return COLORS.ok;
    return Math.abs(value) > 2 * tol ? COLORS.bad : COLORS.warn;
  }

  function bar(label, value, tol, text) {
    var color = colorFor(value, tol);
    var left = Math.max(-150, Math.min(150, value * 16));
    var b = el(
      '<div class="bar"><div class="lab">' + label + '</div>' +
      '<div class="val"></div><div class="track"></div><div class="bub"></div></div>'
    );
    var v = b.querySelector(".val");
    v.textContent = text;
    v.style.color = color;
    var bub = b.querySelector(".bub");
    bub.style.left = "calc(50% + " + Math.round(left) + "px)";
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
    var level = ok && Math.abs(pitch) <= tolP && Math.abs(roll) <= tolR;

    var textR = !ok ? "⚠️ Kein Sensorwert"
      : Math.abs(roll) <= tolR ? "✅ EBEN – STOP"
        : (roll > 0 ? "LINKE Seite hoch" : "RECHTE Seite hoch");
    var textP = !ok ? "⚠️ Kein Sensorwert"
      : Math.abs(pitch) <= tolP ? "✅ EBEN – STOP"
        : (pitch > 0 ? "HECK hoch" : "FRONT hoch");

    target.appendChild(bar("QUER", roll, tolR, textR));
    target.appendChild(bar("LÄNGS", pitch, tolP, textP));

    var plan = el('<div class="plan"></div>');
    var head = level ? "✅ EBEN – STOP" : ok ? "Ausrichten" : "⚠️ Kein Sensorwert";
    var html = "<h2>" + head + "</h2>";
    if (ok) {
      html += '<div class="muted">Längs ' + pitch.toFixed(1) + "° · Quer " + roll.toFixed(1) + "°" +
        (state.motion ? " · in Bewegung" : "") + "</div>";
      var lifts = level ? [] : (wheelLifts() || []);
      var names = isCaravan() ? CARAVAN_WHEEL_NAMES : WHEEL_NAMES;
      var label = function (i) { return names[i.wheel] || WHEEL_NAMES[i.wheel] || i.wheel; };

      if (lifts.length) {
        html += "<ul>";
        if (isCaravan()) {
          // Beide Schritte auf einmal, aber in fester Reihenfolge - und mit
          // Richtung, weil das Stuetzrad auch runter kann.
          lifts.forEach(function (i) {
            html += "<li><b>" + label(i) + "</b> " + i.direction + ", " +
              (i.steps ? "Keilstufe " + i.steps : i.cm.toFixed(1) + " cm") + "</li>";
          });
          html += "</ul>";
          html += '<div class="muted">' + (lifts.length > 1
            ? "Erst das Rad auf den Keil, dann das Stützrad – das Auffahren kippt den Wagen längs mit."
            : "Danach neu messen.") + "</div>";
        } else if (cfg.method === "hebesystem") {
          lifts.forEach(function (i) {
            html += "<li><b>" + label(i) + "</b> " + i.cm.toFixed(1) + " cm</li>";
          });
          html += '</ul><div class="muted">Alle Stützen auf einmal, höchste zuerst. Das nicht genannte Rad bleibt stehen.</div>';
        } else {
          var first = lifts[0];
          html += "<li><b>" + label(first) + "</b> " +
            (first.steps ? "Keilstufe " + first.steps : first.cm.toFixed(1) + " cm") + "</li></ul>" +
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
      : (Math.abs(pitch) <= tolP && Math.abs(roll) <= tolR) ? COLORS.ok
        : (Math.abs(pitch) > 2 * tolP || Math.abs(roll) > 2 * tolR) ? COLORS.bad : COLORS.warn;
    var top = el('<div class="top"><div class="cap">▲ VORNE</div></div>');
    top.appendChild(el(isCaravan() ? CARAVAN_TOP : CAMPER_TOP));
    top.appendChild(el('<div class="ring"></div>'));
    var bubTop = el('<div class="bub"></div>');
    var lim = function (v, max) { return Math.max(-max, Math.min(max, v)); };
    bubTop.style.position = "absolute";
    bubTop.style.borderRadius = "50%";
    bubTop.style.left = "calc(50% + " + Math.round(lim(-roll * 13, 64)) + "px)";
    bubTop.style.top = "calc(50% + " + Math.round(lim(pitch * 13, 118)) + "px)";
    bubTop.style.background = "radial-gradient(circle at 34% 30%,#fff," + overall + " 62%)";
    bubTop.style.boxShadow = "0 4px 12px rgba(0,0,0,.45),0 0 16px " + overall;
    top.appendChild(bubTop);
    target.appendChild(top);

    var clamp = function (v) { return Math.max(-30, Math.min(30, v)); };
    target.appendChild(view(isCaravan() ? CARAVAN_SIDE : CAMPER_SIDE,
      "SEITE · längs — " + (ok ? pitch.toFixed(1) + "°" : "⚠️"),
      colorFor(pitch, tolP), ok ? clamp(pitch) : 0));
    target.appendChild(view(isCaravan() ? CARAVAN_REAR : CAMPER_REAR,
      "HECK · quer — " + (ok ? roll.toFixed(1) + "°" : "⚠️"),
      colorFor(roll, tolR), ok ? clamp(-roll) : 0));

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
   * damit syncSettings() spaeter nur die Werte nachziehen kann. */
  var settingInputs = {};
  var methodSelect = null;
  var vehicleSelect = null;
  var settingsNote = null;

  function settings() {
    settingInputs = {};
    var box = el('<div class="plan"><h2>Fahrzeug</h2></div>');
    // Beim Wohnwagen misst dieselbe Zahl etwas anderes - deshalb die
    // Beschriftung mitfuehren statt sie fest hinzuschreiben.
    var rows = [
      ["wheelbase", isCaravan() ? "Achse → Stützrad (mm)" : "Radstand (mm)"],
      ["track", "Spurweite (mm)"],
      ["tolerance_cm", "Toleranz (cm)"],
      ["wedge_step", "Keilstufe (cm, 0 = aus)"]
    ];
    rows.forEach(function (r) {
      var row = el('<div class="set"><span>' + r[1] + "</span></div>");
      var input = el('<input type="number" step="any">');
      input.value = cfg[r[0]];
      input.onchange = function () {
        var v = parseFloat(input.value);
        if (!isNaN(v)) setNumber(r[0], v);
      };
      settingInputs[r[0]] = input;
      row.appendChild(input);
      box.appendChild(row);
    });

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
    // Beim Wohnwagen ohne Bedeutung: laengs kurbelt man am Stuetzrad, quer
    // faehrt man auf. Ein Hebesystem gibt es dort nicht.
    if (!isCaravan()) box.appendChild(mrow);

    settingsNote = el('<div class="muted" style="margin-top:8px"></div>');
    box.appendChild(settingsNote);
    return box;
  }

  /* Werte nachziehen, ohne die Felder anzufassen, in denen gerade getippt
   * wird. Sonst spraenge der Text waehrend der Eingabe zurueck - genau der
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

  /* Ueberschriften je Bereich. Das Geraet liefert seine Kennungen als
   * "<bereich>-<name>" (je nach Fassung auch mit Schraegstrich), sonst nichts
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
   * Technik zeigt Ablesewerte, keine Bedienelemente. Drei Gruende:
   *
   *   button - Aktionen, keine Werte. Als Zeile mit Zustand sinnlos, und
   *            jede davon gibt es an der passenden Stelle als echten Knopf.
   *   text   - hier stuende das WLAN-Passwort im Klartext in einer Liste.
   *   update - meldet "unknown", solange nicht geprueft wurde. Direkt unter
   *            unserer korrekten Versionsanzeige gelesen wirkt das wie ein
   *            Widerspruch, obwohl beides stimmt.
   *
   * number und select sind die Fahrzeugmasse - die stehen auf der Anzeige
   * und waeren hier eine zweite Darstellung derselben Sache.
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

    // Bekannte Bereiche in fester Reihenfolge, alles Uebrige hinten dran.
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

  /* Aktualisierung von Hand - der Weg fuer die Betriebsart ohne Home
   * Assistant. Ausgeloest wird die Taste im Geraet, die ihrerseits die neue
   * Firmware von GitHub holt. Fuer Update-Entitaeten gibt es keinen
   * dokumentierten REST-Endpunkt, fuer Tasten schon. */
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

    /* Weg ohne Internet: Datei vom Handy hochladen. Moeglich durch
     * "ota: platform: web_server" in der Firmware.
     *
     * ACHTUNG: ESPHome dokumentiert den Endpunkt dieses Formulars nicht -
     * /update mit dem Feldnamen "file" ist der uebliche Weg, aber ungeprueft.
     * Schlaegt es fehl, sagt die Seite das ausdruecklich statt stumm zu
     * bleiben, und nennt den Ausweg. Beim ersten echten Build pruefen. */
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

  /* WLAN-Einrichtung. Uebernimmt die Aufgabe des Captive Portals, das dafuer
   * entfaellt: Es haette im eigenen Netz jede Seitenanfrage abgefangen und
   * die Wasserwaage unerreichbar gemacht.
   *
   * Freiwillig - ohne WLAN funktioniert alles ausser den automatischen
   * Updates. Deshalb steht es unter Technik und nicht auf der Anzeige. */
  function wifiSetup() {
    var box = el('<div class="plan"><h2>WLAN</h2></div>');
    box.appendChild(el('<div class="muted">Nur nötig für automatische Updates und Home Assistant. Ohne WLAN läuft alles Übrige weiter.</div>'));

    var ssid = el('<input type="text" placeholder="Netzwerkname" style="width:100%;margin-top:10px">');
    var pass = el('<input type="password" placeholder="Passwort" style="width:100%;margin-top:8px">');
    var btn = el('<button class="act ghost" style="margin-top:10px">Speichern und verbinden</button>');
    // white-space: pre-line, damit der Absatz im Erfolgstext wirkt.
    var note = el('<div class="muted" style="margin-top:10px;line-height:1.5;white-space:pre-line"></div>');

    /* Rueckmeldung deutlich, nicht als graue Randnotiz: Nach dem Neustart
     * verschwindet dieses Netz, und die Seite kann dann nichts mehr sagen.
     * Was hier steht, ist das Letzte, was der Nutzer sieht. */
    function say(text, kind) {
      note.textContent = text;
      note.style.color = kind === "bad" ? "#ff7a7a" : kind === "good" ? "#37d67a" : "#cfd6de";
      note.style.fontWeight = kind ? "700" : "400";
    }

    /* Wartet, bis das Geraet den gespeicherten Namen ueber den Ereignisstrom
     * zurueckmeldet. Das ist der einzige echte Beweis, dass die Eingabe
     * angekommen ist - eine erfolgreiche HTTP-Antwort sagt nur, dass die
     * Anfrage entgegengenommen wurde. */
    function awaitEcho(expected, timeoutMs, done) {
      var waited = 0;
      var timer = window.setInterval(function () {
        // Auch hier ueber Teilstring statt fester Kennung - siehe objectId().
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

      // Nacheinander, nicht gleichzeitig: der Knopf im Geraet liest beide
      // Felder, sie muessen also vorher angekommen sein.
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
              "Achte auf die WLAN-Liste deines Handys: Verschwindet das Netz CamperMaid " +
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

    /* Werksreset. Steht bewusst hier unten und nicht bei den Bedienelementen
     * oben - er loescht WLAN, Kalibrierung und Fahrzeugmasse auf einmal. */
    box.appendChild(el('<div class="grouphead" style="margin-top:22px">Zurücksetzen</div>'));
    var rnote = el('<div class="muted"></div>');
    rnote.textContent = "Löscht WLAN-Zugangsdaten, Kalibrierung und Fahrzeugmaße. " +
      "Das Gerät startet danach neu und öffnet wieder sein eigenes Netz.";
    box.appendChild(rnote);

    var reset = el('<button class="act ghost" style="margin-top:10px">Auf Werkseinstellungen zurücksetzen</button>');
    reset.onclick = function () {
      if (!window.confirm("Wirklich zurücksetzen?\n\nWLAN, Kalibrierung und Fahrzeugmaße gehen verloren. Das Gerät muss danach neu eingerichtet und neu kalibriert werden.")) return;
      reset.disabled = true;
      reset.textContent = "Setze zurück …";
      press("werkseinstellungen", function () {
        rnote.textContent = "Zurückgesetzt. Das Gerät startet neu – verbinde dich anschließend wieder mit dem Netz CamperMaid.";
      });
    };
    box.appendChild(reset);
    return box;
  }

  /* Erwartet den fertigen Pfad aus pathFor(), nicht die Kennung - der Pfad
   * kommt vom Geraet und wird hier nicht mehr zusammengesetzt. */
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

  /* Die tatsaechliche Objektkennung aus dem Ereignisstrom holen, statt sie
   * fest hinzuschreiben.
   *
   * ESPHome bildet sie aus dem Namen ("WLAN Name" -> "wlan_name"), aber die
   * Regel hat sich zwischen Fassungen schon geaendert, und ein falscher Name
   * scheitert stumm mit 404. Das Geraet meldet seine Kennungen ohnehin - also
   * fragen wir es, statt zu raten. Der Rueckfallwert greift nur, solange noch
   * nichts empfangen wurde. */
  function objectId(domain, needle, fallback) {
    for (var id in state.seen) {
      var parts = splitId(id);
      if (parts[0] === domain && parts[1].indexOf(needle) >= 0) return parts[1];
    }
    return fallback;
  }

  /* Den REST-Pfad einer Entitaet, wie das Geraet ihn selbst angibt.
   *
   * Rueckgabe etwa "/number/radstand". Findet sich nichts, kommt null - dann
   * wird gar nicht erst geschrieben, statt auf gut Glueck eine Adresse zu
   * bauen und den 404 zu verschlucken. */
  function pathFor(domain, needle) {
    for (var id in state.seen) {
      var parts = splitId(id);
      if (parts[0] !== domain || parts[1].indexOf(needle) < 0) continue;
      var nid = state.seen[id].name_id;
      return nid ? "/" + nid : "/" + parts[0] + "/" + parts[1];
    }
    return null;
  }

  // -- Geraet ---------------------------------------------------------------

  /* Auch hier der Pfad vom Geraet. Kennt es die Taste nicht, wird nicht
   * blind gedrueckt - der Aufrufer erfaehrt es ueber einen Status 0. */
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
      /* name_id ist der REST-Pfad, den das Geraet selbst nennt - etwa
       * "sensor/accel_z" fuer /sensor/accel_z. Genau so uebernehmen, nicht
       * aus dem Namen bilden: Beide bisherigen Versuche, ihn zu erraten,
       * endeten in 404. Ein "name"-Feld gibt es in diesem Strom nicht. */
      state.seen[data.id] = {
        name_id: data.name_id || null,
        state: data.state
      };

      // Ueber Teilstrings statt die volle Kennung: dann haelt die Seite auch,
      // wenn jemand dem Geraet einen anderen Namen gibt.
      var id = data.id;
      if (id.indexOf("neigung_pitch") >= 0) state.pitch = num(data.value);
      else if (id.indexOf("neigung_roll") >= 0) state.roll = num(data.value);
      else if (id.indexOf("in_bewegung") >= 0) state.motion = data.value === true || data.state === "ON";
      else if (id.indexOf(IDS.wheelbase) >= 0) { cfg.wheelbase = num(data.value); state.ready = true; }
      else if (id.indexOf(IDS.track) >= 0) cfg.track = num(data.value);
      else if (id.indexOf(IDS.tolerance_cm) >= 0) cfg.tolerance_cm = num(data.value);
      else if (id.indexOf(IDS.wedge_step) >= 0) cfg.wedge_step = num(data.value);
      else if (id.indexOf(IDS.method) >= 0) cfg.method = data.state === METHOD_LIFT ? "hebesystem" : "keile";
      else if (id.indexOf(IDS.vehicle) >= 0) {
        var kind = data.state === VEHICLE_CARAVAN ? "wohnwagen" : "wohnmobil";
        if (kind !== cfg.vehicle) { cfg.vehicle = kind; render(); return; }
      }
      else return;
      // Nur der Messwertbereich - render() wuerde die Eingabefelder mitsamt
      // Inhalt neu anlegen, und zwar mehrmals pro Sekunde.
      update();
    });
    src.onerror = function () {
      // Verbindung weg: keine Werte mehr behaupten. Lieber "kein Sensorwert"
      // als eine eingefrorene Blase, die faelschlich eben anzeigt.
      //
      // Auch hier nur update(): ein Aussetzer waehrend der WLAN-Eingabe darf
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
