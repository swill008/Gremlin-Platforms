# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware, a stick with a map),
enters Edit and checks the Chips panel's filter row (07 S132): at the
panel's narrowest and widest the filter box has the whole top row and Reset
and the Chip only tick sit on the row under it; typing still filters the
pool, Reset clears it. Prints what it saw as JSON.
test_chips_filter_row.py runs it in its own process and user folder.

    python test/unit/chips_filter_row_smoke.py

Waits poll for what is checked with a generous limit; none sleeps a fixed
time (GL-001).
"""

from __future__ import annotations

import importlib.util
import json
import sys
import time
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import cast

from smoke_exit import smoke_exit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "test"))
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

from qt_wait import wait_until  # noqa: E402  # pyright: ignore[reportMissingImports]

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
    QtTest.QTest.qWait(50)


GEOM = ("(function() { " + FIND + " var root = _poolFloat;"
        " function g(n) { var it = _f(root, n);"
        "  var p = it.mapToItem(root, 0, 0);"
        "  return { x: Math.round(p.x), y: Math.round(p.y),"
        "   w: Math.round(it.width), h: Math.round(it.height),"
        "   iw: Math.round(it.implicitWidth),"
        "   shown: it.visible } }"
        " return JSON.stringify({ panel: Math.round(root.width),"
        "  width: Math.round(_chipsSide.panelWidth),"
        "  margins: Math.round(Style.dp(8) + Style.dp(10)),"
        "  box: g('poolFilter'), reset: g('poolReset'),"
        "  tick: g('poolChipOnly') }) })()")


def main() -> None:
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    root = wait_for(lambda: (app.engine.rootObjects() or [None])[0])
    assert isinstance(root, QtCore.QObject)
    out: dict = {}

    card = {"rawName": "pJoy Pro", "name": "pJoy Pro", "guid": GUID}
    call(root, "openDeviceMappingEditorForCard", card)
    win = wait_for(lambda: call(root, "deviceMappingEditorWindow"))
    assert isinstance(win, QtGui.QWindow)
    wait_for(lambda: ev(win, "mapShown && targetName === 'pJoy Pro'"))
    win.resize(1600, 900)
    wait_for(lambda: ev(win, "_mapRow.width > 1500"))
    call(win, "enterEdit")
    wait_for(lambda: ev(win, "editing && _ed() !== null && _ed().seeded"
                        " && !_baseWanted && _poolFloat.visible"))
    QtTest.QTest.qWait(100)

    for key, expr in (("min", "_chipsSide.minWidth"), ("max", "_chipsSide.maxWidth"),
                      ("start", "Style.dp(260)"), ("mid", "Style.dp(320)")):
        ev(win, f"_chipsSide.panelWidth = {expr}; true")
        wait_for(lambda: ev(win, f"Math.abs(_poolFloat.width - {expr}) < 40"))
        QtTest.QTest.qWait(100)
        out[key] = json.loads(cast(str, ev(win, GEOM)))

    # Typing filters the pool; Reset clears it.
    out["all"] = ev(win, "resItems.length")
    click(win, centre(win, "_poolFloat", "poolFilter"))
    for ch in "zzzq":
        QtTest.QTest.keyClick(win, getattr(QtCore.Qt.Key, "Key_" + ch.upper()))
    wait_until(
        lambda: ev(win, "poolFilter === 'zzzq' && resItems.length === 0"),
        "the typed filter", fail=False,
    )
    out["typed"] = ev(win, "poolFilter")
    out["filtered"] = ev(win, "resItems.length")
    click(win, centre(win, "_poolFloat", "poolReset"))
    out["reset"] = ev(win, "poolFilter")
    out["after-reset"] = ev(win, "resItems.length")
    # Chip only still sets the Device Mapping Editor option.
    before = ev(win, "_opts.values['chip-only'] === true")
    click(win, centre(win, "_poolFloat", "poolChipOnly"))
    out["chip-only"] = [before, ev(win, "_opts.values['chip-only'] === true")]

    print("RESULT " + json.dumps(out), flush=True)
    smoke_exit(0)


if __name__ == "__main__":
    try:
        main()
    except BaseException:
        traceback.print_exc()
    finally:
        sys.stdout.flush()
        smoke_exit(1)
