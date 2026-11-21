# -*- coding: utf-8; -*-
# ruff: noqa: ANN001, ANN201, ANN202
# SPDX-License-Identifier: GPL-3.0-only

"""Opens qml/WindowDrivers.qml, DialogDriverPrompt, XboxDriverCheck and the
Home page off-screen with a fake DriversModel (registered as Gremlin.Device
DriversModel unless the real one is importable), presses the buttons and
prints what happened as JSON, for test_drivers_window.py."""

from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path

from smoke_exit import smoke_exit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

spec = importlib.util.spec_from_file_location(
    "fake_hardware", ROOT / "test" / "fake_hardware.py"
)
assert spec is not None and spec.loader is not None
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake_hardware.install()

from PySide6 import QtCore, QtGui, QtQml, QtQuick  # noqa: E402

import gremlin.ui.device_names  # noqa: E402, F401  (Gremlin.Device)
import gremlin.ui.folder_memory  # noqa: E402, F401  (FilePicker)
import gremlin.ui.osc_card_status  # noqa: E402, F401  (OscCardStatus)
import gremlin.ui.window_placement  # noqa: E402, F401  (Gremlin.UI)

calls: list[str] = []
made: list[object] = []


def _dev(i: int, axes: int = 8, buttons: int = 128, hats: int = 4) -> dict:
    return {"id": i, "axes": axes, "buttons": buttons, "hats": hats}


class FakeDrivers(QtCore.QObject):
    changed = QtCore.Signal()
    finished = QtCore.Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        made.append(self)
        self._rows = [
            {"key": "vjoy", "name": "vJoy", "installed": "", "bundled": "2.2.2.0",
             "state": "missing", "label": "not installed", "ticked": True,
             "tickable": True},
            {"key": "vigembus", "name": "ViGEmBus", "installed": "1.21.442.0",
             "bundled": "1.22.0", "state": "older",
             "label": "update available: 1.21.442.0 → 1.22.0", "ticked": False,
             "tickable": True},
            {"key": "hidhide", "name": "HidHide", "installed": "1.5.230",
             "bundled": "1.5.230", "state": "same", "label": "1.5.230",
             "ticked": False, "tickable": False},
        ]
        self._preset = "1 device, full"
        self._devices = [_dev(1)]
        self._busy = False
        self._edited = False

    @QtCore.Property(list, notify=changed)
    def rows(self):
        return self._rows

    @QtCore.Property(list, constant=True)
    def presets(self):
        return ["1 device, full", "2 devices, full", "Custom"]

    @QtCore.Property(str, notify=changed)
    def vjoyPreset(self):
        return self._preset

    @QtCore.Property(list, notify=changed)
    def vjoyDevices(self):
        return self._devices

    @QtCore.Property(list, notify=changed)
    def vjoyCurrent(self):
        return [_dev(1, 6, 32, 1)]

    @QtCore.Property(bool, notify=changed)
    def vjoyEdited(self):
        return self._edited

    @QtCore.Property(str, notify=changed)
    def vjoyWarning(self):
        return ("Running games will lose the vJoy devices until they restart."
                if self._edited else "")

    @QtCore.Property(bool, notify=changed)
    def busy(self):
        return self._busy

    @QtCore.Property(str, notify=changed)
    def progress(self):
        return "Installing vJoy 2.2.2.0…" if self._busy else ""

    @QtCore.Property(list, notify=changed)
    def results(self):
        return [{"driver": "vJoy", "state": "done", "message": "Installed 2.2.2.0"}]

    @QtCore.Property(bool, notify=changed)
    def restartNeeded(self):
        return True

    @QtCore.Property(bool, notify=changed)
    def pendingHidHide(self):
        return True

    @QtCore.Property(str, notify=changed)
    def pendingVersion(self):
        return "1.5.231"

    @QtCore.Slot()
    def reload(self):
        calls.append("reload")

    @QtCore.Slot(str, bool)
    def setTicked(self, key, on):
        calls.append(f"tick {key} {on}")

    @QtCore.Slot(str)
    def setPreset(self, name):
        calls.append(f"preset {name}")
        self._preset = name
        self._edited = True
        if name == "2 devices, full":
            self._devices = [_dev(1), _dev(2)]
        self.changed.emit()

    @QtCore.Slot(int)
    def setDeviceCount(self, n):
        calls.append(f"count {n}")
        self._devices = [_dev(i + 1) for i in range(n)]
        self.changed.emit()

    @QtCore.Slot(int, int, int, int)
    def setDevice(self, index, axes, buttons, hats):
        calls.append(f"device {index} {axes} {buttons} {hats}")

    @QtCore.Slot(result=str)
    def describe(self):
        return "Install vJoy 2.2.2.0 now."

    @QtCore.Slot(result=bool)
    def apply(self):
        calls.append("apply")
        return True

    @QtCore.Slot(result=bool)
    def finishHidHide(self):
        calls.append("finishHidHide")
        return True

    @QtCore.Slot()
    def restartNow(self):
        calls.append("restartNow")

    @QtCore.Slot()
    def laterHidHide(self):
        calls.append("laterHidHide")


if importlib.util.find_spec("gremlin.ui.drivers_model") is None:
    QtQml.qmlRegisterType(FakeDrivers, "Gremlin.Device", 1, 0, "DriversModel")
else:
    # Not the real model: the fake is the contract's API with known values.
    QtQml.qmlRegisterType(FakeDrivers, "Gremlin.Device", 1, 0, "DriversModel")



class FakeBackend(QtCore.QObject):
    changed = QtCore.Signal()
    uiScale = QtCore.Property(int, fget=lambda self: 100, notify=changed)
    gremlinActive = QtCore.Property(bool, fget=lambda self: False, notify=changed)


app = QtGui.QGuiApplication([sys.argv[0]])
engine = QtQml.QQmlEngine()
_backend = FakeBackend()
engine.rootContext().setContextProperty("backend", _backend)
engine.addImportPath(str(ROOT / "theme"))
engine.addImportPath(str(ROOT / "qml"))
QtQml.qmlRegisterSingletonType(
    QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / "Style.qml")),
    "Gremlin.Style", 1, 0, "Style",
)
errors: list[str] = []
_keep: list[object] = []


def settle(ms: int = 200) -> None:
    end = time.monotonic() + ms / 1000
    while time.monotonic() < end:
        app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 20)


def create(name: str, props: dict | None = None) -> QtCore.QObject:
    component = QtQml.QQmlComponent(
        engine, QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / name))
    )
    _keep.append(component)
    obj = component.createWithInitialProperties(props or {}) if props \
        else component.create()
    if obj is None:
        errors.extend(e.toString() for e in component.errors())
        print("RESULT " + json.dumps({"errors": errors}), flush=True)
        smoke_exit(1)
    return obj


def _visual(item: QtCore.QObject, name: str) -> QtCore.QObject | None:
    if item.objectName() == name:
        return item
    for sub in item.childItems():
        found = _visual(sub, name)
        if found is not None:
            return found
    return None


def child(root: QtCore.QObject, name: str) -> QtCore.QObject | None:
    """By object name: the QObject tree first, then the visual tree (a
    Repeater's items hang only from the visual one)."""
    found = root.findChild(QtCore.QObject, name)
    if found is not None:
        return found
    top = root.contentItem() if isinstance(root, QtQuick.QQuickWindow) else root
    return _visual(top, name)


def prop(root: QtCore.QObject, name: str, what: str, default=None):
    item = child(root, name)
    return item.property(what) if item is not None else default


def click(root: QtCore.QObject, name: str) -> None:
    item = child(root, name)
    assert item is not None, name
    QtCore.QMetaObject.invokeMethod(item, "clicked")


win = create("WindowDrivers.qml")
win.show()
settle(400)
out: dict[str, object] = {}
out["title"] = win.property("title")
keys = ["vjoy", "vigembus", "hidhide"]
out["labels"] = {k: prop(win, f"driverLabel_{k}", "text") for k in keys}
out["names"] = {k: prop(win, f"driverName_{k}", "text") for k in keys}
out["tickVisible"] = {k: prop(win, f"driverTick_{k}", "visible") for k in keys}
out["tickChecked"] = {k: prop(win, f"driverTick_{k}", "checked") for k in keys}
out["current"] = prop(win, "vjoyCurrent_1", "text")
out["customVisible"] = prop(win, "vjoyCustom", "visible")
out["warning"] = prop(win, "vjoyWarning", "text")
out["warningVisible"] = prop(win, "vjoyWarning", "visible")
out["result0"] = prop(win, "driverResult_0", "text")
out["restartVisible"] = prop(win, "driversRestart", "visible")
out["applyText"] = prop(win, "driversApply", "text")

# Tick box.
tick = child(win, "driverTick_vigembus")
assert tick is not None
QtCore.QMetaObject.invokeMethod(tick, "click")
settle()
# Preset to Custom through the model, then the editor shows.
fake = made[0]
fake.setPreset("Custom")
settle(300)
out["customAfter"] = prop(win, "vjoyCustom", "visible")
out["axesMax"] = prop(win, "vjoyAxes_0", "to")
out["buttonsMax"] = prop(win, "vjoyButtons_0", "to")
out["hatsMax"] = prop(win, "vjoyHats_0", "to")
out["countRange"] = [prop(win, "vjoyDeviceCount", "from"),
                     prop(win, "vjoyDeviceCount", "to")]
# Apply: prompt first, OK runs apply().
click(win, "driversApply")
settle(300)
prompt = child(win, "driverPrompt")
out["promptOpen"] = bool(prompt.property("opened")) if prompt else False
out["promptBody"] = prop(win, "driverPromptBody", "text")
out["applyBeforeOk"] = "apply" in calls
click(win, "driverPromptOk")
settle(300)
out["applyAfterOk"] = "apply" in calls
click(win, "driversRestartNow")
click(win, "driversRestartLater")
settle()
out["restartHidden"] = not prop(win, "driversRestart", "visible", True)
out["calls"] = list(calls)

# Step 2 through the window property.
calls.clear()
win2 = create("WindowDrivers.qml", {"finishHidHideOnOpen": True})
win2.show()
settle(400)
out["finishCalls"] = list(calls)
fake2 = made[1]
fake2.finished.emit()
settle(300)
out["restartPromptTitle"] = prop(win2, "driverPromptTitle", "text")
out["restartPromptBody"] = prop(win2, "driverPromptBody", "text")
out["restartPromptOk"] = prop(win2, "driverPromptOk", "text")
out["restartPromptCancel"] = prop(win2, "driverPromptCancel", "text")

# Xbox driver check.
check = create("XboxDriverCheck.qml")
signals: list[str] = []
check.driversRequested.connect(lambda: signals.append("driversRequested"))
settle()
out["openDrivers"] = prop(check, "xboxOpenDrivers", "text")
out["testButton"] = prop(check, "xboxTestDriver", "text")
click(check, "xboxOpenDrivers")
out["xboxSignals"] = signals

# Home line.
home = create("StatusPage.qml")
settle(300)
out["homeNotice"] = prop(home, "homeHidHideNotice", "visible")
out["homeText"] = prop(home, "homeHidHideNoticeText", "text")
out["homeButton"] = prop(home, "homeFinishUpdate", "text")

out["errors"] = errors
print("RESULT " + json.dumps(out), flush=True)
smoke_exit(0)
