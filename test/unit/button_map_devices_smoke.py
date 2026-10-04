# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware) and plugs and unplugs a
stick under an open Button Map window; prints what the window shows as
JSON. test_button_map_devices.py runs it in its own process with a fresh
user folder.

    python test/unit/button_map_devices_smoke.py
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
    QtTest.QTest.qWait(600)


def main() -> None:
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    QtTest.QTest.qWait(800)
    root = app.engine.rootObjects()[0]
    out: dict = {}

    def look(tag: str) -> None:
        win = call(root, "buttonMapWindow")
        ed = call(win, "_ed")
        out[tag] = {
            "chips": count(ed.property("nodes")) if ed is not None else None,
            "connected": win.property("targetConnected"),
            "shown": win.property("mapShown"),
            "editing": win.property("editing"),
        }

    # Opened from the Home card while the stick is unplugged.
    card = {"rawName": "pJoy Pro", "name": "pJoy Pro", "guid": GUID}
    call(root, "openButtonMapForCard", card)
    QtTest.QTest.qWait(1000)
    win = call(root, "buttonMapWindow")
    look("opened-unplugged")
    fake.devices.insert(0, stick)
    device_change()
    look("plugged-in")
    fake.devices.remove(stick)
    device_change()
    look("unplugged")
    # Export still draws the map of an unplugged stick.
    target = Path(os.environ["USERPROFILE"]) / "unplugged-export.png"
    call(win, "exportViewTo", QtCore.QUrl.fromLocalFile(str(target)).toString(), "png")
    QtTest.QTest.qWait(1500)
    out["export-while-unplugged"] = target.is_file() and target.stat().st_size > 0
    fake.devices.insert(0, stick)
    device_change()
    look("plugged-in-again")

    # Outputs, Keyboard, Logical Device and OSC show without a stick.
    model = next(
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
    QtTest.QTest.qWait(800)
    editor = call(win, "_ed")
    # The editor fills in what the file leaves out (a chip's name, its
    # leader): that is not a change to save.
    out["unsaved-after-entering-edit"] = call(win, "isDirty")
    fake.devices.append(other)
    device_change()
    out["same-editor-after-other-stick"] = same(call(win, "_ed"), editor)

    menu = next(
        o for o in win.findChildren(QtCore.QObject)
        if o.property("title") == "Device"
        and o.metaObject().indexOfMethod("compactNow()") >= 0
    )
    call(menu, "compactNow")
    out["device-menu-rows-while-editing"] = menu.property("shownCount")

    fake.devices.remove(stick)
    device_change()
    look("unplugged-mid-edit")
    out["same-editor-after-unplug"] = same(call(win, "_ed"), editor)
    call(win, "discardEdit")
    QtTest.QTest.qWait(600)
    look("edit-ended-unplugged")
    fake.devices.insert(0, stick)
    device_change()
    look("back-after-edit")

    # A real change is still one.
    call(win, "enterEdit")
    QtTest.QTest.qWait(800)
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
