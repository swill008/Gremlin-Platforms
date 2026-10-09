# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware) with a stick that is
set up here but not plugged in (its input module file and a "stick
deleted" autosave in the Device Library), opens the Device Library and
runs Remove from Library on it the way the window does (runRemove ->
device_library_open.js toMain -> Main.qml libraryAction -> Delete Device),
then prints as JSON what is left. test_library_remove_error.py makes the
user folder and runs it in its own process."""

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

NAME = sys.argv[1]
MODULE = Path(sys.argv[2])
# Optional file choices to start with (JSON), as a user's settings can hold.
if len(sys.argv) > 3:
    from gremlin.modules import store

    store.set_bindings(json.loads(sys.argv[3]))
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


def ev(obj: QtCore.QObject, code: str) -> object:
    expr = QtQml.QQmlExpression(QtQml.qmlContext(obj), obj, code)
    value = expr.evaluate()
    if expr.hasError():
        raise RuntimeError(expr.error().toString() + " :: " + code[:200])
    value = value[0] if isinstance(value, tuple) else value
    return value.toVariant() if hasattr(value, "toVariant") else value


def window(title: str) -> QtGui.QWindow | None:
    return next(
        (
            w
            for w in QtGui.QGuiApplication.topLevelWindows()
            if w.isVisible() and w.title().startswith(title)
        ),
        None,
    )


app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window
win.setProperty("visible", True)
wait_until(lambda: win.isVisible())
wait_until(lambda: bool(ev(win, "_statusLoader.item !== null")))
ev(win, "_root.openDeviceLibrary('', '', '')")
wait_until(lambda: window("Device Library") is not None, 8000)
lib = window("Device Library")
assert lib is not None
wait_until(lambda: bool(ev(lib, "_lib.lib !== null && _lib.lib.rows.length > 0")), 8000)


def row() -> dict | None:
    rows = json.loads(str(ev(lib, "JSON.stringify(_lib.lib.rows)")))
    return next(
        (r for r in rows if r.get("kind") == "device" and r.get("name") == NAME), None
    )


before = row()
out: dict = {"before": before, "fileBefore": MODULE.is_file()}
if before:
    key = json.dumps(before["key"])
    for name, call in (("target", "deviceTarget"), ("plan", "removalPlan")):
        text = ev(lib, f"JSON.stringify(_lib.lib.{call}({key}))")
        out[name] = json.loads(str(text))
    messages.clear()
    ev(lib, f"_lib.runRemove([{key}])")
    wait_until(lambda: row() is None, 5000)
out["fileAfter"] = MODULE.is_file()
out["after"] = row()
out["message"] = str(ev(lib, "_lib.message") or "")
out["bad"] = bool(ev(lib, "_lib.messageBad"))
out["qml"] = messages[:10]
print("RESULT " + json.dumps(out), flush=True)
sys.stdout.flush()
os._exit(0)
