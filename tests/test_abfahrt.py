"""Abfahrtscheck: was als offen gilt, wann gewarnt und was angesagt wird."""

from __future__ import annotations

import importlib
from types import SimpleNamespace

from conftest import PAKET

abfahrt = importlib.import_module(f"{PAKET}.abfahrt")
const = importlib.import_module(f"{PAKET}.const")


def test_was_als_offen_gilt():
    assert abfahrt.ist_offen("binary_sensor.tuer", "on")
    assert not abfahrt.ist_offen("binary_sensor.tuer", "off")
    assert abfahrt.ist_offen("cover.markise", "open")
    assert abfahrt.ist_offen("cover.markise", "closing")
    assert not abfahrt.ist_offen("cover.markise", "closed")
    assert abfahrt.ist_offen("lock.aufbautuer", "unlocked")
    assert not abfahrt.ist_offen("lock.aufbautuer", "locked")
    assert abfahrt.ist_offen("input_boolean.stufe", "on")


def test_unbekannt_ist_nicht_offen():
    # Eine leere Batterie im Türkontakt darf nicht bei jeder Fahrt warnen.
    for zustand in ("unavailable", "unknown", None):
        assert not abfahrt.ist_offen("binary_sensor.tuer", zustand)
        assert not abfahrt.ist_offen("cover.markise", zustand)


def test_nur_beim_rollen():
    assert abfahrt.bewerte(False, ["Markise"]) == abfahrt.RUHIG
    assert abfahrt.bewerte(True, []) == abfahrt.RUHIG
    befund = abfahrt.bewerte(True, ["Markise", "Trittstufe"])
    assert befund.satz == "Abfahrt - noch offen: Markise, Trittstufe."


class FalschesHass:
    def __init__(self, zustaende: dict[str, str], namen: dict[str, str]):
        self.zustaende = zustaende
        self.namen = namen
        self.aufgaben = []
        self.gedrueckt = []
        self.states = SimpleNamespace(get=self._get)
        self.services = SimpleNamespace(async_call=self._druecken)

    async def _druecken(self, domain, dienst, daten, blocking=False):
        self.gedrueckt.append((domain, dienst, daten["entity_id"]))

    def _get(self, entity_id):
        if entity_id not in self.zustaende:
            return None
        return SimpleNamespace(
            state=self.zustaende[entity_id], name=self.namen.get(entity_id, entity_id)
        )

    def async_create_task(self, coro):
        self.aufgaben.append(coro)
        # Ausführen statt verwerfen: Der Knopfdruck soll sichtbar werden.
        try:
            coro.send(None)
        except StopIteration:
            pass


def waechter(hass, auswahl, markise=None):
    gesagt, gemeldet = [], []

    async def sagen(text):  # pragma: no cover - wird nie abgewartet
        gesagt.append(text)

    config = {
        const.CONF_MOTION_SENSOR: "binary_sensor.in_bewegung",
        const.CONF_DEPARTURE_ENTITIES: auswahl,
        const.CONF_AWNING_ENTITY: markise,
    }
    w = abfahrt.AbfahrtsWaechter(hass, config, lambda: gemeldet.append(1), sagen)
    return w, gemeldet


def test_markise_zaehlt_von_selbst_und_steht_vorn():
    hass = FalschesHass({}, {})
    w, _ = waechter(hass, ["binary_sensor.tuer", "cover.markise"], markise="cover.markise")
    assert w.auswahl == ["binary_sensor.tuer", "cover.markise"]
    w, _ = waechter(hass, ["binary_sensor.tuer"], markise="cover.markise")
    assert w.auswahl == ["cover.markise", "binary_sensor.tuer"]
    w, _ = waechter(hass, None, markise="cover.markise")
    assert w.auswahl == ["cover.markise"]


def test_anrollen_mit_offener_stufe_warnt_und_sagt_an():
    hass = FalschesHass(
        {
            "binary_sensor.in_bewegung": "off",
            "input_boolean.stufe": "on",
            "binary_sensor.tuer": "off",
        },
        {"input_boolean.stufe": "Trittstufe", "binary_sensor.tuer": "Aufbautür"},
    )
    w, gemeldet = waechter(hass, ["input_boolean.stufe", "binary_sensor.tuer"])
    w.ton = "button.level_hinweiston"
    w._pruefen(ansagen=False)
    assert not w.warnung and not gemeldet

    hass.zustaende["binary_sensor.in_bewegung"] = "on"
    w._pruefen(ansagen=True)
    assert w.warnung
    assert w.befund.satz == "Abfahrt - noch offen: Trittstufe."
    # Ansage und Piepen.
    assert len(hass.aufgaben) == 2
    assert hass.gedrueckt == [("button", "press", "button.level_hinweiston")]

    # Die Tür geht während der Fahrt auf: neu angesagt wird nur die Tür.
    hass.zustaende["binary_sensor.tuer"] = "on"
    w._pruefen(ansagen=True)
    assert w.befund.offen == ("Trittstufe", "Aufbautür")
    assert len(hass.aufgaben) == 4

    # Stufe eingefahren: keine neue Ansage, Warnung bleibt für die Tür.
    hass.zustaende["input_boolean.stufe"] = "off"
    w._pruefen(ansagen=True)
    assert w.befund.offen == ("Aufbautür",)
    assert len(hass.aufgaben) == 4

    # Angehalten: Warnung aus.
    hass.zustaende["binary_sensor.in_bewegung"] = "off"
    w._pruefen(ansagen=True)
    assert not w.warnung
    assert len(gemeldet) == 4


def test_ohne_knopf_kein_piepen():
    hass = FalschesHass(
        {"binary_sensor.in_bewegung": "on", "input_boolean.stufe": "on"},
        {"input_boolean.stufe": "Trittstufe"},
    )
    w, _ = waechter(hass, ["input_boolean.stufe"])
    w._pruefen(ansagen=True)
    assert w.warnung and hass.gedrueckt == []


def test_knopfname_wie_in_der_firmware():
    from conftest import WURZEL

    hardware = (WURZEL / "esphome" / "level" / "hardware.yaml").read_text(encoding="utf-8")
    assert f'name: "{abfahrt.HINWEISTON}"' in hardware
