"""Einrichtungs- und Optionsdialog."""

from __future__ import annotations

import logging
import math
from typing import Any

import voluptuous as vol
from homeassistant.components.number.const import (
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
)
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
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
from .coordinator import find_device_sources

_LOGGER = logging.getLogger(__name__)

DEFAULT_TITLE = "CamperMinder"

# Die Fahrzeugmaße im Dialog - und ihre Vorgaben, falls nichts anderes gilt.
# Führt das Gerät sie selbst, gilt das Gerät (siehe CamperCoordinator.get_value).
# Der Dialog ist dann nur ein zweiter Weg zum selben Wert: vorbelegt wird mit
# dem, was im Gerät steht, und was hier geändert wird, geht ins Gerät. Früher
# landete die Eingabe nur in den Optionen und blieb wirkungslos, ohne dass es
# jemand merkte.
DIMENSION_DEFAULTS: dict[str, float] = {
    CONF_WHEELBASE: DEFAULT_WHEELBASE,
    CONF_TRACK: DEFAULT_TRACK,
    CONF_TOLERANCE_CM: DEFAULT_TOLERANCE_CM,
    CONF_WEDGE_STEP: DEFAULT_WEDGE_STEP,
}

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

    Gewertet wird geräteweise. Wer zwei Fahrzeuge in einem Home Assistant hat,
    bekommt so nicht die Längsneigung des einen mit der Querneigung des anderen
    gemischt - ein Fehler, den man am fertigen Dialog nicht sieht und im
    Fahrzeug teuer bezahlt.

    Ein Gerät, das gerade Werte liefert, gewinnt vor einem abgesteckten; erst
    danach zählt die Vollständigkeit. Nach einem Gerätetausch stehen beide noch
    in der Registrierung, und vorzuschlagen ist das neue.
    """
    registry = er.async_get(hass)
    per_device: dict[str, dict[str, str]] = {}

    for entry in registry.entities.values():
        if entry.device_id is None or entry.disabled_by is not None:
            continue
        for key, (domain, name) in FIRMWARE_ENTITIES.items():
            if entry.domain == domain and entry.original_name == name:
                per_device.setdefault(entry.device_id, {})[key] = entry.entity_id

    # Ohne beide Neigungsachsen ist der Fund kein Nivelliergerät. Dann lieber
    # nichts vorschlagen als zwei Felder halb ausgefüllt zu hinterlassen.
    candidates = [
        found
        for found in per_device.values()
        if CONF_PITCH_SENSOR in found and CONF_ROLL_SENSOR in found
    ]
    if not candidates:
        return {}
    return max(
        candidates, key=lambda found: (_is_live(hass, found[CONF_PITCH_SENSOR]), len(found))
    )


def _is_live(hass: HomeAssistant, entity_id: str | None) -> bool:
    """Gibt es die Entität, und ist ihr Gerät erreichbar?"""
    state = hass.states.get(entity_id) if entity_id else None
    return state is not None and state.state != STATE_UNAVAILABLE


def _replacement_sensors(hass: HomeAssistant, current: dict[str, Any]) -> dict[str, Any]:
    """Nach einem Gerätetausch die Entitäten des neuen Geräts vorschlagen.

    Ohne das stünden im Dialog weiter die Sensoren des abgesteckten Geräts, und
    wer nur "Absenden" drückt, rechnet mit Werten, die nie mehr kommen. Greift
    nur, wenn der eingetragene Neigungssensor tot ist und ein anderes Gerät
    lebt - ein kurz abgeschaltetes Gerät bleibt eingetragen.
    """
    if _is_live(hass, current.get(CONF_PITCH_SENSOR)):
        return {}
    found = _autodetect(hass)
    if not found or not _is_live(hass, found[CONF_PITCH_SENSOR]):
        return {}
    # Auch die leerbaren Felder: Bewegungssensor und Kalibrier-Taste des alten
    # Geräts sind genauso tot. Fehlen sie am neuen, bleiben sie leer.
    return {key: found.get(key) for key in FIRMWARE_ENTITIES}


def _device_number(hass: HomeAssistant, entity_id: str) -> float | None:
    """Der Zahlenwert einer Geräte-Entität, oder None, wenn das Gerät fehlt."""
    state = hass.states.get(entity_id)
    try:
        return float(state.state)  # type: ignore[union-attr]
    except (AttributeError, TypeError, ValueError):
        # Kein Zustand, "unavailable" oder "unknown".
        return None


def _effective_values(hass: HomeAssistant, values: dict[str, Any]) -> dict[str, Any]:
    """Die Werte, die gerade wirklich gelten - für die Vorbelegung."""
    result = {**DIMENSION_DEFAULTS, **values}
    if not (pitch := result.get(CONF_PITCH_SENSOR)):
        return result
    sources = find_device_sources(hass, pitch)
    for key in DIMENSION_DEFAULTS:
        if (entity_id := sources.get(key)) is None:
            continue
        if (number := _device_number(hass, entity_id)) is not None:
            result[key] = number
    return result


async def _async_write_to_device(
    hass: HomeAssistant, user_input: dict[str, Any], shown: dict[str, Any]
) -> dict[str, str]:
    """Die Fahrzeugmaße in das Gerät schreiben, das sie führt.

    Maßgeblich ist das Gerät des eingetragenen Neigungssensors, nicht das des
    bisherigen: Wer beim Gerätetausch den Sensor umstellt, nimmt seine Maße ins
    neue Gerät mit. Liefert die Fehler fürs Formular - leer, wenn alles gilt.
    """
    sources = find_device_sources(hass, user_input[CONF_PITCH_SENSOR])
    writes: dict[str, float] = {}
    for key in DIMENSION_DEFAULTS:
        if (entity_id := sources.get(key)) is None:
            continue
        wanted = float(user_input[key])
        current = _device_number(hass, entity_id)
        if current is None:
            # Gerät aus. Unverändert übernommene Werte gehen dabei nicht
            # verloren; eine Änderung dagegen darf der Dialog nicht als
            # gespeichert ausgeben.
            if not math.isclose(wanted, float(shown.get(key, wanted))):
                return {"base": "device_unreachable"}
            continue
        if not math.isclose(wanted, current):
            writes[entity_id] = wanted

    for entity_id, value in writes.items():
        try:
            await hass.services.async_call(
                NUMBER_DOMAIN,
                SERVICE_SET_VALUE,
                {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: value},
                blocking=True,
            )
        except HomeAssistantError as err:
            _LOGGER.warning("%s ließ sich nicht auf %s setzen: %s", entity_id, value, err)
            return {"base": "device_unreachable"}
    return {}


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

    def __init__(self) -> None:
        # Was das Formular zuerst gezeigt hat - daran misst sich, ob ein Maß
        # geändert wurde. Bleibt bei einer Fehlermeldung stehen.
        self._shown: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            # Ein Neigungssensor gehört genau einmal eingerichtet.
            await self.async_set_unique_id(user_input[CONF_PITCH_SENSOR])
            self._abort_if_unique_id_configured()
            errors = await _async_write_to_device(self.hass, user_input, self._shown)
            if not errors:
                return self.async_create_entry(title=DEFAULT_TITLE, data=user_input)
        else:
            # Vorbelegt, nicht festgelegt: die Felder bleiben änderbar, falls
            # die Erkennung danebenliegt oder die Firmware angepasst wurde.
            self._shown = _effective_values(self.hass, _autodetect(self.hass))

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(self.hass, user_input or self._shown),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return CamperOptionsFlow()


class CamperOptionsFlow(OptionsFlow):
    """Spätere Änderungen über "Konfigurieren"."""

    def __init__(self) -> None:
        self._shown: dict[str, Any] = {}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = await _async_write_to_device(self.hass, user_input, self._shown)
            if not errors:
                # Die Optionen überschreiben die ursprünglichen Daten nur
                # dort, wo ein Schlüssel vorhanden ist. Ein geleertes Feld
                # fehlt aber im Formularergebnis - ohne diese Ergänzung ließe
                # sich das Ansageziel zwar wechseln, aber nie wieder
                # abschalten, und die Ansagen gingen weiter an das alte Gerät.
                cleaned = dict(user_input)
                for key in CLEARABLE_KEYS:
                    cleaned.setdefault(key, None)
                return self.async_create_entry(data=cleaned)
        else:
            current = {**self.config_entry.data, **self.config_entry.options}
            # Die Maße aus dem bisherigen Stand, die Sensoren nach einem
            # Gerätetausch vom neuen Gerät: So wandern die Fahrzeugmaße beim
            # Speichern ins neue Gerät, statt dessen Werkswerte zu übernehmen.
            self._shown = _effective_values(self.hass, current)
            self._shown.update(_replacement_sensors(self.hass, current))

        return self.async_show_form(
            step_id="init",
            data_schema=_schema(self.hass, user_input or self._shown),
            errors=errors,
        )
