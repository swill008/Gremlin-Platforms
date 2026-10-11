# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Help's Show me › into the Button Map window (07 S126,
D-07-PLANES-FOLLOWUP Q1a), off-screen with stand-in hardware: Main's own
Style.helpLinks.reveal() for show:buttonmap/<name>, first with no Button Map
open (it opens on the first device, not editing: the message), then while
editing (each place pulsed). The removed switch, bmPlaneSwitch, is refused
(07 S113, S126). Prints "RESULT <json>".
test_help_showme_buttonmap.py runs it in its own process with a fresh user
folder.
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

NAMES = ("bmBgBanner", "bmBgRow")
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
        if w.isVisible() and w.title().startswith("Button Map"):
            return w
    return None


def reveal(link: str) -> str:
    return str(ev(win, f"String(Style.helpLinks.reveal({json.dumps(link)}))"))


def pulsed(bm: QtQuick.QQuickWindow, name: str) -> bool:
    if name == "bmBgRow":
        item = ev(bm, "_layersPanel.bgRowPart('bmBgRow')")
    else:
        item = find_item(bm.contentItem(), name)
    if not isinstance(item, QtQuick.QQuickItem):
        return False
    return any(c.objectName() == "helpPulse" for c in item.childItems())


out: dict = {"errors": []}
app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window
win.setProperty("visible", True)
wait_until(lambda: win.isVisible())
wait_until(lambda: bool(ev(win, "Style.helpLinks !== null")), 8000)
try:
    out["check"] = {
        n: str(ev(win, f"String(Style.helpLinks.check('show:buttonmap/{n}'))"))
        for n in (*NAMES, "bmPlaneSwitch", "noSuchThing")
    }
    out["closed"] = reveal("show:buttonmap/bmBgBanner")
    wait_until(lambda: map_window() is not None, 5000)
    bm = map_window()
    out["opened"] = bm is not None
    if bm is not None:
        settle(500)
        out["device"] = str(ev(bm, "_buttonMap.targetName"))
        out["message"] = str(ev(bm, "_messageLine.text"))
        out["not_editing"] = {n: reveal(f"show:buttonmap/{n}") for n in NAMES}
        ev(bm, "_buttonMap.enterEdit(); 1")
        wait_until(
            lambda: bool(ev(bm, "_buttonMap.editing && !!_buttonMap._ed()")), 5000
        )
        settle(300)
        out["editing"] = {}
        for n in NAMES:
            why = reveal(f"show:buttonmap/{n}")
            settle(100)
            out["editing"][n] = {
                "why": why, "pulsed": pulsed(bm, n),
                "plane": str(ev(bm, "_buttonMap._ed().editPlane")),
                "layers": bool(ev(bm, LAYERS_SIDE + ".open")),
            }
        ev(bm, "_buttonMap.discardEdit(); 1")
        settle(200)
except Exception as exc:  # noqa: BLE001
    out["errors"].append(repr(exc))

print("RESULT " + json.dumps(out), flush=True)
sys.stdout.flush()
smoke_exit(0)
