# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
# ruff: noqa: E501 - the QML list rows below read best on one line each

"""The row bindings (05 S142, D-05-BINDINGS-BOXES): every row that can
have bindings on the Device Bindings, Keyboard, Logical Device and OSC pages
carries bindingCount (the shown mode's actions, every binding's) and
bindingTargets (one text per target, "vJoy 1 · Button 1"); ControlTree shows
"Bindings", "[n]" and one box per target after the name, all rows' boxes in
one column, cut with "…", every target on hover; nothing with none.

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
MANY = [f"vJoy 1 · Button {n}" for n in range(1, 31)]


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


def _summaries(model: Any) -> dict[str, tuple[int, list[str]]]:  # noqa: ANN401
    return {
        row["key"]: (row["bindingCount"], list(row["bindingTargets"]))
        for row in model._rows
        if row["rowKind"] == "parent"
    }


def test_the_targets() -> None:
    from gremlin.ui import binding_catalog
    from gremlin.ui.binding_catalog import binding_targets

    assert binding_targets([]) == []
    assert binding_targets([("map-to-vjoy", "Map to vJoy", "vJoy 1 X")]) == [
        "vJoy 1 X"
    ]
    three = [("", "", "A"), ("", "", "B"), ("", "", "C")]
    assert binding_targets(three) == ["A", "B", "C"]
    # An action with no target has no box (it still counts).
    assert binding_targets([("", "", ""), ("", "", "B")]) == ["B"]
    # The old one-line summary is gone.
    assert not hasattr(binding_catalog, "action_summary")


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
        assert rows["parent:button:1"] == (3, [_dest(a) for a in made])
        assert rows["parent:button:2"] == (1, [_dest(single[0])])
        # A claimed input with no actions shows nothing.
        assert rows["parent:button:3"] == (0, [])
        # Action rows carry none.
        assert all(
            row["bindingCount"] == 0 and row["bindingTargets"] == []
            for row in model._rows
            if row["rowKind"] != "parent"
        )
        names = [bytes(v.data()) for v in model.roleNames().values()]
        assert b"bindingCount" in names and b"bindingTargets" in names
        assert b"actionSummary" not in names
        # The tree's name column measures the parent rows' names.
        assert model.parentTitles == [
            row["title"] for row in model._rows if row["rowKind"] == "parent"
        ]
        # It follows the profile (an edit elsewhere, Undo, a load).
        real.action_sequences.pop()
        signal.profileChanged.emit()
        rows = _summaries(model)
        assert rows["parent:button:1"] == (2, [_dest(a) for a in made[:2]])
        # Another mode shows that mode's actions: none here.
        model._mode = "Nowhere"
        model._rebuild()
        assert _summaries(model)["parent:button:1"] == (0, [])
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
        assert rows == [(1, [_dest(made[0])])], rows
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
        assert rows["parent:button:1"] == (2, [_dest(a) for a in made])
        assert rows["parent:button:2"] == (0, [])
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
        assert rows[f"parent:{word}:{row.input_id}"] == (1, [_dest(made[0])])
    finally:
        model.endPane()
        OscDevice().rows.reset()
        OscRuntime().reset_live()
        shared_state.current_profile = saved


# -- ControlTree's defaults; the Xbox list has no bindings -------------------


def test_tree_defaults_and_xbox() -> None:
    tree = (_ROOT / "qml" / "ControlTree.qml").read_text(encoding="utf-8")
    assert "property bool showBindings: true" in tree
    assert "showActionSummary" not in tree
    assert "_actionSummary" not in tree
    # Colours come from Style tokens.
    assert "property color bindingTargetTextColor: Style.bindingText" in tree
    assert "property color bindingTargetBgColor: Style.bindingBg" in tree
    assert "property color bindingTargetBorderColor: Style.bindingBorder" in tree
    # The Xbox Output View's list (S139) has no binding roles: nothing shows.
    xbox = (_ROOT / "gremlin" / "ui" / "xbox_output_list.py").read_text(
        encoding="utf-8"
    )
    assert "bindingCount" not in xbox


# -- The list (off-screen QML) ----------------------------------------------


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
        if line.startswith("WARN") and "ControlTree" in line
    ]
    assert not ours, ours
    return {
        line.split(" ", 2)[1]: (line.split(" ", 2) + [""])[2]
        for line in lines
        if line.startswith("RESULT ")
    }


def test_the_tree_shows_bindings_after_the_name(tmp_path: pathlib.Path) -> None:
    r = _run("tree", tmp_path)
    # "Bindings", "[2]" in the number style, one box per target.
    assert r["two"] == (
        "Bindings|[2]|mono|vJoy 1 · Button 1,Xbox 360 Controller · A|same-line"
    ), r["two"]
    assert r["twoBoxes"] == "salmon|bg|border|1|5", r["twoBoxes"]
    # Nothing bound: nothing after the name.
    assert r["none"] == "false", r["none"]
    # One column: the strip starts at the same x on short and long names,
    # with and without a caret or a ⚠, past the widest name.
    assert r["column"] == "same", r["column"]
    # Too many: clipped with "…", every target on hover.
    assert r["many"] == "clipped|…", r["many"]
    assert r["tip"] == "\\n".join(MANY), r["tip"]
    # Brackets off: the bare number; the switch off hides it all.
    assert r["bare"] == "2", r["bare"]
    assert r["off"] == "false", r["off"]


_QML = """
import QtQuick
import QtQuick.Window
import Gremlin.Style
Window {
    width: 700; height: 600; visible: true
    ControlTree {
        id: _tree
        width: 700; height: 560
        layout: rowsModel
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
    function part(key, name) {
        var r = row(key)
        return r ? find(r, function(i) { return i.objectName === name }) : null
    }
    function boxes(key) {
        var s = part(key, "bindingsStrip")
        var out = []
        if (!s) return out
        var walk = function(it) {
            if (it.objectName === "bindingBox") out.push(it)
            for (var i = 0; i < it.children.length; i++) walk(it.children[i])
        }
        walk(s)
        return out
    }
    function shown(key) {
        var w = part(key, "bindingsWord")
        if (!w || !w.visible || w.width <= 0) return "false"
        var n = part(key, "bindingsCount")
        var name = part(key, "rowName")
        var a = w.mapToItem(null, 0, 0)
        var b = name.mapToItem(null, 0, 0)
        var line = Math.abs((a.y + w.height / 2) - (b.y + name.height / 2)) < 4 && a.x > b.x
        var texts = boxes(key).map(function(b) { return b.children[0].text })
        return w.text + "|" + n.text + "|"
            + (n.font.family === Style.monoFont ? "mono" : n.font.family) + "|"
            + texts.join(",") + "|" + (line ? "same-line" : "other-line")
    }
    function boxLook(key) {
        var b = boxes(key)[0]
        return (Qt.colorEqual(b.children[0].color, Style.bindingText) ? "salmon" : String(b.children[0].color))
            + "|" + (Qt.colorEqual(b.color, Style.bindingBg) ? "bg" : String(b.color))
            + "|" + (Qt.colorEqual(b.border.color, Style.bindingBorder) ? "border" : String(b.border.color))
            + "|" + (b.border.width === Style.dp(1) ? _tree.bindingTargetBorderWidth : b.border.width)
            + "|" + (b.radius === Style.dp(5) ? _tree.bindingTargetRadius : b.radius)
    }
    function stripX(key) { var s = part(key, "bindingsWord"); return s ? Math.round(s.mapToItem(null, 0, 0).x) : -1 }
    function column() {
        var xs = ["parent:button:1", "parent:button:4", "parent:button:5", "parent:button:2"].map(stripX)
        var name = part("parent:button:4", "rowName")
        var past = xs[0] >= name.mapToItem(null, 0, 0).x + name.implicitWidth
        for (var i = 1; i < xs.length; i++)
            if (Math.abs(xs[i] - xs[0]) > 1) return xs.join(",")
        return past ? "same" : "inside-name"
    }
    function many() {
        var s = part("parent:button:2", "bindingsStrip")
        var dots = part("parent:button:2", "bindingsMore")
        return (s.clip && s.width < s.contentWidth ? "clipped" : "fits")
            + "|" + (dots && dots.visible ? dots.text : "none")
    }
    function tip() {
        var t = part("parent:button:2", "bindingsTip")
        return t ? t.text : "missing"
    }
}
"""


def _rows_model(rows: list[dict]) -> Any:  # noqa: ANN401
    """A minimal row model for ControlTree: the real roles, fixed rows."""
    from PySide6 import QtCore

    from gremlin.ui.control_layout import ROW_DEFAULTS

    names = list(ROW_DEFAULTS)
    full = [{**ROW_DEFAULTS, **row} for row in rows]

    class Model(QtCore.QAbstractListModel):
        changed = QtCore.Signal()

        def rowCount(self, parent: Any = None) -> int:  # noqa: ANN401
            return len(full)

        def roleNames(self) -> dict:
            base = QtCore.Qt.ItemDataRole.UserRole + 1
            return {
                base + i: QtCore.QByteArray(n.encode()) for i, n in enumerate(names)
            }

        def data(self, index: Any, role: int = 0) -> Any:  # noqa: ANN401
            i = role - QtCore.Qt.ItemDataRole.UserRole - 1
            if not (0 <= i < len(names)):
                return None
            return full[index.row()][names[i]]

        @QtCore.Slot(int, result=str)
        def keyAt(self, i: int) -> str:
            return full[i]["key"]

        @QtCore.Slot(list)
        def setSelection(self, keys: list) -> None:
            pass

        def _titles(self) -> list:
            return [r["title"] for r in full if r["rowKind"] == "parent"]

        parentTitles = QtCore.Property(list, _titles, notify=changed)

    return Model()


def _row_of(n: int, title: str, targets: list[str], **more: Any) -> dict:  # noqa: ANN401
    key = f"parent:button:{n}"
    return {
        "rowKind": "parent",
        "key": key,
        "title": title,
        "parentKey": key,
        "groupKey": "g",
        "systemName": title,
        "childCount": len(targets),
        "bindingCount": len(targets),
        "bindingTargets": targets,
        **more,
    }


def _tree(s, out: pathlib.Path) -> None:  # noqa: ANN001
    from PySide6 import QtCore

    app, engine, warnings = s._engine(out)  # noqa: F841
    two = ["vJoy 1 · Button 1", "Xbox 360 Controller · A"]
    rows = [
        {
            "rowKind": "group",
            "key": "group:",
            "title": "Ungrouped",
            "groupKey": "g",
            "childCount": 5,
        },
        _row_of(1, "B1", two),
        _row_of(2, "Button 2", MANY),
        _row_of(3, "Button 3", []),
        _row_of(4, "A much longer button name here", two),
        # Bound, but no caret (no action rows) and a ⚠.
        _row_of(5, "Mid name", two, childCount=0, cantSend="vJoy 1 is off"),
    ]
    model = _rows_model(rows)
    engine.rootContext().setContextProperty("rowsModel", model)
    engine.loadData(
        _QML.encode("utf-8"),
        QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "Root.qml")),
    )
    if not engine.rootObjects():
        for warning in warnings:
            print("ERROR load: " + warning, flush=True)
        os._exit(1)
    win = engine.rootObjects()[0]
    s._wait(300)
    js = lambda code: s._js(win, code)  # noqa: E731
    s._Out.result("two", js("shown('parent:button:1')"))
    s._Out.result("twoBoxes", js("boxLook('parent:button:1')"))
    s._Out.result("none", js("shown('parent:button:3')"))
    s._Out.result("column", js("column()"))
    s._Out.result("many", js("many()"))
    s._Out.result("tip", str(js("tip()")).replace("\n", "\\n"))
    js("_tree.bindingsBrackets = false; 1")
    s._wait(50)
    s._Out.result("bare", js("part('parent:button:1', 'bindingsCount').text"))
    js("_tree.showBindings = false; 1")
    s._wait(50)
    s._Out.result("off", js("shown('parent:button:1')"))
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
