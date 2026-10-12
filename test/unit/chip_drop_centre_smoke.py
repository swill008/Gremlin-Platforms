# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware, a stick with a map),
enters Edit and drops chips from the Chips panel onto the map (07 S156):
through the window's dropPool at zoom 1 and 2, with Chip only off and on,
and once with no point (the view's centre). For each it records the drop
point, the drawn chip's centre and the hotspot, in map pixels. Prints what
it saw as JSON. test_chip_drop_centre.py runs it in its own process and
user folder.

    python test/unit/chip_drop_centre_smoke.py

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
    QtTest.QTest.qWait(50)


CHIP = ("(function(hw) { var e = _ed(); var L = e.nodes || [];"
        " for (var i = 0; i < L.length; i++) { var n = L[i];"
        "  if (n.kind === 'btn' && n.hwId === hw) {"
        "   var it = e._chipsItem(i);"
        "   var c = it.mapToItem(_mapHost, it.width / 2, it.height / 2);"
        "   var h = e.mapToItem(_mapHost, e.fxToX(n.hotFx), e.fyToY(n.hotFy));"
        "   var vc = e.viewCenterPage();"
        "   var vp = e.mapToItem(_mapHost, e.fxToX(vc.x), e.fyToY(vc.y));"
        "   return JSON.stringify({ cx: c.x, cy: c.y, hx: h.x, hy: h.y,"
        "    w: it.width, h: it.height, guess: e.chipWGuess(n, null),"
        "    hidden: n.hotHidden === true,"
        "    leaders: n.leaders ? n.leaders.length : -1,"
        "    vx: vp.x, vy: vp.y }) } }"
        " return 'missing' })")

# A point on the page, left of the Chips panel, away from the page's edges.
POINT = ("(function() { var e = _ed(); var s = e.spaceRect();"
         " var p = e.mapToItem(_mapHost, s.x + s.w * 0.37, s.y + s.h * 0.41);"
         " return JSON.stringify([p.x, p.y]) })()")


def chip(win: QtCore.QObject, hw: int) -> object:
    got = ev(win, CHIP + f"({hw})")
    return json.loads(got) if isinstance(got, str) and got.startswith("{") else got


def main() -> None:
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    root = wait_for(lambda: (app.engine.rootObjects() or [None])[0])
    assert isinstance(root, QtCore.QObject)
    out: dict = {"drops": []}

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

    hw = 20
    for zoom in (1, 2):
        ev(win, f"_ed().face.zoom = {zoom}; true")
        QtTest.QTest.qWait(150)
        for chip_only in (False, True):
            ev(win, f"_opts.set('chip-only', {str(chip_only).lower()}); true")
            x, y = json.loads(cast(str, ev(win, POINT)))
            ev(win, f"poolKind = 'btn'; poolHw = {hw}; dropPool({x}, {y}); true")
            QtTest.QTest.qWait(100)
            out["drops"].append({"zoom": zoom, "chipOnly": chip_only,
                                 "x": x, "y": y, "got": chip(win, hw)})
            hw += 1
    # No point: the chip goes to the view's centre, centred there too.
    ev(win, "_opts.set('chip-only', false); true")
    ev(win, f"_ed().addChiplet('btn', {hw}); true")
    QtTest.QTest.qWait(100)
    out["centre"] = chip(win, hw)

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
