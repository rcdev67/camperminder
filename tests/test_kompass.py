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
const a = src.indexOf("function kompassRichtung");
const b = src.indexOf("const KOMPASS_FEHLER");
const { kompassMessen, kompassLive } = new Function(src.slice(a, b) + "; return { kompassMessen, kompassLive };")();

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
  win._hoerer = hoerer;
  return win;
}

(async () => {
  const fall = JSON.parse(process.argv[3]);
  if (fall.live) {
    const werte = [];
    let still = false;
    const win = umgebung(fall);
    const r = await kompassLive((w) => werte.push(w), () => { still = true; }, win);
    if (r.fehler) { console.log(JSON.stringify(r)); return; }
    await new Promise((ok) => setTimeout(ok, fall.warte || 60));
    r.stop();
    const nachStop = werte.length;
    for (const e of (fall.nachher || [])) (win._hoerer.deviceorientationabsolute || []).forEach((f) => f(e));
    console.log(JSON.stringify({ werte, still, neuNachStop: werte.length - nachStop,
                                 abgemeldet: (win._hoerer.deviceorientationabsolute || []).length === 0 }));
    return;
  }
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


# -- Echte Geometrie: Haltung und Richtung unabhaengig von der Formel -------

import math


def _dreh(alpha, beta, gamma):
    """Rotation Z(alpha) X(beta) Y(gamma), wie W3C sie fuer Lagedaten festlegt."""
    a, b, g = (math.radians(w) for w in (alpha, beta, gamma))
    ca, sa, cb, sb, cg, sg = math.cos(a), math.sin(a), math.cos(b), math.sin(b), math.cos(g), math.sin(g)
    rz = [[ca, -sa, 0], [sa, ca, 0], [0, 0, 1]]
    rx = [[1, 0, 0], [0, cb, -sb], [0, sb, cb]]
    ry = [[cg, 0, sg], [0, 1, 0], [-sg, 0, cg]]

    def mal(m, n):
        return [[sum(m[i][k] * n[k][j] for k in range(3)) for j in range(3)] for i in range(3)]

    return mal(mal(rz, rx), ry)


def _richtung(vektor):
    """Kompassrichtung eines Vektors in Welt (x Ost, y Nord)."""
    return math.degrees(math.atan2(vektor[0], vektor[1])) % 360


def _anwenden(r, v):
    return [sum(r[i][k] * v[k] for k in range(3)) for i in range(3)]


def _winkel_gleich(a, b, eps=1.5):
    return abs((a - b + 180) % 360 - 180) <= eps


@pytest.mark.parametrize("alpha,beta,gamma", [
    (30, 90, 0),      # hochkant in der Halterung, Bildschirm zum Fahrer
    (200, 85, 5),     # leicht geneigt
    (310, 80, -10),
    (120, 95, 8),     # etwas nach hinten gekippt
    (75, 5, 85),      # Querformat hochkant (gamma gross)
])
def test_aufrecht_rueckseite_zeigt_in_blickrichtung(tmp_path, alpha, beta, gamma):
    r = _dreh(alpha, beta, gamma)
    wahr = _richtung(_anwenden(r, [0, 0, -1]))      # Rueckseite
    ergebnis = messen(tmp_path, absolut=True, ereignisse={
        "deviceorientationabsolute": [{"alpha": alpha, "beta": beta, "gamma": gamma,
                                       "absolute": True}] * 3})
    assert ergebnis["lage"] == "aufrecht"
    assert _winkel_gleich(ergebnis["grad"], wahr), (ergebnis["grad"], wahr)


@pytest.mark.parametrize("alpha", [0, 45, 135, 250, 359])
def test_flach_oberkante_zeigt_in_richtung(tmp_path, alpha):
    r = _dreh(alpha, 0, 0)
    wahr = _richtung(_anwenden(r, [0, 1, 0]))       # Oberkante
    ergebnis = messen(tmp_path, absolut=True, ereignisse={
        "deviceorientationabsolute": [{"alpha": alpha, "beta": 3, "gamma": -2,
                                       "absolute": True}] * 3})
    assert ergebnis["lage"] == "flach"
    assert _winkel_gleich(ergebnis["grad"], wahr, eps=4)


# -- Live-Betrieb ------------------------------------------------------------

def test_live_liefert_geglaettete_werte(tmp_path):
    ereignisse = [{"alpha": 270, "absolute": True}] * 5
    r = messen(tmp_path, live=True, absolut=True,
               ereignisse={"deviceorientationabsolute": ereignisse})
    assert len(r["werte"]) == 5
    assert all(round(w["grad"]) == 90 for w in r["werte"])
    assert r["werte"][0]["lage"] == "flach"


def test_live_glaettet_ueber_norden_ohne_sprung_durch_180(tmp_path):
    # 359 und 1 Grad: der Mittelwert darf nie in die Naehe von 180 geraten.
    folge = [{"alpha": 1, "absolute": True}, {"alpha": 359, "absolute": True}] * 4
    r = messen(tmp_path, live=True, absolut=True,
               ereignisse={"deviceorientationabsolute": folge})
    for w in r["werte"]:
        assert min(w["grad"], 360 - w["grad"]) < 5, w


def test_live_haltung_aufrecht(tmp_path):
    rot = _dreh(30, 90, 0)
    wahr = _richtung(_anwenden(rot, [0, 0, -1]))
    r = messen(tmp_path, live=True, absolut=True, ereignisse={
        "deviceorientationabsolute": [{"alpha": 30, "beta": 90, "gamma": 0, "absolute": True}] * 3})
    assert r["werte"][-1]["lage"] == "aufrecht"
    assert _winkel_gleich(r["werte"][-1]["grad"], wahr)


def test_live_stop_meldet_ab(tmp_path):
    r = messen(tmp_path, live=True, absolut=True,
               ereignisse={"deviceorientationabsolute": [{"alpha": 10, "absolute": True}]},
               nachher=[{"alpha": 99, "absolute": True}] * 3)
    assert r["abgemeldet"] is True
    assert r["neuNachStop"] == 0


def test_live_ohne_https_meldet_fehler(tmp_path):
    r = messen(tmp_path, live=True, sicher=False, schnittstelle=False)
    assert r["fehler"] == "unsicher"
