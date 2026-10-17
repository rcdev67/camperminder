"""Binärsensoren: steht das Fahrzeug eben? Droht der Markise etwas?"""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import CamperCoordinator
from .entity import CamperEntity
from .abfahrt import AbfahrtsWaechter
from .wetter import WetterWaechter


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    stored = hass.data[DOMAIN][entry.entry_id]
    coordinator: CamperCoordinator = stored["coordinator"]
    entities: list[BinarySensorEntity] = [CamperLevelBinarySensor(coordinator, entry)]
    if (wetter := stored.get("wetter")) is not None:
        entities.append(CamperAwningWarning(coordinator, entry, wetter))
    if (abfahrt := stored.get("abfahrt")) is not None:
        entities.append(CamperDepartureWarning(coordinator, entry, abfahrt))
    async_add_entities(entities)


class CamperLevelBinarySensor(CamperEntity, BinarySensorEntity):
    """An, wenn das Fahrzeug innerhalb der eingestellten Toleranz steht."""

    _attr_icon = "mdi:spirit-level"

    def __init__(self, coordinator: CamperCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "level")

    @property
    def available(self) -> bool:
        # Ohne Messwerte lieber nicht verfügbar sein, als fälschlich "eben"
        # zu melden. Ein stiller Sensor fällt auf, ein falsches Ja nicht.
        return self.coordinator.available

    @property
    def is_on(self) -> bool:
        return self.coordinator.is_level


class CamperAwningWarning(CamperEntity, BinarySensorEntity):
    """An, solange die Vorhersage der Markise etwas zumutet.

    Der Melder für den Blueprint "Wetterwächter Markise" - wie die Melder des
    Geräts für Kühlschrank, Wächter und Frost: Der Blueprint hängt am Wechsel
    auf "an", den Satz liest er aus dem Attribut "meldung".
    """

    _attr_device_class = BinarySensorDeviceClass.SAFETY
    _attr_icon = "mdi:storefront-outline"

    def __init__(
        self, coordinator: CamperCoordinator, entry: ConfigEntry, wetter: WetterWaechter
    ) -> None:
        super().__init__(coordinator, entry, "awning_warning")
        self._wetter = wetter

    @property
    def is_on(self) -> bool:
        return self._wetter.warnung

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        wetter = self._wetter
        return {
            **super().extra_state_attributes,
            "stufe": wetter.befund.stufe,
            "meldung": wetter.befund.satz,
            "wetter_entitaet": wetter.wetter,
            "markise_draussen": wetter.markise_draussen,
            "geprueft": wetter.geprueft.isoformat() if wetter.geprueft else None,
        }


class CamperDepartureWarning(CamperEntity, BinarySensorEntity):
    """An, solange das Fahrzeug rollt und noch etwas offen ist.

    Der Melder für den Blueprint "Abfahrtscheck"; den Satz liest er aus dem
    Attribut "meldung".
    """

    _attr_device_class = BinarySensorDeviceClass.SAFETY
    _attr_icon = "mdi:car-door"

    def __init__(
        self, coordinator: CamperCoordinator, entry: ConfigEntry, abfahrt: AbfahrtsWaechter
    ) -> None:
        super().__init__(coordinator, entry, "departure_warning")
        self._abfahrt = abfahrt

    @property
    def is_on(self) -> bool:
        return self._abfahrt.warnung

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        return {
            **super().extra_state_attributes,
            "meldung": self._abfahrt.befund.satz,
            "offen": list(self._abfahrt.befund.offen),
            "geprueft_wird": self._abfahrt.auswahl,
            "hinweiston": self._abfahrt.ton,
        }
