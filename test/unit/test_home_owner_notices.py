# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Home cards follow the owners' notices (D-01-OWNER-NOTICES).

- Driven by follows bindingsChanged, the bindings' owner's one notice
  (Delete Mode, undo, OSC page edits: 1a), not a list of raw signals.
- A full reload tells the pages that ask the list (targetsChanged), so the
  Output View header does not go stale after a profile loads.
- A card shows the user's name for its device and follows
  deviceNamesChanged (10 S7, 2a); rawName still names the module file.
- Output and input cards drop their copy of the claims when the store says
  a module file changed (6b); the Device Mapping Editor's file watch follows the same
  notice.
"""

from __future__ import annotations

import pathlib
from types import SimpleNamespace

import pytest
from PySide6 import QtCore

from gremlin import config
from gremlin.common import SingletonMetaclass
from gremlin.signal import signal
from gremlin.ui import module_model

_STICK = "{00000001-0000-0000-0000-000000000000}"
_VJOY = "{00000009-0000-0000-0000-000000000000}"


def _stick(name: str, guid: str) -> SimpleNamespace:
    return SimpleNamespace(
        name=name,
        device_guid=guid,
        vendor_id=1,
        product_id=1,
        button_count=4,
        axis_count=2,
        hat_count=0,
    )


def _vjoy() -> SimpleNamespace:
    return SimpleNamespace(
        vjoy_id=1, device_guid=_VJOY, button_count=8, axis_count=2, hat_count=0
    )


@pytest.fixture
def setup(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path):  # noqa: ANN201
    from gremlin import device_initialization

    QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    monkeypatch.setattr(config, "_config_file_path", str(tmp_path / "c.json"))
    monkeypatch.delitem(
        SingletonMetaclass._instances, config.Configuration, raising=False
    )
    config.Configuration()
    monkeypatch.setattr(
        device_initialization, "physical_devices", lambda: [_stick("Throttle", _STICK)]
    )
    monkeypatch.setattr(device_initialization, "vjoy_devices", lambda: [_vjoy()])
    monkeypatch.setattr(module_model, "module_exists", lambda _name, _guid="": False)
    monkeypatch.setattr(module_model, "_show_stubs", lambda: True)
    monkeypatch.setattr(module_model.ModuleListModel, "_stacks", lambda _self: [])
    monkeypatch.setattr(module_model, "apply_cant_send", lambda _rows: [])
    wires: list[tuple[str, str, int]] = []
    monkeypatch.setattr(module_model, "_profile_wire_maps", lambda: list(wires))
    model = module_model.ModuleListModel()
    model._dest_timer.stop()
    yield model, wires
    model.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)


def _row(model: module_model.ModuleListModel, slug: str) -> module_model.ModuleRow:
    return next(r for r in model._rows if r.slug == slug)


def test_driven_by_follows_the_bindings_notice(setup: tuple) -> None:
    model, wires = setup
    vjoy = next(r for r in model._rows if r.vjoy_id == 1)
    assert vjoy.target == ""
    told: list[int] = []
    model.targetsChanged.connect(lambda: told.append(1))
    wires[:] = [(module_model.guid_key(_STICK), "vjoy", 1)]
    signal.bindingsChanged.emit()
    assert vjoy.target == "Throttle"
    assert _row(model, "throttle").target == "vJoy 1"
    assert told == [1]
    # Delete Mode / an undo: the same notice takes it away again.
    wires[:] = []
    signal.bindingsChanged.emit()
    assert vjoy.target == ""


def test_a_full_reload_tells_the_header(setup: tuple) -> None:
    model, _wires = setup
    told: list[int] = []
    model.targetsChanged.connect(lambda: told.append(1))
    model._reload()
    assert told == [1]


def test_cards_show_the_users_name_and_follow_it(setup: tuple) -> None:
    from gremlin import device_aliases

    model, wires = setup
    wires[:] = [(module_model.guid_key(_STICK), "vjoy", 1)]
    named: list[int] = []
    model.namesChanged.connect(lambda: named.append(1))
    device_aliases.set_alias(_STICK, "My Throttle")
    device_aliases.set_alias(_VJOY, "Game Pad")
    signal.deviceNamesChanged.emit()
    stick = _row(model, "throttle")
    vjoy = next(r for r in model._rows if r.vjoy_id == 1)
    assert named
    assert model.cardMap("throttle")["name"] == "My Throttle"
    # The module file keeps the device's own name.
    assert model.cardMap("throttle")["rawName"] == "Throttle"
    # Driven by uses the shown names; the vJoy number still comes from the
    # card's own name.
    assert stick.target == "Game Pad"
    assert vjoy.target == "My Throttle"
    # The Device Bindings page title asks by device id and file name.
    assert model.shownName(_STICK, "Throttle") == "My Throttle"
    assert model.boundLine("vJoy 1") == "Driven by: [My Throttle]"
    # A reload keeps it; forgetting the name brings the device's own back.
    model._reload()
    assert model.cardMap("throttle")["name"] == "My Throttle"
    device_aliases.set_alias(_STICK, "")
    signal.deviceNamesChanged.emit()
    assert model.cardMap("throttle")["name"] == "Throttle"
    # Keyboard, OSC, Xbox and the Logical Device are named by their key.
    device_aliases.set_alias("keyboard", "Keys")
    signal.deviceNamesChanged.emit()
    assert model.cardMap("keyboard")["name"] == "Keys"


def test_a_module_file_notice_drops_the_claim_copies(setup: tuple) -> None:
    model, _wires = setup
    model._dest_targets["vjoy_1"] = (1, {"buttons": [1]})
    model._source_claims["throttle"] = (0.0, None, {"buttons": [1]})
    told: list[int] = []
    model.claimsChanged.connect(lambda: told.append(1))
    signal.moduleFilesChanged.emit()
    assert model._dest_targets == {}
    assert model._source_claims == {}
    assert told == [1]


def test_the_device_mapping_editor_file_watch_follows_the_store_notice(
    setup: tuple,
) -> None:
    watch = module_model.ModuleFileWatch()
    told: list[int] = []
    watch.changed.connect(lambda: told.append(1))
    signal.moduleFilesChanged.emit()
    assert told == [1]
    watch.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
