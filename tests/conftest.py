"""Prüfstand für die Integration - ohne Home Assistant.

    python -m pip install pytest
    python -m pytest tests

Home Assistant selbst wird hier bewusst NICHT installiert. Es ist schwer, legt
die Python-Fassung fest und ändert sich monatlich - der Prüfstand wäre öfter
kaputt als die Integration. Geprüft wird die Logik: Rechenkern, Dialog und
Ansage. Alles aus homeassistant.* ersetzen Platzhalter; wo die Logik einen
echten Wert braucht (Konstanten, Basisklassen, Ausnahmen), steht er unten
ausdrücklich.

Die Folge: Diese Tests sagen nichts darüber, ob die Integration zu einer
bestimmten Home-Assistant-Fassung passt. Das prüft hassfest in der CI, und
der Rest gehört an den Prototyp.
"""

from __future__ import annotations

import importlib
import importlib.machinery
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

WURZEL = Path(__file__).resolve().parent.parent
if str(WURZEL) not in sys.path:
    sys.path.insert(0, str(WURZEL))


class _Platzhalter(types.ModuleType):
    """Ein Modul, das jedes Attribut liefert - als leere Klasse."""

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        wert = type(name, (), {"__init__": lambda self, *a, **k: None,
                               "__call__": lambda self, *a, **k: None})
        setattr(self, name, wert)
        return wert


def _platzhalter(name: str, **attrs) -> types.ModuleType:
    """Platzhaltermodul anlegen, samt Elternmodulen und Verweis im Elternteil."""
    if name in sys.modules:
        modul = sys.modules[name]
    else:
        modul = _Platzhalter(name)
        modul.__path__ = []  # als Paket gelten lassen
        sys.modules[name] = modul
        eltern, _, kind = name.rpartition(".")
        if eltern:
            setattr(_platzhalter(eltern), kind, modul)
    for schluessel, wert in attrs.items():
        setattr(modul, schluessel, wert)
    return modul


class _Finder:
    """homeassistant, voluptuous und aiohttp als Platzhalter liefern.

    aiohttp nur, weil __init__.py der Integration es für den Karten-View
    importiert; geprüft wird dort hier nichts."""

    def find_spec(self, name, path=None, target=None):
        wurzel = name.split(".")[0]
        if wurzel in ("homeassistant", "voluptuous", "aiohttp"):
            return importlib.machinery.ModuleSpec(name, self, is_package=True)
        return None

    def create_module(self, spec):
        return _platzhalter(spec.name)

    def exec_module(self, module):
        pass


sys.meta_path.insert(0, _Finder())


class HomeAssistantError(Exception):
    """Wie homeassistant.exceptions.HomeAssistantError."""


class _FlowBasis:
    """Genug von ConfigFlow/OptionsFlow für den Dialog."""

    def __init_subclass__(cls, **kwargs):
        pass

    def async_show_form(self, **kw):
        return {"type": "form", **kw}

    def async_create_entry(self, **kw):
        return {"type": "create_entry", **kw}

    async def async_set_unique_id(self, unique_id):
        self.unique_id = unique_id

    def _abort_if_unique_id_configured(self):
        pass


_platzhalter(
    "homeassistant.const",
    ATTR_ENTITY_ID="entity_id",
    STATE_ON="on",
    STATE_OFF="off",
    STATE_UNAVAILABLE="unavailable",
    STATE_UNKNOWN="unknown",
    Platform=SimpleNamespace(
        BINARY_SENSOR="binary_sensor", NUMBER="number", SELECT="select",
        SENSOR="sensor", SWITCH="switch",
    ),
)
_platzhalter(
    "homeassistant.core",
    HomeAssistant=object,
    callback=lambda funktion: funktion,
    Event=object,
    EventStateChangedData=object,
)
_platzhalter(
    "homeassistant.config_entries",
    ConfigFlow=_FlowBasis,
    OptionsFlow=_FlowBasis,
    ConfigEntry=object,
    ConfigFlowResult=dict,
)
_platzhalter("homeassistant.exceptions", HomeAssistantError=HomeAssistantError)
_platzhalter(
    "homeassistant.components.number.const",
    ATTR_VALUE="value",
    DOMAIN="number",
    SERVICE_SET_VALUE="set_value",
)
_platzhalter(
    "voluptuous",
    Schema=lambda x: x,
    Required=lambda key, **kw: key,
    Optional=lambda key, **kw: key,
    UNDEFINED=object(),
)

PAKET = "custom_components.camperminder"
const = importlib.import_module(f"{PAKET}.const")
coordinator = importlib.import_module(f"{PAKET}.coordinator")
config_flow = importlib.import_module(f"{PAKET}.config_flow")
announce = importlib.import_module(f"{PAKET}.announce")

WOHNMOBIL, WOHNWAGEN = const.VEHICLE_TYPES


class FakeHass:
    """Zustände und Dienstaufrufe - mehr braucht die Logik nicht."""

    def __init__(self, zustaende: dict[str, str] | None = None, dienst_fehler: bool = False):
        self.zustaende = dict(zustaende or {})
        self.aufrufe: list[tuple] = []
        self.dienst_fehler = dienst_fehler
        self.states = SimpleNamespace(get=self._zustand)
        self.services = SimpleNamespace(async_call=self._dienst)

    def _zustand(self, entity_id):
        if entity_id not in self.zustaende:
            return None
        return SimpleNamespace(state=self.zustaende[entity_id])

    async def _dienst(self, domain, service, data, blocking=False):
        if self.dienst_fehler:
            raise HomeAssistantError("Gerät nicht erreichbar")
        self.aufrufe.append((domain, service, data["entity_id"], data["value"]))
        self.zustaende[data["entity_id"]] = str(float(data["value"]))


def rechenkern(
    pitch,
    roll,
    fahrzeug=WOHNMOBIL,
    methode="keile",
    keilstufe=5,
    radstand=4213,
    spur=1710,
    toleranz=3,
):
    """Rechenkern mit Messwerten, ohne Gerät - Werte kommen aus dem Dialog."""
    kern = coordinator.CamperCoordinator(SimpleNamespace(), "eintrag", {
        "pitch_sensor": "sensor.pitch",
        "roll_sensor": "sensor.roll",
        "wheelbase": radstand,
        "track": spur,
        "tolerance_cm": toleranz,
        "wedge_step": keilstufe,
        "vehicle_type": fahrzeug,
        "level_method": methode,
    })
    kern.pitch, kern.roll = pitch, roll
    return kern


def eintrag(entity_id, geraet, domain, name, deaktiviert=None):
    """Ein Eintrag der Entitätsregistrierung."""
    return SimpleNamespace(entity_id=entity_id, device_id=geraet, domain=domain,
                           original_name=name, disabled_by=deaktiviert)


def registrierung(*eintraege):
    """Entitätsregistrierung aus Einträgen, wie er.async_get sie liefert."""
    nach_id = {e.entity_id: e for e in eintraege}
    return SimpleNamespace(async_get=nach_id.get, entities=nach_id)


@pytest.fixture(autouse=True)
def mit_registrierung(monkeypatch):
    """Die Entitätsregistrierung für Dialog und Rechenkern austauschen.

    Für jeden Test, standardmäßig leer: Auch ein Test, der sich nicht dafür
    interessiert, kann über die Geräteerkennung laufen."""

    def setzen(reg):
        monkeypatch.setattr(config_flow.er, "async_get", lambda hass: reg, raising=False)
        monkeypatch.setattr(coordinator.er, "async_get", lambda hass: reg, raising=False)

    setzen(registrierung())
    return setzen
