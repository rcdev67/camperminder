"""CamperMaid - Einrichtung der Integration."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.start import async_at_started
from homeassistant.loader import async_get_integration

from .announce import CamperAnnouncer
from .const import (
    CARD_URL,
    CONF_CALIBRATE_BUTTON,
    CONF_MOTION_SENSOR,
    CONF_NOTIFY_TTS,
    CONF_PITCH_SENSOR,
    CONF_ROLL_SENSOR,
    DOMAIN,
    STATIC_URL,
)
from .coordinator import CamperCoordinator

# Änderungen an diesen Schlüsseln erfordern ein Neuaufsetzen: die Quell-
# Entitäten werden beim Start abonniert, die Vorleseeinstellung liest der
# Ansageteil einmalig ein. Alles andere hält der Rechenkern zur Laufzeit.
STRUCTURAL_KEYS = (
    CONF_PITCH_SENSOR,
    CONF_ROLL_SENSOR,
    CONF_MOTION_SENSOR,
    CONF_CALIBRATE_BUTTON,
    CONF_NOTIFY_TTS,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

CARD_REGISTERED = f"{DOMAIN}_card_registered"

LOVELACE_DOMAIN = "lovelace"


async def _async_register_resource(hass: HomeAssistant, card_url: str) -> None:
    """Die Karte in die Ressourcenliste der Dashboards eintragen.

    Der naheliegendere Weg wäre add_extra_js_url - der schreibt aber nur ein
    script-Tag in die Index-Seite, und darauf ist kein Verlass: läuft das
    Frontend als Single-Page-Anwendung weiter, wird die Seite nie neu geholt,
    und in der Praxis kommt das Tag auch nach einem Neustart nicht zwingend an.
    Die Ressourcenliste holt sich das Frontend dagegen zur Laufzeit über die
    Websocket-Verbindung. Nebenbei ist der Eintrag unter Einstellungen ->
    Dashboards -> Ressourcen sichtbar, statt unauffindbar im Seitenqülltext.
    """
    lovelace = hass.data.get(LOVELACE_DOMAIN)
    resources = getattr(lovelace, "resources", None)

    # Bei YAML-verwalteten Dashboards ist die Liste unveränderlich. Dort
    # bleibt es beim script-Tag aus add_extra_js_url.
    if resources is None or not hasattr(resources, "async_create_item"):
        _LOGGER.debug(
            "Ressourcenliste nicht beschreibbar (YAML-Modus?) - "
            "die Karte kommt nur über die Index-Seite"
        )
        return

    await resources.async_get_info()

    for item in resources.async_items():
        url = str(item.get("url", ""))
        if not url.startswith(CARD_URL):
            continue
        # Vorhandener Eintrag - nach einem Update zeigt er auf die alte
        # Version. Aktualisieren statt einen zweiten danebenzusetzen; das
        # gilt auch für von Hand angelegte Einträge.
        if url != card_url:
            await resources.async_update_item(item["id"], {"url": card_url})
            _LOGGER.info("Lovelace-Ressource auf %s aktualisiert", card_url)
        return

    await resources.async_create_item({"res_type": "module", "url": card_url})
    _LOGGER.info("Lovelace-Ressource %s angelegt", card_url)


async def _async_register_card(hass: HomeAssistant) -> None:
    """Die mitgelieferte Lovelace-Karte ausliefern und bekannt machen.

    Dadurch muss niemand von Hand eine Ressource eintragen oder card-mod
    installieren - die Karte gehört zur Integration und wird mit ihr
    aktualisiert.

    Die Version aus der manifest.json hängt als Abfrage an der URL. Ohne sie
    lädt der Browser nach einem Update die alte Karte aus dem Zwischenspeicher
    weiter - anders als bei HACS-Ressourcen gibt es hier keinen hacstag, der
    das von selbst erledigt.
    """
    if hass.data.get(CARD_REGISTERED):
        return

    www_dir = Path(__file__).parent / "www"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_URL, str(www_dir), cache_headers=False)]
    )

    integration = await async_get_integration(hass, DOMAIN)
    card_url = f"{CARD_URL}?v={integration.version}"

    # Zweiter Weg, kostenlos und für YAML-Dashboards der einzige. Dass die
    # Karte dadurch doppelt geladen werden kann, fängt sie selbst ab.
    add_extra_js_url(hass, card_url)
    hass.data[CARD_REGISTERED] = True

    async def _register_when_ready(_: HomeAssistant) -> None:
        # Erst wenn Home Assistant durchgestartet ist, steht die
        # Ressourcenliste bereit. Ein Fehler hier darf die Integration nicht
        # mitreißen - Werte und Ansagen funktionieren auch ohne Karte.
        try:
            await _async_register_resource(hass, card_url)
        except Exception:  # noqa: BLE001
            _LOGGER.exception(
                "Karte konnte nicht als Lovelace-Ressource eingetragen werden. "
                "Von Hand nachholen: Einstellungen -> Dashboards -> Ressourcen, "
                "URL %s, Typ JavaScript-Modul",
                card_url,
            )

    async_at_started(hass, _register_when_ready)

    # Bewusst info und nicht debug: ohne diese Zeile lässt sich nicht
    # nachsehen, ob die Karte überhaupt ausgeliefert wird.
    _LOGGER.info("Lovelace-Karte unter %s ausgeliefert", card_url)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Einen eingerichteten Camper aufsetzen."""
    await _async_register_card(hass)

    config = {**entry.data, **entry.options}

    coordinator = CamperCoordinator(hass, entry.entry_id, config)
    announcer = CamperAnnouncer(hass, coordinator, config)

    # Der Rechenkern meldet jede Änderung; die Ansage entscheidet selbst, ob
    # daraus etwas Hörbares wird.
    original_notify = coordinator.async_notify

    @callback
    def _notify_and_announce() -> None:
        original_notify()
        announcer.async_phase_changed()

    coordinator.async_notify = _notify_and_announce  # type: ignore[method-assign]

    coordinator.async_start()
    announcer.async_start()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "announcer": announcer,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Auf Änderungen am Config-Eintrag reagieren.

    Seit die Regler und Auswahlfelder ihren Wert selbst hier hineinschreiben,
    läuft jede Schieberbewegung durch diesen Listener. Ein Neuaufsetzen bei
    jedem Zentimeter wäre nicht nur verschwenderisch - die Entitäten würden
    mitten in ihrem eigenen Aufruf zerstört. Neu aufgesetzt wird deshalb nur,
    wenn sich etwas Strukturelles geändert hat: eine Quell-Entität oder die
    Vorleseeinstellung, die der Ansageteil beim Start einliest.
    """
    stored = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if stored is None:
        await hass.config_entries.async_reload(entry.entry_id)
        return

    coordinator: CamperCoordinator = stored["coordinator"]
    config = {**entry.data, **entry.options}

    if any(config.get(key) != coordinator.config.get(key) for key in STRUCTURAL_KEYS):
        await hass.config_entries.async_reload(entry.entry_id)
        return

    coordinator.async_apply_config(config)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Aufräumen."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        stored = hass.data[DOMAIN].pop(entry.entry_id)
        stored["announcer"].async_stop()
        stored["coordinator"].async_stop()
    return unloaded
