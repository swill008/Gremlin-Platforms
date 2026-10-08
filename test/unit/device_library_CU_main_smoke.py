# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware), opens the Device
Library and sends its row menus' Show on Home, Open Button Map and Open
Module Setup to the main window the way the window does
(device_library_open.js toMain -> Main.qml libraryAction), and prints as
JSON what happened and what QML printed. test_device_library_CU_main.py
runs it in its own process with a fresh user folder.
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
card = ev(win, "JSON.stringify(_moduleModel.firstCardMap('source'))")
card = json.loads(str(card))
ev(win, "_root.openDeviceLibrary('', '', '')")
wait_until(lambda: window("Device Library") is not None, 8000)
lib = window("Device Library")
assert lib is not None
messages.clear()
target = json.dumps(
    {
        "name": card.get("rawName") or card.get("name"),
        "guid": card.get("guid", ""),
        "slug": card.get("slug", ""),
    }
)
out: dict = {"card": card.get("slug", "")}
# Home's focus elsewhere first, so Show on Home has something to do.
ev(win, "_moduleModel.setFocus('')")
out["home"] = json.loads(str(ev(lib, f"DeviceLibraryOpen.toMain('home', {target})")))
wait_until(lambda: ev(win, "_moduleModel.focusedSlug") == card.get("slug"), 3000)
out["focused"] = ev(win, "_moduleModel.focusedSlug")
out["room"] = ev(win, "uiState.currentRoom")
out["map"] = json.loads(
    str(ev(lib, f"DeviceLibraryOpen.toMain('buttonMap', {target})"))
)
out["mapOpened"] = wait_until(lambda: window("Button Map") is not None, 8000)
out["setup"] = json.loads(
    str(ev(lib, f"DeviceLibraryOpen.toMain('moduleSetup', {target})"))
)
out["setupOpened"] = wait_until(
    lambda: bool(ev(win, "_root.configureWin !== null")), 8000
)
out["noCard"] = json.loads(
    str(
        ev(
            lib,
            "DeviceLibraryOpen.toMain('home', {name: 'Gone', guid: '', slug: 'gone'})",
        )
    )
)
out["recursion"] = any("Maximum call stack" in m for m in messages)
out["errors"] = [
    m for m in messages if "Error" in m or "is not a function" in m or "Too many" in m
][:5]
print("RESULT " + json.dumps(out), flush=True)
sys.stdout.flush()
os._exit(0)
