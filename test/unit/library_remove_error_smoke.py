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
# GREMLIN_SMOKE_HISTORY=1: a saved setup first, and after the removal its
# History entries, then Restore of the newest (10 S51, D-10-IN-HISTORY).
HISTORY = os.environ.get("GREMLIN_SMOKE_HISTORY") == "1"
# GREMLIN_SMOKE_CLEAR=1: Clear Setup instead of Remove (S52).
CLEAR = os.environ.get("GREMLIN_SMOKE_CLEAR") == "1"


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


# The device's Library key: found by it once a friendly name changes the
# name it is shown by.
KEY = ""


def row() -> dict | None:
    rows = json.loads(str(ev(lib, "JSON.stringify(_lib.lib.rows)")))
    return next(
        (
            r
            for r in rows
            if r.get("kind") == "device"
            and (r.get("name") == NAME or r.get("key") == KEY)
        ),
        None,
    )


if HISTORY:
    from gremlin import device_library

    _guid = json.loads(MODULE.read_text(encoding="utf-8")).get("boundGuidLocal", "")
    from gremlin import device_aliases

    KEY = (row() or {}).get("key", "")
    device_aliases.set_alias(_guid, "Left Box")
    saved = device_library.save_setup(NAME, _guid, [], own=True)
    assert saved["ok"], saved
    ev(lib, "_lib.lib.refresh()")
    wait_until(lambda: bool(row()) and row().get("count", 0) > 0, 5000)

before = row()
out: dict = {"before": before, "fileBefore": MODULE.is_file()}
if HISTORY:
    from gremlin import history

    count = len(history.entries())
if before:
    key = json.dumps(before["key"])
    for name, call in (("target", "deviceTarget"), ("plan", "removalPlan")):
        text = ev(lib, f"JSON.stringify(_lib.lib.{call}({key}))")
        out[name] = json.loads(str(text))
    messages.clear()
    if CLEAR:
        ev(lib, f"_lib.runClearSetup({key})")
        wait_until(lambda: not MODULE.is_file(), 5000)
    else:
        ev(lib, f"_lib.runRemove([{key}])")
    wait_until(lambda: row() is None, 5000)
out["fileAfter"] = MODULE.is_file()
out["after"] = row()
from gremlin.modules import store as _store  # noqa: E402

out["bindingsAfter"] = _store.bindings()
if HISTORY:
    out["aliasAfter"] = device_aliases.display_name(_guid, "")
if HISTORY and before:
    from gremlin.ui import history_model

    wait_until(lambda: not bool(ev(lib, "_lib.lib.busy")), 5000)
    new = history.entries()
    new = new[: len(new) - count]
    out["titles"] = [e["title"] for e in new]
    if new:
        out["restore"] = history_model.restore(new[0]["id"], "before")
        ev(lib, "_lib.lib.refresh()")
        wait_until(lambda: row() is not None, 5000)
    out["fileRestored"] = MODULE.is_file()
    out["bindingsRestored"] = _store.bindings()
    out["aliasRestored"] = device_aliases.display_name(_guid, "")
    out["rowRestored"] = row()
out["message"] = str(ev(lib, "_lib.message") or "")
out["bad"] = bool(ev(lib, "_lib.messageBad"))
out["qml"] = messages[:10]
print("RESULT " + json.dumps(out), flush=True)
sys.stdout.flush()
os._exit(0)
