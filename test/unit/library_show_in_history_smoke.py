# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware), opens the Device
Library and sends a row's Show in History (10 S56) to the main window the
way the window does (device_library_open.js toMain -> Main.qml
libraryAction "history"), with Tools > History already open on every
change, and prints as JSON what the History window then shows.
test_library_show_in_history.py runs it with a fresh user folder.
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
card = json.loads(str(ev(win, "JSON.stringify(_moduleModel.firstCardMap('source'))")))
name = card.get("rawName") or card.get("name")
guid = card.get("guid", "")
ev(win, "_root.openDeviceLibrary('', '', '')")
wait_until(lambda: window("Device Library") is not None, 8000)
lib = window("Device Library")
assert lib is not None
# Tools > History open on every change first (08 S34): Show in History
# must still narrow it.
ev(win, "_root.openToolWith('DialogHistory.qml', { filter: '' })")
wait_until(lambda: window("History") is not None, 8000)
# The device's changes: its module file, and Device Library actions that
# list it (subject "devices", as device_library records them); a twin
# stick (same name, other id) and another file must not show.
from gremlin import history  # noqa: E402

mine = {"guid": guid, "name": name}
twin = {"guid": "{00000000-1111-2222-3333-444444444444}", "name": name}
module_file = (
    str(ev(win, f"_moduleModel.moduleFileFor({json.dumps(guid)}, {json.dumps(name)})"))
    + ".json"
)
lib_subject = {"library": "x", "files": []}
history.record(
    "modules", "UR module save", {"device": name, "fileName": module_file}, "a", "b"
)
history.record(
    "modules", "UR other file", {"device": "Other", "fileName": "other.json"}, "a", "b"
)
history.record(
    "modules",
    "UR save setup",
    dict(lib_subject, devices=[mine]),
    {},
    {},
    kind="library",
)
history.record(
    "modules",
    "UR delete setup",
    dict(lib_subject, devices=[mine]),
    {},
    {},
    kind="library",
)
history.record(
    "modules",
    "UR twin setup",
    dict(lib_subject, devices=[twin]),
    {},
    {},
    kind="library",
)
part = history._make(
    "modules", "lib part", dict(lib_subject, devices=[mine]), {}, {}, "library"
)
history._append(history.group_entry("modules", "UR remove", [part]))
messages.clear()
target = json.dumps(
    {"name": name, "guid": guid, "slug": card.get("slug", ""), "shown": "Shown Name"}
)
out: dict = {"file": module_file}
out["result"] = json.loads(
    str(ev(lib, f"DeviceLibraryOpen.toMain('history', {target})"))
)
hist = window("History")
out["opened"] = hist is not None
if hist is not None:
    out["filter"] = json.loads(str(ev(hist, "filter")) or "{}")
    out["about"] = str(ev(hist, "aboutText()"))
    model = ev(hist, "_model")
    out["titles"] = sorted(str(r.get("title")) for r in getattr(model, "_rows", []))
# A device with no card on Home (not plugged in) still has its History.
gone = json.dumps(
    {"name": "Gone Stick", "guid": "{ABCD}", "slug": "gone", "shown": "Gone Stick"}
)
out["gone"] = json.loads(str(ev(lib, f"DeviceLibraryOpen.toMain('history', {gone})")))
if hist is not None:
    out["goneAbout"] = str(ev(hist, "aboutText()"))
out["errors"] = [
    m for m in messages if "Error" in m or "is not a function" in m or "Too many" in m
][:5]
print("RESULT " + json.dumps(out), flush=True)
sys.stdout.flush()
os._exit(0)
