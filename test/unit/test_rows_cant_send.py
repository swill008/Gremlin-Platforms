# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
# ruff: noqa: E501 - the QML list rows below read best on one line each

"""Bindings that can't be sent show on the source's page (D-05-CANT-SEND):
on the Device Bindings, Keyboard, Logical Device and OSC pages each action row
whose Map to vJoy (nested ones too) can't be sent carries the tooltip text
(output.cant_send_text) in its cantSend role, its input row carries it too
(a collapsed row stays findable), and the Find bar's "Can't be sent" tick
shows only those inputs. ControlTree draws the red ⚠ with the tooltip;
Clear on the Find bar resets the tick (D-05-FIND-CLEAR).

Model parts run in-process with output.cant_send_text replaced by a stand-in
(vJoy 1 Button 99 can't be sent); the QML part runs off-screen in its own
process (this file run as a script).

Spec: 05 (D-05-CANT-SEND).
"""

from __future__ import annotations

import os
import pathlib
import sys
import uuid
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

sys.path.append(".")

import pytest

from gremlin import plugin_manager, shared_state
from gremlin.common import InputType
from gremlin.logical_device import LogicalDevice
from gremlin.profile import Profile
from gremlin.signal import signal

_HERE = pathlib.Path(__file__).parent
_ROOT = _HERE.parents[1]
BAD = 99
# The stick on the Device Bindings page (as test_hardware_layout's).
STICK = uuid.UUID("11111111-2222-3333-4444-555555555555")
GUID = "{11111111-2222-3333-4444-555555555555}"
NAME = "Test Stick"
TEXT = "vJoy 1's Button 99 is not Found (vJoy 1 has Buttons 1–20)."


@pytest.fixture
def cant(monkeypatch: pytest.MonkeyPatch) -> dict[int, str]:
    """vJoy 1's buttons listed here can't be sent, with this text."""
    from gremlin.modules import output

    bad = {BAD: TEXT}

    def fake(vjoy_id: int, kind: object, control_id: int) -> str | None:
        return bad.get(int(control_id))

    monkeypatch.setattr(output, "cant_send_text", fake)
    return bad


def _vjoy(button: int) -> Any:  # noqa: ANN401
    action = plugin_manager.PluginManager().create_instance(
        "Map to vJoy", InputType.JoystickButton
    )
    action.vjoy_device_id = 1
    action.vjoy_input_id = button
    action.vjoy_input_type = InputType.JoystickButton
    return action


def _bind(item: Any, button: int, nested: bool = False) -> None:  # noqa: ANN401
    root = item.add_item_binding().root_action
    action = _vjoy(button)
    if nested:
        chain = plugin_manager.PluginManager().create_instance(
            "Chain", InputType.JoystickButton
        )
        if not chain.chain_sequences:
            chain.chain_sequences.append([])
        chain.insert_action(action, "0")
        action = chain
    root.insert_action(action, "children")


def _rows(model: Any, kind: str) -> dict[str, dict]:  # noqa: ANN401
    return {row["key"]: row for row in model._rows if row["rowKind"] == kind}


def _check(model: Any, bad: str, good: str) -> None:  # noqa: ANN401
    """bad's input has one sendable and one unsendable action; good's are
    all sendable."""
    parents = _rows(model, "parent")
    assert TEXT in parents[bad]["cantSend"]
    assert parents[good]["cantSend"] == ""
    children = [
        row for row in _rows(model, "child").values() if row["parentKey"] == bad
    ]
    texts = sorted(row["cantSend"] for row in children)
    assert texts == ["", TEXT], texts
    assert all(
        row["cantSend"] == ""
        for row in _rows(model, "child").values()
        if row["parentKey"] == good
    )
    # The role reaches QML by name.
    assert b"cantSend" in [bytes(v.data()) for v in model.roleNames().values()]
    # The Find tick: only the inputs with an action that can't be sent.
    model.setCantSendOnly(True)
    assert list(_rows(model, "parent")) == [bad]
    model.setCantSendOnly(False)
    assert set(_rows(model, "parent")) >= {bad, good}


# -- Logical Device page (the base's own child rows) ------------------------


@pytest.fixture
def logical(qapp: object, cant: dict) -> Iterator[Any]:
    from gremlin.ui.logical_layout import LogicalLayoutModel

    LogicalDevice().load_dict({"controls": [], "groups": []})
    old = shared_state.current_profile
    profile = Profile()
    shared_state.current_profile = profile
    device = LogicalDevice()
    device.create(InputType.JoystickButton)
    device.create(InputType.JoystickButton)
    for number, outs in ((1, (1, BAD)), (2, (2,))):
        real = profile.get_input_item(
            device.device_guid, InputType.JoystickButton, number, "Default", True
        )
        for n, out in enumerate(outs):
            _bind(real, out, nested=n == 1)
    model = LogicalLayoutModel()
    try:
        yield model
    finally:
        model.endPane()
        model.deleteLater()
        shared_state.current_profile = old
        LogicalDevice().load_dict({"controls": [], "groups": []})


def test_logical_rows_and_find_tick(logical: Any) -> None:  # noqa: ANN401
    _check(logical, "parent:button:1", "parent:button:2")


def test_rows_follow_the_contract_signals(
    logical: Any,  # noqa: ANN401
    cant: dict,
) -> None:
    # What can be sent changed: the output layer's one notice
    # (D-05-CANT-SEND-LIVE); the rows ask again.
    cant.clear()
    signal.cantSendChanged.emit()
    assert _rows(logical, "parent")["parent:button:1"]["cantSend"] == ""
    cant[BAD] = TEXT
    signal.profileChanged.emit()
    assert TEXT in _rows(logical, "parent")["parent:button:1"]["cantSend"]


# -- Device Bindings page ---------------------------------------------------


def test_configuration_rows_and_find_tick(cant: dict, module: Any) -> None:  # noqa: ANN401
    from gremlin.ui.hardware_layout import HardwareLayoutModel

    saved = shared_state.current_profile
    profile = Profile()
    shared_state.current_profile = profile
    for number, outs in ((1, (1, BAD)), (2, (2,))):
        real = profile.get_input_item(
            STICK, InputType.JoystickButton, number, "Default", True
        )
        for n, out in enumerate(outs):
            _bind(real, out, nested=n == 1)
    model = HardwareLayoutModel()
    try:
        model.setDevice(GUID, NAME)
        _check(model, "parent:button:1", "parent:button:2")
    finally:
        model.endPane()
        shared_state.current_profile = saved


# -- Keyboard page ----------------------------------------------------------


def test_keyboard_rows_and_find_tick(cant: dict, modules: Any) -> None:  # noqa: ANN401
    import dill
    from gremlin.modules import store
    from gremlin.ui.keyboard_layout import KeyboardLayoutModel, keyboard_store

    old = shared_state.current_profile
    profile = Profile()
    shared_state.current_profile = profile
    store.discard_pending("")
    keyboard_store().load()
    for code, outs in (((30, False), (1, BAD)), ((31, False), (2,))):
        real = profile.get_input_item(
            dill.UUID_Keyboard, InputType.Keyboard, code, "Default", True
        )
        for n, out in enumerate(outs):
            _bind(real, out, nested=n == 1)
    model = KeyboardLayoutModel()
    try:
        keys = [k for k in _rows(model, "parent")]
        assert len(keys) == 2, keys
        bad = next(
            k
            for k in keys
            if any(
                r["parentKey"] == k and r["cantSend"]
                for r in _rows(model, "child").values()
            )
            or _rows(model, "parent")[k]["cantSend"]
        )
        good = next(k for k in keys if k != bad)
        _check(model, bad, good)
    finally:
        model.endPane()
        model.deleteLater()
        store.discard_pending("")
        keyboard_store().load()
        shared_state.current_profile = old


# -- OSC page ---------------------------------------------------------------


def test_osc_rows_and_find_tick(qapp: object, cant: dict, modules: Any) -> None:  # noqa: ANN401
    from gremlin.ui import osc_device_model

    def _add(address: str) -> None:
        row, error = osc_device_model.add_input({"address": address})
        assert row is not None and not error, error
        osc_device_model._emit_modified()

    def _key(address: str) -> str:
        row = OscDevice().find_address(address)
        assert row is not None
        word = "axis" if row.input_type == InputType.JoystickAxis else "button"
        return f"parent:{word}:{row.input_id}"

    from gremlin.osc import OSC_DEVICE_UUID, OscDevice, OscRuntime
    from gremlin.ui.osc_layout import OscLayoutModel

    OscDevice().rows.reset()
    OscRuntime().reset_live()
    saved = shared_state.current_profile
    profile = Profile()
    shared_state.current_profile = profile
    model = OscLayoutModel()
    try:
        _add("/bad")
        _add("/good")
        for address, outs in (("/bad", (1, BAD)), ("/good", (2,))):
            row = OscDevice().find_address(address)
            real = profile.get_input_item(
                OSC_DEVICE_UUID, row.input_type, row.input_id, "Default", True
            )
            for n, out in enumerate(outs):
                _bind(real, out, nested=n == 1)
        signal.profileChanged.emit()
        _check(model, _key("/bad"), _key("/good"))
    finally:
        model.endPane()
        OscDevice().rows.reset()
        OscRuntime().reset_live()
        shared_state.current_profile = saved


@pytest.fixture
def modules(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> pathlib.Path:
    from gremlin.modules import store

    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setattr(store, "folder", lambda: folder)
    return folder


@pytest.fixture
def module(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, qapp: object
) -> Iterator[pathlib.Path]:
    """The stick's input module (as test_hardware_layout's), buttons 1-3."""
    from gremlin import history_modules
    from gremlin.modules import store
    from gremlin.ui import hardware_layout

    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setattr(store, "folder", lambda: folder)
    from test.unit._device_folders import put_module

    # Its own folder, found by its id (device.json; 03 S1, S130).
    path = put_module(
        folder,
        NAME,
        {
            "kind": "control.hardware",
            "device": NAME,
            "direction": "source",
            "claim": {"buttons": [1, 2, 3], "axes": [1]},
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


def _device() -> SimpleNamespace:
    return SimpleNamespace(
        name=NAME,
        axis_count=2,
        button_count=4,
        hat_count=0,
        axis_map=[SimpleNamespace(axis_index=1), SimpleNamespace(axis_index=2)],
        device_guid=SimpleNamespace(uuid=STICK),
    )


# -- The list and the Find bar (off-screen QML) -----------------------------


def _run(part: str, tmp_path: pathlib.Path) -> dict[str, str]:
    import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
    import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

    result = proc_tree.run(
        [sys.executable, str(pathlib.Path(__file__)), part, str(tmp_path)],
        text=True,
        timeout=180,
        cwd=str(_ROOT),
        env={
            **os.environ,
            "QT_QPA_PLATFORM": "offscreen",
            "GREMLIN_OFFLINE": "1",
            "USERPROFILE": str(tmp_path),
        },
        encoding="utf-8",
    )
    lines = result.stdout.splitlines()
    assert "done" in lines, smoke_report.explain(result)
    errors = [line for line in lines if line.startswith("ERROR")]
    assert not errors, errors
    ours = [
        line
        for line in lines
        if line.startswith("WARN")
        and any(name in line for name in ("ControlTree", "ControlFindBar"))
    ]
    assert not ours, ours
    return {
        line.split(" ", 2)[1]: (line.split(" ", 2) + [""])[2]
        for line in lines
        if line.startswith("RESULT ")
    }


def test_tree_shows_the_red_marker_with_its_tooltip(tmp_path: pathlib.Path) -> None:
    r = _run("tree", tmp_path)
    # The action row and its input row: the ⚠ in Style.danger, tooltip = text.
    assert r["child"] == f"true|⚠|{TEXT}|danger", r["child"]
    assert r["parent"] == f"true|⚠|{TEXT}|danger", r["parent"]
    # A row that can be sent has no marker.
    assert r["ok"] == "false", r["ok"]


def test_find_tick_filters_and_clear_resets_it(tmp_path: pathlib.Path) -> None:
    r = _run("tree", tmp_path)
    assert r["tickLabel"] == "Binding output not found"
    assert r["ticked"] == "true true", r["ticked"]
    assert r["cleared"] == "false false", r["cleared"]


def _tree(s, out: pathlib.Path) -> None:  # noqa: ANN001
    from PySide6 import QtCore

    app, engine, warnings = s._engine(out)  # noqa: F841
    qml = (
        """
import QtQuick
import QtQuick.Window
import Gremlin.Style
Window {
    width: 800; height: 600; visible: true
    ListModel {
        id: _rows
        property bool only: false
        function keyAt(i) { return get(i).key }
        function setSelection(keys) {}
        function setCantSendOnly(on) { only = on }
        property int parentCount: 2
        property bool canUndo: false
        property bool canRedo: false
        property string undoTip: ""
        property string redoTip: ""
        property string lastChange: ""
        property string undone: ""
        ListElement { rowKind: "group"; key: "group:"; title: "Ungrouped"; subtitle: ""; parentKey: ""; groupKey: "g"; groupName: ""; systemName: ""; userName: ""; sequenceIndex: -1; childCount: 2; cantSend: "" }
        ListElement { rowKind: "parent"; key: "parent:button:1"; title: "Button 1"; subtitle: ""; parentKey: "parent:button:1"; groupKey: "g"; groupName: ""; systemName: "Button 1"; userName: ""; sequenceIndex: -1; childCount: 1; cantSend: "TEXT" }
        ListElement { rowKind: "child"; key: "child:button:1:0"; title: "Map to vJoy"; subtitle: "vJoy 1 Button 99"; parentKey: "parent:button:1"; groupKey: "g"; groupName: ""; systemName: "Button 1"; userName: ""; sequenceIndex: 0; childCount: 0; cantSend: "TEXT" }
        ListElement { rowKind: "parent"; key: "parent:button:2"; title: "Button 2"; subtitle: ""; parentKey: "parent:button:2"; groupKey: "g"; groupName: ""; systemName: "Button 2"; userName: ""; sequenceIndex: -1; childCount: 0; cantSend: "" }
    }
    ControlFindBar {
        id: _find
        width: 800
        layout: _rows
    }
    ControlTree {
        id: _tree
        y: 120
        width: 800; height: 400
        layout: _rows
        Component.onCompleted: _tree.opened = { "parent:button:1": true }
    }
    function find(item, test) {
        if (test(item))
            return item
        for (var i = 0; i < item.children.length; i++) {
            var f = find(item.children[i], test)
            if (f) return f
        }
        return null
    }
    function row(key) { return find(_tree, function(i) { return i.rowKind !== undefined && i.key === key && i.shown !== undefined }) }
    function mark(key) {
        var r = row(key)
        var m = r ? find(r, function(i) { return i.objectName === "cantSendMark" }) : null
        if (!m || !m.visible) return "false"
        var tip = null
        for (var d = 0; d < m.data.length; d++)
            if (m.data[d].objectName === "cantSendTip") tip = m.data[d]
        return "true|" + m.text + "|" + (tip ? tip.text : "") + "|"
            + (Qt.colorEqual(m.color, Style.danger) ? "danger" : String(m.color))
    }
    function tick() { return find(_find, function(i) { return i.objectName === "cantSendTick" }) }
}
"""
    ).replace("TEXT", TEXT)
    engine.loadData(
        qml.encode("utf-8"),
        QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "Root.qml")),
    )
    if not engine.rootObjects():
        for warning in warnings:
            print("ERROR load: " + warning, flush=True)
        os._exit(1)
    win = engine.rootObjects()[0]
    s._wait(300)
    js = lambda code: s._js(win, code)  # noqa: E731
    s._Out.result("child", js("mark('child:button:1:0')"))
    s._Out.result("parent", js("mark('parent:button:1')"))
    s._Out.result("ok", js("mark('parent:button:2')"))
    s._Out.result("tickLabel", js("tick() ? tick().text : 'missing'"))
    js("tick().toggle(); tick().clicked(); 1")
    s._wait(50)
    s._Out.result("ticked", js("String(_rows.only) + ' ' + String(_find.filtering)"))
    js("_find.clear(); 1")
    s._wait(50)
    s._Out.result("cleared", js("String(_rows.only) + ' ' + String(tick().checked)"))
    s._report(warnings)


if __name__ == "__main__":
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "_audit3_screens", _HERE / "test_audit3_screens.py"
    )
    assert spec is not None and spec.loader is not None
    _s = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_s)
    _s._boot()
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    _part, _out_dir = sys.argv[1], pathlib.Path(sys.argv[2])
    _out_dir.mkdir(parents=True, exist_ok=True)
    try:
        {"tree": _tree}[_part](_s, _out_dir)
    except Exception as failed:  # noqa: BLE001
        import traceback

        traceback.print_exc()
        print(f"ERROR {_part}: {failed!r}", flush=True)
        os._exit(1)
