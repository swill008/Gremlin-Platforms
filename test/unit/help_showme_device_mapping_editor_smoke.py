# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Help's Show me › into the Device Mapping Editor window (07 S126,
D-07-PLANES-FOLLOWUP Q1a), off-screen with stand-in hardware: Main's own
Style.helpLinks.reveal() for show:devicemappingeditor/<name>, first with no
Device Mapping Editor open (it opens on the first device, not editing: the
message, but the menus that work outside Edit are pulsed), then while editing
(each place pulsed; Properties first with nothing selected, then with a line
selected). One link per area (user 2026-10-11): each menu's title in the bar,
the Chips and Layers side panels, Properties, the Background banner and row.
The removed switch, dmePlaneSwitch, is refused (07 S113, S126). Prints
"RESULT <json>". test_help_showme_device_mapping_editor.py runs it in its own
process with a fresh user folder.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

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

from PySide6 import QtCore, QtGui, QtQml, QtQuick  # noqa: E402

import joystick_gremlin  # noqa: E402
from gremlin import clock  # noqa: E402

# The menus that open outside Edit, those that need it, and the other places.
FREE_MENUS = (
    "dmeMenuFile", "dmeMenuEdit", "dmeMenuView", "dmeMenuFormat", "dmeMenuHelp"
)
EDIT_MENUS = ("dmeMenuInsert", "dmeMenuArrange", "dmeMenuLeader")
PLACES = ("chipsSide", "layersSide", "propsPanel", "dmeBgBanner", "dmeBgRow")
NAMES = (*FREE_MENUS, *EDIT_MENUS, *PLACES)
# Layers is the right side panel (07 S128): the SidePanel holding _layersPanel.
LAYERS_SIDE = ("(function(){ var p = _layersPanel;"
               " while (p && p.takenWidth === undefined) p = p.parent; return p })()")


def wait_until(cond, limit_ms: int = 10000) -> bool:  # noqa: ANN001
    end = clock.monotonic() + limit_ms / 1000.0
    qapp = QtCore.QCoreApplication.instance()
    while True:
        if cond():
            return True
        if clock.monotonic() > end:
            return False
        qapp.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 20)
        clock.sleep(0.005)


def settle(ms: int = 250) -> None:
    wait_until(lambda: False, ms)


def ev(obj: QtCore.QObject, code: str) -> object:
    expr = QtQml.QQmlExpression(QtQml.qmlContext(obj), obj, code)
    value = expr.evaluate()
    if expr.hasError():
        raise RuntimeError(expr.error().toString() + " :: " + code[:200])
    value = value[0] if isinstance(value, tuple) else value
    return value.toVariant() if hasattr(value, "toVariant") else value


def find_item(item: QtQuick.QQuickItem, name: str) -> QtQuick.QQuickItem | None:
    if item.objectName() == name:
        return item
    for child in item.childItems():
        found = find_item(child, name)
        if found is not None:
            return found
    return None


def map_window() -> QtQuick.QQuickWindow | None:
    for w in QtGui.QGuiApplication.topLevelWindows():
        if w.isVisible() and w.title().startswith("Device Mapping Editor"):
            return w
    return None


def reveal(link: str) -> str:
    return str(ev(win, f"String(Style.helpLinks.reveal({json.dumps(link)}))"))


def in_bar(bm: QtQuick.QQuickWindow, name: str, what: str) -> object:
    """what ("item" or "title") of the menu bar's menu with this objectName."""
    get = "_menuBar.itemAt(i)" if what == "item" else "_menuBar.menuAt(i).title"
    return ev(bm, "(function(){ for (var i = 0; i < _menuBar.count; ++i)"
                  f" if (_menuBar.menuAt(i).objectName === {json.dumps(name)})"
                  f" return {get}; return null }})()")


def bar_item(bm: QtQuick.QQuickWindow, name: str) -> object:
    """The menu bar's title for the menu with this objectName."""
    return in_bar(bm, name, "item")


def target(bm: QtQuick.QQuickWindow, name: str) -> object:
    if name == "dmeBgRow":
        return ev(bm, "_layersPanel.bgRowPart('dmeBgRow')")
    if name.startswith("dmeMenu"):
        return bar_item(bm, name)
    return find_item(bm.contentItem(), name)


def pulses(bm: QtQuick.QQuickWindow, name: str) -> int:
    item = target(bm, name)
    if not isinstance(item, QtQuick.QQuickItem):
        return -1
    return sum(c.objectName() == "helpPulse" for c in item.childItems())


def show(bm: QtQuick.QQuickWindow, name: str) -> dict:
    """Show me › for name: why not, and whether a new pulse marks it."""
    before = pulses(bm, name)
    why = reveal(f"show:devicemappingeditor/{name}")
    settle(100)
    after = pulses(bm, name)
    # The place may only exist once shown (the Background row): -1 before.
    got = {"why": why, "pulsed": after > max(before, 0)}
    if name.startswith("dmeMenu"):
        item = bar_item(bm, name)
        ok = isinstance(item, QtCore.QObject)
        got["text"] = str(item.property("text")) if ok else ""
        got["title"] = str(in_bar(bm, name, "title") or "")
    return got


out: dict = {"errors": []}
app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window
win.setProperty("visible", True)
wait_until(lambda: win.isVisible())
wait_until(lambda: bool(ev(win, "Style.helpLinks !== null")), 8000)
try:
    out["check"] = {
        n: str(ev(
            win, f"String(Style.helpLinks.check('show:devicemappingeditor/{n}'))"
        ))
        for n in (*NAMES, "dmePlaneSwitch", "noSuchThing")
    }
    out["closed"] = reveal("show:devicemappingeditor/dmeBgBanner")
    wait_until(lambda: map_window() is not None, 5000)
    bm = map_window()
    out["opened"] = bm is not None
    if bm is not None:
        settle(500)
        out["device"] = str(ev(bm, "_editorWin.targetName"))
        out["message"] = str(ev(bm, "_messageLine.text"))
        out["not_editing"] = {n: show(bm, n) for n in NAMES}
        ev(bm, "_editorWin.enterEdit(); 1")
        wait_until(
            lambda: bool(ev(bm, "_editorWin.editing && !!_editorWin._ed()")), 5000
        )
        settle(300)
        # Nothing selected: Properties says so.
        ev(bm, "_ed().setSelection([]); 1")
        settle(100)
        out["props_unselected"] = show(bm, "propsPanel")
        # Background mode first, so Chips has to come back from it.
        ev(bm, "_editorWin.setEditPlane('background'); 1")
        settle(200)
        out["editing"] = {}
        for n in NAMES:
            if n == "propsPanel":
                # Properties hidden by View > Properties and Layers folded:
                # Show me brings both out.
                ev(bm, "(function(){ var e = _ed(); e.setSelection([]);"
                       " e.addDrawFree('line', e.fxToX(0.6), e.fyToY(0.6),"
                       " e.fxToX(0.8), e.fyToY(0.8)); return 1 })()")
                ev(bm, "_editorWin.propsOn = false; " + LAYERS_SIDE + ".fold(); 1")
                settle(200)
            got = show(bm, n)
            got["plane"] = str(ev(bm, "_editorWin._ed().editPlane"))
            got["layers"] = bool(ev(bm, LAYERS_SIDE + ".open"))
            got["chips"] = bool(ev(bm, "_chipsSide.open"))
            got["props"] = bool(ev(bm, "_editorWin.propsShown"))
            out["editing"][n] = got
        ev(bm, "_editorWin.discardEdit(); 1")
        settle(200)
except Exception as exc:  # noqa: BLE001
    out["errors"].append(repr(exc))

print("RESULT " + json.dumps(out), flush=True)
sys.stdout.flush()
smoke_exit(0)
