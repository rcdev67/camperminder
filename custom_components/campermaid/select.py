"""Auswahlfelder: Ausrichtart und Ansageziel.

Beides stand frueher nur im Einrichtungsdialog. Das war schwer zu finden und
liess sich weder in einer Automation noch auf dem Dashboard verwenden - obwohl
es gewoehnliche Bedieneinstellungen sind und keine Anschlussdaten. Als
Entitaeten stehen sie jetzt dort, wo Toleranz, Radstand und Keilstufe auch
schon stehen: auf der Geraeteseite.
"""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import CONF_LEVEL_METHOD, CONF_NOTIFY_SERVICE, DOMAIN, METHODS
from .coordinator import CamperCoordinator
from .entity import CamperEntity

# Ohne diesen Eintrag liesse sich das Ansageziel nur wechseln, nicht
# abschalten - und wer keine Ansagen will, haette keine Wahl.
OPTION_OFF = "aus"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: CamperCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities: list[SelectEntity] = [CamperNotifySelect(coordinator, entry)]
    # Die Ausrichtart fuehrt das Geraet, sobald die mitgelieferte Firmware
    # laeuft - dann waere ein zweites Auswahlfeld hier nur verwirrend.
    if CONF_LEVEL_METHOD not in coordinator.device_sources:
        entities.append(CamperMethodSelect(coordinator, entry))
    async_add_entities(entities)


class CamperMethodSelect(CamperEntity, SelectEntity, RestoreEntity):
    """Auffahrkeile oder Hebesystem."""

    _attr_options = list(METHODS)
    _attr_icon = "mdi:car-lifted-pickup"

    def __init__(self, coordinator: CamperCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, CONF_LEVEL_METHOD)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None:
            if last.state in METHODS:
                self.coordinator.async_restore_value(CONF_LEVEL_METHOD, last.state)

    @property
    def current_option(self) -> str:
        return self.coordinator.level_method

    async def async_select_option(self, option: str) -> None:
        if option in METHODS:
            self.coordinator.async_set_value(CONF_LEVEL_METHOD, option)


class CamperNotifySelect(CamperEntity, SelectEntity, RestoreEntity):
    """Wohin die Sprachansagen gehen.

    Die Liste wird bei jedem Aufruf frisch aus den vorhandenen
    notify-Diensten gebildet. Ein fest eingebrannte Liste wuerde veralten,
    sobald ein Handy dazukommt oder verschwindet.
    """

    _attr_icon = "mdi:cellphone-message"

    def __init__(self, coordinator: CamperCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "notify_target")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is None:
            return
        # Beim allerersten Start nach dem Umbau gibt es noch keinen Zustand -
        # dann bleibt der Wert aus der Einrichtung stehen.
        if last.state == OPTION_OFF:
            self.coordinator.async_restore_value(CONF_NOTIFY_SERVICE, None)
        elif last.state and "." not in last.state:
            self.coordinator.async_restore_value(
                CONF_NOTIFY_SERVICE, f"notify.{last.state}"
            )

    @property
    def options(self) -> list[str]:
        services = sorted(self.hass.services.async_services().get("notify", {}))
        current = self.current_option
        # Ein eingestelltes Ziel, das es gerade nicht gibt (Handy offline,
        # Integration neu geladen), bleibt trotzdem sichtbar. Sonst faellt die
        # Auswahl still auf einen anderen Eintrag zurueck.
        if current != OPTION_OFF and current not in services:
            services.append(current)
        return [OPTION_OFF, *services]

    @property
    def current_option(self) -> str:
        service = self.coordinator.notify_service
        if not service:
            return OPTION_OFF
        return service.split(".", 1)[-1]

    async def async_select_option(self, option: str) -> None:
        value = None if option == OPTION_OFF else f"notify.{option}"
        self.coordinator.async_set_value(CONF_NOTIFY_SERVICE, value)
