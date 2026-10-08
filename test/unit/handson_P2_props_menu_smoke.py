# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware, a stick with a map) and
checks the Button Map's View > Properties (07 S100: the palette lists every
usable command): outside Edit it is disabled and the palette leaves it out;
in Edit it is enabled and the palette's pick toggles it. Prints what it saw
as JSON. test_props_menu_in_edit.py runs it in its own process and user folder.

    python test/unit/handson_P2_props_menu_smoke.py

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


def props_item(win: QtCore.QObject) -> QtCore.QObject | None:
    """The View menu's Properties item."""
    for obj in win.findChildren(QtCore.QObject):
        if ("ThemedMenuItem" in obj.metaObject().className()
                and obj.property("text") == "Properties"):
            return obj
    return None


def main() -> None:
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    root = wait_for(lambda: (app.engine.rootObjects() or [None])[0])
    assert isinstance(root, QtCore.QObject)
    out: dict = {}

    card = {"rawName": "pJoy Pro", "name": "pJoy Pro", "guid": GUID}
    call(root, "openButtonMapForCard", card)
    win = wait_for(lambda: call(root, "buttonMapWindow"))
    assert isinstance(win, QtCore.QObject)
    wait_for(lambda: ev(win, "mapShown && targetName === 'pJoy Pro'"))
    win.requestActivate()
    wait_for(win.isActive)
    item = props_item(win)
    out["item-found"] = item is not None
    assert item is not None

    # Outside Edit.
    out["view-editing"] = ev(win, "editing")
    out["view-enabled"] = item.property("enabled")
    ev(win, "_palette.open()")
    out["view-opened"] = bool(wait_for(lambda: ev(win, "_palette.opened")))
    ev(win, "_palette.search('properties')")
    out["view-lists"] = list(ev(win, "_palette.describe()") or [])
    ev(win, "_palette.close()")
    wait_for(lambda: ev(win, "!_palette.opened"))

    # In Edit.
    call(win, "enterEdit")
    out["editing"] = bool(wait_for(
        lambda: ev(win, "editing && _ed() !== null && _ed().seeded && !_baseWanted")))
    out["edit-enabled"] = item.property("enabled")
    before = ev(win, "_tools.isOpen('props')")
    ev(win, "_palette.open()")
    wait_for(lambda: ev(win, "_palette.opened"))
    ev(win, "_palette.search('properties')")
    out["edit-lists"] = list(ev(win, "_palette.describe()") or [])
    ev(win, "_palette.runPick(0)")
    out["edit-toggled"] = bool(wait_for(
        lambda: ev(win, "_tools.isOpen('props')") is (not before)))

    print("RESULT " + json.dumps(out), flush=True)
    os._exit(0)


if __name__ == "__main__":
    try:
        main()
    finally:
        # The program's threads would keep it running after a failed check.
        sys.stdout.flush()
        os._exit(1)
