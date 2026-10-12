# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware, a stick with a map) and
drives the Device Mapping Editor's side panels, Chips on the left and Layers on the
right (07 S99, S128-S131, D-07-SIDE-PANELS), with mouse clicks on the real
window: hidden outside Edit, the map narrowed by a pinned panel and not by
an unpinned one, a map click and the other strip's click folding an unpinned
panel, Background mode folding Chips and bringing it back, a narrow window
folding Chips then Layers and bringing them back, a user's own fold kept,
Properties under Layers with its divider (View > Properties, F4), and the
state kept in the Device Mapping Editor settings (DeviceMapOptions) for the next
window, View > Reset Panels putting it back. Prints what it saw as JSON.
test_side_panels_window.py runs it in its own process and user folder.

    python test/unit/side_panels_window_smoke.py

Waits poll for what is checked with a generous limit; none sleeps a fixed
time (GL-001).
"""

from __future__ import annotations

import importlib.util
import json
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import cast

from smoke_exit import smoke_exit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location(
    "fake_hardware", ROOT / "test" / "fake_hardware.py"
)
assert spec is not None and spec.loader is not None
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake = fake_hardware.install()

import gremlin.ui.update_model as um  # noqa: E402

um.UpdateModel.startup = lambda self, *a, **k: None

import shiboken6  # noqa: E402
from PySide6 import QtCore, QtGui, QtQml, QtTest  # noqa: E402

import dill  # noqa: E402

stick = fake.devices[0]
GUID = str(dill.GUID(stick.device_guid).uuid)
NODES = [
    {"kind": "btn", "id": f"b{i}", "label": f"Button {i}",
     "chipFx": 0.2 + 0.05 * i, "chipFy": 0.15}
    for i in range(1, 4)
]
from gremlin.modules import store  # noqa: E402

store.module_file_in(store.ensure_device_dir("pJoy Pro", GUID)).write_text(
    json.dumps({"kind": "control.hardware", "device": "pJoy Pro", "nodes": NODES}),
    encoding="utf-8",
)

import joystick_gremlin  # noqa: E402

Btn = QtCore.Qt.MouseButton
NoMod = QtCore.Qt.KeyboardModifier.NoModifier
LIMIT_S = 15.0


def call(obj: QtCore.QObject, name: str, *args: object) -> object:
    return QtCore.QMetaObject.invokeMethod(
        obj, name, QtCore.Q_RETURN_ARG("QVariant"),
        *[QtCore.Q_ARG("QVariant", a) for a in args],
    )


def same(a: object, b: object) -> bool:
    if not isinstance(a, QtCore.QObject) or not isinstance(b, QtCore.QObject):
        return False
    return shiboken6.getCppPointer(a)[0] == shiboken6.getCppPointer(b)[0]


def wait_for(check: Callable[[], object], limit: float = LIMIT_S) -> object:
    end = time.monotonic() + limit
    while True:
        value = check()
        if value or time.monotonic() > end:
            return value
        QtTest.QTest.qWait(25)


def ev(obj: QtCore.QObject, code: str) -> object:
    context = QtQml.qmlContext(obj)
    assert context is not None
    expr = QtQml.QQmlExpression(context, obj, code)
    value = expr.evaluate()
    if expr.hasError():
        return "error: " + expr.error().description()
    value = value[0] if isinstance(value, tuple) else value
    if hasattr(value, "toVariant"):
        value = value.toVariant()
    return value


FIND = ("function _f(it, n) { if (it.objectName === n) return it;"
        " for (var i = 0; i < it.children.length; i++) { var r = _f(it.children[i], n);"
        " if (r) return r } return null }")


def centre(win: QtCore.QObject, owner: str, name: str = "") -> QtCore.QPoint:
    """The scene centre of owner (or its child named name)."""
    target = f"_f({owner}, '{name}')" if name else owner
    got = ev(win, "(function() { " + FIND + " var s = " + target + ";"
             " var p = s.mapToItem(null, s.width / 2, s.height / 2);"
             " return JSON.stringify([Math.round(p.x), Math.round(p.y)]) })()")
    x, y = json.loads(cast(str, got))
    return QtCore.QPoint(x, y)


def click(win: QtGui.QWindow, point: QtCore.QPoint) -> None:
    QtTest.QTest.mouseClick(win, Btn.LeftButton, NoMod, point)
    # Past a side panel's slide (about 0.12 s), so the next click finds
    # its parts where they stay.
    QtTest.QTest.qWait(200)


STATE = ("JSON.stringify({"
         " chips: { open: _chipsSide.open, pinned: _chipsSide.pinned,"
         "  shown: _chipsSide.visible, taken: _chipsSide.takenWidth,"
         "  pool: _poolFloat.visible },"
         " layers: { open: _layersSide.open, pinned: _layersSide.pinned,"
         "  shown: _layersSide.visible, taken: _layersSide.takenWidth,"
         "  width: _layersSide.panelWidth },"
         " map: Math.round(_mapHost.width), row: Math.round(_mapRow.width),"
         " leftSlot: Math.round(_leftSlot.width),"
         " rightSlot: Math.round(_rightSlot.width),"
         " saved: { chips: _opts.sidePanelState('chips'),"
         "  layers: _opts.sidePanelState('layers') },"
         " props: { on: _editorWin.propsOn, shown: _editorWin.propsShown,"
         "  split: _editorWin.propsSplit, panel: _propsPanel.visible,"
         "  divider: _propsDivider.visible,"
         "  layersH: Math.round(_layersPanel.height),"
         "  bodyH: Math.round(_rightBody.height),"
         "  savedSplit: _opts.propsSplit(), savedShown: _opts.propsShown() } })")


def main() -> None:
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    root = wait_for(lambda: (app.engine.rootObjects() or [None])[0])
    assert isinstance(root, QtCore.QObject)
    out: dict = {}

    def state(win: QtCore.QObject) -> dict:
        QtTest.QTest.qWait(50)
        return json.loads(cast(str, ev(win, STATE)))

    def open_map() -> QtGui.QWindow:
        card = {"rawName": "pJoy Pro", "name": "pJoy Pro", "guid": GUID}
        call(root, "openDeviceMappingEditorForCard", card)
        win = wait_for(lambda: call(root, "deviceMappingEditorWindow"))
        assert isinstance(win, QtGui.QWindow)
        wait_for(lambda: ev(win, "mapShown && targetName === 'pJoy Pro'"))
        win.resize(1600, 900)
        wait_for(lambda: ev(win, "_mapRow.width > 1500"))
        return win

    def edit(win: QtCore.QObject) -> None:
        call(win, "enterEdit")
        wait_for(lambda: ev(win, "editing && _ed() !== null && _ed().seeded"
                            " && !_baseWanted"))
        QtTest.QTest.qWait(100)

    win = open_map()
    out["not-editing"] = state(win)
    rows = ", ".join(f"_f(_editorWin.contentItem, 'toolRow{side}')"
                     for side in ("Left", "Right", "Top", "Bottom"))
    out["tool-rows"] = ev(win, "(function() { " + FIND + " return [" + rows + "]"
                          ".map(function(r) { return !!r }) })()")
    edit(win)
    out["editing"] = state(win)
    # Folded Layers: its drawer's frame ajar on the window's right edge.
    out["layers-edge"] = ev(win, "(function() { " + FIND + " var b ="
                            " _f(_layersSide, 'sidePanelBody');"
                            " var p = b.mapToItem(null, 0, 0);"
                            " return [Math.round(_editorWin.width - p.x),"
                            " Math.round(Style.dp(7))] })()")
    # The status line: one slim row of small text.
    out["status-height"] = ev(win, "_statusLine.height")

    # Layers' strip: out over the map (the map keeps its width).
    click(win, centre(win, "_layersSide", "sideStrip"))
    out["layers-strip"] = state(win)
    # A click on the map folds the unpinned Layers, not the pinned Chips.
    click(win, centre(win, "_mapHost"))
    out["map-click"] = state(win)

    # Chips unpinned (its pin): over the map, the map wider.
    click(win, centre(win, "_chipsSide", "sidePin"))
    out["chips-unpinned"] = state(win)
    # Layers' strip folds the unpinned Chips.
    click(win, centre(win, "_layersSide", "sideStrip"))
    out["other-strip"] = state(win)
    # Chips' strip folds the unpinned Layers.
    click(win, centre(win, "_chipsSide", "sideStrip"))
    out["other-strip-back"] = state(win)

    # Chips pinned again; Background mode folds it, Foreground brings it back.
    click(win, centre(win, "_chipsSide", "sidePin"))
    out["chips-pinned"] = state(win)
    ev(win, "setEditPlane('background')")
    wait_for(lambda: ev(win, "bgMode"))
    # Past Chips' slide back to its ajar edge (about 0.12 s).
    QtTest.QTest.qWait(200)
    out["bg-mode"] = state(win)
    ev(win, "setEditPlane('foreground')")
    wait_for(lambda: not ev(win, "bgMode"))
    QtTest.QTest.qWait(200)
    out["fg-mode"] = state(win)

    # Layers pinned and out too; then a narrow window: Chips folds first.
    click(win, centre(win, "_layersSide", "sideStrip"))
    click(win, centre(win, "_layersSide", "sidePin"))
    out["both-pinned"] = state(win)
    # Layers wider (as a restore sets it, not kept), so the narrowest window
    # has no room for it beside the map either (the ajar Chips edge is only
    # 7 px).
    ev(win, "_layersSide.panelWidth = Style.dp(400); true")
    QtTest.QTest.qWait(100)
    # Room for the map with Layers but not with both: only Chips folds.
    win.resize(900, 900)
    wait_for(lambda: ev(win, "Math.round(_mapRow.width) === 900"))
    QtTest.QTest.qWait(100)
    out["mid"] = state(win)
    win.resize(1600, 900)
    wait_for(lambda: ev(win, "_mapRow.width > 1500"))
    QtTest.QTest.qWait(100)
    out["mid-wide"] = state(win)
    min_w = int(cast(float, ev(win, "minimumWidth")))
    win.resize(min_w, 900)
    wait_for(lambda: ev(win, f"Math.round(_mapRow.width) < {min_w}"))
    QtTest.QTest.qWait(100)
    out["min-width"] = min_w
    out["narrow"] = state(win)
    win.resize(1600, 900)
    wait_for(lambda: ev(win, "_mapRow.width > 1500"))
    QtTest.QTest.qWait(100)
    out["wide-again"] = state(win)

    # Narrow again, then the user opens Chips by its strip: their choice
    # stays when there is room again.
    win.resize(min_w, 900)
    wait_for(lambda: ev(win, f"Math.round(_mapRow.width) < {min_w}"))
    QtTest.QTest.qWait(100)
    click(win, centre(win, "_chipsSide", "sideStrip"))
    out["narrow-user-open"] = state(win)
    win.resize(1600, 900)
    wait_for(lambda: ev(win, "_mapRow.width > 1500"))
    QtTest.QTest.qWait(100)
    out["wide-user-kept"] = state(win)

    # Properties under Layers (Layers is out, pinned): shown while something
    # is selected, with the divider between them (07 S135).
    out["props-none"] = state(win)
    ev(win, "_editorWin.selectAllNow()")
    wait_for(lambda: ev(win, "_editorWin.propsShown"))
    out["props-selected"] = state(win)
    # The divider dragged down by a tenth of the room: kept when let go.
    start = centre(win, "_layersSide", "propsDivider")
    room = cast(float, ev(win, "_rightBody.height - _rightBody.grip"))
    end = QtCore.QPoint(start.x(), start.y() + round(room * 0.1))
    QtTest.QTest.mousePress(win, Btn.LeftButton, NoMod, start)
    for i in range(1, 9):
        QtTest.QTest.mouseMove(win, QtCore.QPoint(
            start.x(), start.y() + (end.y() - start.y()) * i // 8))
        QtTest.QTest.qWait(15)
    QtTest.QTest.mouseRelease(win, Btn.LeftButton, NoMod, end)
    QtTest.QTest.qWait(100)
    out["props-dragged"] = state(win)
    # View > Properties (F4) hides it; kept for the next window.
    QtTest.QTest.keyClick(win, QtCore.Qt.Key.Key_F4)
    wait_for(lambda: not ev(win, "_editorWin.propsOn"))
    out["props-f4"] = state(win)

    # A width kept from the inner edge (as a drag ends), then leaving Edit.
    ev(win, "_layersSide.panelWidth = 333; _layersSide.changed(); true")
    call(win, "discardEdit")
    wait_for(lambda: not ev(win, "editing"))
    out["left-edit"] = state(win)

    # The next window has them as they were left.
    old = win
    ev(win, "_editorWin.close()")
    wait_for(lambda: not same(call(root, "deviceMappingEditorWindow"), old))
    win = open_map()
    edit(win)
    out["reopened"] = state(win)

    # View > Reset Panels, the menu item itself: back to the first look.
    items = [o for o in win.findChildren(QtCore.QObject, "dmeResetPanels")
             if o.metaObject().indexOfSignal("triggered()") >= 0]
    out["reset-items"] = [o.property("text") for o in items]
    if items:
        ev(items[0], "triggered()")
    QtTest.QTest.qWait(200)
    out["reset"] = state(win)

    print("RESULT " + json.dumps(out), flush=True)
    smoke_exit(0)


if __name__ == "__main__":
    try:
        main()
    finally:
        sys.stdout.flush()
        smoke_exit(1)
