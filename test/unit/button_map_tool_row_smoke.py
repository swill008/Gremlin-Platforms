# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware), opens the Button Map
for a stick and uses its tool row; prints what shows after each step as
JSON. test_button_map_tool_row.py runs it in its own process with a fresh
user folder.

    python test/unit/button_map_tool_row_smoke.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location(
    "fake_hardware", ROOT / "test" / "fake_hardware.py"
)
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake = fake_hardware.install()

import gremlin.ui.update_model as um  # noqa: E402

um.UpdateModel.startup = lambda self, *a, **k: None

from PySide6 import QtCore, QtQml, QtTest  # noqa: E402

import dill  # noqa: E402
import joystick_gremlin  # noqa: E402

GUID = str(dill.GUID(fake.devices[0].device_guid).uuid)


def call(obj: QtCore.QObject, name: str, *args: object) -> object:
    return QtCore.QMetaObject.invokeMethod(
        obj, name, QtCore.Q_RETURN_ARG("QVariant"),
        *[QtCore.Q_ARG("QVariant", a) for a in args],
    )


def main() -> None:
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    QtTest.QTest.qWait(800)
    root = app.engine.rootObjects()[0]
    card = {"rawName": "pJoy Pro", "name": "pJoy Pro", "guid": GUID}
    call(root, "openButtonMapForCard", card)
    QtTest.QTest.qWait(1000)
    win = call(root, "buttonMapWindow")
    win.setProperty("width", 1200)
    win.setProperty("height", 800)
    QtTest.QTest.qWait(300)
    out: dict = {}

    def ev(code: str) -> object:
        expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
        value = expr.evaluate()
        if expr.hasError():
            return "error: " + expr.error().toString()
        value = value[0] if isinstance(value, tuple) else value
        return value.toVariant() if hasattr(value, "toVariant") else value

    def look(tag: str) -> None:
        out[tag] = json.loads(ev(
            "JSON.stringify({chips: _poolFloat.visible, props: _tools.isOpen('props'),"
            " layers: _layersPanel.visible, palette: _palette.opened,"
            " order: _tools.order()})"
        ))

    def step(code: str, tag: str, wait: int = 250) -> None:
        ev(code)
        QtTest.QTest.qWait(wait)
        look(tag)

    call(win, "enterEdit")
    QtTest.QTest.qWait(800)
    look("1-edit")
    step("_tools.toggle('chips')", "2-chips-open")
    # A click on the map: the unpinned pool hides.
    step("_ed().mapPressed()", "3-map-click")
    step("_tools.setPinned('chips', true); _tools.setOpen('chips', true);"
         " _tools.setOpen('layers', true)", "4-chips-pinned-layers-open")
    # Pinned stays, unpinned (Layers) hides.
    step("_ed().mapPressed()", "5-map-click")
    step("_tools.moveTo('palette', 0)", "6-moved")
    # Locked: it stays where it is.
    step("_tools.setLocked('palette', true); _tools.moveTo('palette', 3)",
         "7-locked-move")
    step("_tools.setOpen('palette', true)", "8-palette")
    step("_palette.close()", "9-palette-closed")

    # The bars: the status line one row of small text, the tool row below
    # the map; the pool docked just above the tool row.
    out["status-height"] = ev("_statusLine.height")
    out["pool-bottom-gap"] = ev(
        "Math.round(_poolFloat.parent.height - _poolFloat.y - _poolFloat.height)")
    from gremlin.ui import window_placement

    out["saved"] = window_placement.tool_row_state("button-map")
    print("RESULT " + json.dumps(out), flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
