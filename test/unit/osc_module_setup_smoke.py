# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware), sends
signal.openOscModuleSetup the way Options' OSC line does, and prints as JSON
whether the main window opened OSC's Module Setup. test_osc_backend.py runs
it in its own process with a fresh user folder (D-09-OSC-FILE).
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
from gremlin.signal import signal  # noqa: E402

out: dict = {"osc": str(ev(win, "uiState.oscDeviceGuid || ''"))}
messages.clear()
sig = getattr(signal, "openOscModuleSetup", None)
out["signal"] = sig is not None
if sig is not None:
    sig.emit()
out["opened"] = wait_until(lambda: bool(ev(win, "_root.configureWin !== null")), 8000)
out["guid"] = str(ev(win, "_root.configureWin ? _root.configureWin.deviceGuid : ''"))
out["direction"] = str(
    ev(win, "_root.configureWin ? _root.configureWin.direction : ''")
)
out["errors"] = [
    m for m in messages if "Error" in m or "is not a function" in m
][:5]
print("RESULT " + json.dumps(out), flush=True)
sys.stdout.flush()
os._exit(0)
