# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Opens qml/WindowScreenSaverMode.qml off-screen with the real
ScreenSaverModeModel and the stand-ins from ssm_ui_fakes.py, works its
controls and prints what happened as JSON, for test_ssm_ui.py."""

from __future__ import annotations

import importlib.util
import json
import sys
import threading
import time
from pathlib import Path

from smoke_exit import smoke_exit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

spec = importlib.util.spec_from_file_location(
    "fake_hardware", ROOT / "test" / "fake_hardware.py"
)
assert spec is not None and spec.loader is not None
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake_hardware.install()

import ssm_ui_fakes  # noqa: E402

manager, calls = ssm_ui_fakes.install()

from PySide6 import QtCore, QtGui, QtQml, QtQuick  # noqa: E402

import gremlin.ui.device_names  # noqa: E402, F401  (Gremlin.Device)
import gremlin.ui.screen_saver_mode_model as ssm_model  # noqa: E402
import gremlin.ui.window_placement  # noqa: E402, F401  (Gremlin.UI)
from gremlin.config import Configuration  # noqa: E402

app = QtGui.QGuiApplication([sys.argv[0]])
engine = QtQml.QQmlEngine()
engine.addImportPath(str(ROOT / "theme"))
QtQml.qmlRegisterSingletonType(
    QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / "Style.qml")),
    "Gremlin.Style",
    1,
    0,
    "Style",
)
url = QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / "WindowScreenSaverMode.qml"))
component = QtQml.QQmlComponent(engine, url)
win = component.create()
if win is None:
    print(json.dumps({"errors": [e.toString() for e in component.errors()]}))
    smoke_exit(1)
win.show()
context = QtQml.QQmlEngine.contextForObject(win)


def ev(code: str) -> object:
    value, _ = QtQml.QQmlExpression(context, win, code).evaluate()
    return value


def settle(ms: int = 150) -> None:
    end = time.monotonic() + ms / 1000
    while time.monotonic() < end:
        app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 20)


def until(check, limit: float = 5.0) -> bool:  # noqa: ANN001
    end = time.monotonic() + limit
    while time.monotonic() < end:
        app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 20)
        if check():
            return True
    return False


def child(name: str) -> QtCore.QObject:
    found = win.findChild(QtCore.QObject, name)
    assert found is not None, name
    return found


def prop(name: str, key: str) -> object:
    return child(name).property(key)


def emit(name: str, sig: str) -> None:
    QtCore.QMetaObject.invokeMethod(child(name), sig)


def toggle(name: str, on: bool) -> None:
    obj = child(name)
    obj.setProperty("checked", on)
    QtCore.QMetaObject.invokeMethod(obj, "toggled")


def cfg(name: str) -> object:
    return Configuration().value(ssm_model.SECTION, ssm_model.GROUP, name)


def texts() -> dict:
    out = {}
    for name in (
        "ssmListening",
        "ssmIdleText",
        "ssmWindowsIdleText",
        "ssmHoldText",
        "ssmProblemText",
        "ssmWindowsWait",
    ):
        out[name] = str(prop(name, "text"))
        out[name + "Visible"] = bool(prop(name, "visible"))
    return out


def _items_named(item: QtQuick.QQuickItem, name: str) -> list[QtQuick.QQuickItem]:
    found = [item] if item.objectName() == name else []
    for sub in item.childItems():
        found += _items_named(sub, name)
    return found


def switches() -> list[dict]:
    """The Ignore this program switches, top to bottom (ListView delegates
    have no QObject parent, so they are found through the items)."""
    view = win.findChild(QtQuick.QQuickItem, "ssmProgramList")
    assert view is not None
    rows = _items_named(view.property("contentItem"), "ssmIgnoreSwitch")
    return sorted(
        (
            {
                "y": float(o.mapToItem(view, QtCore.QPointF(0, 0)).y()),
                "checked": bool(o.property("checked")),
                "obj": o,
            }
            for o in rows
        ),
        key=lambda r: r["y"],
    )


settle(300)
out: dict[str, object] = {
    "title": win.property("title"),
    "objectName": win.objectName(),
    "visible": bool(win.property("visible")),
}

# Start: off, power off displays, Windows' time.
out["start"] = {
    "enabled": bool(prop("ssmEnabled", "checked")),
    "screenSaver": bool(prop("ssmActionScreenSaver", "checked")),
    "powerOff": bool(prop("ssmActionPowerOff", "checked")),
    "hold": bool(prop("ssmHoldFullscreen", "checked")),
    "waitText": str(prop("ssmWaitBox", "text")),
    "placeholder": str(prop("ssmWaitBox", "placeholderText")),
    "clearVisible": bool(prop("ssmWaitClear", "visible")),
    "cfgEnabled": cfg("enabled"),
    "cfgAction": cfg("action"),
    "cfgWait": cfg("wait-override-s"),
    "cfgHold": cfg("hold-fullscreen"),
    **texts(),
}

# On (S2): saved and applied.
toggle("ssmEnabled", True)
settle()
out["on"] = {
    "cfgEnabled": cfg("enabled"),
    "applied": manager.settings().enabled,
    **texts(),
}

# Screen saver (S4): saved, applied, Windows' screen saver time shown.
toggle("ssmActionScreenSaver", True)
settle()
out["screenSaver"] = {
    "cfgAction": cfg("action"),
    "applied": manager.settings().action,
    "powerOff": bool(prop("ssmActionPowerOff", "checked")),
    "placeholder": str(prop("ssmWaitBox", "placeholderText")),
    **texts(),
}

# Hold off during full-screen programs off (S7).
toggle("ssmHoldFullscreen", False)
settle()
out["holdOff"] = {
    "cfgHold": cfg("hold-fullscreen"),
    "applied": manager.settings().hold_fullscreen,
}

# A typed time (S5) replaces Windows' time; text that isn't a time goes back.
box = child("ssmWaitBox")
box.setProperty("text", "10")
emit("ssmWaitBox", "editingFinished")
settle()
out["typed"] = {
    "cfgWait": cfg("wait-override-s"),
    "applied": manager.settings().wait_override_s,
    "clearVisible": bool(prop("ssmWaitClear", "visible")),
    "waitText": str(prop("ssmWaitBox", "text")),
}
box.setProperty("text", "0")
emit("ssmWaitBox", "editingFinished")
settle()
out["badTyped"] = {
    "cfgWait": cfg("wait-override-s"),
    "waitText": str(prop("ssmWaitBox", "text")),
}

# ✕ clears: Windows' time again.
emit("ssmWaitClear", "clicked")
settle()
out["cleared"] = {
    "cfgWait": cfg("wait-override-s"),
    "applied": manager.settings().wait_override_s,
    "waitText": str(prop("ssmWaitBox", "text")),
    "clearVisible": bool(prop("ssmWaitClear", "visible")),
    "placeholder": str(prop("ssmWaitBox", "placeholderText")),
}

# Status texts follow the manager, polled once a second (S9, S15, S8).
manager.extra = {
    "idle_s": 161.0,
    "windows_idle_s": 0.0,
    "hold": "display_request",
    "hold_program": "chrome.exe",
}
until(lambda: "On hold" in str(prop("ssmHoldText", "text")), 3.0)
out["held"] = texts()
manager.extra = {"idle_s": 30.0, "windows_idle_s": 30.0, "hold": "fullscreen"}
until(lambda: "full-screen" in str(prop("ssmHoldText", "text")), 3.0)
out["fullscreen"] = texts()
manager.extra = {"problem": "no_screen_saver"}
until(lambda: bool(prop("ssmProblemText", "text")), 3.0)
out["noScreenSaver"] = texts()
manager.extra = {"problem": "not_listening", "listening": False}
until(lambda: "can't be listened" in str(prop("ssmProblemText", "text")), 3.0)
out["notListening"] = texts()
manager.extra = {"remaining_s": 139.0, "idle_s": 461.0}
until(lambda: "in 2 min" in str(prop("ssmHoldText", "text")), 3.0)
out["countdown"] = texts()
manager.extra = {}

# Refresh Devices (S12): busy text while it reads, then the list.
out["devicesBefore"] = int(prop("ssmDeviceList", "count"))
calls.gate = threading.Event()
emit("ssmRefreshDevices", "clicked")
settle(100)
out["devicesBusy"] = {
    "text": str(prop("ssmRefreshDevices", "text")),
    "enabled": bool(prop("ssmRefreshDevices", "enabled")),
}
calls.gate.set()
until(lambda: int(prop("ssmDeviceList", "count")) > 0)
settle()
out["devices"] = {
    "scans": list(calls.scans),
    "count": int(prop("ssmDeviceList", "count")),
    "rows": [
        str(d["name"]) + " · " + str(round(d["rate"])) for d in ev("_ssm.devices")
    ],
    "text": str(prop("ssmRefreshDevices", "text")),
}
calls.gate = None

# Refresh Programs (S13), then Ignore this program (S14).
emit("ssmRefreshPrograms", "clicked")
until(lambda: int(prop("ssmProgramList", "count")) == 2)
settle()
rows = switches()
out["programs"] = {
    "lists": calls.lists,
    "count": int(prop("ssmProgramList", "count")),
    "checked": [r["checked"] for r in rows],
    "message": str(prop("ssmProgramsMessage", "text")),
}

# Refused: the switch goes back, the window says so.
calls.ignore_answer = (False, "Administrator rights were refused.")
first = rows[0]["obj"]
first.setProperty("checked", True)
QtCore.QMetaObject.invokeMethod(first, "toggled")
until(lambda: "refused" in str(prop("ssmProgramsMessage", "text")))
settle()
out["refused"] = {
    "ignores": list(calls.ignores),
    "checked": [r["checked"] for r in switches()],
    "message": str(prop("ssmProgramsMessage", "text")),
}

# Accepted: it stays on.
calls.ignore_answer = (True, "")
first = switches()[0]["obj"]
first.setProperty("checked", True)
QtCore.QMetaObject.invokeMethod(first, "toggled")
until(lambda: "is ignored" in str(prop("ssmProgramsMessage", "text")))
settle()
out["accepted"] = {
    "ignores": list(calls.ignores),
    "checked": [r["checked"] for r in switches()],
    "message": str(prop("ssmProgramsMessage", "text")),
}

# A refused list (S13): the window says so, the list stays as it was.
calls.requests = ssm_ui_fakes.RequestsResult(
    False, "Administrator rights were refused.", []
)
emit("ssmRefreshPrograms", "clicked")
until(lambda: calls.lists == 2 and not ev("_ssm.scanningPrograms"))
settle()
out["listRefused"] = {
    "count": int(prop("ssmProgramList", "count")),
    "message": str(prop("ssmProgramsMessage", "text")),
}

win.close()
settle()
out["closed"] = not bool(win.property("visible"))
print(json.dumps(out), flush=True)
smoke_exit(0)
