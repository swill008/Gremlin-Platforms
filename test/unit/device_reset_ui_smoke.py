# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""D-02-RESET-DEVICES, the window, off-screen in the real program: the app
starts as joystick_gremlin.py starts it (fake hardware, a fake HidHide
driver, a stand-in home folder, a fake device list and a fake reset runner:
pnputil is never run), the HidHide page is opened by the Tools menu's item,
and Reset Devices… gets real mouse clicks. Prints "RESULT name json" per
check and "done". test_device_reset_ui.py runs it.

    python test/unit/device_reset_ui_smoke.py <work folder>
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
_spec = importlib.util.spec_from_file_location(
    "fake_hardware", ROOT / "test" / "fake_hardware.py"
)
assert _spec and _spec.loader
fake_hardware = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fake_hardware)
fake_hardware.install()

import gremlin.ui.update_model as um  # noqa: E402

um.UpdateModel.startup = lambda self, *a, **k: None

import shiboken6  # noqa: E402
from PySide6 import QtCore, QtQuick, QtTest  # noqa: E402

from gremlin import device_reset, hidhide_driver, process_paths  # noqa: E402

WORK = Path(sys.argv[1])
SHOT = Path(sys.argv[2]) if len(sys.argv) > 2 else WORK / "reset.png"
LIVE = r"D:\StarCitizen\LIVE\Bin64\StarCitizen.exe"
Left = QtCore.Qt.MouseButton.LeftButton
NoMod = QtCore.Qt.KeyboardModifier.NoModifier

# The devices: two hidden VKB sticks (one with two HID collections), pedals
# that aren't hidden, vJoy and a ViGEm pad (never listed).
R_USB = r"USB\VID_231D&PID_0200\9&AAC4F3F&0&2"
L_USB = r"USB\VID_231D&PID_3201\9&1D65FFE4&0&3"
P_USB = r"USB\VID_16D0&PID_0A38\7&11111111&0&1"
R_HID = r"HID\VID_231D&PID_0200\A&1111&0&0000"
L_HID = r"HID\VID_231D&PID_3201\A&2222&0&0000"
L_HID2 = r"HID\VID_231D&PID_3201\A&2222&0&0001"
P_HID = r"HID\VID_16D0&PID_0A38\B&3333&0&0000"
GONE_HID = r"HID\VID_CAFE&PID_BAF2\C&4444&0&0000"
ROWS = [
    {"hid_id": R_HID, "usb_id": R_USB, "bus_id": "", "bus_desc": "",
     "name": "VKBsim Gladiator EVO R", "windows_name": "VKBsim Gladiator EVO R",
     "vid": 0x231D, "pid": 0x0200},
    {"hid_id": L_HID, "usb_id": L_USB, "bus_id": "", "bus_desc": "",
     "name": "VKBsim Gladiator EVO OT L", "windows_name": "VKBsim Gladiator EVO OT L",
     "vid": 0x231D, "pid": 0x3201},
    {"hid_id": L_HID2, "usb_id": L_USB, "bus_id": "", "bus_desc": "",
     "name": "VKBsim Gladiator EVO OT L", "windows_name": "VKBsim Gladiator EVO OT L",
     "vid": 0x231D, "pid": 0x3201},
    {"hid_id": P_HID, "usb_id": P_USB, "bus_id": "", "bus_desc": "",
     "name": "Example pedals", "windows_name": "Example pedals",
     "vid": 0x16D0, "pid": 0x0A38},
    {"hid_id": r"HID\HIDCLASS&COL01\1&2D595CA7&0&0000", "usb_id": r"ROOT\HIDCLASS\0000",
     "bus_id": "", "bus_desc": "", "name": "vJoy Device", "windows_name": "vJoy Device",
     "vid": 0x1234, "pid": 0xBEAD},
    {"hid_id": r"HID\VID_045E&PID_028E&IG_00\D&1&0&0000",
     "usb_id": r"USB\VID_045E&PID_028E\D&5555&0&1", "bus_id": r"ROOT\VIGEMBUS",
     "bus_desc": "Virtual Gamepad Emulation Bus", "name": "Xbox 360 Controller",
     "windows_name": "Xbox 360 Controller for Windows", "vid": 0x045E, "pid": 0x028E},
]
# A real (USB) Xbox pad, plugged in while the window is open.
X_USB = r"USB\VID_045E&PID_0B12\8&6666&0&5"
XPAD = {"hid_id": r"HID\VID_045E&PID_0B12&IG_00\E&6666&0&0000", "usb_id": X_USB,
        "bus_id": "", "bus_desc": "", "name": "Xbox Wireless Controller",
        "windows_name": "Xbox Wireless Controller", "vid": 0x045E, "pid": 0x0B12}
device_reset.set_enumerator(lambda: [dict(r) for r in ROWS])
device_reset.set_presence(lambda _instance: True)

# The runner: never the real one. Each call is recorded; the answer is set
# per step (an exit code per id, or Cancelled: permission declined).
CALLS: list[list[str]] = []
ANSWER: list = [device_reset.Cancelled()]


def _runner(ids: list[str]) -> dict[str, int]:
    CALLS.append(list(ids))
    answer = ANSWER[0]
    if isinstance(answer, Exception):
        raise answer
    return dict(answer)


device_reset.set_runner(_runner)


# A fake HidHide driver: never the real one.
class Driver:
    present = True
    active = True
    inverse = False
    blacklist: list[str] = [R_HID, L_HID, L_HID2, GONE_HID]
    whitelist: list[str] = []


DRV = Driver()


def _set(name: str, value: object) -> bool:
    setattr(DRV, name, value)
    return True


from gremlin.ui import hidhide as hh  # noqa: E402

_FAKES = {
    "driver_present": lambda: True,
    "driver_version": lambda: "1.5",
    "get_active": lambda: DRV.active,
    "set_active": lambda on: _set("active", on),
    "get_inverse": lambda: DRV.inverse,
    "set_inverse": lambda on: _set("inverse", on),
    "get_blacklist": lambda: list(DRV.blacklist),
    "set_blacklist": lambda ids: _set("blacklist", list(ids)),
    "get_whitelist": lambda: list(DRV.whitelist),
    "set_whitelist": lambda paths: _set("whitelist", list(paths)),
    "list_hid_devices": lambda gaming_only=False: [],
    "_full_image_name": lambda path: path,
    "_gremlin_exe": lambda: r"C:\Gremlin\joystick_gremlin.exe",
}
for _name, _fake in _FAKES.items():
    for _mod in (hidhide_driver, hh):
        if hasattr(_mod, _name):
            setattr(_mod, _name, _fake)

# The listed game is running.
process_paths.running_programs = lambda names=None: [(LIVE, None)]
process_paths.running_images = lambda: [LIVE]

hh._ensure_options()
hh._save_games([{"name": "Star Citizen", "path": LIVE}])
hh._mark_managed()
hh._save_hidden(list(DRV.blacklist))

# QML warnings from the two windows (engine.warnings: a Python Qt message
# handler can deadlock while QML compiles, gremlin/qt_log.py).
WARNINGS: list[str] = []


def _warned(found: list) -> None:
    for w in found:
        text = w.toString()
        if "DialogResetDevices" in text or "DialogHardwareHide" in text:
            WARNINGS.append(text)


import joystick_gremlin  # noqa: E402


def result(name: str, value: object) -> None:
    print(f"RESULT {name} {json.dumps(value)}", flush=True)


def wait_until(check, timeout: float = 10.0):  # noqa: ANN001, ANN201
    deadline = time.monotonic() + timeout
    while True:
        value = check()
        if value:
            return value
        if time.monotonic() > deadline:
            return None
        QtTest.QTest.qWait(20)


def items(item: QtQuick.QQuickItem) -> list:
    found = [item]
    for c in item.childItems():
        found += items(c)
    return found


def named(win: QtQuick.QQuickWindow, name: str) -> list:
    return [
        i for i in items(win.contentItem())
        if i.objectName() == name and i.isVisible()
    ]


def texts(win: QtQuick.QQuickWindow, name: str) -> list[str]:
    return [str(i.property("text")) for i in named(win, name)]


def click_item(win: QtQuick.QQuickWindow, it: QtQuick.QQuickItem) -> None:
    QtTest.QTest.qWait(150)
    p = it.mapToScene(QtCore.QPointF(it.width() / 2, it.height() / 2)).toPoint()
    QtTest.QTest.mouseClick(win, Left, NoMod, p)
    QtTest.QTest.qWait(50)


def click(win: QtQuick.QQuickWindow, name: str) -> bool:
    found = [i for i in named(win, name) if i.isEnabled()]
    if not found:
        return False
    click_item(win, found[0])
    return True


def window(app, title: str) -> QtQuick.QQuickWindow | None:  # noqa: ANN001
    win = wait_until(
        lambda: next(
            (w for w in app.topLevelWindows()
             if isinstance(w, QtQuick.QQuickWindow) and w.isVisible()
             and w.title() == title),
            None,
        )
    )
    if win is None:
        return None
    return shiboken6.wrapInstance(shiboken6.getCppPointer(win)[0], QtQuick.QQuickWindow)


def open_page(app, root) -> QtQuick.QQuickWindow | None:  # noqa: ANN001
    item = next(
        (o for o in root.findChildren(QtCore.QObject)
         if "ThemedMenuItem" in o.metaObject().className()
         and o.property("command") == "tools.hidhide"),
        None,
    )
    if item is None:
        return None
    QtCore.QMetaObject.invokeMethod(item, "triggered")
    win = window(app, "HidHide")
    if win is not None:
        win.resize(900, 900)
        QtTest.QTest.qWait(200)
    return win


def state(win: QtQuick.QQuickWindow) -> dict:
    ticks = named(win, "resetDevicesTick")
    return {
        "names": texts(win, "resetDevicesName"),
        "usb": [str(i.property("usbId")) for i in named(win, "resetDevicesUsbId")],
        "ticked": [bool(i.property("checked")) for i in ticks],
        "enabled": [bool(i.isEnabled()) for i in ticks],
        "results": texts(win, "resetDevicesResult"),
        "notes": [t for t in texts(win, "resetDevicesNote") if t],
        "warning": texts(win, "resetDevicesWarning"),
        "games": texts(win, "resetDevicesGame"),
        "permission": texts(win, "resetDevicesPermission"),
        "count": texts(win, "resetDevicesCount"),
        "reset": texts(win, "resetDevicesReset"),
        "close": texts(win, "resetDevicesClose"),
    }


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    app.engine.warnings.connect(_warned)
    root = wait_until(lambda: app.engine.rootObjects())[0]
    # The Gremlin name of the right stick (after the start-up scan, which
    # forgets links to cards that have no module file).
    hh._save_links({R_HID: "Right stick"})
    page = open_page(app, root)
    result("page", page is not None)
    if page is None:
        print("done", flush=True)
        os._exit(0)
    result("page-button", {
        "header": texts(page, "hidHideResetDevices"),
        "enabled": [i.isEnabled() for i in named(page, "hidHideResetDevices")],
    })

    # Open #1: the hidden sticks are ticked; untick and tick one by clicks.
    result("clicked", click(page, "hidHideResetDevices"))
    win = window(app, "Reset Devices")
    result("open", win is not None)
    if win is None:
        print("done", flush=True)
        os._exit(0)
    win.resize(900, 520)
    QtTest.QTest.qWait(300)
    result("first", state(win))
    click_item(win, named(win, "resetDevicesTick")[0])
    result("untick", state(win))
    click_item(win, named(win, "resetDevicesTick")[0])
    result("tick", state(win))

    # 02 S144: the open window follows the program's device-change signal.
    from gremlin import event_handler

    pedals = [r for r in ROWS if r["usb_id"] == P_USB]
    ROWS[:] = [r for r in ROWS if r["usb_id"] != P_USB]
    event_handler.EventListener().device_change_event.emit()
    QtTest.QTest.qWait(200)
    result("unplugged", state(win))
    ROWS.extend(pedals)
    event_handler.EventListener().device_change_event.emit()
    QtTest.QTest.qWait(200)
    result("replugged", state(win))
    # A real Xbox pad plugged in (02 S145): listed unticked, with its note.
    ROWS.append(XPAD)
    event_handler.EventListener().device_change_event.emit()
    QtTest.QTest.qWait(200)
    result("xbox", state(win))
    ROWS.remove(XPAD)
    event_handler.EventListener().device_change_event.emit()
    QtTest.QTest.qWait(200)

    # Reset, Windows permission declined: no device touched.
    ANSWER[0] = device_reset.Cancelled()
    clicked = click(win, "resetDevicesReset")
    wait_until(lambda: named(win, "resetDevicesClose"), 10)
    result("declined", {"clicked": clicked, "calls": list(CALLS), **state(win)})
    click(win, "resetDevicesClose")
    wait_until(lambda: not win.isVisible(), 3)
    result("closed", not win.isVisible())

    # Open #2: ticked again from the hidden list; Reset with exit codes.
    CALLS.clear()
    click(page, "hidHideResetDevices")
    win = window(app, "Reset Devices")
    result("second-open", win is not None)
    if win is None:
        print("done", flush=True)
        os._exit(0)
    QtTest.QTest.qWait(300)
    result("second", state(win))
    SHOT.parent.mkdir(parents=True, exist_ok=True)
    win.grabWindow().save(str(SHOT))
    ANSWER[0] = {R_USB: 0, L_USB: 3010}
    clicked = click(win, "resetDevicesReset")
    wait_until(lambda: named(win, "resetDevicesClose"), 15)
    QtTest.QTest.qWait(100)
    result("reset", {"clicked": clicked, "calls": list(CALLS), **state(win)})
    win.grabWindow().save(str(SHOT.with_name(SHOT.stem + "_after.png")))
    result("warnings", WARNINGS)
    print("done", flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
