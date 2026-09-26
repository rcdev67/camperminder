"""Sprachansagen und Kalibrier-Selbsttest.

Die Ansagen hängen am PHASEN-WECHSEL, nicht an einem Zeittakt. Ein Zeittakt
mit cm-Text führte zu einer Ansage alle drei Sekunden ("noch 2" / "noch 3" /
"noch 2" ...), weil der cm-Wert um rund einen Zentimeter zappelt und sich der
Text dadurch ständig ändert. Nicht zurückbauen.
"""

from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.util import dt as dt_util

from .const import (
    ANNOUNCE_STABLE_SECONDS,
    CALIBRATION_CHECK_DELAY,
    CALIBRATION_MAX_RESIDUAL_DEG,
    CARAVAN_INSTRUCTION_NAMES,
    CONF_CALIBRATE_BUTTON,
    CONF_NOTIFY_TTS,
    DIRECTION_PHASES,
    DOMAIN,
    INSTRUCTION_NAMES,
    PHASE_CLOSE,
    PHASE_LEVEL,
)
from .coordinator import CamperCoordinator

_LOGGER = logging.getLogger(__name__)

# Beim Auffahren auf einen Keil zählt jede Sekunde: drei Sekunden Wartezeit
# sind im Schritttempo etwa ein Meter. Die Stabilisierung ist gegen das
# Flattern an den Richtungsgrenzen gedacht - "eben" ist keine Grenze, sondern
# das Ziel. Deshalb geht diese eine Phase ohne Verzögerung durch.
IMMEDIATE_PHASES = (PHASE_LEVEL,)


def _spoken_cm(centimetres: float) -> str:
    """Zahl zum Vorlesen: "4" statt "4,0", aber "4,5" bleibt."""
    if float(centimetres).is_integer():
        return str(int(centimetres))
    return f"{centimetres:.1f}".replace(".", ",")


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
        """Vom Rechenkern gerufen, sobald sich etwas geändert hat."""
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

        # Alle anderen Phasen müssen erst eine Weile stabil stehen. Sonst
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
            # Kein Manöver - sonst meldet sich das Fahrzeug nachts, wenn es
            # durch Temperaturgang knapp über die Schwelle driftet.
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
        return self._build_instruction_announcement()

    def _build_instruction_announcement(self) -> str | None:
        """Die Anweisung zum Vorlesen - dieselbe wie auf Karte und Geräteseite.

        Ecke für Ecke und auf halbe Zentimeter gerastet, aus coordinator.
        instruction. Vorher sprach die Ansage Achsen in 5-cm-Stufen ("Heck
        anheben, etwa 5 Zentimeter"), während der Bildschirm eine Ecke nannte -
        wer beides hört und liest, glaubt keinem von beiden.
        """
        instruction = self.coordinator.instruction
        if not instruction or not instruction["steps"]:
            return None
        steps = instruction["steps"]
        names = (
            CARAVAN_INSTRUCTION_NAMES if self.coordinator.is_caravan else INSTRUCTION_NAMES
        )
        # .get und kein direkter Zugriff: Ein unbekannter Schlüssel wäre hier
        # ein KeyError mitten in einer Ansage - also genau dann, wenn niemand
        # am Rechner sitzt. Lieber die rohe Kennung vorlesen als abbrechen.
        teile = [
            f"{names.get(step['wheel'], step['wheel'])} {_spoken_cm(step['cm'])}"
            for step in steps
        ]
        text = teile[0] if len(teile) == 1 else f"{', '.join(teile[:-1])} und {teile[-1]}"
        text += f" Zentimeter {steps[-1]['direction']}"
        if len(steps) == 1 and steps[0]["wedge_steps"]:
            text += f", Keilstufe {steps[0]['wedge_steps']}"
        if instruction["then"]:
            text += f", danach {names.get(instruction['then'], instruction['then'])}"
        return text + "."

    async def _async_speak(self, text: str) -> None:
        # Aus dem Rechenkern, nicht aus der Einrichtung: das Ziel ist eine
        # Entität und darf sich im laufenden Betrieb ändern.
        service = self.coordinator.notify_service
        if not service or "." not in service:
            _LOGGER.debug("Kein Ansageziel eingerichtet, Ansage entfällt: %s", text)
            return

        domain, name = service.split(".", 1)
        if self._config.get(CONF_NOTIFY_TTS, True):
            # Muster der Home-Assistant-App unter Android: die Nachricht "TTS"
            # lässt das Telefon den Text vorlesen statt ihn anzuzeigen.
            payload = {"message": "TTS", "data": {"tts_text": text}}
        else:
            payload = {"message": text, "title": "Nivellierung"}

        try:
            await self.hass.services.async_call(domain, name, payload, blocking=False)
        except Exception:  # noqa: BLE001 - ein defektes Ansageziel darf nichts weiter stören
            _LOGGER.exception("Ansage über %s fehlgeschlagen", service)

    # -- Kalibrier-Selbsttest ----------------------------------------------

    @callback
    def _handle_calibrate_pressed(self, event: Event[EventStateChangedData]) -> None:
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")
        if new_state is None or new_state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return
        if old_state is None or old_state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            # Erster Zustand nach einem Neustart oder Wiederverbinden des
            # Geräts - kein echter Tastendruck.
            return

        self.coordinator.async_set_calibration(dt_util.utcnow())

        if self._cancel_calibration is not None:
            self._cancel_calibration()
        self._cancel_calibration = async_call_later(
            self.hass, CALIBRATION_CHECK_DELAY, self._check_calibration
        )

    @callback
    def _check_calibration(self, _now) -> None:
        """Nach dem Kalibrieren müssen beide Achsen bei ~0 stehen.

        Tun sie das nicht, rechnen Anzeige und gespeicherter Offset in der
        Firmware mit unterschiedlichen Achsen - ein Fehler, der sonst erst auf
        dem Stellplatz auffällt, wenn alle Angaben falsch sind.
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
            f"Fünf Sekunden nach dem Kalibrieren steht längs {pitch:.2f}° / quer "
            f"{roll:.2f}° statt 0.\n\n"
            "Mögliche Ursachen: das Fahrzeug hat sich während des Tastendrucks "
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
