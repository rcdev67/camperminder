/* CamperMinder - Diagnoseseite
 * ---------------------------------------------------------------------------
 * NICHT die Bedienoberflaeche. Diese Datei tritt voruebergehend an ihre
 * Stelle (js_include in muster-supermini.yaml) und beantwortet genau eine
 * Frage: Was schickt das Geraet ueber /events, und kommt es an?
 *
 * Sie kennt keine Uebersetzung, keine Zustandsverwaltung, keine Skizzen -
 * nichts, was selbst kaputtgehen koennte. Jedes Ereignis wird roh angezeigt,
 * dazu ein Zaehler und der Zustand der Verbindung.
 */
(function () {
  var stil = document.createElement("style");
  stil.textContent =
    "body{background:#11151c;color:#dfe6ef;font:14px/1.5 system-ui,sans-serif;margin:0;padding:12px}" +
    "h1{font-size:16px;margin:0 0 8px}" +
    "#kopf{position:sticky;top:0;background:#11151c;padding-bottom:8px;border-bottom:1px solid #2a3340}" +
    "#zustand{font-weight:700}" +
    "pre{white-space:pre-wrap;word-break:break-all;margin:4px 0;font-size:12px}" +
    ".neu{color:#7ee081}";
  document.head.appendChild(stil);

  var kopf = document.createElement("div");
  kopf.id = "kopf";
  kopf.innerHTML =
    "<h1>CamperMinder – Diagnose</h1>" +
    "<div>Verbindung: <span id='zustand'>…</span></div>" +
    "<div>Ereignisse: <b id='zaehler'>0</b> · letztes vor <b id='alter'>–</b> s</div>" +
    "<div>Seite: <b>diagnose.js</b></div>";
  document.body.appendChild(kopf);

  var liste = document.createElement("div");
  document.body.appendChild(liste);

  var zustand = document.getElementById("zustand");
  var zaehler = document.getElementById("zaehler");
  var alter = document.getElementById("alter");
  var n = 0;
  var zuletzt = 0;

  setInterval(function () {
    alter.textContent = zuletzt ? Math.round((Date.now() - zuletzt) / 1000) : "–";
  }, 1000);

  function zeige(text) {
    var p = document.createElement("pre");
    p.className = "neu";
    p.textContent = text;
    liste.insertBefore(p, liste.firstChild);
    while (liste.childNodes.length > 40) liste.removeChild(liste.lastChild);
  }

  var src = new EventSource("/events");

  src.onopen = function () {
    zustand.textContent = "offen";
    zeige("-- Verbindung offen --");
  };

  src.onerror = function () {
    zustand.textContent = "Fehler / getrennt (readyState " + src.readyState + ")";
    zeige("-- Fehler, readyState " + src.readyState + " --");
  };

  src.addEventListener("state", function (ev) {
    n++;
    zuletzt = Date.now();
    zaehler.textContent = n;
    zeige(ev.data);
  });

  /* Auch alles andere zeigen, was hereinkommt - ping, log, was auch immer.
   * Gerade das, womit niemand rechnet, ist hier interessant. */
  src.onmessage = function (ev) {
    n++;
    zuletzt = Date.now();
    zaehler.textContent = n;
    zeige("(ohne Ereignisnamen) " + ev.data);
  };

  ["log", "ping", "state_detail_all"].forEach(function (name) {
    src.addEventListener(name, function (ev) {
      n++;
      zuletzt = Date.now();
      zaehler.textContent = n;
      zeige("[" + name + "] " + ev.data);
    });
  });
})();
