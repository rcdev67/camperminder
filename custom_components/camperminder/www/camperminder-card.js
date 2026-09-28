/*
 * CamperMinder - Lovelace-Karte
 *
 * Wird von der Integration selbst ausgeliefert und registriert. Kein card-mod,
 * keine Base64-Grafiken im CSS: als echtes Custom Element dürfen wir normales
 * SVG und normales CSS benutzen.
 *
 * Die Karte liest ihre Werte aus den Attributen des Phasen-Sensors. Dadurch
 * braucht sie genau eine Entität zu finden und kann Messwert und Schwelle
 * nicht aus verschiedenen Quellen mischen.
 */

const STATIC = "/camperminder_static";

/*
 * Die Nummer dieser Karte - im INHALT, nicht aus der Adresse.
 *
 * Bis 4.0.3 las die Karte sie aus der Adresse, unter der sie geladen wurde
 * ("?v=..."). Das war der Kern des Fehlers mit "3.5.2" in der Companion-App:
 * Die App hielt eine alte Seite mit einer alten Adresse im Zwischenspeicher,
 * und diese Adresse gab selbst neuen Code als "3.5.2" aus. Eine Nummer, die
 * am Verweis hängt statt am Code, beschreibt den Verweis.
 *
 * Eine zweite Wahrheit neben manifest.json ist es trotzdem nicht:
 * tools/build_release.ps1 bricht ab und tests/test_gleichlauf.py schlägt an,
 * sobald sie voneinander abweichen - wie bei SEITE_VERSION der Geräteseite.
 */
const VERSION = "4.2.2";

/* Ist Fassung a älter als Fassung b? "4.0.3" gegen "4.0.10" - zahlweise. */
function aelterAls(a, b) {
  const teile = (v) => String(v).split(/[.-]/).map((t) => (/^\d+$/.test(t) ? Number(t) : t));
  const x = teile(a);
  const y = teile(b);
  for (let i = 0; i < Math.max(x.length, y.length); i++) {
    const p = x[i] ?? 0;
    const q = y[i] ?? 0;
    if (p === q) continue;
    if (typeof p === "number" && typeof q === "number") return p < q;
    return String(p) < String(q);
  }
  return false;
}

/* Eine ältere Karte ersetzen - ohne dass jemand einen Zwischenspeicher leert.

   Läuft noch alter Code - die Companion-App hält die HA-Oberfläche samt
   Kartendatei im Zwischenspeicher, auch über einen Neustart der App -, dann:
   jede Adresse, unter der diese Karte geladen wurde, frisch vom Server holen
   (das überschreibt die alte Kopie im Zwischenspeicher), alte Einträge aus
   dem Cache Storage löschen und die Seite EINMAL neu laden.

   Einmal je Sitzung und Anlass: Hilft es nicht, bleibt der Hinweis stehen,
   statt die Seite endlos neu zu laden. Nie im Bearbeitungsmodus des
   Dashboards - dort gingen Änderungen verloren. Ein Fingertipp auf den
   Hinweis (erzwingen) übergeht beides. */
async function karteErneuern(anlass, erzwingen = false) {
  const schluessel = `camperminder-erneuert-${anlass}`;
  try {
    if (!erzwingen && sessionStorage.getItem(schluessel)) return false;
    sessionStorage.setItem(schluessel, "1");
  } catch (e) {
    // Ohne Gedächtnis kein selbsttätiges Neuladen - sonst droht eine Schleife.
    if (!erzwingen) return false;
  }
  if (!erzwingen && new URLSearchParams(window.location.search).has("edit")) return false;

  const adressen = new Set();
  try {
    for (const eintrag of performance.getEntriesByType("resource")) {
      if (eintrag.name.includes("camperminder-card.js")) adressen.add(eintrag.name);
    }
  } catch (e) {
    // Ohne Performance-Schnittstelle bleiben die Skript-Tags.
  }
  for (const skript of document.querySelectorAll('script[src*="camperminder-card.js"]')) {
    adressen.add(skript.src);
  }
  await Promise.all(
    [...adressen].map((adresse) => fetch(adresse, { cache: "reload" }).catch(() => undefined))
  );
  try {
    if (window.caches) {
      for (const name of await caches.keys()) {
        const speicher = await caches.open(name);
        for (const anfrage of await speicher.keys()) {
          if (anfrage.url.includes("camperminder-card.js")) await speicher.delete(anfrage);
        }
      }
    }
  } catch (e) {
    // Cache Storage ist nicht überall erreichbar - dann bleibt der HTTP-Weg.
  }
  window.location.reload();
  return true;
}

const COLORS = {
  ok: "#37d67a",
  warn: "#ffb020",
  bad: "#ff5c5c",
  off: "#6b7280",
};

/*
 * Für die Beschriftung unter Seiten- und Heckansicht: farbige Fläche,
 * dunkler Text. Farbige Schrift auf dunklem Grund ist am Handy schlecht zu
 * lesen - ausgerechnet Rot am schlechtesten, also genau dann, wenn es
 * wichtig wird. Rot und Grau sind hier aufgehellt, damit der dunkle Text auf
 * allen vier Flächen deutlich steht; auf hellem wie auf dunklem Design.
 */
const CHIP = {
  [COLORS.ok]: "#37d67a",
  [COLORS.warn]: "#ffb020",
  [COLORS.bad]: "#ff7a7a",
  [COLORS.off]: "#b0b7c3",
};
const CHIP_TEXT = "#10141a";

const TEXTS = {
  noSensor: "Kein Sensorwert",
  noSensorHint:
    "Das Nivelliergerät liefert gerade keine Werte – Anzeige nicht verwenden.",
  implausible: "Erst kalibrieren",
  implausibleHint: "Sensorwerte unrealistisch – bitte im Fahrzeug kalibrieren.",
  level: "EBEN – STOP",
  almost: "Fast geschafft",
  across: "QUER",
  along: "LÄNGS",
  front: "▲ VORNE",
  side: "SEITE · längs",
  rear: "HECK · quer",
  raiseLeft: "LINKE Seite hoch",
  raiseRight: "RECHTE Seite hoch",
  raiseRear: "HECK hoch",
  raiseFront: "FRONT hoch",
  step: "Keilstufe",
  hintWedge: "Eine Anweisung nach der anderen – nach dem Auffahren neu messen.",
  hintLift: "Alle Stützen auf einmal, höchste zuerst. Das nicht genannte Rad bleibt stehen.",
  hintCaravan: "Erst das Rad auf den Keil, dann das Stützrad – das Auffahren kippt den Wagen längs mit.",
  calibrate: "Neigung kalibrieren",
  calibrateDone: "Kalibriert",
  resetCalibration: "Kalibrierung zurücksetzen",
  resetCalibrationQuestion:
    "Kalibrierung zurücksetzen?\n\nDie Kalibrierung im Fahrzeug wird gelöscht. Danach gilt wieder die Werkskalibrierung – so, wie das Gerät ausgeliefert wurde.",
  resetCalibrationDone: "Zurückgesetzt – es gilt die Werkskalibrierung",
  factoryReset: "Werkseinstellungen",
  factoryResetQuestion:
    "Gerät auf Werkseinstellungen zurücksetzen?\n\nWLAN, die Kalibrierung im Fahrzeug und die Fahrzeugmaße werden gelöscht; die Werkskalibrierung bleibt erhalten.\n\nDas Gerät startet neu und ist danach NICHT MEHR in Home Assistant erreichbar – nur noch über sein eigenes Netz „CamperMinder“ (http://192.168.4.1), bis das WLAN dort neu eingetragen ist.",
  factoryResetDone: "Zurückgesetzt – das Gerät startet neu",
  thenJockey: "Danach das Stützrad – sein Maß folgt, wenn das Rad auf dem Keil steht.",
  outdated: "Diese Karte ist älter als die Integration (Karte {karte}, Integration {integration}) und wird gerade erneuert. Bleibt dieser Hinweis stehen: hier tippen.",
  restartNeeded: "Die Karte ist neuer als die laufende Integration (Karte {karte}, Integration {integration}). Home Assistant einmal neu starten, dann ist das Update abgeschlossen.",
  bTilt: "Neigung",
  bMotion: "Bewegung",
  bPos: "Lage",
  bOk: "ok",
  bFridge: "Kühlschrank!",
  bTilted: "schief",
  bTiltHint:
    "Über {grenze}° arbeitet ein Absorberkühlschrank nicht mehr zuverlässig.",
  bMotionHint:
    "Erschütterung – jemand steigt ein, Wind, der Nachbar rangiert. Kein Alarm.",
  bPosHint:
    "Weicht die Neigung von der Ruhelage ab, wurde das Fahrzeug bewegt.",
  moving: "in Bewegung",
  still: "steht ruhig",
  moved: "verändert!",
  notMoved: "unverändert",
  notFound:
    "Keine CamperMinder gefunden. Ist die Integration eingerichtet?",
};

const WHEEL_NAMES = {
  vorne_links: "Vorne links",
  vorne_rechts: "Vorne rechts",
  hinten_links: "Hinten links",
  hinten_rechts: "Hinten rechts",
  stuetzrad: "Stützrad",
};

/* Beim Wohnwagen sitzen beide Räder auf einer Achse - "hinten links" wäre
 * dort falsch. Und vorn steht kein Rad, sondern das Stützrad. */
const CARAVAN_WHEEL_NAMES = {
  hinten_links: "Linkes Rad",
  hinten_rechts: "Rechtes Rad",
  stuetzrad: "Stützrad",
};

const clamp = (value, limit) => Math.max(-limit, Math.min(limit, value));

/*
 * Der Maßstab der Anzeige ist die TOLERANZ, nicht das Grad.
 * ---------------------------------------------------------------------------
 * Vorher wanderte die Blase mit festen 16 px je Grad, und die grüne Mitte der
 * Skala war ein fester Streifen. Beides wusste nichts von der eingestellten
 * Toleranz - bei 5 cm Toleranz stand die Blase deshalb weit neben der Mitte,
 * während der Text daneben "EBEN - STOP" meldete. Zwei Aussagen, ein Zustand,
 * und die auffälligere von beiden war die falsche.
 *
 * Jetzt gilt: Toleranzgrenze = Rand der grünen Zone. Innerhalb der Toleranz
 * steht die Blase in der Mitte, und zwar in jeder Ansicht und auf beiden
 * Achsen - obwohl längs und quer bei gleicher Zentimeterangabe verschiedene
 * Gradzahlen bedeuten (5 cm sind 0,82° längs und 1,59° quer).
 *
 * Genauigkeit geht dabei nicht verloren, sie wandert: Wer die Neigung auf
 * Hundertstelgrad sehen will, schaltet den Präzisionsmodus ein. Dann ist die
 * Toleranz eine feste, viel engere Gradzahl - derselbe Maßstab, nur schärfer,
 * und die Blase zeigt wieder jede Regung.
 */

/* Vollausschlag der Wasserwaage in Prozent der Kachelbreite. Die Skala (.track)
 * steht 6 % vom Rand, ihre grüne Mitte liegt bei 45-55 % - das sind ±4,4 % der
 * Kachel um die Mitte. Beide Zahlen MÜSSEN zum Verlauf im CSS passen. */
const BAR_FULL = 40;
const BAR_TOLERANCE = 4.4;

/* Draufsicht in px: das Zielfeld (.ring) ist 56 px groß, also ±28 px. */
const TOP_TOLERANCE = 28;
const TOP_FULL_X = 64;
const TOP_FULL_Y = 118;

/* Jenseits der Toleranz staucht sich der Maßstab: bei doppelter Toleranz ist
 * ein Drittel des Restwegs verbraucht, bei fünffacher zwei Drittel, und den
 * Rand erreicht die Blase nie ganz. So bleibt auch eine grobe Schieflage im
 * Bild und zeigt weiter Veränderung, statt am Anschlag zu kleben. */
const OUTSIDE_K = 2;

function deflect(value, tolerance, atTolerance, full) {
  if (!(tolerance > 0)) return 0;
  const units = Math.abs(value) / tolerance;
  const out =
    units <= 1
      ? units * atTolerance
      : atTolerance + (full - atTolerance) * ((units - 1) / (units - 1 + OUTSIDE_K));
  return value < 0 ? -out : out;
}

class CamperMinderCard extends HTMLElement {
  /* Damit eine später geladene Fassung erkennt, wer schon definiert ist. */
  static get version() {
    return VERSION;
  }

  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._built = false;
    // Zuletzt angezeigte Zahlen - siehe _steady.
    this._shown = {};
  }

  setConfig(config) {
    this._config = { show_controls: true, ...config };
  }

  getCardSize() {
    return 12;
  }

  static getStubConfig() {
    return {};
  }

  set hass(hass) {
    this._hass = hass;
    const source = this._findSource(hass);
    if (!source) {
      this.shadowRoot.innerHTML = `<ha-card><div class="empty">${TEXTS.notFound}</div></ha-card>`;
      this._built = false;
      return;
    }
    // Auch neu aufbauen, wenn diese Karte noch mit dem Aufbau einer älteren
    // Fassung dasteht - nach einer Übernahme im laufenden Betrieb (uebernehmen).
    if (!this._built || this._gebautMit !== VERSION) {
      this._build();
    }
    this._render(source, hass);
    meldungenSenden(hass);
  }

  /* Die Quelle ist der Phasen-Sensor - erkennbar an seiner Rollenkennung. */
  _findSource(hass) {
    if (this._config && this._config.entity) {
      return hass.states[this._config.entity];
    }
    for (const state of Object.values(hass.states)) {
      if (state.attributes && state.attributes.camper_role === "phase") {
        return state;
      }
    }
    return null;
  }

  /* Bedienelemente derselben Integration, über ihre Rolle gefunden. */
  _findRole(hass, role) {
    for (const [entityId, state] of Object.entries(hass.states)) {
      if (state.attributes && state.attributes.camper_role === role) {
        return { entityId, state };
      }
    }
    return null;
  }

  _build() {
    this.shadowRoot.innerHTML = `
      <style>
        ha-card { padding: 12px; display: flex; flex-direction: column; gap: 12px; }
        .empty { padding: 24px; text-align: center; color: var(--secondary-text-color); }

        .bar {
          position: relative; height: 108px; border-radius: 16px;
          background: var(--card-background-color, #1b2029);
          border: 1px solid var(--divider-color, rgba(255,255,255,.08));
          overflow: hidden;
        }
        .bar .label {
          position: absolute; inset: 10px 0 auto 0; text-align: center;
          font-size: .8rem; letter-spacing: .18em; opacity: .65;
        }
        .bar .value {
          position: absolute; inset: 30px 0 auto 0; text-align: center;
          font-weight: 800; font-size: 1.1rem;
        }
        .track {
          position: absolute; left: 6%; right: 6%; top: 78px; height: 16px;
          margin-top: -8px; border-radius: 8px;
          background: linear-gradient(90deg,
            rgba(127,127,127,.18) 0%, rgba(127,127,127,.18) 45%,
            rgba(55,214,122,.35) 45%, rgba(55,214,122,.35) 55%,
            rgba(127,127,127,.18) 55%);
        }
        .bubble {
          position: absolute; top: 78px; width: 26px; height: 26px;
          margin: -13px 0 0 -13px; border-radius: 50%;
          transition: left .25s ease, background .25s ease;
        }

        .top {
          position: relative; height: 340px; border-radius: 20px;
          background: var(--card-background-color, #1b2029);
          border: 1px solid var(--divider-color, rgba(255,255,255,.08));
          overflow: hidden;
        }
        .top .caption {
          position: absolute; inset: 10px 0 auto 0; text-align: center;
          font-size: .78rem; letter-spacing: .2em; opacity: .6;
        }
        .top img { position: absolute; left: 50%; top: 50%;
          transform: translate(-50%, -50%); height: 290px; }
        /* Zielfeld, kein Kreis: Die Toleranz gilt je Achse, längs und quer
           getrennt. Der erlaubte Bereich ist deshalb ein Rechteck und keine
           Scheibe - bei einem Kreis läge die Blase mit beiden Achsen knapp
           innerhalb der Toleranz trotzdem außerhalb der Markierung. */
        .ring {
          position: absolute; left: 50%; top: 50%; width: 56px; height: 56px;
          margin: -28px 0 0 -28px; border-radius: 14px;
          border: 2px dashed rgba(127,127,127,.5);
        }
        /* Eckwerte in der Draufsicht - die Zahl steht dort, wo der Keil
           hin muss. Das ist der Unterschied zu einer Liste unter dem Bild:
           Man muss nicht übersetzen, welche Zeile welche Ecke meint. */
        /* Drei Badges: Neigung, Bewegung, Lage.

           Drei Themen, die NICHT das Ausrichten betreffen und deshalb eine
           eigene Zeile bekommen - mit drei Farben, die auf einen Blick sagen,
           ob etwas zu tun ist.

           Bewusst andere Farbwerte als die Nivellieranzeige: Dort heißt Grün
           "innerhalb der Toleranz", hier "alles in Ordnung". Gleiche Farbe für
           zwei verschiedene Aussagen wäre genau die Verwechslung, die eine
           Warnung wertlos macht. Wortgleich zur Geräteseite. */
        .badges { display: flex; gap: 8px; }
        .badge {
          flex: 1; min-width: 0; padding: 9px 8px; border-radius: 12px;
          text-align: center;
          background: var(--card-background-color, #1b2029);
          border: 1px solid var(--divider-color, rgba(255,255,255,.10));
        }
        .badge .bt {
          font-size: .66rem; letter-spacing: .14em; font-weight: 800;
          opacity: .75; text-transform: uppercase;
          white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        .badge .bs {
          margin-top: 3px; font-size: .9rem; font-weight: 800;
          white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        .badge.ok { background: #1e3326; border-color: #2f6b45; }
        .badge.ok .bs { color: #9fe3b8; }
        .badge.achtung { background: #4a3410; border-color: #ffb020; }
        .badge.achtung .bs { color: #ffd48a; }
        .badge.alarm { background: #4a1d1d; border-color: #b3564f; }
        .badge.alarm .bs { color: #ffd9d6; }
        .badge.aus .bs { color: #6f7885; }

        /* Wächterleiste. Sie steht ganz oben, aber nur, wenn es etwas zu
           sagen gibt: Wer den Wächter nicht benutzt, sieht die Karte
           unverändert. Scharf ohne Alarm bleibt bewusst zurückhaltend - eine
           Dauermeldung in Alarmfarbe gewöhnt man sich ab, und dann übersieht
           man den echten Fall. */
        .wache {
          display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
          margin-bottom: 10px; padding: 9px 12px; border-radius: 12px;
          font-size: .88rem; font-weight: 700;
          background: var(--card-background-color, #1b2029);
          border: 1px solid var(--divider-color, rgba(255,255,255,.10));
          color: var(--secondary-text-color);
        }
        .wache[hidden] { display: none; }
        .wache .satz { flex: 1; min-width: 0; }
        .wache.alarm {
          background: #4a1d1d; border-color: #b3564f; color: #ffd9d6;
          font-size: .95rem;
        }
        /* Selbstüberwachung: gelb, nicht rot. Hier nimmt nichts Schaden, hier
           stimmt nur eine Zahl womöglich nicht mehr. Rot bleibt dem
           Wächteralarm vorbehalten - sonst gewöhnt man sich an Rot. */
        .wache.hinweis {
          background: #4a3410; border-color: #ffb020; color: #ffd48a;
        }
        .wache button {
          border: 0; border-radius: 8px; padding: 7px 12px;
          font-size: .82rem; font-weight: 800; cursor: pointer;
          background: rgba(255,255,255,.14); color: inherit;
        }

        .ecke {
          position: absolute; min-width: 52px; text-align: center;
          padding: 3px 6px; border-radius: 8px; transform: translate(-50%, -50%);
          font-size: .82rem; font-weight: 800; font-variant-numeric: tabular-nums;
          background: rgba(12,16,22,.82); border: 1px solid rgba(255,255,255,.14);
          color: #cfd6de;
        }
        .ecke.tun { background: #4a3410; border-color: #ffb020; color: #ffd48a; }
        .ecke.fertig { color: #6f7885; }

        .top .bubble { width: 42px; height: 42px; margin: -21px 0 0 -21px;
          transition: all .3s ease; }

        /* Untereinander statt nebeneinander: nebeneinander bleibt für die
           Seitenansicht auf einem Handy nur die halbe Kartenbreite, und weil
           sie mehr als doppelt so breit wie hoch ist, schrumpft sie dabei auf
           gut die Hälfte der Heckansicht zusammen. */
        .views { display: flex; flex-direction: column; gap: 12px; }
        .view {
          position: relative; height: 220px; border-radius: 16px;
          background: var(--card-background-color, #1b2029);
          border: 1px solid var(--divider-color, rgba(255,255,255,.08));
          overflow: hidden;
        }
        .view .caption {
          position: absolute; left: 50%; top: 10px;
          transform: translateX(-50%);
          padding: 5px 14px; border-radius: 999px; white-space: nowrap;
          font-size: 1rem; font-weight: 800; letter-spacing: .01em;
          color: ${CHIP_TEXT};
        }
        .view .ground {
          position: absolute; left: 8%; right: 8%; bottom: 28px;
          border-top: 2px dashed rgba(127,127,127,.35);
        }
        .view img {
          position: absolute; left: 50%; bottom: 28px;
          transform-origin: 50% 100%;
          transition: transform .3s ease;
        }

        /* Gleich hohe Fahrzeuge bei jeder Kartenbreite: die Breiten stehen im
           Verhältnis der beiden Seitenverhältnisse (380:170 und 220:200).
           220/200 geteilt durch 380/170 ergibt die 49.2 % - damit rendern
           beide Bilder rechnerisch exakt gleich hoch, statt dass eines an der
           Breite und das andere an der Höhe hängenbleibt. Die max-width
           deckelt beide bei 140 px Höhe, sonst wächst die Seitenansicht auf
           breiten Bildschirmen aus der Kachel heraus. */
        #imgSide { width: 100%; max-width: 313px; }
        #imgRear { width: 49.2%; max-width: 154px; }


        .plan { font-size: .95rem; line-height: 1.55; }
        .plan h2 { margin: 0 0 4px; font-size: 1.15rem; }
        .plan ul { margin: 6px 0 0; padding-left: 1.1rem; }
        .plan li { margin: 2px 0; }
        .plan .muted { color: var(--secondary-text-color); }
        .plan .hint { margin-top: 6px; font-size: .82rem; }

        .controls { display: flex; flex-wrap: wrap; gap: 8px 18px; align-items: center;
          border-top: 1px solid var(--divider-color, rgba(255,255,255,.08));
          padding-top: 10px; }
        .controls label { display: flex; align-items: center; gap: 6px;
          font-size: .9rem; cursor: pointer; }
        .controls .knoepfe { display: flex; flex-wrap: wrap; gap: 8px; width: 100%; }
        .controls .knoepfe button { flex: 1 1 auto; padding: 7px 10px; border-radius: 8px;
          font-size: .85rem; cursor: pointer;
          border: 1px solid var(--divider-color, rgba(255,255,255,.2));
          background: var(--card-background-color, #1b2029);
          color: var(--primary-text-color, #e8ecf1); }
        .controls .knoepfe button:disabled { opacity: .6; cursor: default; }
        .controls select { padding: 5px 8px; border-radius: 8px; font-size: .9rem;
          border: 1px solid var(--divider-color, rgba(255,255,255,.2));
          background: var(--card-background-color, #1b2029);
          color: var(--primary-text-color, #e8ecf1); }

        /* Fußzeile: bewusst zurückhaltend. Sie soll im Betrieb nicht
           auffallen, im Supportfall aber ohne Nachfragen die Version zeigen. */
        .foot { margin-top: 10px; padding-top: 8px;
          border-top: 1px solid var(--divider-color, rgba(255,255,255,.08));
          display: flex; justify-content: space-between; gap: 10px;
          font-size: .72rem; color: var(--secondary-text-color);
          opacity: .75; }
        .foot a { color: inherit; text-decoration: none; }
        .foot a:hover { text-decoration: underline; }
      </style>

      <ha-card>
        <div class="wache hinweis" id="veraltet" hidden></div>
        <div class="wache hinweis" id="hinweis" hidden></div>
        <div class="wache" id="wache" hidden></div>

        <div class="bar" id="barRoll">
          <div class="label">${TEXTS.across}</div>
          <div class="value" id="valRoll"></div>
          <div class="track"></div>
          <div class="bubble" id="bubRoll"></div>
        </div>

        <div class="bar" id="barPitch">
          <div class="label">${TEXTS.along}</div>
          <div class="value" id="valPitch"></div>
          <div class="track"></div>
          <div class="bubble" id="bubPitch"></div>
        </div>

        <div class="plan" id="plan"></div>

        <div class="top">
          <div class="caption">${TEXTS.front}</div>
          <img id="imgTop" src="${STATIC}/camper_top.svg" alt="">
          <div class="ring"></div>
          <div class="ecke" id="eckeVL"></div>
          <div class="ecke" id="eckeVR"></div>
          <div class="ecke" id="eckeHL"></div>
          <div class="ecke" id="eckeHR"></div>
          <div class="bubble" id="bubTop"></div>
        </div>

        <div class="badges">
          <div class="badge" id="badgeNeigung"><div class="bt"></div><div class="bs"></div></div>
          <div class="badge" id="badgeBewegung"><div class="bt"></div><div class="bs"></div></div>
          <div class="badge" id="badgeLage"><div class="bt"></div><div class="bs"></div></div>
        </div>

        <div class="views">
          <div class="view">
            <div class="caption" id="capSide"></div>
            <div class="ground"></div>
            <img id="imgSide" src="${STATIC}/camper_side.svg" alt="">
          </div>
          <div class="view">
            <div class="caption" id="capRear"></div>
            <div class="ground"></div>
            <img id="imgRear" src="${STATIC}/camper_rear.svg" alt="">
          </div>
        </div>

        <div class="controls" id="controls"></div>

        <div class="foot">
          <span>© 2026 rcdev</span>
          <a href="https://github.com/rcdev67/camperminder" target="_blank"
             rel="noopener noreferrer">CamperMinder${VERSION ? " " + VERSION : ""}</a>
        </div>
      </ha-card>
    `;
    this._built = true;
    this._gebautMit = VERSION;
    // Der Neuaufbau setzt die Bilder auf die Wohnmobil-Fassung zurück.
    // Ohne das Vergessen hier würde _setArtwork den Wechsel verschlafen.
    this._artwork = null;
  }

  /* Zeichnungen zur Fahrzeugart. Nur bei echtem Wechsel angefasst - ein
     erneutes Setzen desselben src lässt den Browser die Datei neu holen und
     die Ansicht kurz flackern, und zwar bei jeder Messwertänderung. */
  _setArtwork(kind) {
    if (this._artwork === kind) return;
    this._artwork = kind;
    const root = this.shadowRoot;
    for (const [id, view] of [["imgTop", "top"], ["imgSide", "side"], ["imgRear", "rear"]]) {
      const node = root.getElementById(id);
      if (node) node.src = `${STATIC}/${kind}_${view}.svg`;
    }
  }

  /* Eine Zahl, die stehen bleibt.
   *
   * Der Messwert rauscht um wenige Hundertstelgrad, und über den Radstand
   * gerechnet werden daraus schnell ein paar Zehntel Zentimeter. Nackt
   * angezeigt wechselt die Zahl dadurch mehrmals je Sekunde zwischen zwei
   * Werten, obwohl das Fahrzeug still steht - und eine zappelnde Zahl liest
   * niemand, sie beunruhigt nur.
   *
   * Deshalb rastet die Anzeige auf ein Raster und verlässt es erst, wenn der
   * Messwert deutlich weiterwandert (0,75 Rasterschritte). Das ist keine
   * Glättung über die Zeit: Der angezeigte Wert weicht nie mehr als diese
   * 0,75 Schritte vom Messwert ab, und er hinkt einer echten Änderung nicht
   * hinterher. Im Präzisionsmodus ist das Raster entsprechend fein.
   */
  _steady(key, value, step) {
    const number = Number(value);
    if (value === null || value === undefined || Number.isNaN(number)) return null;
    const last = this._shown[key];
    if (last === undefined || Math.abs(number - last) >= step * 0.75) {
      this._shown[key] = Math.round(number / step) * step;
    }
    return this._shown[key];
  }

  _render(source, hass) {
    const a = source.attributes || {};
    const root = this.shadowRoot;
    this._setArtwork(a.vehicle_type === "wohnwagen" ? "caravan" : "camper");
    const caravanTop = a.vehicle_type === "wohnwagen";
    const available = a.sensors_available !== false && a.pitch !== null &&
      a.roll !== null && a.pitch !== undefined && a.roll !== undefined;
    const implausible = source.state === "unbekannt" && available;

    /* Die ABWEICHUNG vom Ziel des Profils - das ist es, was noch zu tun ist
       und was die Anzeige zeigt. Bei "Ausrichten" ist das Ziel null und alles
       wie zuvor.

       Der ECHTE Winkel bleibt in a.pitch/a.roll und wird weiter unten für die
       Neigungskachel gebraucht: Ein Absorberkühlschrank interessiert sich
       nicht dafür, wie jemand schlafen möchte. */
    const zielP = Number(a.target_pitch) || 0;
    const zielR = Number(a.target_roll) || 0;
    const pitch = available ? Number(a.pitch) - zielP : 0;
    const roll = available ? Number(a.roll) - zielR : 0;
    const tolP = Number(a.tolerance_pitch) || 0.82;
    const tolR = Number(a.tolerance_roll) || 1.59;
    const precise = a.precise === true;

    /* Rastermaß der Grad - so fein wie die angezeigte Stelle, nicht gröber.
       Es bremst nur das Flackern der letzten Stelle; wie ruhig es darüber
       hinaus zugeht, entscheidet der Regler "Anzeigeruhe" der Firmware.
       Zentimeter rastet die Karte nicht selbst: Die Anweisung kommt auf
       halbe Zentimeter gerastet aus der Integration, wie in der Firmware. */
    const stepDeg = precise ? 0.05 : 0.1;
    const deg = (key, value) => this._steady(key, value, stepDeg) ?? 0;

    /* Ob eine Achse eben steht, entscheidet der Rechenkern - dort trägt die
       Antwort eine Hysterese und ist damit die einzige, die nicht flattert.
       Der Rückfall auf den nackten Vergleich greift nur bei einer älteren
       Integration; dann ist die Karte unruhiger, aber nicht falsch. */
    const levelPitch = available &&
      (a.level_pitch === undefined ? Math.abs(pitch) <= tolP : a.level_pitch === true);
    const levelRoll = available &&
      (a.level_roll === undefined ? Math.abs(roll) <= tolR : a.level_roll === true);

    /* Steht die Achse innerhalb der Toleranz, zeigt die Anzeige die Mitte -
       Blase mittig, Fahrzeug waagerecht. Denn genau das ist die Aussage: Hier
       ist nichts mehr zu tun. Eine Blase, die dabei sichtbar neben der Mitte
       steht, widerspricht dem Text daneben.

       Im Präzisionsmodus bleibt die Feinlage stehen: Wer ihn einschaltet, will
       die letzten Zehntel sehen und nicht eine Anzeige, die sie wegräumt. */
    const centred = (level) => level && !precise;

    const colorFor = (value, tol, level) => {
      if (!available) return COLORS.off;
      if (level) return COLORS.ok;
      return Math.abs(value) > 2 * tol ? COLORS.bad : COLORS.warn;
    };

    const colRoll = colorFor(roll, tolR, levelRoll);
    const colPitch = colorFor(pitch, tolP, levelPitch);

    // --- Wasserwaagen ---
    const setBar = (valueId, bubbleId, value, tol, level, color, text) => {
      const val = root.getElementById(valueId);
      const bub = root.getElementById(bubbleId);
      val.textContent = text;
      val.style.color = color;
      const out = centred(level)
        ? 0
        : deflect(value, tol, BAR_TOLERANCE, BAR_FULL);
      bub.style.left = `calc(50% + ${out.toFixed(2)}%)`;
      bub.style.background =
        `radial-gradient(circle at 34% 30%, #fff, ${color} 62%)`;
      bub.style.boxShadow = `0 3px 8px rgba(0,0,0,.45), 0 0 12px ${color}`;
    };

    /* Nur die Richtung, wie auf der Geräteseite. Hier stand ein Achsmaß
       ("HECK hoch – noch 3,4 cm"); neben der Anweisung, die eine Ecke nennt,
       war das eine zweite Zahl für denselben Handgriff. */
    let textRoll;
    if (!available) textRoll = `⚠️ ${TEXTS.noSensor}`;
    else if (implausible) textRoll = TEXTS.implausible;
    else if (levelRoll) textRoll = `✅ ${TEXTS.level}`;
    else {
      textRoll = roll > 0 ? TEXTS.raiseLeft : TEXTS.raiseRight;
    }

    let textPitch;
    if (!available) textPitch = `⚠️ ${TEXTS.noSensor}`;
    else if (implausible) textPitch = TEXTS.implausible;
    else if (levelPitch) textPitch = `✅ ${TEXTS.level}`;
    else {
      textPitch = pitch > 0 ? TEXTS.raiseRear : TEXTS.raiseFront;
    }

    setBar("valRoll", "bubRoll", roll, tolR, levelRoll, colRoll, textRoll);
    setBar("valPitch", "bubPitch", pitch, tolP, levelPitch, colPitch, textPitch);

    // --- Draufsicht ---
    const bubTop = root.getElementById("bubTop");
    const overall = !available
      ? COLORS.off
      : levelPitch && levelRoll
        ? COLORS.ok
        : Math.abs(pitch) > 2 * tolP || Math.abs(roll) > 2 * tolR
          ? COLORS.bad
          : COLORS.warn;
    // Jede Achse an ihrer eigenen Toleranz gemessen: Innerhalb steht die Blase
    // im Zielfeld, außerhalb daneben - obwohl 5 cm längs und quer
    // verschiedene Winkel sind.
    const topX = centred(levelRoll)
      ? 0
      : deflect(-roll, tolR, TOP_TOLERANCE, TOP_FULL_X);
    const topY = centred(levelPitch)
      ? 0
      : deflect(pitch, tolP, TOP_TOLERANCE, TOP_FULL_Y);
    bubTop.style.left = `calc(50% + ${topX.toFixed(1)}px)`;
    bubTop.style.top = `calc(50% + ${topY.toFixed(1)}px)`;
    bubTop.style.background =
      `radial-gradient(circle at 34% 30%, #fff, ${overall} 62%)`;
    bubTop.style.boxShadow = `0 4px 12px rgba(0,0,0,.45), 0 0 16px ${overall}`;

    // --- Seiten- und Heckansicht, 1:1 geneigt ---
    //
    // Anders als die Blasen bleiben diese beiden am echten Winkel: Sie zeigen
    // das Fahrzeug, nicht eine Skala. Nur innerhalb der Toleranz stehen sie
    // waagerecht - sonst kippelte das Bild um Zehntelgrad weiter, während
    // daneben "EBEN - STOP" steht.
    const degSide = deg("pitch_deg", pitch);
    const degRear = deg("roll_deg", roll);

    /* Drei Badges: Neigung, Bewegung, Lage.
     *
     * Sie beantworten drei Fragen, die mit dem Ausrichten nichts zu tun haben
     * und die man sonst aus einer Liste zusammensuchen müsste: Leidet der
     * Kühlschrank? Ist gerade jemand am Fahrzeug? Steht es noch, wo es stand?
     *
     * Alle drei Zustände kommen aus dem Rechenkern, damit Karte, Geräteseite
     * und Automation dieselbe Aussage treffen. Sie stehen hier und nicht
     * weiter oben, weil sie die gerasteten Winkel von eben brauchen. */
    const setzeBadge = (id, titel, text, klasse, hinweis) => {
      const b = root.getElementById(id);
      b.className = `badge ${klasse}`;
      b.querySelector(".bt").textContent = titel;
      b.querySelector(".bs").textContent = text;
      b.title = hinweis || "";
    };
    const zahl = (wert) => wert.toFixed(1).replace(".", ",");

    if (!available) {
      setzeBadge("badgeNeigung", TEXTS.bTilt, "–", "aus");
      setzeBadge("badgeBewegung", TEXTS.bMotion, "–", "aus");
      setzeBadge("badgeLage", TEXTS.bPos, "–", "aus");
    } else {
      /* Drei Stufen statt an und aus - wortgleich zur Geräteseite.
       *
       * Was einen Absorberkühlschrank beschädigt, ist der Winkel MAL DER
       * ZEIT. Eine Kachel, die beim Rangieren rot wird, warnt, wo nichts ist
       * - und wer sie so kennt, sieht über sie hinweg, wenn es ernst wird.
       *
       * Gelb: steht schief, noch folgenlos. Rot: jetzt leidet er. Die Grenze
       * zieht das Gerät, das die Zeit ununterbrochen mitzählt. */
      const schraeg = a.tilt_warning === true;
      const kuehlWarn = a.fridge_warning === true;
      // Der ECHTE Winkel, nicht die Abweichung vom Ziel: Im Schlafprofil
      // steht das Fahrzeug absichtlich schief, und genau das muss die Kachel
      // zeigen - der Kühlschrank kennt kein Schlafprofil.
      const schiefste = available
        ? Math.max(Math.abs(Number(a.pitch)), Math.abs(Number(a.roll)))
        : 0;
      const min = Number(a.tilt_minutes);
      const wieLang = !Number.isFinite(min) || !schraeg
        ? ""
        : min < 1 ? " <1 min"
          : min < 60 ? ` ${Math.round(min)} min`
            : ` ${Math.round(min / 60)} h`;
      setzeBadge(
        "badgeNeigung",
        TEXTS.bTilt,
        `${zahl(schiefste)}° · ${
          kuehlWarn ? TEXTS.bFridge + wieLang
            : schraeg ? TEXTS.bTilted + wieLang
              : TEXTS.bOk
        }`,
        kuehlWarn ? "alarm" : schraeg ? "achtung" : "ok",
        // Der Satz kommt vom Gerät. Zwei Formulierungen für denselben Zustand
        // wären zwei Wahrheiten, sobald eine davon veraltet.
        schraeg && a.fridge_text
          ? a.fridge_text
          : TEXTS.bTiltHint.replace("{grenze}", zahl(Number(a.tilt_limit || 3)))
      );
      setzeBadge(
        "badgeBewegung",
        TEXTS.bMotion,
        a.in_motion === true ? TEXTS.moving : TEXTS.still,
        a.in_motion === true ? "achtung" : "ok",
        // Wann zuletzt jemand am Fahrzeug war, gehört zu genau dieser Frage -
        // und in den Hinweis statt in die Kachel, weil die Kachel den JETZIGEN
        // Zustand zeigt und für zwei Aussagen zu schmal ist.
        a.last_motion
          ? `${TEXTS.bMotionHint} Zuletzt: ${a.last_motion}.`
          : TEXTS.bMotionHint
      );
      setzeBadge(
        "badgeLage",
        TEXTS.bPos,
        a.position_changed === true ? TEXTS.moved : TEXTS.notMoved,
        a.position_changed === true ? "alarm" : "ok",
        TEXTS.bPosHint
      );
    }

    const tilt = (value, level) =>
      !available || centred(level) ? 0 : clamp(value, 30);
    const side = root.getElementById("imgSide");
    const rear = root.getElementById("imgRear");
    side.style.transform =
      `translateX(-50%) rotate(${tilt(degSide, levelPitch).toFixed(1)}deg)`;
    rear.style.transform =
      `translateX(-50%) rotate(${tilt(-degRear, levelRoll).toFixed(1)}deg)`;

    const places = precise ? 2 : 1;
    const capSide = root.getElementById("capSide");
    const capRear = root.getElementById("capRear");
    capSide.textContent = available
      ? `${TEXTS.side} — ${degSide.toFixed(places)}°`
      : `${TEXTS.side} — ⚠️`;
    capRear.textContent = available
      ? `${TEXTS.rear} — ${degRear.toFixed(places)}°`
      : `${TEXTS.rear} — ⚠️`;
    capSide.style.background = CHIP[colPitch];
    capRear.style.background = CHIP[colRoll];

    /* Vier Eckwerte, an ihrem Platz im Bild.
     *
     * Orange steht, was der wheel_plan verlangt - derselbe Wert wie in der
     * Anweisung darunter, sonst sucht der Nutzer den Unterschied. Räder, die
     * der Plan nicht nennt, zeigen grau den echten Höhenunterschied bis ganz
     * waagerecht (wheel_heights): Eine Achse in der Toleranz ist fertig, ihr
     * Rest bleibt aber sichtbar. Vorher stand dort "0", und im Stand sah man
     * nur noch Grad.
     *
     * Beim Wohnwagen tragen die hinteren Felder die beiden Räder der einen
     * Achse; vorne links zeigt das Stützrad, vorne rechts bleibt leer. */
    const hub = {};
    if (Array.isArray(a.wheel_plan)) {
      for (const item of a.wheel_plan) hub[item.wheel] = item;
    }
    const rest = a.wheel_heights || {};
    const zentimeter = (wert) => Math.abs(wert).toFixed(1).replace(".", ",");
    const setzeEcke = (id, schluessel, oben, links) => {
      const e = root.getElementById(id);
      e.style.top = oben;
      e.style.left = links;
      if (schluessel === null) { e.hidden = true; return; }
      e.hidden = false;
      const eintrag = hub[schluessel];
      if (!available) { e.textContent = "–"; e.className = "ecke fertig"; return; }
      if (eintrag) {
        const pfeil = eintrag.direction === "runter" ? "▼ " : "";
        e.textContent = pfeil + zentimeter(Number(eintrag.cm));
        e.className = "ecke tun";
        return;
      }
      const wert = Number(rest[schluessel]);
      if (!Number.isFinite(wert)) { e.textContent = "0"; e.className = "ecke fertig"; return; }
      // Nur das Stützrad kann negativ werden - dann ist es "runter".
      e.textContent = (wert <= -0.05 ? "▼ " : "") + zentimeter(wert);
      e.className = "ecke fertig";
    };

    if (caravanTop) {
      setzeEcke("eckeVL", "stuetzrad", "16%", "50%");
      setzeEcke("eckeVR", null, "20%", "78%");
      setzeEcke("eckeHL", "hinten_links", "78%", "22%");
      setzeEcke("eckeHR", "hinten_rechts", "78%", "78%");
    } else {
      setzeEcke("eckeVL", "vorne_links", "20%", "22%");
      setzeEcke("eckeVR", "vorne_rechts", "20%", "78%");
      setzeEcke("eckeHL", "hinten_links", "80%", "22%");
      setzeEcke("eckeHR", "hinten_rechts", "80%", "78%");
    }

    // --- Klartext ---
    this._renderPlan(root.getElementById("plan"), source, a, {
      available,
      implausible,
      pitch: degSide,
      roll: degRear,
      places,
      levelPitch,
      levelRoll,
    });

    this._renderVeraltet(root.getElementById("veraltet"), a);
    this._renderHinweis(root.getElementById("hinweis"), a);
    this._renderWache(root.getElementById("wache"), hass, a);

    if (this._config.show_controls) {
      this._renderControls(root.getElementById("controls"), hass, a);
    }
  }

  /* Selbstüberwachung.
   *
   * Meldungen, die sagen "traue der Anzeige gerade nicht". Die gehören nach
   * oben und nicht in eine Diagnoseliste, die niemand öffnet: Wer einer
   * verschobenen Kalibrierung vertraut, richtet sein Fahrzeug falsch aus und
   * merkt es nie. Eine Wasserwaage sagt einem nicht, dass sie lügt.
   *
   * Die Montage geht vor: Wenn der Sensor gar nicht mehr richtig sitzt, ist
   * die Frage nach der Kalibrierung zweitrangig. */
  /* Karte und Integration tragen verschiedene Nummern.

     Ist die Karte älter, läuft im Browser oder in der Companion-App noch der
     alte Code: Sie erneuert sich selbst (karteErneuern). Ist sie neuer, hat
     HACS die Dateien schon ersetzt, Home Assistant aber noch nicht neu
     gestartet - Neuladen hülfe dort nichts. */
  _renderVeraltet(node, a) {
    if (!node) return;
    const integration = a.integration_version;
    if (!integration || integration === VERSION) {
      node.hidden = true;
      return;
    }
    const aelter = aelterAls(VERSION, integration);
    const text = (aelter ? TEXTS.outdated : TEXTS.restartNeeded)
      .replace("{karte}", VERSION)
      .replace("{integration}", integration);
    node.hidden = false;
    node.textContent = `⚠️ ${text}`;
    if (aelter) {
      const anlass = `integration-${integration}`;
      node.style.cursor = "pointer";
      node.onclick = () => karteErneuern(anlass, true);
      karteErneuern(anlass);
    } else {
      node.style.cursor = "";
      node.onclick = null;
    }
  }

  _renderHinweis(node, a) {
    if (!node) return;
    const montage = a.mount_check === true;
    const kalib = a.calibration_check === true;

    if (!montage && !kalib) {
      node.hidden = true;
      node.dataset.signature = "";
      return;
    }

    const text = montage
      ? "Der Sensor liefert unglaubwürdige Werte – sitzt das Gehäuse noch " +
        "fest? Solange das so ist, stimmt die Anzeige nicht."
      : `Kalibrierung: ${a.calibration_text || "bitte prüfen"}`;

    if (node.dataset.signature === text) return;
    node.dataset.signature = text;
    node.hidden = false;
    node.textContent = `⚠️ ${text}`;
  }

  /* Die Wächterleiste.
   *
   * Sie zeigt den Satz des GERÄTS, nicht einen eigenen. Beim Zeitpunkt einer
   * Meldung wäre eine zweite Formulierung kein Schönheitsfehler: Stünde auf
   * der Geräteseite "03:14" und hier "vor 4 Stunden", wüsste niemand, welcher
   * Angabe er trauen soll.
   *
   * Unscharf und ohne Alarm bleibt die Leiste leer und unsichtbar - die Karte
   * sieht dann aus wie bisher. */
  _renderWache(node, hass, a) {
    if (!node) return;
    const alarm = a.guard_alarm === true;
    const scharf = a.guard === true;

    if (!alarm && !scharf) {
      node.hidden = true;
      node.dataset.signature = "";
      return;
    }

    const satz = a.guard_status || (alarm ? "ALARM" : "scharf");
    const signature = [alarm, scharf, satz, a.guard_ack_entity].join("|");
    if (node.dataset.signature === signature) return;
    node.dataset.signature = signature;

    node.hidden = false;
    node.className = alarm ? "wache alarm" : "wache";
    node.innerHTML = "";

    const zeile = document.createElement("div");
    zeile.className = "satz";
    zeile.textContent = (alarm ? "🚨 " : "🛡 ") + satz;
    node.appendChild(zeile);

    // Quittieren drückt den Knopf des GERÄTS. Eine eigene Nachbildung in Home
    // Assistant hätte den Alarm nur hier gelöscht - auf der Geräteseite stünde
    // er weiter, und der Wächter meldete ihn beim nächsten Takt erneut.
    if (alarm && a.guard_ack_entity && hass.states[a.guard_ack_entity]) {
      const knopf = document.createElement("button");
      knopf.textContent = "Quittieren";
      knopf.addEventListener("click", () => {
        knopf.disabled = true;
        hass.callService("button", "press", { entity_id: a.guard_ack_entity });
      });
      node.appendChild(knopf);
    }
  }

  /* Welches Ziel gerade gilt, als ein Satz. Leer bei "Ausrichten" - dann ist
     das Ziel eben, und darüber muss man kein Wort verlieren. */
  _zielSatz(a) {
    if (!a.profile || a.profile === "Ausrichten") return "";
    const laengs = Number(a.target_long_cm) || 0;
    const quer = Number(a.target_lat_cm) || 0;
    const zahl = (w) => Math.abs(w).toFixed(1).replace(".", ",");
    const teile = [];
    if (laengs) teile.push(`${laengs > 0 ? "Front" : "Heck"} ${zahl(laengs)} cm höher`);
    if (quer) teile.push(`${quer > 0 ? "rechts" : "links"} ${zahl(quer)} cm höher`);
    return teile.length
      ? `Profil <b>${a.profile}</b> – Ziel: ${teile.join(", ")}`
      : `Profil <b>${a.profile}</b> – Ziel: eben`;
  }

  _renderPlan(node, source, a, ctx) {
    if (!ctx.available) {
      node.innerHTML =
        `<h2>⚠️ ${TEXTS.noSensor}</h2><div class="muted">${TEXTS.noSensorHint}</div>`;
      return;
    }
    if (ctx.implausible) {
      node.innerHTML =
        `<h2>${TEXTS.implausible}</h2><div class="muted">${TEXTS.implausibleHint}</div>`;
      return;
    }

    const level = source.state === "eben";
    const almost = source.state === "fast";
    const heading = level ? `✅ ${TEXTS.level}` : almost ? TEXTS.almost : "Ausrichten";

    /* Die Anweisung der Integration - Ecke für Ecke, auf halbe Zentimeter
       gerastet, und wortgleich zum Satz der Firmware. Vorher baute die Karte
       eigene Zeilen: Achsen mit Keilen ("Heck noch 3,4 cm"), zusammengefasste
       Seiten, ungerastet. Dann sagten Karte und Gerät verschiedene Dinge. */
    const caravan = a.vehicle_type === "wohnwagen";
    const instruction = a.instruction || {};
    const steps = level || !Array.isArray(instruction.steps) ? [] : instruction.steps;
    const names = caravan ? CARAVAN_WHEEL_NAMES : WHEEL_NAMES;
    const rows = steps.map(
      (step) =>
        `<li><b>${names[step.wheel] || step.wheel}</b> ` +
        `${Number(step.cm).toFixed(1).replace(".", ",")} cm ${step.direction}` +
        `${step.wedge_steps ? ` – ${TEXTS.step} ${step.wedge_steps}` : ""}</li>`
    );
    if (rows.length && caravan && instruction.then) {
      rows.push(`<li class="muted">${TEXTS.thenJockey}</li>`);
    }

    /* Läuft ein Zielprofil, MUSS das hier stehen.
       Die Anzeige darüber rechnet dann gegen das Ziel - ohne diesen Satz
       stünde "EBEN – STOP", während das Fahrzeug sichtbar mit dem Heck hoch
       steht, und der Nutzer hielte das Gerät für kaputt. */
    const zielSatz = this._zielSatz(a);

    node.innerHTML = `
      <h2>${heading}</h2>
      <div class="muted">Längs ${ctx.pitch.toFixed(ctx.places).replace(".", ",")}° · Quer ${ctx.roll.toFixed(ctx.places).replace(".", ",")}°</div>
      ${zielSatz ? `<div class="muted hint">${zielSatz}</div>` : ""}
      ${rows.length ? `<ul>${rows.join("")}</ul>` : ""}
      ${rows.length ? `<div class="muted hint">${
        caravan
          ? TEXTS.hintCaravan
          : a.level_method === "hebesystem" ? TEXTS.hintLift : TEXTS.hintWedge
      }</div>` : ""}
    `;
  }

  _renderControls(node, hass, a) {
    const voice = this._findRole(hass, "voice");
    /* Den Präzisionsmodus führt das Gerät, sobald es ihn kennt - dann legt die
       Integration keinen eigenen Schalter an, und die Rollensuche findet
       nichts. Der Umweg über die Entity-ID aus den Attributen ist hier also
       kein Notnagel, sondern der Regelfall bei aktueller Firmware. */
    const precise =
      this._findRole(hass, "precise") ||
      (a.precise_entity && hass.states[a.precise_entity]
        ? { entityId: a.precise_entity, state: hass.states[a.precise_entity] }
        : null);
    /* Der Wächter wohnt ausschließlich im Gerät - es gibt dafür keine eigene
       Entität in dieser Integration, also auch keine Rolle zum Suchen. Sein
       Schalter steht hier bei den anderen, weil er dasselbe ist: ein Kippen,
       kein Messwert. */
    const wache =
      a.guard_entity && hass.states[a.guard_entity]
        ? { entityId: a.guard_entity, state: hass.states[a.guard_entity] }
        : null;

    /* Die Knöpfe des Geräts - dieselben wie auf der Geräteseite, und
       ausgelöst wird immer der Knopf DES GERÄTS. Die beiden, die etwas
       löschen, fragen vorher nach; kalibrieren tut es dort auch nicht. */
    const knoepfe = [
      [a.calibrate_entity, TEXTS.calibrate, null, TEXTS.calibrateDone],
      [a.calibration_reset_entity, TEXTS.resetCalibration,
        TEXTS.resetCalibrationQuestion, TEXTS.resetCalibrationDone],
      [a.factory_reset_entity, TEXTS.factoryReset,
        TEXTS.factoryResetQuestion, TEXTS.factoryResetDone],
    ].filter(([entityId]) => entityId && hass.states[entityId]);

    if (!voice && !precise && !wache && !a.profile_entity && !knoepfe.length) {
      node.innerHTML = "";
      return;
    }

    const signature = [
      voice && voice.state.state,
      precise && precise.state.state,
      wache && wache.state.state,
      a.profile,
      knoepfe.map(([entityId]) => entityId).join(","),
    ].join("|");
    if (node.dataset.signature === signature) return;
    node.dataset.signature = signature;

    node.innerHTML = "";
    for (const [item, label] of [
      [voice, "Sprachansage"],
      [precise, "Präzisionsmodus"],
      [wache, "Wächter"],
    ]) {
      if (!item) continue;
      const wrapper = document.createElement("label");
      const toggle = document.createElement("ha-switch");
      toggle.checked = item.state.state === "on";
      toggle.addEventListener("change", () => {
        hass.callService("switch", toggle.checked ? "turn_on" : "turn_off", {
          entity_id: item.entityId,
        });
      });
      wrapper.appendChild(toggle);
      wrapper.appendChild(document.createTextNode(label));
      node.appendChild(wrapper);
    }

    /* Das Zielprofil als Auswahl - dieselbe Bedienung wie auf der
       Geräteseite. Sie schaltet die Auswahl DES GERÄTS; eine eigene daneben
       hätte zwei Wahrheiten ergeben. */
    if (a.profile_entity && hass.states[a.profile_entity]) {
      const zustand = hass.states[a.profile_entity];
      const wrapper = document.createElement("label");
      wrapper.appendChild(document.createTextNode("Ziel"));
      const auswahl = document.createElement("select");
      for (const option of zustand.attributes.options || []) {
        const o = document.createElement("option");
        o.value = option;
        o.textContent = option;
        auswahl.appendChild(o);
      }
      auswahl.value = zustand.state;
      auswahl.addEventListener("change", () => {
        hass.callService("select", "select_option", {
          entity_id: a.profile_entity,
          option: auswahl.value,
        });
      });
      wrapper.appendChild(auswahl);
      node.appendChild(wrapper);
    }

    if (knoepfe.length) {
      const reihe = document.createElement("div");
      reihe.className = "knoepfe";
      for (const [entityId, label, frage, fertig] of knoepfe) {
        const knopf = document.createElement("button");
        knopf.textContent = label;
        knopf.addEventListener("click", () => {
          if (frage && !window.confirm(frage)) return;
          knopf.disabled = true;
          Promise.resolve(hass.callService("button", "press", { entity_id: entityId }))
            .then(() => { knopf.textContent = fertig; })
            .catch(() => { knopf.textContent = label; })
            .finally(() => {
              window.setTimeout(() => {
                knopf.disabled = false;
                knopf.textContent = label;
              }, 5000);
            });
        });
        reihe.appendChild(knopf);
      }
      node.appendChild(reihe);
    }
  }
}

/*
 * Zweimal registrieren wirft - und zwar bevor die Karte in customCards
 * eingetragen ist. Danach ist sie in der Auswahl unauffindbar, obwohl das
 * Element längst existiert. Passiert, sobald jemand die Datei zusätzlich von
 * Hand als Lovelace-Ressource einträgt.
 */
const TAG = "camperminder-card";

/* Meldungen an das Protokoll von Home Assistant - für das, was nur im
   Browser oder in der App geschieht und sonst niemand zu sehen bekommt.
   Gesendet wird beim nächsten "hass", weil erst dann eine Verbindung da ist.
   Zu finden unter Einstellungen -> System -> Protokolle, Logger
   "camperminder.karte". */
const meldungen = [];

function melden(text) {
  meldungen.push(text);
}

function meldungenSenden(hass) {
  if (!meldungen.length || !hass || typeof hass.callService !== "function") return;
  // Der Dienst system_log.write - einen Websocket-Befehl "system_log/write"
  // gibt es NICHT. Bis 4.0.5 stand hier genau der, und die Meldungen gingen
  // still verloren (.catch). Den Dienst gegen das HA im Wohnmobil geprüft.
  for (const message of meldungen.splice(0)) {
    Promise.resolve(
      hass.callService("system_log", "write", {
        message,
        level: "warning",
        logger: "camperminder.karte",
      })
    ).catch(() => undefined);
  }
}

/* Eine ältere, schon definierte Karte im laufenden Betrieb übernehmen.

   Die Companion-App hielt die Karte 3.5.2 über drei Updates hinweg fest -
   weder der Zwischenspeicher-Fix (4.0.3) noch das Neuladen (4.0.4) kamen an
   ihr vorbei, während Chrome auf demselben Handy längst 4.0.4 zeigte. Ein
   definiertes Custom Element lässt sich nicht ersetzen, seine Klasse aber
   schon: Alle Methoden der neuen Fassung kommen auf die alte Klasse, und
   jede vorhandene Karte baut sich beim nächsten "hass" neu auf (_gebautMit).
   Das braucht kein Neuladen und keinen Zwischenspeicher - nur, dass diese
   Datei überhaupt geladen wird. Der Konstruktor der alten Fassung bleibt;
   er legt dieselben Felder an (geprüft bis zurück zu 3.5.2). */
function uebernehmen(Alt) {
  for (const name of Object.getOwnPropertyNames(CamperMinderCard.prototype)) {
    if (name === "constructor") continue;
    Object.defineProperty(
      Alt.prototype, name, Object.getOwnPropertyDescriptor(CamperMinderCard.prototype, name)
    );
  }
  for (const name of Object.getOwnPropertyNames(CamperMinderCard)) {
    if (["length", "name", "prototype"].includes(name)) continue;
    Object.defineProperty(Alt, name, Object.getOwnPropertyDescriptor(CamperMinderCard, name));
  }
}

const vorhanden = customElements.get(TAG);
if (!vorhanden) {
  customElements.define(TAG, CamperMinderCard);
} else if (
  vorhanden !== CamperMinderCard &&
  (!vorhanden.version || aelterAls(vorhanden.version, VERSION))
) {
  const alteFassung = vorhanden.version || "ohne Nummer";
  uebernehmen(vorhanden);
  melden(
    `CamperMinder-Karte ${VERSION} hat eine ältere, schon geladene Karte ` +
      `(${alteFassung}) im laufenden Betrieb übernommen. ` +
      `Geladen von ${import.meta.url}. ` +
      `Service Worker: ${navigator.serviceWorker && navigator.serviceWorker.controller ? "ja" : "nein"}. ` +
      `Browser: ${navigator.userAgent}`
  );
}

window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === TAG)) {
  window.customCards.push({
    type: TAG,
    name: "CamperMinder",
    description:
      "Wasserwaagen, Draufsicht und Klartext-Anweisung für die Wohnmobil-Nivellierung.",
    preview: false,
  });
}

console.info("%c CAMPERMINDER-CARD %c geladen ", "background:#2fb6c9;color:#fff", "");
