# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware) and plugs and unplugs a
stick under an open Button Map window; prints what the window shows as
JSON. test_button_map_devices.py runs it in its own process with a fresh
user folder.

    python test/unit/button_map_devices_smoke.py

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
from typing import Any, cast

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

import shiboken6  # noqa: E402
from PySide6 import QtCore, QtQml, QtTest  # noqa: E402

import dill  # noqa: E402
from gremlin import event_handler  # noqa: E402
from gremlin.ui import hardware_profile  # noqa: E402

# The stick ("pJoy Pro") starts unplugged; its map has five chips.
stick = fake.devices[0]
fake.devices.remove(stick)
other = fake_hardware.raw_device(is_virtual=False)
other.device_guid.Data1 += 7
other.name = b"Other Stick"
GUID = str(dill.GUID(stick.device_guid).uuid)
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
_map = hardware_profile.module_json_path("pJoy Pro", GUID)
_map.parent.mkdir(parents=True, exist_ok=True)
_map.write_text(
    json.dumps({"kind": "control.hardware", "device": "pJoy Pro", "nodes": NODES}),
    encoding="utf-8",
)

import joystick_gremlin  # noqa: E402


def call(obj: QtCore.QObject, name: str, *args: object) -> object:
    return QtCore.QMetaObject.invokeMethod(
        obj,
        name,
        QtCore.Q_RETURN_ARG("QVariant"),
        *[QtCore.Q_ARG("QVariant", a) for a in args],
    )


def count(value: object) -> int:
    if hasattr(value, "toVariant"):
        value = value.toVariant()
    return len(value or [])


def same(a: object, b: object) -> bool:
    return (
        a is not None
        and b is not None
        and shiboken6.getCppPointer(a)[0] == shiboken6.getCppPointer(b)[0]
    )


def device_change() -> None:
    # What the device thread does after a plug or unplug (on its timer).
    event_handler.EventListener()._run_device_list_update()


# Generous: a busy PC is slow, never wrong. A check that something does NOT
# happen waits the shorter limit for it.
LIMIT_S = 15.0
NOT_S = 2.0


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
    value = QtQml.QQmlExpression(context, obj, code).evaluate()
    return value[0] if isinstance(value, tuple) else value


def main() -> None:
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    root = wait_for(lambda: (app.engine.rootObjects() or [None])[0])
    assert isinstance(root, QtCore.QObject)
    out: dict = {}

    def seen() -> dict:
        win = call(root, "buttonMapWindow")
        ed = call(win, "_ed")
        return {
            "chips": count(ed.property("nodes")) if ed is not None else None,
            "connected": win.property("targetConnected"),
            "shown": win.property("mapShown"),
            "editing": win.property("editing"),
        }

    def look(tag: str, want: dict) -> None:
        """What the window shows once it shows want (or after the limit)."""
        wait_for(lambda: seen() == want)
        out[tag] = seen()

    def shown(chips: int, connected: bool, mapped: bool, editing: bool) -> dict:
        return {"chips": chips, "connected": connected, "shown": mapped,
                "editing": editing}

    def edit_ready() -> bool:
        return bool(ev(cast(QtCore.QObject, win),
                       "editing && _ed() !== null && _ed().seeded && !_baseWanted"))

    # Opened from the Home card while the stick is unplugged.
    card = {"rawName": "pJoy Pro", "name": "pJoy Pro", "guid": GUID}
    call(root, "openButtonMapForCard", card)
    win = wait_for(lambda: call(root, "buttonMapWindow"))
    assert isinstance(win, QtCore.QObject)
    look("opened-unplugged", shown(5, False, False, False))
    fake.devices.insert(0, stick)
    device_change()
    look("plugged-in", shown(5, True, True, False))
    fake.devices.remove(stick)
    device_change()
    look("unplugged", shown(5, False, False, False))
    # Export still draws the map of an unplugged stick.
    target = Path(os.environ["USERPROFILE"]) / "unplugged-export.png"
    call(win, "exportTo", QtCore.QUrl.fromLocalFile(str(target)).toString(), "png")
    out["export-while-unplugged"] = bool(
        wait_for(lambda: target.is_file() and target.stat().st_size > 0)
    )
    fake.devices.insert(0, stick)
    device_change()
    look("plugged-in-again", shown(5, True, True, False))

    # Outputs, Keyboard, Logical Device and OSC show without a stick.
    model: Any = next(
        o for o in win.findChildren(QtCore.QObject)
        if o.metaObject().className() == "ViewerDeviceModel"
    )
    out["available"] = {
        name: model.available(guid, name)
        for name, guid in (
            ("vJoy Device 1", ""),
            ("Xbox 360 Controller", ""),
            ("Keyboard", str(dill.UUID_Keyboard)),
            ("pJoy Pro", GUID),
            ("Nowhere Stick", ""),
        )
    }

    # Edit: other devices coming and going leave the editor as it is; an
    # unplugged stick keeps the edit on screen until it ends.
    call(win, "enterEdit")
    wait_for(edit_ready)
    editor = call(win, "_ed")
    # The editor fills in what the file leaves out (a chip's name, its
    # leader): that is not a change to save.
    out["unsaved-after-entering-edit"] = bool(
        wait_for(lambda: call(win, "isDirty"), NOT_S)
    )
    fake.devices.append(other)
    device_change()
    # The other stick is in the window's device list, and the editor stays.
    other_guid = str(dill.GUID(other.device_guid).uuid)
    wait_for(lambda: model.available(other_guid, "Other Stick"))
    out["same-editor-after-other-stick"] = not wait_for(
        lambda: not same(call(win, "_ed"), editor), NOT_S
    )

    menu = next(
        o for o in win.findChildren(QtCore.QObject)
        if o.property("title") == "Device"
        and o.metaObject().indexOfMethod("compactNow()") >= 0
    )
    call(menu, "compactNow")
    out["device-menu-rows-while-editing"] = menu.property("shownCount")

    fake.devices.remove(stick)
    device_change()
    look("unplugged-mid-edit", shown(5, False, True, True))
    out["same-editor-after-unplug"] = not wait_for(
        lambda: not same(call(win, "_ed"), editor), NOT_S
    )
    call(win, "discardEdit")
    look("edit-ended-unplugged", shown(5, False, False, False))
    fake.devices.insert(0, stick)
    device_change()
    look("back-after-edit", shown(5, True, True, False))

    # A real change is still one.
    call(win, "enterEdit")
    wait_for(edit_ready)
    move = QtQml.QQmlExpression(
        QtQml.qmlContext(win),
        win,
        "(function() { var e = _ed(); e.nodes[0].chipFx += 0.05; e.bump()"
        "; return isDirty() })()",
    )
    moved = move.evaluate()
    out["unsaved-after-a-move"] = moved[0] if isinstance(moved, tuple) else moved
    call(win, "discardEdit")

    print("RESULT " + json.dumps(out), flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
