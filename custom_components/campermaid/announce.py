"""Sprachansagen und Kalibrier-Selbsttest.

Die Ansagen haengen am PHASEN-WECHSEL, nicht an einem Zeittakt. Ein Zeittakt
mit cm-Text fuehrte zu einer Ansage alle drei Sekunden ("noch 2" / "noch 3" /
"noch 2" ...), weil der cm-Wert um rund einen Zentimeter zappelt und sich der
Text dadurch staendig aendert. Nicht zurueckbauen.
"""

from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.util import dt as dt_util

from .const import (
    ANNOUNCE_CM_STEP,
    ANNOUNCE_STABLE_SECONDS,
    CALIBRATION_CHECK_DELAY,
    CALIBRATION_MAX_RESIDUAL_DEG,
    CONF_CALIBRATE_BUTTON,
    CONF_NOTIFY_TTS,
    DIRECTION_PHASES,
    DOMAIN,
    PHASE_CLOSE,
    PHASE_FRONT,
    PHASE_LEFT,
    PHASE_LEVEL,
    PHASE_REAR,
    PHASE_RIGHT,
    POINT_JOCKEY,
    WHEEL_FRONT_LEFT,
    WHEEL_FRONT_RIGHT,
    WHEEL_REAR_LEFT,
    WHEEL_REAR_RIGHT,
)
from .coordinator import CamperCoordinator

_LOGGER = logging.getLogger(__name__)

SIDE_NAMES = {
    PHASE_LEFT: "Linke Seite",
    PHASE_RIGHT: "Rechte Seite",
    PHASE_REAR: "Heck",
    PHASE_FRONT: "Front",
}

WHEEL_NAMES = {
    WHEEL_FRONT_LEFT: "Vorne links",
    WHEEL_FRONT_RIGHT: "Vorne rechts",
    WHEEL_REAR_LEFT: "Hinten links",
    WHEEL_REAR_RIGHT: "Hinten rechts",
    POINT_JOCKEY: "Stützrad",
}

# Beim Wohnwagen sitzen beide Raeder auf einer Achse - "hinten links" waere
# dort schlicht falsch.
CARAVAN_NAMES = {
    WHEEL_REAR_LEFT: "Linkes Rad",
    WHEEL_REAR_RIGHT: "Rechtes Rad",
    POINT_JOCKEY: "Stützrad",
}

# Beim Auffahren auf einen Keil zaehlt jede Sekunde: drei Sekunden Wartezeit
# sind im Schritttempo etwa ein Meter. Die Stabilisierung ist gegen das
# Flattern an den Richtungsgrenzen gedacht - "eben" ist keine Grenze, sondern
# das Ziel. Deshalb geht diese eine Phase ohne Verzoegerung durch.
IMMEDIATE_PHASES = (PHASE_LEVEL,)


def _round_to_step(centimetres: float) -> int:
    """Auf 5-cm-Stufen runden, mindestens eine Stufe."""
    return max(round(centimetres / ANNOUNCE_CM_STEP) * ANNOUNCE_CM_STEP, ANNOUNCE_CM_STEP)


class CamperAnnouncer:
    """Beobachtet die Phase und sagt die Eckpunkte an."""

    def __init__(
        self, hass: HomeAssistant, coordinator: CamperCoordinator, config: dict
    ) -> None:
        self.hass = hass
        self.coordinator = coordinator
        self._config = config
        self._last_phase: str | None = None
        self._pending_phase: str | None = None
        self._cancel_pending = None
        self._cancel_button = None
        self._cancel_calibration = None

    # -- Lebenszyklus -------------------------------------------------------

    @callback
    def async_start(self) -> None:
        self._last_phase = self.coordinator.phase

        if button := self._config.get(CONF_CALIBRATE_BUTTON):
            self._cancel_button = async_track_state_change_event(
                self.hass, [button], self._handle_calibrate_pressed
            )

    @callback
    def async_stop(self) -> None:
        for cancel in (self._cancel_pending, self._cancel_button, self._cancel_calibration):
            if cancel is not None:
                cancel()
        self._cancel_pending = None
        self._cancel_button = None
        self._cancel_calibration = None

    # -- Ansagen ------------------------------------------------------------

    @callback
    def async_phase_changed(self) -> None:
        """Vom Rechenkern gerufen, sobald sich etwas geaendert hat."""
        phase = self.coordinator.phase
        if phase == self._last_phase:
            return

        # "Eben" darf nicht warten - siehe IMMEDIATE_PHASES.
        if phase in IMMEDIATE_PHASES:
            if self._cancel_pending is not None:
                self._cancel_pending()
                self._cancel_pending = None
            self._pending_phase = phase
            self._phase_settled(None)
            return

        # Alle anderen Phasen muessen erst eine Weile stabil stehen. Sonst
        # redet das System an der Grenze zwischen zwei Phasen ununterbrochen.
        if phase != self._pending_phase:
            self._pending_phase = phase
            if self._cancel_pending is not None:
                self._cancel_pending()
            self._cancel_pending = async_call_later(
                self.hass, ANNOUNCE_STABLE_SECONDS, self._phase_settled
            )

    @callback
    def _phase_settled(self, _now) -> None:
        self._cancel_pending = None
        phase = self.coordinator.phase
        if phase != self._pending_phase:
            return  # zwischenzeitlich weitergewandert

        self._last_phase = phase
        self._pending_phase = None

        if not self.coordinator.voice:
            return
        if not self.coordinator.in_motion:
            # Kein Manoever - sonst meldet sich das Fahrzeug nachts, wenn es
            # durch Temperaturgang knapp ueber die Schwelle driftet.
            return

        if (text := self.build_announcement(phase)) is not None:
            self.hass.async_create_task(self._async_speak(text))

    def build_announcement(self, phase: str) -> str | None:
        """Ansagetext zu einer Phase - oder None, wenn nichts zu sagen ist."""
        if phase == PHASE_LEVEL:
            return "Steht eben. Stopp."
        if phase == PHASE_CLOSE:
            if self.coordinator.uses_wedges:
                return "Fast geschafft. Ganz langsam."
            return "Fast geschafft. Nur noch feinjustieren."
        if phase not in DIRECTION_PHASES:
            return None

        # Wohnwagen: quer der Keil, laengs das Stuetzrad. Zwei verschiedene
        # Handgriffe an zwei Stellen - eine Richtungsansage waere hier
        # nutzlos.
        if self.coordinator.is_caravan:
            return self._build_caravan_announcement()

        # Mit Hydraulik oder Luftkissen steht das Fahrzeug. Dann ist nicht die
        # naechste Fahrtrichtung gefragt, sondern was an welcher Ecke zu tun
        # ist - und zwar alles auf einmal, weil nichts neu angefahren wird.
        if not self.coordinator.uses_wedges:
            return self._build_lift_announcement()

        if phase in (PHASE_LEFT, PHASE_RIGHT):
            centimetres = self.coordinator.correction_roll_cm
        else:
            centimetres = self.coordinator.correction_pitch_cm
        if centimetres is None:
            return None

        side = SIDE_NAMES[phase]
        if (steps := self.coordinator.wedge_steps_for(centimetres)) is not None:
            return f"{side} anheben, Keilstufe {steps}."
        return f"{side} anheben, etwa {_round_to_step(centimetres)} Zentimeter."

    def _build_caravan_announcement(self) -> str | None:
        """Wohnwagen: erst der Keil, dann das Stuetzrad.

        Die Reihenfolge kommt aus dem Rechenkern und ist keine Kosmetik - das
        Auffahren auf den Keil kippt den Wagen laengs mit. Wer zuerst kurbelt,
        kurbelt zweimal.
        """
        plan = self.coordinator.wheel_plan
        if not plan:
            return None

        teile = []
        for item in plan:
            name = CARAVAN_NAMES.get(item["wheel"], WHEEL_NAMES.get(item["wheel"], ""))
            if item.get("steps"):
                teile.append(f"{name} {item['direction']}, Keilstufe {item['steps']}")
            else:
                teile.append(f"{name} {item['direction']}, {item['cm']:.0f} Zentimeter")
        return ". ".join(teile) + "."

    def _build_lift_announcement(self) -> str | None:
        """Alle Stuetzen auf einmal - fuer Hydraulik und Luftkissen.

        Bewusst ohne Rundung auf 5-cm-Schritte: ein Hebesystem faehrt
        stufenlos, da waere Runden ein kuenstlich verschenkter Rest. Und
        bewusst hoechstes Rad zuerst, weil man dort anfaengt.
        """
        plan = self.coordinator.wheel_plan
        if not plan:
            return None

        teile = [
            f"{WHEEL_NAMES[item['wheel']]} {item['cm']:.0f} Zentimeter"
            for item in plan
        ]
        if len(teile) == 1:
            return f"{teile[0]} anheben."
        return f"Anheben: {', '.join(teile[:-1])} und {teile[-1]}."

    async def _async_speak(self, text: str) -> None:
        # Aus dem Rechenkern, nicht aus der Einrichtung: das Ziel ist eine
        # Entitaet und darf sich im laufenden Betrieb aendern.
        service = self.coordinator.notify_service
        if not service or "." not in service:
            _LOGGER.debug("Kein Ansageziel eingerichtet, Ansage entfaellt: %s", text)
            return

        domain, name = service.split(".", 1)
        if self._config.get(CONF_NOTIFY_TTS, True):
            # Muster der Home-Assistant-App unter Android: die Nachricht "TTS"
            # laesst das Telefon den Text vorlesen statt ihn anzuzeigen.
            payload = {"message": "TTS", "data": {"tts_text": text}}
        else:
            payload = {"message": text, "title": "Nivellierung"}

        try:
            await self.hass.services.async_call(domain, name, payload, blocking=False)
        except Exception:  # noqa: BLE001 - ein defektes Ansageziel darf nichts weiter stoeren
            _LOGGER.exception("Ansage ueber %s fehlgeschlagen", service)

    # -- Kalibrier-Selbsttest ----------------------------------------------

    @callback
    def _handle_calibrate_pressed(self, event: Event[EventStateChangedData]) -> None:
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")
        if new_state is None or new_state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return
        if old_state is None or old_state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            # Erster Zustand nach einem Neustart oder Wiederverbinden des
            # Geraets - kein echter Tastendruck.
            return

        self.coordinator.async_set_calibration(dt_util.utcnow())

        if self._cancel_calibration is not None:
            self._cancel_calibration()
        self._cancel_calibration = async_call_later(
            self.hass, CALIBRATION_CHECK_DELAY, self._check_calibration
        )

    @callback
    def _check_calibration(self, _now) -> None:
        """Nach dem Kalibrieren muessen beide Achsen bei ~0 stehen.

        Tun sie das nicht, rechnen Anzeige und gespeicherter Offset in der
        Firmware mit unterschiedlichen Achsen - ein Fehler, der sonst erst auf
        dem Stellplatz auffaellt, wenn alle Angaben falsch sind.
        """
        self._cancel_calibration = None
        pitch = self.coordinator.pitch
        roll = self.coordinator.roll
        if pitch is None or roll is None:
            return

        ok = (
            abs(pitch) <= CALIBRATION_MAX_RESIDUAL_DEG
            and abs(roll) <= CALIBRATION_MAX_RESIDUAL_DEG
        )
        notification_id = f"{DOMAIN}_kalibrierung"

        if ok:
            self.hass.async_create_task(
                self.hass.services.async_call(
                    "persistent_notification",
                    "dismiss",
                    {"notification_id": notification_id},
                    blocking=False,
                )
            )
            return

        message = (
            f"Fuenf Sekunden nach dem Kalibrieren steht laengs {pitch:.2f}° / quer "
            f"{roll:.2f}° statt 0.\n\n"
            "Moegliche Ursachen: das Fahrzeug hat sich waehrend des Tastendrucks "
            "bewegt, oder Anzeige und gespeicherter Offset in der Firmware rechnen "
            "mit unterschiedlicher Achszuordnung (axis_pitch / axis_roll). "
            "Bis dahin sind alle Zentimeterangaben falsch."
        )
        self.hass.async_create_task(
            self.hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "notification_id": notification_id,
                    "title": "Nivellierung: Kalibrierung hat nicht gegriffen",
                    "message": message,
                },
                blocking=False,
            )
        )
