# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware, a stick with a map) and
runs commands from the Command Palette (07 S100, 01 S65): the Button Map's
unpinned palette choosing View > Properties (while editing) toggles it, and the main
window's palette runs its pick once. Prints what it saw as JSON.
test_palette_runs_commands.py runs it in its own process and user folder.

    python test/unit/palette_runs_commands_smoke.py

Waits poll for what is checked with a generous limit; none sleeps a fixed
time (GL-001).
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from collections.abc import Callable
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
from gremlin.ui import hardware_profile  # noqa: E402

# Two sticks, each with a map of five chips.
stick = fake.devices[0]
other = fake_hardware.raw_device(is_virtual=False)
other.device_guid.Data1 += 7
other.name = b"Other Stick"
fake.devices.append(other)
GUID = str(dill.GUID(stick.device_guid).uuid)
OTHER_GUID = str(dill.GUID(other.device_guid).uuid)
NODES = [
    {
        "kind": "btn",
        "id": f"b{i}",
        "label": f"Button {i}",
        "chipFx": 0.2 + 0.05 * i,
        "chipFy": 0.3,
    }
    for i in range(1, 6)
]
for _name, _guid in (("pJoy Pro", GUID), ("Other Stick", OTHER_GUID)):
    _map = hardware_profile.module_json_path(_name, _guid)
    _map.parent.mkdir(parents=True, exist_ok=True)
    _map.write_text(
        json.dumps({"kind": "control.hardware", "device": _name, "nodes": NODES}),
        encoding="utf-8",
    )

import joystick_gremlin  # noqa: E402

Key = QtCore.Qt.Key
Mod = QtCore.Qt.KeyboardModifier
# Generous: a busy PC is slow, never wrong.
LIMIT_S = 15.0


def call(obj: QtCore.QObject, name: str, *args: object) -> object:
    return QtCore.QMetaObject.invokeMethod(
        obj,
        name,
        QtCore.Q_RETURN_ARG("QVariant"),
        *[QtCore.Q_ARG("QVariant", a) for a in args],
    )


def wait_for(check: Callable[[], object], limit: float = LIMIT_S) -> object:
    """Runs the event loop until check() is true (its value), up to limit."""
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



def main() -> None:
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    root = wait_for(lambda: (app.engine.rootObjects() or [None])[0])
    assert isinstance(root, QtCore.QObject)
    out: dict = {}

    # The main window's palette (Ctrl+K): a test command that counts its runs.
    out["main-defined"] = ev(
        root,
        "Commands.define({ id: 'main:p1-test', text: 'Zq palette test',"
        " owner: 'main', n: 0, run: function() { this.n += 1 } }); true",
    )
    ev(root, "_commandPalette.open()")
    out["main-opened"] = bool(wait_for(lambda: ev(root, "_commandPalette.opened")))
    ev(root, "_commandPalette.search('zq palette test')")
    out["main-lists"] = list(ev(root, "_commandPalette.describe()") or [])
    ev(root, "_commandPalette.runPick(0)")
    out["main-runs"] = bool(wait_for(
        lambda: ev(root, "Commands.get('main:p1-test').n") == 1))
    # Let any second, deferred run through before counting again.
    wait_for(lambda: not ev(root, "_commandPalette.visible"))
    for _ in range(3):
        QtCore.QCoreApplication.processEvents()
    out["main-run-count"] = ev(root, "Commands.get('main:p1-test').n")
    out["main-closed"] = ev(root, "_commandPalette.opened") is False

    # The Button Map's palette, not pinned: View > Properties.
    card = {"rawName": "pJoy Pro", "name": "pJoy Pro", "guid": GUID}
    call(root, "openButtonMapForCard", card)
    win = wait_for(lambda: call(root, "buttonMapWindow"))
    assert isinstance(win, QtCore.QObject)
    wait_for(lambda: ev(win, "mapShown && targetName === 'pJoy Pro'"))
    # Properties is a tool for editing.
    call(win, "enterEdit")
    out["editing"] = bool(wait_for(
        lambda: ev(win, "editing && _ed() !== null && _ed().seeded && !_baseWanted")))
    win.requestActivate()
    wait_for(win.isActive)
    out["pinned"] = ev(win, "_tools.isPinned('palette')")
    before = ev(win, "_tools.isOpen('props')")
    out["props-before"] = before
    ev(win, "_palette.open()")
    out["map-opened"] = bool(wait_for(lambda: ev(win, "_palette.opened")))
    ev(win, "_palette.search('properties')")
    out["map-lists"] = list(ev(win, "_palette.describe()") or [])
    ev(win, "_palette.runPick(0)")
    out["props-toggled"] = bool(wait_for(
        lambda: ev(win, "_tools.isOpen('props')") is (not before)))
    out["map-closed"] = bool(wait_for(lambda: ev(win, "!_palette.opened")))
    # And back again, the same way.
    ev(win, "_palette.open()")
    wait_for(lambda: ev(win, "_palette.opened"))
    ev(win, "_palette.search('properties')")
    ev(win, "_palette.runPick(0)")
    out["props-toggled-back"] = bool(wait_for(
        lambda: ev(win, "_tools.isOpen('props')") is before))

    print("RESULT " + json.dumps(out), flush=True)
    os._exit(0)


if __name__ == "__main__":
    try:
        main()
    finally:
        # The program's threads would keep it running after a failed check.
        sys.stdout.flush()
        os._exit(1)
