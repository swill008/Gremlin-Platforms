# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Device Bindings page's model on the shared control page base
(HardwareLayoutModel): the module's claimed inputs only, Find/Type/Output/
No actions filters, groups/order/names held until File > Save, Rename
writes the friendly name, one Undo for OK, Delete and layout (layout steps
survive a profile load, a device switch clears all), live roles.

Spec: 05 S121-S131, S15, S18-S20, S31, S35, S37; 03 S121.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)
from PySide6 import QtCore

from gremlin import history_modules, plugin_manager, shared_state
from gremlin.modules import store
from gremlin.profile import Profile
from gremlin.signal import signal
from gremlin.types import InputType
from test.unit._device_folders import put_module

STICK = uuid.UUID("11111111-2222-3333-4444-555555555555")
GUID = "{11111111-2222-3333-4444-555555555555}"
OTHER = "{99999999-2222-3333-4444-555555555555}"
NAME = "Test Stick"


_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    # A bare Qt application: the page's model, not the main window.
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


def _device() -> SimpleNamespace:
    return SimpleNamespace(
        name=NAME,
        axis_count=2,
        button_count=4,
        hat_count=0,
        axis_map=[SimpleNamespace(axis_index=1), SimpleNamespace(axis_index=2)],
        device_guid=SimpleNamespace(uuid=STICK),
    )


@pytest.fixture
def module(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    from gremlin.ui import hardware_layout

    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setattr(store, "folder", lambda: folder)
    # The device's own folder, found by its id (03 S1, S128).
    path = put_module(
        folder,
        NAME,
        {
            "kind": "control.hardware",
            "device": NAME,
            "direction": "source",
            # Button 9 isn't on the device: no row.
            "claim": {
                "buttons": [1, 2, 3, 9],
                "axes": [1],
                "friendly": {"button:1": "Fire"},
            },
            "nodes": [],
        },
        GUID,
    )
    monkeypatch.setattr(hardware_layout.hardware, "device_info", lambda guid: _device())
    monkeypatch.setattr(hardware_layout, "_mapping_for", lambda device: None)
    monkeypatch.setattr(
        history_modules, "note_write", lambda path, text, old=None: None
    )
    store.discard_pending()
    yield path
    store.discard_pending()


@pytest.fixture
def page(module: Path) -> Iterator[tuple[Any, Profile]]:
    from gremlin.ui.hardware_layout import HardwareLayoutModel

    saved = shared_state.current_profile
    profile = Profile()
    shared_state.current_profile = profile
    model = HardwareLayoutModel()
    model.setDevice(GUID, NAME)
    yield model, profile
    model.endPane()
    shared_state.current_profile = saved


def _map(profile: Profile, button: int, out: int) -> None:
    item = profile.get_input_item(
        STICK, InputType.JoystickButton, button, "Default", create_if_missing=True
    )
    action = plugin_manager.PluginManager().create_instance(
        "Map to vJoy", InputType.JoystickButton
    )
    action.vjoy_device_id = 1
    action.vjoy_input_id = out
    action.vjoy_input_type = InputType.JoystickButton
    item.add_item_binding().root_action.insert_action(action, "children")


def _count(profile: Profile, button: int) -> int:
    item = profile.get_input_item(
        STICK, InputType.JoystickButton, button, "Default", create_if_missing=False
    )
    return len(item.action_sequences) if item is not None else 0


def _rows(model: Any) -> list[dict]:  # noqa: ANN401
    return list(model._rows)


def _parents(model: Any) -> list[str]:  # noqa: ANN401
    return [row["key"] for row in _rows(model) if row["rowKind"] == "parent"]


def _row(model: Any, key: str) -> dict:  # noqa: ANN401
    return next(row for row in _rows(model) if row["key"] == key)


def _doc(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_rows_are_the_claimed_inputs_only(page: tuple[Any, Profile]) -> None:
    model, _profile = page
    assert _parents(model) == [
        "parent:axis:1",
        "parent:button:1",
        "parent:button:2",
        "parent:button:3",
    ]
    fire = _row(model, "parent:button:1")
    assert fire["title"] == "Fire" and fire["userName"] == "Fire"
    assert _row(model, "parent:button:2")["title"] == fire["systemName"].replace(
        "1", "2"
    )
    # Claims belong to Module Setup: rows can't be removed here.
    model.deleteParents(["parent:button:2"])
    assert "parent:button:2" in _parents(model)
    assert not model.canUndo


def test_filters(page: tuple[Any, Profile]) -> None:
    model, profile = page
    _map(profile, 2, 5)
    model.reload()
    assert any("5" in dest for dest in model.destChoices[1:])
    model.setActionFilters("vjoy", "All devices")
    assert _parents(model) == ["parent:button:2"]
    model.setActionFilters("keyboard", "all")
    assert _parents(model) == []
    model.setActionFilters("all", "all")
    # No bindings in this mode (S123).
    model.setFilter("", "all", False, False, True)
    assert "parent:button:2" not in _parents(model)
    assert "parent:button:1" in _parents(model)
    model.setFilter("fire", "all", False, False, False)
    assert _parents(model) == ["parent:button:1"]


def test_groups_and_order_wait_for_save(
    page: tuple[Any, Profile], module: Path
) -> None:
    model, _profile = page
    model.addGroup("Weapons")
    model.moveRow("parent:button:2", "group:Weapons")
    assert _row(model, "parent:button:2")["groupName"] == "Weapons"
    assert "layout" not in _doc(module)
    assert store.has_pending()
    store.save_pending()
    saved = _doc(module)["layout"]
    assert saved["groups"] == ["Weapons"]
    assert saved["group_of"] == {"button:2": "Weapons"}
    assert not store.has_pending()


def test_rename_writes_the_friendly_name(
    page: tuple[Any, Profile], module: Path
) -> None:
    model, _profile = page
    model.setUserName("parent:button:2", "Gear")
    assert _row(model, "parent:button:2")["title"] == "Gear"
    assert store.friendly_name_for(GUID, "button:2", NAME) == "Gear"
    assert "button:2" not in _doc(module)["claim"]["friendly"]
    store.save_pending()
    assert _doc(module)["claim"]["friendly"]["button:2"] == "Gear"
    assert _doc(module)["claim"]["friendly"]["button:1"] == "Fire"


def test_rename_undo_clears_the_held_change(page: tuple[Any, Profile]) -> None:
    model, _profile = page
    model.setUserName("parent:button:2", "Gear")
    assert model.lastChange.startswith("Last change: Rename")
    model.undo()
    assert _row(model, "parent:button:2")["userName"] == ""
    assert not store.has_pending()


def test_one_undo_for_ok_delete_and_layout(page: tuple[Any, Profile]) -> None:
    model, profile = page
    _map(profile, 1, 3)
    model.reload()
    model.addGroup("Weapons")
    assert model.deleteAction("parent:button:1", 0)
    assert _count(profile, 1) == 0
    model.undo()
    assert _count(profile, 1) == 1
    model.undo()
    assert "Weapons" not in [g["name"] for g in model.groups]
    model.redo()
    assert "Weapons" in [g["name"] for g in model.groups]


def test_ok_is_an_undo_step(page: tuple[Any, Profile]) -> None:
    model, profile = page
    _map(profile, 1, 3)
    model.reload()
    model.beginPane("parent:button:1", -1)
    shadow = model._pane_shadow
    shadow.action_sequences[0].root_action.get_actions()[0][0].vjoy_input_id = 8
    assert model.commitPane() >= 0
    model.endPane()
    assert model.canUndo
    model.undo()
    item = profile.get_input_item(STICK, InputType.JoystickButton, 1, "Default")
    assert item.action_sequences[0].root_action.get_actions()[0][0].vjoy_input_id == 3


def test_delete_waits_while_the_pane_edits_that_input(
    page: tuple[Any, Profile],
) -> None:
    model, profile = page
    _map(profile, 1, 3)
    model.reload()
    model.beginPane("parent:button:1", -1)
    assert model.paneKey == "parent:button:1"
    assert not model.canDelete("parent:button:1")
    assert not model.deleteAction("parent:button:1", 0)
    assert not model.deleteActions("parent:button:1")
    assert _count(profile, 1) == 1
    model.endPane()
    assert model.deleteActions("parent:button:1")
    assert _count(profile, 1) == 0


def test_layout_steps_survive_a_profile_load(page: tuple[Any, Profile]) -> None:
    model, profile = page
    _map(profile, 1, 3)
    model.reload()
    model.deleteAction("parent:button:1", 0)
    model.addGroup("Weapons")
    shared_state.current_profile = Profile()
    signal.profileChanged.emit()
    # The action step stayed with the old profile; the group step is kept.
    assert model.canUndo
    model.undo()
    assert "Weapons" not in [g["name"] for g in model.groups]
    assert not model.canUndo


def test_switching_device_clears_undo(page: tuple[Any, Profile]) -> None:
    model, _profile = page
    model.addGroup("Weapons")
    assert model.canUndo
    model.setDevice(OTHER, NAME)
    assert not model.canUndo and not model.canRedo
    assert model.guid == OTHER


def test_discard_reloads_and_clears_steps(page: tuple[Any, Profile]) -> None:
    model, _profile = page
    model.addGroup("Weapons")
    store.discard_pending()
    assert not model.canUndo
    assert "Weapons" not in [g["name"] for g in model.groups]


def test_live_roles(page: tuple[Any, Profile]) -> None:
    model, _profile = page
    # Axes first, then buttons (DeviceLiveState's index).
    assert _row(model, "parent:axis:1")["deviceIndex"] == 0
    assert _row(model, "parent:button:1")["deviceIndex"] == 2
    # ControlTree's live lights and bars read liveIndex on parent rows.
    assert _row(model, "parent:axis:1")["liveIndex"] == 0
    assert _row(model, "parent:button:1")["liveIndex"] == 2
    assert _row(model, "parent:button:1")["kind"] == "button"
    assert _row(model, "parent:button:1")["hwId"] == 1
    assert model.keyForDeviceIndex(3) == "parent:button:2"
    assert model.keyForDeviceIndex(5) == ""
    names = {bytes(v.data()).decode() for v in model.roleNames().values()}
    wanted = {
        "liveIndex",
        "deviceIndex",
        "kind",
        "hwId",
        "note",
        "bindingCount",
        "bindingTargets",
    }
    assert wanted <= names


def test_undo_waits_while_an_action_is_open_in_the_pane(
    page: tuple[Any, Profile],
) -> None:
    # 05 S36: Undo/Redo wait while an action is open in the pane.
    model, _ = page
    model.addGroup("Wait")
    assert model.canUndo
    model.beginPane("parent:button:1", -1)
    assert not model.canUndo
    model.undo()
    assert "Wait" in [g["name"] for g in model.groups]
    model.endPane()
    assert model.canUndo
    model.undo()
    assert "Wait" not in [g["name"] for g in model.groups]


_QML_BUILD = """
import sys
from PySide6 import QtCore, QtGui, QtQml
app = QtGui.QGuiApplication([])
import gremlin.ui.hardware_layout  # registers HardwareLayoutModel
engine = QtQml.QQmlEngine()
component = QtQml.QQmlComponent(engine)
component.setData(
    b"import QtQml; import Gremlin.Device; HardwareLayoutModel {"
    b" property string k: paneKey;"
    b" property bool u: canUndo; property var d: destChoices;"
    b" Component.onCompleted: setDevice('x', 'pJoy Pro') }",
    QtCore.QUrl(),
)
built = component.create()
print("BUILT" if built is not None else "NULL " + component.errorString())
"""


def test_qml_builds_the_model_and_sets_a_device() -> None:
    # A property notified by a base class's signal (paneModelChanged) made
    # QML crash (access violation) building the model; in a child process
    # so a crash fails this test instead of the run.
    import os
    import sys

    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
    done = proc_tree.run(
        [sys.executable, "-c", _QML_BUILD],
        cwd=str(Path(__file__).resolve().parents[2]),
        env=env,
        text=True,
        timeout=60,
    )
    assert done.returncode == 0, smoke_report.explain(done)
    assert "BUILT" in done.stdout, smoke_report.explain(done)
