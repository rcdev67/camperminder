"""Einrichtungs- und Optionsdialog."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er, selector

from .const import (
    CONF_CALIBRATE_BUTTON,
    CONF_MOTION_SENSOR,
    CONF_NOTIFY_TTS,
    CONF_PITCH_SENSOR,
    CONF_ROLL_SENSOR,
    CONF_TOLERANCE_CM,
    CONF_TRACK,
    CONF_WEDGE_STEP,
    CONF_WHEELBASE,
    DEFAULT_TOLERANCE_CM,
    DEFAULT_TRACK,
    DEFAULT_WEDGE_STEP,
    DEFAULT_WHEELBASE,
    DOMAIN,
)

DEFAULT_TITLE = "CamperMaid"

# Felder, die leer bleiben dürfen. Ein leergeräumtes Feld taucht im Ergebnis
# des Formulars gar nicht auf - deshalb müssen sie beim Speichern ausdrücklich
# auf None gesetzt werden, sonst überlebt der alte Wert aus entry.data.
CLEARABLE_KEYS = (CONF_MOTION_SENSOR, CONF_CALIBRATE_BUTTON)

# Die Namen, die die mitgelieferte Firmware vergibt. Gesucht wird nicht über
# die Entity-ID, sondern über den ursprünglichen Namen aus der
# Entitätsregistrierung: der bleibt stehen, auch wenn jemand das Gerät oder
# die Entitäten im Frontend umbenennt.
FIRMWARE_ENTITIES: dict[str, tuple[str, str]] = {
    CONF_PITCH_SENSOR: ("sensor", "Neigung Pitch"),
    CONF_ROLL_SENSOR: ("sensor", "Neigung Roll"),
    CONF_MOTION_SENSOR: ("binary_sensor", "In Bewegung"),
    CONF_CALIBRATE_BUTTON: ("button", "Neigung kalibrieren"),
}


def _autodetect(hass: HomeAssistant) -> dict[str, str]:
    """Die vier Entitäten des Nivelliergeräts vorschlagen.

    Gewertet wird geräteweise und das vollständigste Gerät gewinnt. Wer zwei
    Fahrzeuge in einem Home Assistant hat, bekommt so nicht die Längsneigung
    des einen mit der Querneigung des anderen gemischt - ein Fehler, den man am
    fertigen Dialog nicht sieht und im Fahrzeug teuer bezahlt.
    """
    registry = er.async_get(hass)
    per_device: dict[str, dict[str, str]] = {}

    for entry in registry.entities.values():
        if entry.device_id is None or entry.disabled_by is not None:
            continue
        for key, (domain, name) in FIRMWARE_ENTITIES.items():
            if entry.domain == domain and entry.original_name == name:
                per_device.setdefault(entry.device_id, {})[key] = entry.entity_id

    if not per_device:
        return {}

    found = max(per_device.values(), key=len)

    # Ohne beide Neigungsachsen ist der Fund kein Nivelliergerät. Dann lieber
    # nichts vorschlagen als zwei Felder halb ausgefüllt zu hinterlassen.
    if CONF_PITCH_SENSOR not in found or CONF_ROLL_SENSOR not in found:
        return {}
    return found


def _schema(hass: HomeAssistant, defaults: dict[str, Any]) -> vol.Schema:
    """Formular für Einrichtung und spätere Änderungen.

    Hier stehen nur Anschlussdaten und Fahrzeugmaße. Ausrichtart und
    Ansageziel sind bewusst nicht mehr dabei: sie sind gewöhnliche
    Bedieneinstellungen und liegen als Entitäten auf der Geräteseite. Sie
    zusätzlich hier zu führen hätte zwei Wahrheiten ergeben - und die im
    Dialog eingetragene hätte nach jedem Neustart verloren.
    """

    def default(key: str, fallback: Any = None) -> Any:
        value = defaults.get(key, fallback)
        return value if value is not None else vol.UNDEFINED

    return vol.Schema(
        {
            vol.Required(
                CONF_PITCH_SENSOR, default=default(CONF_PITCH_SENSOR)
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Required(
                CONF_ROLL_SENSOR, default=default(CONF_ROLL_SENSOR)
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(
                CONF_MOTION_SENSOR, default=default(CONF_MOTION_SENSOR)
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="binary_sensor")
            ),
            vol.Optional(
                CONF_CALIBRATE_BUTTON, default=default(CONF_CALIBRATE_BUTTON)
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="button")
            ),
            vol.Required(
                CONF_WHEELBASE, default=defaults.get(CONF_WHEELBASE, DEFAULT_WHEELBASE)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1000, max=8000, step=10, unit_of_measurement="mm",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_TRACK, default=defaults.get(CONF_TRACK, DEFAULT_TRACK)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=800, max=2600, step=10, unit_of_measurement="mm",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_TOLERANCE_CM,
                default=defaults.get(CONF_TOLERANCE_CM, DEFAULT_TOLERANCE_CM),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1, max=20, step=0.5, unit_of_measurement="cm",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_WEDGE_STEP,
                default=defaults.get(CONF_WEDGE_STEP, DEFAULT_WEDGE_STEP),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0, max=10, step=0.5, unit_of_measurement="cm",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_NOTIFY_TTS, default=defaults.get(CONF_NOTIFY_TTS, True)
            ): selector.BooleanSelector(),
        }
    )


class CamperConfigFlow(ConfigFlow, domain=DOMAIN):
    """Erste Einrichtung."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            # Ein Neigungssensor gehört genau einmal eingerichtet.
            await self.async_set_unique_id(user_input[CONF_PITCH_SENSOR])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=DEFAULT_TITLE, data=user_input)

        # Vorbelegt, nicht festgelegt: die Felder bleiben änderbar, falls die
        # Erkennung danebenliegt oder die Firmware angepasst wurde.
        return self.async_show_form(
            step_id="user", data_schema=_schema(self.hass, _autodetect(self.hass))
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return CamperOptionsFlow()


class CamperOptionsFlow(OptionsFlow):
    """Spätere Änderungen über "Konfigurieren"."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            # Die Optionen überschreiben die ursprünglichen Daten nur dort,
            # wo ein Schlüssel vorhanden ist. Ein geleertes Feld fehlt aber im
            # Formularergebnis - ohne diese Ergänzung ließe sich das
            # Ansageziel zwar wechseln, aber nie wieder abschalten, und die
            # Ansagen gingen weiter an das alte Gerät.
            cleaned = dict(user_input)
            for key in CLEARABLE_KEYS:
                cleaned.setdefault(key, None)
            return self.async_create_entry(data=cleaned)

        current = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="init", data_schema=_schema(self.hass, current)
        )
