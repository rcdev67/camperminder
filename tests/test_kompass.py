"""Die Kompassmessung der Karte, gegen eine nachgebaute Browserumgebung.

Die Funktion steht in camperminder-card.js, einer Browserdatei. Sie wird hier
aus dem Text geschnitten und in Node ausgefuehrt; ohne Node wird uebersprungen.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

KARTE = Path(__file__).parent.parent / "custom_components/camperminder/www/camperminder-card.js"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="Node fehlt")

LAUF = r"""
const fs = require("fs");
const src = fs.readFileSync(process.argv[2], "utf8");
const a = src.indexOf("async function kompassMessen");
const b = src.indexOf("const KOMPASS_FEHLER");
const kompassMessen = new Function(src.slice(a, b) + "; return kompassMessen;")();

function umgebung(opt) {
  const hoerer = {};
  const win = {
    isSecureContext: opt.sicher !== false,
    addEventListener: (n, f) => { (hoerer[n] = hoerer[n] || []).push(f); },
    removeEventListener: (n, f) => { hoerer[n] = (hoerer[n] || []).filter((g) => g !== f); },
  };
  if (opt.schnittstelle !== false) {
    win.DeviceOrientationEvent = function () {};
    if (opt.erlaubnis) win.DeviceOrientationEvent.requestPermission = async () => opt.erlaubnis;
  }
  if (opt.absolut) win.ondeviceorientationabsolute = null;
  setTimeout(() => {
    for (const [art, werte] of Object.entries(opt.ereignisse || {})) {
      for (const e of werte) (hoerer[art] || []).forEach((f) => f(e));
    }
  }, 5);
  return win;
}

(async () => {
  const fall = JSON.parse(process.argv[3]);
  const r = await kompassMessen(umgebung(fall), 50);
  console.log(JSON.stringify(r));
})();
"""


def messen(tmp_path, **fall):
    skript = tmp_path / "lauf.js"
    skript.write_text(LAUF, encoding="utf-8")
    ergebnis = subprocess.run(
        ["node", str(skript), str(KARTE), json.dumps(fall)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(ergebnis.stdout)


def test_android_absolut(tmp_path):
    # alpha 270 gegen den Uhrzeigersinn = Handy zeigt nach Osten (90 Grad)
    r = messen(tmp_path, absolut=True, ereignisse={
        "deviceorientationabsolute": [{"alpha": 270, "absolute": True}] * 3})
    assert round(r["grad"]) == 90


def test_ios_webkit_mit_erlaubnis(tmp_path):
    r = messen(tmp_path, erlaubnis="granted", ereignisse={
        "deviceorientation": [{"alpha": 5, "absolute": False, "webkitCompassHeading": 200}] * 3})
    assert round(r["grad"]) == 200


def test_ios_erlaubnis_abgelehnt(tmp_path):
    assert messen(tmp_path, erlaubnis="denied")["fehler"] == "abgelehnt"


def test_http_ist_unsicher_auch_ohne_schnittstelle(tmp_path):
    # Bei http fehlt DeviceOrientationEvent ganz - es ist trotzdem die Adresse.
    assert messen(tmp_path, sicher=False, schnittstelle=False)["fehler"] == "unsicher"


def test_schnittstelle_fehlt_trotz_https(tmp_path):
    r = messen(tmp_path, schnittstelle=False)
    assert r["fehler"] == "kein_sensor"
    assert "fehlt" in r["diagnose"]


def test_absolutes_ereignis_bekannt_aber_stumm_relatives_ohne_nord(tmp_path):
    # Relative Ereignisse ohne Nordbezug duerfen NICHT als Kompass gelten.
    r = messen(tmp_path, absolut=True, ereignisse={
        "deviceorientation": [{"alpha": 40, "absolute": False}] * 3})
    assert r["fehler"] == "keine_daten"
    assert "relativ 3" in r["diagnose"]


def test_absolutes_ereignis_ueber_den_normalen_kanal(tmp_path):
    # Manche Umgebungen melden absolute Werte als "deviceorientation".
    r = messen(tmp_path, ereignisse={
        "deviceorientation": [{"alpha": 180, "absolute": True}] * 3})
    assert round(r["grad"]) == 180


def test_mittelung_ueber_norden(tmp_path):
    # 359 und 1 Grad ergeben 0, nicht 180.
    r = messen(tmp_path, absolut=True, ereignisse={
        "deviceorientationabsolute": [{"alpha": 1, "absolute": True},
                                      {"alpha": 359, "absolute": True}]})
    assert round(r["grad"]) % 360 == 0
