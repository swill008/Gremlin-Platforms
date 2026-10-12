# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
# ruff: noqa: E501 - the QML list rows below read best on one line each

"""The row action summary (05 S142, D-05-ROW-ACTION-SUMMARY): every row
that can have bindings on the Device Bindings, Keyboard, Logical Device and
OSC pages carries "1 action · <target>" / "N actions · <targets>" in its
actionSummary role (the shown mode's actions, every binding's), "" with
none; ControlTree shows it in grey after the name, cut with "…", the full
text on hover, while Appearance › Shown › "Show action summary" is on.

Model parts run in-process; the QML part runs off-screen in its own process
(this file run as a script).

Spec: 05 S142, S125.
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
STICK = uuid.UUID("11111111-2222-3333-4444-555555555555")
GUID = "{11111111-2222-3333-4444-555555555555}"
NAME = "Test Stick"
LONG = "3 actions · vJoy 1 Button 3, vJoy 1 Button 4, Xbox 360 2 A, " + "x" * 200


def _vjoy(button: int) -> Any:  # noqa: ANN401
    action = plugin_manager.PluginManager().create_instance(
        "Map to vJoy", InputType.JoystickButton
    )
    action.vjoy_device_id = 1
    action.vjoy_input_id = button
    action.vjoy_input_type = InputType.JoystickButton
    return action


def _bind(item: Any, *buttons: int) -> list[Any]:  # noqa: ANN401
    """One binding on item with a Map to vJoy for each button."""
    root = item.add_item_binding().root_action
    made = [_vjoy(button) for button in buttons]
    for action in made:
        root.insert_action(action, "children")
    return made


def _dest(action: Any) -> str:  # noqa: ANN401
    from gremlin.ui.binding_catalog import summarize_action

    return summarize_action(action)[1]


def _summaries(model: Any) -> dict[str, str]:  # noqa: ANN401
    return {
        row["key"]: row["actionSummary"]
        for row in model._rows
        if row["rowKind"] == "parent"
    }


def test_the_wording() -> None:
    from gremlin.ui.binding_catalog import action_summary

    assert action_summary([]) == ""
    assert action_summary([("map-to-vjoy", "Map to vJoy", "vJoy 1 X")]) == (
        "1 action · vJoy 1 X"
    )
    three = [("", "", "A"), ("", "", "B"), ("", "", "C")]
    assert action_summary(three) == "3 actions · A, B, C"
    # An action with no target still counts.
    assert action_summary([("", "", ""), ("", "", "B")]) == "2 actions · B"
    assert action_summary([("", "", "")]) == "1 action"


# -- Device Bindings page ---------------------------------------------------


def test_device_bindings_rows(module: Any) -> None:  # noqa: ANN401
    from gremlin.ui.hardware_layout import HardwareLayoutModel

    saved = shared_state.current_profile
    profile = Profile()
    shared_state.current_profile = profile
    real = profile.get_input_item(
        STICK, InputType.JoystickButton, 1, "Default", True
    )
    # Two bindings, the first with two actions: three actions.
    made = _bind(real, 3, 4) + _bind(real, 5)
    one = profile.get_input_item(STICK, InputType.JoystickButton, 2, "Default", True)
    single = _bind(one, 7)
    model = HardwareLayoutModel()
    try:
        model.setDevice(GUID, NAME)
        rows = _summaries(model)
        wanted = "3 actions · " + ", ".join(_dest(a) for a in made)
        assert rows["parent:button:1"] == wanted
        assert rows["parent:button:2"] == "1 action · " + _dest(single[0])
        # A claimed input with no actions shows nothing.
        assert rows["parent:button:3"] == ""
        # Action rows carry none.
        assert all(
            row["actionSummary"] == ""
            for row in model._rows
            if row["rowKind"] != "parent"
        )
        assert b"actionSummary" in [
            bytes(v.data()) for v in model.roleNames().values()
        ]
        # It follows the profile (an edit elsewhere, Undo, a load).
        real.action_sequences.pop()
        signal.profileChanged.emit()
        rows = _summaries(model)
        wanted = "2 actions · " + ", ".join(_dest(a) for a in made[:2])
        assert rows["parent:button:1"] == wanted
        # Another mode shows that mode's actions: none here.
        model._mode = "Nowhere"
        model._rebuild()
        assert _summaries(model)["parent:button:1"] == ""
    finally:
        model.endPane()
        shared_state.current_profile = saved


# -- Keyboard page ----------------------------------------------------------


def test_keyboard_row(modules: Any) -> None:  # noqa: ANN401
    import dill
    from gremlin.modules import store
    from gremlin.ui.keyboard_layout import KeyboardLayoutModel, keyboard_store

    old = shared_state.current_profile
    profile = Profile()
    shared_state.current_profile = profile
    store.discard_pending("")
    keyboard_store().load()
    real = profile.get_input_item(
        dill.UUID_Keyboard, InputType.Keyboard, (30, False), "Default", True
    )
    made = _bind(real, 2)
    model = KeyboardLayoutModel()
    try:
        rows = list(_summaries(model).values())
        assert rows == ["1 action · " + _dest(made[0])], rows
    finally:
        model.endPane()
        model.deleteLater()
        store.discard_pending("")
        keyboard_store().load()
        shared_state.current_profile = old


# -- Logical Device page ----------------------------------------------------


def test_logical_row(qapp: object) -> None:
    from gremlin.ui.logical_layout import LogicalLayoutModel

    LogicalDevice().load_dict({"controls": [], "groups": []})
    old = shared_state.current_profile
    profile = Profile()
    shared_state.current_profile = profile
    device = LogicalDevice()
    device.create(InputType.JoystickButton)
    device.create(InputType.JoystickButton)
    real = profile.get_input_item(
        device.device_guid, InputType.JoystickButton, 1, "Default", True
    )
    made = _bind(real, 2, 3)
    model = LogicalLayoutModel()
    try:
        rows = _summaries(model)
        wanted = "2 actions · " + ", ".join(_dest(a) for a in made)
        assert rows["parent:button:1"] == wanted
        assert rows["parent:button:2"] == ""
    finally:
        model.endPane()
        model.deleteLater()
        shared_state.current_profile = old
        LogicalDevice().load_dict({"controls": [], "groups": []})


# -- OSC page ---------------------------------------------------------------


def test_osc_row(qapp: object, modules: Any) -> None:  # noqa: ANN401
    from gremlin.osc import OSC_DEVICE_UUID, OscDevice, OscRuntime
    from gremlin.ui import osc_device_model
    from gremlin.ui.osc_layout import OscLayoutModel

    OscDevice().rows.reset()
    OscRuntime().reset_live()
    saved = shared_state.current_profile
    profile = Profile()
    shared_state.current_profile = profile
    model = OscLayoutModel()
    try:
        row, error = osc_device_model.add_input({"address": "/gear"})
        assert row is not None and not error, error
        osc_device_model._emit_modified()
        real = profile.get_input_item(
            OSC_DEVICE_UUID, row.input_type, row.input_id, "Default", True
        )
        made = _bind(real, 9)
        signal.profileChanged.emit()
        word = "axis" if row.input_type == InputType.JoystickAxis else "button"
        rows = _summaries(model)
        assert rows[f"parent:{word}:{row.input_id}"] == "1 action · " + _dest(
            made[0]
        )
    finally:
        model.endPane()
        OscDevice().rows.reset()
        OscRuntime().reset_live()
        shared_state.current_profile = saved


# -- The pages pass the switch; the Xbox list keeps it off ------------------


def test_pages_bind_the_switch() -> None:
    for page in (
        "DeviceBindingsPage.qml",
        "KeyboardPage.qml",
        "LogicalPage.qml",
        "OscPage.qml",
    ):
        text = (_ROOT / "qml" / page).read_text(encoding="utf-8")
        assert "showActionSummary: _appear.showActionSummary" in text, page
    tree = (_ROOT / "qml" / "ControlTree.qml").read_text(encoding="utf-8")
    # Off unless a page turns it on: the Xbox Output View's list doesn't.
    assert "property bool showActionSummary: false" in tree
    xbox = (_ROOT / "qml" / "XboxPadCard.qml").read_text(encoding="utf-8")
    assert "showActionSummary" not in xbox
    panel = (_ROOT / "qml" / "ListAppearancePanel.qml").read_text(encoding="utf-8")
    assert 'text: "Show action summary"' in panel
    assert '"showActionSummary": showActionSummary' in panel
    assert "showActionSummary = v.showActionSummary !== false" in panel
    assert 'pageKey !== "xbox-output"' in panel


# -- The list (off-screen QML) ----------------------------------------------


def _run(part: str, tmp_path: pathlib.Path) -> dict[str, str]:
    import proc_tree  # pyright: ignore[reportMissingImports]  (test/)

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
    assert "done" in lines, result.stdout[-3000:] + result.stderr[-3000:]
    errors = [line for line in lines if line.startswith("ERROR")]
    assert not errors, errors
    ours = [
        line
        for line in lines
        if line.startswith("WARN") and "ControlTree" in line
    ]
    assert not ours, ours
    return {
        line.split(" ", 2)[1]: (line.split(" ", 2) + [""])[2]
        for line in lines
        if line.startswith("RESULT ")
    }


def test_the_tree_shows_it_after_the_name(tmp_path: pathlib.Path) -> None:
    r = _run("tree", tmp_path)
    # Grey, on the name's line, cut with "…", the full text on hover.
    assert r["bound"] == "true|1 action · vJoy 1 X|muted|same-line", r["bound"]
    assert r["long"].startswith("true|" + LONG + "|muted|same-line|elided"), r["long"]
    assert r["tip"] == LONG, r["tip"]
    # No actions: nothing after the name.
    assert r["empty"] == "false", r["empty"]
    # The switch off hides it.
    assert r["off"] == "false", r["off"]


def _tree(s, out: pathlib.Path) -> None:  # noqa: ANN001
    from PySide6 import QtCore

    app, engine, warnings = s._engine(out)  # noqa: F841
    qml = (
        """
import QtQuick
import QtQuick.Window
import Gremlin.Style
Window {
    width: 500; height: 600; visible: true
    ListModel {
        id: _rows
        function keyAt(i) { return get(i).key }
        function setSelection(keys) {}
        ListElement { rowKind: "group"; key: "group:"; title: "Ungrouped"; subtitle: ""; parentKey: ""; groupKey: "g"; groupName: ""; systemName: ""; userName: ""; sequenceIndex: -1; childCount: 3; cantSend: ""; actionSummary: "" }
        ListElement { rowKind: "parent"; key: "parent:button:1"; title: "Button 1"; subtitle: ""; parentKey: "parent:button:1"; groupKey: "g"; groupName: ""; systemName: "Button 1"; userName: ""; sequenceIndex: -1; childCount: 0; cantSend: ""; actionSummary: "1 action · vJoy 1 X" }
        ListElement { rowKind: "parent"; key: "parent:button:2"; title: "Button 2"; subtitle: ""; parentKey: "parent:button:2"; groupKey: "g"; groupName: ""; systemName: "Button 2"; userName: ""; sequenceIndex: -1; childCount: 0; cantSend: ""; actionSummary: "LONG" }
        ListElement { rowKind: "parent"; key: "parent:button:3"; title: "Button 3"; subtitle: ""; parentKey: "parent:button:3"; groupKey: "g"; groupName: ""; systemName: "Button 3"; userName: ""; sequenceIndex: -1; childCount: 0; cantSend: ""; actionSummary: "" }
    }
    ControlTree {
        id: _tree
        width: 500; height: 500
        layout: _rows
        showActionSummary: true
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
    function label(key) {
        var r = row(key)
        return r ? find(r, function(i) { return i.objectName === "actionSummary" }) : null
    }
    function nameOf(key) {
        var r = row(key)
        return r ? find(r, function(i) { return i.objectName === "rowName" }) : null
    }
    function summary(key) {
        var m = label(key)
        if (!m || !m.visible || m.width <= 0) return "false"
        var n = nameOf(key)
        var a = m.mapToItem(null, 0, 0)
        var b = n.mapToItem(null, 0, 0)
        var line = Math.abs((a.y + m.height / 2) - (b.y + n.height / 2)) < 4 && a.x > b.x
        return "true|" + m.text + "|"
            + (Qt.colorEqual(m.color, _tree.colorMuted) ? "muted" : String(m.color))
            + "|" + (line ? "same-line" : "other-line")
            + (m.truncated ? "|elided" : "")
    }
    function tip(key) {
        var m = label(key)
        var t = m ? find(m, function(i) { return i.objectName === "actionSummaryTip" }) : null
        return t ? t.text : "missing"
    }
}
"""
    ).replace("LONG", LONG)
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
    s._Out.result("bound", js("summary('parent:button:1')"))
    s._Out.result("long", js("summary('parent:button:2')"))
    s._Out.result("tip", js("tip('parent:button:2')"))
    s._Out.result("empty", js("summary('parent:button:3')"))
    js("_tree.showActionSummary = false; 1")
    s._wait(50)
    s._Out.result("off", js("summary('parent:button:1')"))
    s._report(warnings)


# -- Fixtures (as test_rows_cant_send's) ------------------------------------


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
