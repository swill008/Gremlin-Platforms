# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""05 S125, S131: each list page's own Appearance, the row placement
options and the optional live decoration of the shared tree (AP2, AP3,
CF-Q10).

- Each page (Device Bindings, Logical Device, Keyboard, OSC) keeps its own
  Appearance (WindowPlacement listAppearance(page)): saving the Logical
  Device page's leaves the Device Bindings page's as it was.
- Input and action rows take an alignment (left, center, right) and a
  width %, and groups get "Space between groups"; the defaults keep
  today's look (left, full width, no extra space).
- ControlTree's live lights/bars are off by default (Logical, OSC) and,
  when a page turns them on, tint a pressed button's row and draw an
  axis bar; showKey() jumps to a row.

Off-screen, each QML part in its own process (this file run as a script).
"""

from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import sys

sys.path.append(".")

_HERE = pathlib.Path(__file__).parent
_ROOT = _HERE.parents[1]


def _screens():  # noqa: ANN202
    spec = importlib.util.spec_from_file_location(
        "_audit3_screens", _HERE / "test_audit3_screens.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
    )
    lines = result.stdout.splitlines()
    assert "done" in lines, result.stdout[-3000:] + result.stderr[-3000:]
    errors = [line for line in lines if line.startswith("ERROR")]
    assert not errors, errors
    ours = [
        line
        for line in lines
        if line.startswith("WARN")
        and any(
            name in line
            for name in ("LogicalPage", "ListAppearancePanel", "ControlTree")
        )
    ]
    assert not ours, ours
    return {
        line.split(" ", 2)[1]: line.split(" ", 2)[2]
        for line in lines
        if line.startswith("RESULT ")
    }


def test_each_page_keeps_its_own_appearance(tmp_path: pathlib.Path) -> None:
    r = _run("store", tmp_path)
    assert r["store"] == "ok", r["store"]


def test_the_logical_page_panel_uses_its_own_setting(tmp_path: pathlib.Path) -> None:
    r = _run("logical", tmp_path)
    assert r["pageKey"] == "logical"
    # A value saved before the page opened is shown by its list.
    assert r["loaded"] == "9 9"
    saved = json.loads(r["saved"])
    assert saved["parentHeight"] == 60
    assert saved["rowSpacing"] == 9
    # The row options are saved with the rest, at their defaults.
    assert saved["parentAlign"] == "left" and saved["parentWidthPct"] == 100
    assert saved["childAlign"] == "left" and saved["childWidthPct"] == 100
    assert saved["groupSpacing"] == 0
    # The Device Bindings page's own values are untouched.
    assert json.loads(r["other"]) == {"rowSpacing": 3}
    assert r["toast"] == "Saved for this page."
    # The live keys ride along, so a save here never drops Device Bindings'.
    assert saved["showLiveBars"] is True and saved["showLeds"] is True
    # The old Logical-only "logical-layout" setting is gone.
    assert r["old"] == "False"
    assert r["tree"] == "60"
    # The live rows of the panel are Device Bindings' only.
    assert r["liveRows"] == "false"
    # The Logical Device page tints and follows like Device Bindings
    # (D-05-FOLLOW-ALL-PAGES).
    assert r["liveDecoration"] == "true"


def test_live_decoration_is_off_by_default_and_lights_rows_when_on(
    tmp_path: pathlib.Path,
) -> None:
    r = _run("tree", tmp_path)
    assert r["default"] == "false"
    assert r["off"] == "false false"  # off: no light, no bar
    assert r["on"] == "true axis"  # on: the pressed button lights, the axis has its bar
    assert r["leds_off"] == "false"  # Appearance "Show LED dots" off
    assert r["show"] == "true k:axis parent:axis:1"
    assert r["missing"] == "false"
    assert r["clicked"] == "parent:button:1|Button 1|false"


def test_row_alignment_width_and_group_space_apply_to_the_tree(
    tmp_path: pathlib.Path,
) -> None:
    r = _run("rows", tmp_path)
    total, p_indent, c_indent, gap = (int(n) for n in r["metrics"].split())
    p_room, c_room = total - p_indent, total - c_indent
    group_h = int(r["groupH"])
    # Defaults: today's look, left placed and full width, no group space.
    assert r["default"] == f"{p_indent} {p_room} {c_indent} {c_room} 0 {group_h}"
    # Center, 50 %.
    w = round(p_room * 0.5)
    assert r["parentCenter"] == f"{p_indent + round((p_room - w) / 2)} {w}"
    # Right, 40 %.
    w = round(c_room * 0.4)
    assert r["childRight"] == f"{c_indent + c_room - w} {w}"
    # Left, 60 %: the row's text stops inside the box too.
    w = round(p_room * 0.6)
    assert r["parentLeft"].startswith(f"{p_indent} {w} ")
    assert int(r["parentLeft"].split()[2]) <= p_indent + w
    # Space between groups: above the second group, not the first.
    first_h, second_y, second_h = (int(n) for n in r["groupGap"].split())
    assert first_h == group_h
    assert second_y == gap and second_h == group_h + gap


def test_the_logical_page_turns_the_live_decoration_on() -> None:
    page = (_ROOT / "qml" / "LogicalPage.qml").read_text(encoding="utf-8")
    # Tint and follow as on the Device Bindings page (D-05-FOLLOW-ALL-PAGES).
    assert "liveDecoration: true" in page
    # Its panel is the shared PageAppearance part (to-do 91).
    assert "PageAppearance {" in page
    assert 'pageKey: "logical"' in page
    # Appearance... is on the page bar (01 S58a), as on the other pages.
    assert "readonly property Component pageBar: _appear.pageBar" in page
    assert 'buttonName: "logicalAppearanceButton"' in page
    assert "setLogicalValue" not in page and "logicalValue(" not in page


def _logical(s, out: pathlib.Path) -> None:  # noqa: ANN001
    from PySide6 import QtCore

    app, engine, warnings = s._engine(out)  # noqa: F841
    import gremlin.config
    import gremlin.ui.logical_layout  # noqa: F401
    import gremlin.ui.profile  # noqa: F401
    from gremlin import plugin_manager, shared_state
    from gremlin.common import InputType
    from gremlin.logical_device import LogicalDevice
    from gremlin.profile import Profile
    from gremlin.signal import signal
    from gremlin.ui import window_placement
    from gremlin.ui.backend import UIState

    plugin_manager.PluginManager()
    shared_state.current_profile = Profile()
    LogicalDevice().reset()
    LogicalDevice().create_many(InputType.JoystickButton, 2, "", "")
    window_placement.set_list_appearance("logical", {"rowSpacing": 9})
    window_placement.set_list_appearance("device-bindings", {"rowSpacing": 3})
    backend_cls, _ = s._fakes()
    engine.rootContext().setContextProperty("backend", backend_cls())
    engine.rootContext().setContextProperty("uiState", UIState())
    engine.rootContext().setContextProperty("signal", signal)
    engine.loadData(
        b"""
import QtQuick
import QtQuick.Window
Window {
    width: 1200; height: 800; visible: true
    QtObject { id: bsi; property var icons: ({ remove: "x" }) }
    LogicalPage { id: _page; anchors.fill: parent }
    function find(item, test) {
        if (test(item))
            return item
        for (var i = 0; i < item.children.length; i++) {
            var f = find(item.children[i], test)
            if (f) return f
        }
        return null
    }
    function panel() { return find(_page, function(i) { return i.liveOptions !== undefined && i.save !== undefined }) }
    function tree() { return find(_page, function(i) { return i.liveDecoration !== undefined }) }
}
""",
        QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "Root.qml")),
    )
    if not engine.rootObjects():
        for warning in warnings:
            print("ERROR load: " + warning, flush=True)
        os._exit(1)
    win = engine.rootObjects()[0]
    s._wait(400)
    js = lambda code: s._js(win, code)  # noqa: E731
    s._Out.result("pageKey", js("panel().pageKey"))
    s._Out.result("loaded", js("panel().rowSpacing + ' ' + tree().rowSpacing"))
    js("panel().parentHeight = 60; panel().save(); 1")
    s._wait(100)
    s._Out.result("saved", json.dumps(window_placement.list_appearance("logical")))
    other = window_placement.list_appearance("device-bindings")
    s._Out.result("other", json.dumps(other))
    s._Out.result("toast", js("panel().toastText"))
    s._Out.result(
        "old",
        str(
            gremlin.config.Configuration().exists(
                "global", "internal", "logical-layout"
            )
        ),
    )
    s._Out.result("tree", js("String(tree().parentHeight)"))
    s._Out.result("liveRows", js("String(panel().liveOptions)"))
    s._Out.result("liveDecoration", js("String(tree().liveDecoration)"))
    s._report(warnings)


def _tree(s, out: pathlib.Path) -> None:  # noqa: ANN001
    from PySide6 import QtCore

    app, engine, warnings = s._engine(out)  # noqa: F841
    engine.loadData(
        b"""
import QtQuick
import QtQuick.Window
Window {
    width: 800; height: 600; visible: true
    property string clicked: ""
    ListModel {
        id: _rows
        function keyAt(i) { return get(i).key }
        function setSelection(keys) {}
        ListElement { rowKind: "group"; key: "group:"; title: "Ungrouped"; subtitle: ""; parentKey: ""; groupKey: "g"; groupName: ""; systemName: ""; userName: ""; sequenceIndex: -1; childCount: 2; liveIndex: -1 }
        ListElement { rowKind: "parent"; key: "parent:button:1"; title: "Button 1"; subtitle: ""; parentKey: ""; groupKey: "g"; groupName: ""; systemName: "Button 1"; userName: ""; sequenceIndex: -1; childCount: 0; liveIndex: 0 }
        ListElement { rowKind: "parent"; key: "parent:axis:1"; title: "Axis 1"; subtitle: ""; parentKey: ""; groupKey: "g"; groupName: ""; systemName: "Axis 1"; userName: ""; sequenceIndex: -1; childCount: 0; liveIndex: 1 }
    }
    QtObject {
        id: _live
        property int stamp: 1
        function kindAt(i) { return i === 0 ? "button" : "axis" }
        function valueAt(i) { return i === 0 ? 1.0 : 0.5 }
    }
    ControlTree {
        id: _tree
        anchors.fill: parent
        layout: _rows
        liveState: _live
        onParentClicked: (key, title, shift) => clicked = key + "|" + title + "|" + shift
    }
    ControlTree { id: _bare; width: 10; height: 10 }
    function find(item, test) {
        if (test(item))
            return item
        for (var i = 0; i < item.children.length; i++) {
            var f = find(item.children[i], test)
            if (f) return f
        }
        return null
    }
    function row(key) { return find(_tree, function(i) { return i.ledOn !== undefined && i.key === key }) }
}
""",
        QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "Root.qml")),
    )
    if not engine.rootObjects():
        for warning in warnings:
            print("ERROR load: " + warning, flush=True)
        os._exit(1)
    win = engine.rootObjects()[0]
    s._wait(300)
    js = lambda code: s._js(win, code)  # noqa: E731
    s._Out.result("default", js("String(_bare.liveDecoration)"))
    s._Out.result(
        "off",
        js(
            "row('parent:button:1').ledOn + ' ' + (row('parent:axis:1').liveKind === 'axis')"
        ),
    )
    js("_tree.liveDecoration = true; 1")
    s._wait(50)
    s._Out.result(
        "on", js("row('parent:button:1').ledOn + ' ' + row('parent:axis:1').liveKind")
    )
    js("_tree.liveLeds = false; 1")
    s._wait(50)
    s._Out.result("leds_off", js("String(row('parent:button:1').ledOn)"))
    shown = js("_tree.showKey('parent:axis:1')")
    s._Out.result("show", f"{str(shown).lower()} k:axis {js('_tree.highlightKey')}")
    s._Out.result("missing", str(js("_tree.showKey('parent:hat:9')")).lower())
    # A left click on a parent row says so (the Device Bindings page opens its pane).
    from PySide6 import QtTest

    at = js(
        "var r = row('parent:button:1'); var p = r.mapToItem(null, r.width / 2, 10); "
        "Math.round(p.x) + ',' + Math.round(p.y)"
    )
    pos = QtCore.QPoint(*(int(n) for n in str(at).split(",")))
    QtTest.QTest.mouseClick(
        win,
        QtCore.Qt.MouseButton.LeftButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
        pos,
    )
    s._wait(100)
    s._Out.result("clicked", js("clicked"))
    s._report(warnings)


def _store(s, out: pathlib.Path) -> None:  # noqa: ANN001
    from gremlin.ui import window_placement

    placement = window_placement.WindowPlacement()
    mine = {"rowSpacing": 9, "parentAlign": "right"}
    window_placement.set_list_appearance("device-bindings", {"rowSpacing": 3})
    placement.setListAppearance("logical", json.dumps(mine))
    checks = [
        window_placement.list_appearance("logical") == mine,
        window_placement.list_appearance("device-bindings") == {"rowSpacing": 3},
        json.loads(placement.listAppearance("logical")) == mine,
        placement.listAppearance("keyboard") == "{}",
        placement.listAppearance("osc") == "{}",
    ]
    placement.setListAppearance("logical", "[1, 2]")  # not an object: ignored
    placement.setListAppearance("logical", "not json")
    checks.append(json.loads(placement.listAppearance("logical")) == mine)
    # Reset one page: the others keep theirs.
    placement.setListAppearance("logical", "{}")
    checks.append(placement.listAppearance("logical") == "{}")
    other = window_placement.list_appearance("device-bindings")
    checks.append(other == {"rowSpacing": 3})
    s._Out.result("store", "ok" if all(checks) else repr(checks))
    print("done", flush=True)


def _rows(s, out: pathlib.Path) -> None:  # noqa: ANN001
    from PySide6 import QtCore

    app, engine, warnings = s._engine(out)  # noqa: F841
    engine.loadData(
        b"""
import QtQuick
import QtQuick.Window
import Gremlin.Style
Window {
    width: 800; height: 600; visible: true
    ListModel {
        id: _rows
        function keyAt(i) { return get(i).key }
        function setSelection(keys) {}
        ListElement { rowKind: "group"; key: "group:a"; title: "A"; subtitle: ""; parentKey: ""; groupKey: "a"; groupName: "A"; systemName: ""; userName: ""; sequenceIndex: -1; childCount: 1 }
        ListElement { rowKind: "parent"; key: "parent:button:1"; title: "Button 1"; subtitle: ""; parentKey: ""; groupKey: "a"; groupName: "A"; systemName: "Button 1"; userName: ""; sequenceIndex: -1; childCount: 1 }
        ListElement { rowKind: "child"; key: "child:1"; title: "Map to vJoy"; subtitle: ""; parentKey: "parent:button:1"; groupKey: "a"; groupName: "A"; systemName: ""; userName: ""; sequenceIndex: 0; childCount: 0 }
        ListElement { rowKind: "group"; key: "group:b"; title: "B"; subtitle: ""; parentKey: ""; groupKey: "b"; groupName: "B"; systemName: ""; userName: ""; sequenceIndex: -1; childCount: 0 }
    }
    ControlTree {
        id: _tree
        anchors.fill: parent
        layout: _rows
        opened: ({ "parent:button:1": true })
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
    function row(key) { return find(_tree, function(i) { return i.ledOn !== undefined && i.key === key }) }
    // The row's box (its first child) and the right end of its text line.
    function box(key) { var b = row(key).children[0]; return Math.round(b.x) + " " + Math.round(b.width) }
    function textRight(key) {
        var r = row(key)
        for (var i = 0; i < r.children.length; i++)
            if (r.children[i].spacing !== undefined)
                return Math.round(r.children[i].x + r.children[i].width)
        return -1
    }
}
""",
        QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "Root.qml")),
    )
    if not engine.rootObjects():
        for warning in warnings:
            print("ERROR load: " + warning, flush=True)
        os._exit(1)
    win = engine.rootObjects()[0]
    s._wait(300)
    js = lambda code: s._js(win, code)  # noqa: E731
    s._Out.result(
        "metrics",
        js(
            "Math.round(row('parent:button:1').width) + ' ' + Style.dp(16)"
            " + ' ' + Style.dp(48) + ' ' + Style.dp(12)"
        ),
    )
    s._Out.result("groupH", js("String(Math.round(row('group:b').height))"))
    s._Out.result(
        "default",
        js(
            "box('parent:button:1') + ' ' + box('child:1')"
            " + ' ' + Math.round(row('group:b').children[0].y)"
            " + ' ' + Math.round(row('group:b').height)"
        ),
    )
    js("_tree.parentAlign = 'center'; _tree.parentWidthPct = 50; 1")
    s._wait(50)
    s._Out.result("parentCenter", js("box('parent:button:1')"))
    js("_tree.childAlign = 'right'; _tree.childWidthPct = 40; 1")
    s._wait(50)
    s._Out.result("childRight", js("box('child:1')"))
    js("_tree.parentAlign = 'left'; _tree.parentWidthPct = 60; 1")
    s._wait(50)
    s._Out.result(
        "parentLeft", js("box('parent:button:1') + ' ' + textRight('parent:button:1')")
    )
    js("_tree.groupSpacing = 12; 1")
    s._wait(50)
    s._Out.result(
        "groupGap",
        js(
            "Math.round(row('group:a').height)"
            " + ' ' + Math.round(row('group:b').children[0].y)"
            " + ' ' + Math.round(row('group:b').height)"
        ),
    )
    s._report(warnings)


if __name__ == "__main__":
    _s = _screens()
    _s._boot()
    sys.stdout.reconfigure(encoding="utf-8")
    _part, _out_dir = sys.argv[1], pathlib.Path(sys.argv[2])
    _out_dir.mkdir(parents=True, exist_ok=True)
    try:
        parts = {"logical": _logical, "tree": _tree, "rows": _rows, "store": _store}
        parts[_part](_s, _out_dir)
    except Exception as failed:  # noqa: BLE001
        import traceback

        traceback.print_exc()
        print(f"ERROR {_part}: {failed!r}", flush=True)
        os._exit(1)
