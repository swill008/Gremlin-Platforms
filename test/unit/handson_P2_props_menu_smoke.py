# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware, a stick with a map) and
checks the Device Mapping Editor's View > Properties (F4; 07 S133, S135): outside Edit
it is disabled; in Edit it is enabled, and it and F4 show or hide
Properties. Prints what it saw
as JSON. test_props_menu_in_edit.py runs it in its own process and user folder.

    python test/unit/handson_P2_props_menu_smoke.py

Waits poll for what is checked with a generous limit; none sleeps a fixed
time (GL-001).
"""

from __future__ import annotations

import importlib.util
import json
import sys
import time
from collections.abc import Callable
from pathlib import Path

from smoke_exit import smoke_exit

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
    from gremlin.modules import store

    _map = store.module_file_in(store.ensure_device_dir(_name, _guid))
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
    call(root, "openDeviceMappingEditorForCard", card)
    win = wait_for(lambda: call(root, "deviceMappingEditorWindow"))
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
    out["view-hint"] = item.property("hint")

    # In Edit: the item and F4 (07 S133) show or hide Properties under
    # Layers (S135).
    call(win, "enterEdit")
    out["editing"] = bool(wait_for(
        lambda: ev(win, "editing && _ed() !== null && _ed().seeded && !_baseWanted")))
    out["edit-enabled"] = item.property("enabled")

    def shown() -> object:
        return ev(win, "propsOn && _layersSide.open")

    before = shown()
    QtCore.QMetaObject.invokeMethod(item, "triggered")
    out["edit-toggled"] = bool(wait_for(lambda: shown() is (not before)))
    out["checked-follows"] = item.property("checked") is shown()
    win.requestActivate()
    wait_for(win.isActive)
    QtTest.QTest.keyClick(win, QtCore.Qt.Key.Key_F4)
    out["f4-toggled"] = bool(wait_for(lambda: shown() is before))

    print("RESULT " + json.dumps(out), flush=True)
    smoke_exit(0)


if __name__ == "__main__":
    try:
        main()
    finally:
        # The program's threads would keep it running after a failed check.
        sys.stdout.flush()
        smoke_exit(1)
