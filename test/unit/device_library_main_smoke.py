# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware), fires Home's
openDeviceLibrary signal the way its Device Library... button and the card
menu do, and prints as JSON whether the Device Library window opened and
what QML printed. test_device_library_main_route.py runs it in its own
process with a fresh user folder.
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
assert spec is not None and spec.loader is not None
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake = fake_hardware.install()

import gremlin.ui.update_model as um  # noqa: E402

um.UpdateModel.startup = lambda self, *a, **k: None

from PySide6 import QtCore, QtGui, QtQml  # noqa: E402

import joystick_gremlin  # noqa: E402
from gremlin import clock  # noqa: E402

messages: list[str] = []


def _capture(mode, context, text: str) -> None:  # noqa: ANN001
    messages.append(text)


QtCore.qInstallMessageHandler(_capture)


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


def ev(obj: QtCore.QObject, code: str) -> object:
    expr = QtQml.QQmlExpression(QtQml.qmlContext(obj), obj, code)
    value = expr.evaluate()
    if expr.hasError():
        raise RuntimeError(expr.error().toString() + " :: " + code[:200])
    value = value[0] if isinstance(value, tuple) else value
    return value.toVariant() if hasattr(value, "toVariant") else value


def library_open() -> bool:
    return any(
        w.isVisible() and w.title() == "Device Library"
        for w in QtGui.QGuiApplication.topLevelWindows()
    )


app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window
win.setProperty("visible", True)
wait_until(lambda: win.isVisible())
wait_until(lambda: bool(ev(win, "_statusLoader.item !== null")))
messages.clear()
# Home's Device Library... button: no card, no action.
ev(win, "_statusLoader.item.openDeviceLibrary(null, '')")
opened = wait_until(library_open, 8000)
button = {
    "opened": opened,
    "recursion": any("Maximum call stack" in m for m in messages),
    "too_many_arguments": sum("Too many arguments" in m for m in messages),
}
# Tools > Device Setup > Device Library..., through the command registry.
for w in QtGui.QGuiApplication.topLevelWindows():
    if w.title() == "Device Library":
        w.close()
wait_until(lambda: not library_open(), 3000)
messages.clear()
ev(win, "Commands.trigger('tools.deviceLibrary')")
tools = {
    "opened": wait_until(library_open, 8000),
    "recursion": any("Maximum call stack" in m for m in messages),
    "errors": [m for m in messages if "Error" in m or "is not a function" in m][:5],
}
out = {"button": button, "tools": tools}
print("RESULT " + json.dumps(out), flush=True)
sys.stdout.flush()
os._exit(0)
