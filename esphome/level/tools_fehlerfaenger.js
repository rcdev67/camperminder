/* Fehlerfaenger - wird der Bedienoberflaeche voran gestellt.
 * ---------------------------------------------------------------------------
 * NUR FUER DIE FEHLERSUCHE. Auf dem Handy gibt es keine Browserkonsole, und
 * ein Fehler im Ereignisbehandler verpufft dort lautlos - genau daran ist am
 * 22.09.2026 ein ganzer Nachmittag vergangen.
 *
 * Diese Datei schreibt jeden unbehandelten Fehler gross sichtbar oben auf die
 * Seite, mitsamt Aufrufstapel. tools/baue_diagnose.py setzt sie vor
 * webui.js zusammen.
 */
(function () {
  var kasten = null;
  var gesehen = {};

  function zeige(text) {
    if (gesehen[text]) return;
    gesehen[text] = true;

    if (!kasten) {
      kasten = document.createElement("pre");
      kasten.style.cssText =
        "position:fixed;left:0;right:0;top:0;z-index:99999;margin:0;" +
        "max-height:60vh;overflow:auto;background:#5a1111;color:#ffd7d7;" +
        "font:12px/1.4 ui-monospace,monospace;padding:10px;" +
        "white-space:pre-wrap;word-break:break-all;" +
        "border-bottom:2px solid #ff6b6b";
      var anhaengen = function () { document.body.appendChild(kasten); };
      if (document.body) anhaengen();
      else document.addEventListener("DOMContentLoaded", anhaengen);
    }
    kasten.textContent += text + "\n\n";
  }

  window.addEventListener("error", function (e) {
    zeige("FEHLER: " + ((e.error && e.error.stack) || e.message));
  });

  window.addEventListener("unhandledrejection", function (e) {
    zeige("OFFENES VERSPRECHEN: " + (e.reason && (e.reason.stack || e.reason)));
  });
})();
