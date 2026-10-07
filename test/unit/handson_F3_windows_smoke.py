# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware) and opens Swap Devices,
Device Information or Calibration; prints what the window shows as JSON.
test_handson_F3_windows.py runs it in its own process with a fresh user
folder.

    python test/unit/handson_F3_windows_smoke.py swap 150
    python test/unit/handson_F3_windows_smoke.py devinfo
    python test/unit/handson_F3_windows_smoke.py calib
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

PART = sys.argv[1] if len(sys.argv) > 1 else "swap"
SCALE = int(sys.argv[2]) if len(sys.argv) > 2 else 100

from vjoy import vjoy  # noqa: E402

if PART == "devinfo":
    # vJoy 1 with discrete hats: the program leaves it out.
    vjoy.hat_configuration_valid = lambda vjoy_id: False  # type: ignore[assignment]

from gremlin.ui import ui_scale_option  # noqa: E402

ui_scale_option.active_scale = lambda: SCALE

import gremlin.ui.update_model as um  # noqa: E402

um.UpdateModel.startup = lambda self, *a, **k: None

import shiboken6  # noqa: E402
from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest  # noqa: E402

import dill  # noqa: E402
import joystick_gremlin  # noqa: E402
from gremlin import clock  # noqa: E402

LIMIT_MS = 10000


def wait_until(cond, limit_ms: int = LIMIT_MS) -> bool:  # noqa: ANN001
    """Runs the event loop until cond() is true or limit_ms has passed."""
    end = clock.monotonic() + limit_ms / 1000.0
    qapp = QtCore.QCoreApplication.instance()
    while True:
        if cond():
            return True
        if clock.monotonic() > end:
            return False
        qapp.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 20)
        QtCore.QCoreApplication.sendPostedEvents(
            None, QtCore.QEvent.Type.DeferredDelete
        )
        clock.sleep(0.005)  # leaves the program's threads room to run


def ev(obj: QtCore.QObject, code: str) -> object:
    expr = QtQml.QQmlExpression(QtQml.qmlContext(obj), obj, code)
    value = expr.evaluate()
    if expr.hasError():
        raise RuntimeError(expr.error().toString() + " :: " + code[:200])
    value = value[0] if isinstance(value, tuple) else value
    return value.toVariant() if hasattr(value, "toVariant") else value


def top_window(title: str):  # noqa: ANN201
    for w in QtGui.QGuiApplication.topLevelWindows():
        if w.isVisible() and w.title() == title:
            return shiboken6.wrapInstance(
                shiboken6.getCppPointer(w)[0], QtQuick.QQuickWindow
            )
    return None


def items(item: QtQuick.QQuickItem) -> list:
    found = [item]
    for child in item.childItems():
        found += items(child)
    return found


def open_window(win, qml: str, title: str, props: str = "{}"):  # noqa: ANN001, ANN201
    ev(win, f"Helpers.createComponent('{qml}', {props})")
    if not wait_until(lambda: top_window(title) is not None):
        raise RuntimeError(f"{title} did not open")
    return top_window(title)


app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window
win.setProperty("visible", True)
wait_until(lambda: win.isVisible())
out: dict = {"part": PART, "scale": SCALE}


def part_swap() -> None:
    """04 S80: the Swap Bindings question fits in the window and can be
    answered (click or keyboard)."""
    w = open_window(win, "DialogSwapDevices.qml", "Swap Devices")
    wait_until(w.isExposed)
    out["window-before"] = [w.width(), w.height()]
    box = ev(w, "_physicalDeviceSelection")
    out["swap-connected"] = [
        ev(box, f"textAt({i})") for i in range(int(ev(box, "count")))
    ]
    # Press Swap Bindings: the question opens.
    button = next(
        it for it in items(w.contentItem())
        if it.property("text") == "Swap Bindings" and it.isVisible()
    )
    QtCore.QMetaObject.invokeMethod(button, "clicked")
    wait_until(lambda: ev(button, "_swapGate.opened"))
    out["opened"] = bool(ev(button, "_swapGate.opened"))
    # The question laid out (its buttons side by side), and room for the
    # window to grow.
    wait_until(lambda: ev(button, "_swapGate.contentItem.children[2].children[2].x")
               > ev(button, "_swapGate.contentItem.children[2].children[0].x"))
    wait_until(lambda: w.height() >= ev(button, "_swapGate.height"))
    out["window"] = [w.width(), w.height()]
    # The question's buttons, by their row in the dialog, in window pixels.
    boxes = {}
    for i in range(3):
        box = ev(button, f"""(function() {{
            var b = _swapGate.contentItem.children[2].children[{i}]
            var p = b.mapToItem(null, 0, 0)
            return [b.text, b.visible, p.x, p.y, b.width, b.height] }})()""")
        if box[1]:
            boxes[box[0]] = box[2:]
    out["buttons"] = boxes
    # Esc answers Cancel: the question closes and nothing is swapped.
    status = ev(button, "_statusMessage.text")
    w.requestActivate()
    out["active"] = wait_until(w.isActive)
    QtTest.QTest.keyClick(w, QtCore.Qt.Key.Key_Escape)
    out["closed-by-esc"] = wait_until(lambda: not ev(button, "_swapGate.opened"))
    out["status-unchanged"] = ev(button, "_statusMessage.text") == status
    # Return never answers it (a stick can send Return).
    QtCore.QMetaObject.invokeMethod(button, "clicked")
    wait_until(lambda: ev(button, "_swapGate.opened"))
    QtTest.QTest.keyClick(w, QtCore.Qt.Key.Key_Return)
    wait_until(lambda: not ev(button, "_swapGate.opened"), 300)
    out["open-after-return"] = bool(ev(button, "_swapGate.opened"))
    # Tab reaches the question's buttons; Space presses the one in focus.
    focused = None
    for _ in range(4):
        QtTest.QTest.keyClick(w, QtCore.Qt.Key.Key_Tab)
        item = w.activeFocusItem()
        text = item.property("text") if item is not None else None
        if text in ("Cancel", "Swap bindings"):
            focused = text
            break
    out["tab-focus"] = focused
    if focused == "Cancel":
        QtTest.QTest.keyClick(w, QtCore.Qt.Key.Key_Space)
        out["closed-by-space"] = wait_until(
            lambda: not ev(button, "_swapGate.opened")
        )
    out["window-after"] = [w.width(), w.height()]
    out["min-height"] = w.minimumHeight()


def part_devinfo() -> None:
    """02 S9: Device Information lists the left-out vJoy; Swap Devices'
    connected devices are sticks only (no vJoy)."""
    w = open_window(win, "DialogDeviceInformation.qml", "Device Information")
    wait_until(lambda: any(
        isinstance(it.property("text"), str) and "pJoy Pro" in it.property("text")
        for it in items(w.contentItem())
    ))
    out["devinfo-names"] = sorted({
        it.property("text") for it in items(w.contentItem())
        if isinstance(it.property("text"), str) and (
            "pJoy" in it.property("text") or "vJoy" in it.property("text"))
    })


def part_calib() -> None:
    """03 S101: Calibration opened for a stick that isn't plugged in waits
    for it (no other stick picked) and shows it when it connects."""
    from gremlin import event_handler
    from gremlin.ui import hardware_profile

    first = fake.devices[0]
    second = fake_hardware.raw_device(is_virtual=False)
    second.device_guid.Data1 += 5
    second.name = b"Second Stick"
    for dev, name, slug in ((first, "pJoy Pro", "pjoy_pro"),
                            (second, "Second Stick", "second_stick")):
        guid = str(dill.GUID(dev.device_guid).uuid)
        path = hardware_profile.module_json_path(name, guid)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "kind": "control.hardware", "device": name, "direction": "source",
            "boundGuidLocal": guid,
            "claim": {"buttons": [1], "axes": [1, 2], "hats": [], "keys": []},
        }), encoding="utf-8")
        out[f"file-{slug}"] = path.stem
    event_handler.EventListener()._run_device_list_update()
    w = open_window(win, "DialogCalibration.qml", "Calibration",
                    "{initialSlug: 'second_stick'}")
    root = w
    wait_until(lambda: int(ev(root, "_moduleSelection.count")) > 0)
    wait_until(lambda: ev(root, "shownSlug"))

    def state() -> dict:
        return {
            "shown": ev(root, "shownSlug"),
            "current": ev(root, "_moduleSelection.currentText"),
            "axes": int(ev(root, "_axisView.count")),
            "waiting": ev(root, "waitingSlug"),
            "not-connected": any(
                it.property("text") == "This input module is not connected."
                and it.isVisible() for it in items(w.contentItem())
            ),
        }

    out["before"] = state()
    fake.devices.append(second)
    event_handler.EventListener()._run_device_list_update()
    wait_until(lambda: ev(root, "_moduleSelection.currentText") == "Second Stick"
               and int(ev(root, "_axisView.count")) > 0)
    out["after"] = state()


try:
    {"swap": part_swap, "devinfo": part_devinfo, "calib": part_calib}[PART]()
except Exception as exc:  # noqa: BLE001
    out["error"] = repr(exc)
print("RESULT " + json.dumps(out), flush=True)
os._exit(0)  # threads started by the app would keep it alive
