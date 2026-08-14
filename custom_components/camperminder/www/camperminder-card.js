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
 * Version für die Fußzeile - aus der eigenen Skriptadresse gelesen.
 *
 * Die Integration registriert die Karte als ".../camperminder-card.js?v=<Version
 * aus manifest.json>". Diese Angabe hier abzuschreiben hieße, eine zweite
 * Wahrheit zu pflegen, die früher oder später von der ersten abweicht. Also
 * fragen wir die Adresse, unter der wir selbst geladen wurden.
 *
 * Nebenwirkung, die uns gerade recht ist: Die Zeile zeigt genau dann eine neue
 * Nummer, wenn der Browser die Datei wirklich neu geholt hat. Bleibt sie nach
 * einem Update stehen, liegt noch die alte Fassung im Zwischenspeicher - das
 * ist dann kein Rätsel, sondern eine Anzeige.
 *
 * BEDINGUNG: Die Datei muss als Modul geladen werden. Beide Wege tun das -
 * add_extra_js_url legt sie ohne es5 unter den Modul-URLs ab, und die
 * Lovelace-Ressource trägt res_type "module". Wer das umstellt, bekommt hier
 * keinen leeren Wert, sondern einen Syntaxfehler beim Einlesen - und damit
 * keine Karte mehr.
 */
const VERSION = (() => {
  try {
    return new URL(import.meta.url).searchParams.get("v") || "";
  } catch (e) {
    return "";
  }
})();

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

/* Steht nur eine Achse schief, zieht der Rechenkern die beiden Räder derselben
 * Seite zu EINER Anweisung zusammen und liefert statt zweier Radpositionen eine
 * Seite. Ohne diese Namen stünde die rohe Kennung auf der Karte. */
const SIDE_NAMES = {
  links: "Linke Seite",
  rechts: "Rechte Seite",
  vorne: "Vorne",
  hinten: "Hinten",
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
    if (!this._built) {
      this._build();
    }
    this._render(source, hass);
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
          <div class="bubble" id="bubTop"></div>
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
    const available = a.sensors_available !== false && a.pitch !== null &&
      a.roll !== null && a.pitch !== undefined && a.roll !== undefined;
    const implausible = source.state === "unbekannt" && available;

    const pitch = available ? Number(a.pitch) : 0;
    const roll = available ? Number(a.roll) : 0;
    const tolP = Number(a.tolerance_pitch) || 0.82;
    const tolR = Number(a.tolerance_roll) || 1.59;
    const precise = a.precise === true;

    /* Rastermaß der Zahlen. Im Realitätsmodus grob genug, dass nichts mehr
       flackert - ein halber Zentimeter ist ohnehin die Grenze dessen, was mit
       Keil oder Stütze eingestellt werden kann. Im Präzisionsmodus fein. */
    const stepCm = precise ? 0.1 : 0.5;
    const stepDeg = precise ? 0.05 : 0.1;
    const cm = (key, value) => this._steady(key, value, stepCm);
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

    const cmRoll = cm("roll_cm", a.correction_roll_cm);
    const cmPitch = cm("pitch_cm", a.correction_pitch_cm);

    let textRoll;
    if (!available) textRoll = `⚠️ ${TEXTS.noSensor}`;
    else if (implausible) textRoll = TEXTS.implausible;
    else if (levelRoll) textRoll = `✅ ${TEXTS.level}`;
    else {
      const side = roll > 0 ? TEXTS.raiseLeft : TEXTS.raiseRight;
      textRoll = `${side} – ${this._distance(a, cmRoll, a.wedge_steps_roll)}`;
    }

    let textPitch;
    if (!available) textPitch = `⚠️ ${TEXTS.noSensor}`;
    else if (implausible) textPitch = TEXTS.implausible;
    else if (levelPitch) textPitch = `✅ ${TEXTS.level}`;
    else {
      const side = pitch > 0 ? TEXTS.raiseRear : TEXTS.raiseFront;
      textPitch = `${side} – ${this._distance(a, cmPitch, a.wedge_steps_pitch)}`;
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

    // --- Klartext ---
    this._renderPlan(root.getElementById("plan"), source, a, {
      available,
      implausible,
      pitch: degSide,
      roll: degRear,
      places,
      levelPitch,
      levelRoll,
      cmPitch,
      cmRoll,
      cm,
    });

    if (this._config.show_controls) {
      this._renderControls(root.getElementById("controls"), hass, a);
    }
  }

  _distance(attributes, centimetres, steps) {
    if (centimetres === null || centimetres === undefined) return "–";
    if (attributes.wedge_step > 0 && steps) {
      return `${TEXTS.step} ${steps}`;
    }
    return `noch ${Number(centimetres).toFixed(1)} cm`;
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

    const caravan = a.vehicle_type === "wohnwagen";
    const rows = level
      ? []
      : caravan
        ? this._caravanRows(a, ctx)
        : a.level_method === "hebesystem"
          ? this._liftRows(a, ctx)
          : this._wedgeRows(a, ctx);

    node.innerHTML = `
      <h2>${heading}</h2>
      <div class="muted">Längs ${ctx.pitch.toFixed(ctx.places)}° · Quer ${ctx.roll.toFixed(ctx.places)}°</div>
      ${rows.length ? `<ul>${rows.join("")}</ul>` : ""}
      ${rows.length ? `<div class="muted hint">${
        caravan
          ? (rows.length > 1 ? TEXTS.hintCaravan : TEXTS.hintWedge)
          : a.level_method === "hebesystem" ? TEXTS.hintLift : TEXTS.hintWedge
      }</div>` : ""}
    `;
  }

  /* Keile: eine Anweisung nach der anderen. Zwischen zwei Versuchen muss das
     Fahrzeug bewegt werden, eine Liste aller vier Räder wäre hier also
     nicht hilfreich, sondern verwirrend. */
  _wedgeRows(a, ctx) {
    const rows = [];
    if (!ctx.levelPitch) {
      const what = ctx.pitch > 0 ? "Heck" : "Front";
      rows.push(
        `<li><b>${what}</b> ${this._distance(a, ctx.cmPitch, a.wedge_steps_pitch)}</li>`
      );
    }
    if (!ctx.levelRoll) {
      const what = ctx.roll > 0 ? "Linke Seite" : "Rechte Seite";
      rows.push(
        `<li><b>${what}</b> ${this._distance(a, ctx.cmRoll, a.wedge_steps_roll)}</li>`
      );
    }
    return rows;
  }

  /* Wohnwagen: quer der Keil unter das tiefere Rad, längs das Stützrad.
     Mit Richtung, weil das Stützrad auch nach unten kann - und in der
     Reihenfolge aus dem Rechenkern, die nicht vertauscht werden darf. */
  _caravanRows(a, ctx) {
    if (!Array.isArray(a.wheel_plan)) return [];
    return a.wheel_plan.map((item) => {
      const name =
        CARAVAN_WHEEL_NAMES[item.wheel] ||
        WHEEL_NAMES[item.wheel] ||
        SIDE_NAMES[item.wheel] ||
        item.wheel;
      const wie = item.steps
        ? `Keilstufe ${item.steps}`
        : `${ctx.cm(`plan_${item.wheel}`, item.cm).toFixed(1)} cm`;
      return `<li><b>${name}</b> ${item.direction} – ${wie}</li>`;
    });
  }

  /* Hebesystem: alle Ecken auf einmal, höchste zuerst. Stufenlos, deshalb in
     Zentimetern statt in Stufen - und ohne Rundung, die es hier nicht braucht. */
  _liftRows(a, ctx) {
    if (!Array.isArray(a.wheel_plan)) return [];
    return a.wheel_plan.map(
      (item) =>
        `<li><b>${WHEEL_NAMES[item.wheel] || SIDE_NAMES[item.wheel] || item.wheel}</b> ${ctx
          .cm(`plan_${item.wheel}`, item.cm)
          .toFixed(1)} cm</li>`
    );
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
    if (!voice && !precise) {
      node.innerHTML = "";
      return;
    }

    const signature = [voice && voice.state.state, precise && precise.state.state].join("|");
    if (node.dataset.signature === signature) return;
    node.dataset.signature = signature;

    node.innerHTML = "";
    for (const [item, label] of [
      [voice, "Sprachansage"],
      [precise, "Präzisionsmodus"],
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
  }
}

/*
 * Zweimal registrieren wirft - und zwar bevor die Karte in customCards
 * eingetragen ist. Danach ist sie in der Auswahl unauffindbar, obwohl das
 * Element längst existiert. Passiert, sobald jemand die Datei zusätzlich von
 * Hand als Lovelace-Ressource einträgt.
 */
const TAG = "camperminder-card";

if (!customElements.get(TAG)) {
  customElements.define(TAG, CamperMinderCard);
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
