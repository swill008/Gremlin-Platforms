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


ALL_AXES = ["x", "y", "z", "rx", "ry", "rz", "sl0", "sl1"]


def _dev(i: int, axes: list | None = None, buttons: int = 128, hats: int = 4) -> dict:
    return {"id": i, "axes": list(ALL_AXES if axes is None else axes),
            "buttons": buttons, "hats": hats}


class FakeDrivers(QtCore.QObject):
    changed = QtCore.Signal()
    finished = QtCore.Signal()
    inUseRead = QtCore.Signal()

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
        # The vJoy layout is the real model's, so a tick box drives the real
        # setAxis; everything else here is the fake.
        from gremlin import drivers
        from gremlin.ui.drivers_model import DriversModel

        # vJoy installed, so an edited layout plans a vjoy_setup job and the
        # real alikeWarning() has devices to check.
        vjoy = drivers.DriverStatus("vjoy", "vJoy", "2.2.2.0", "2.2.2.0", "same")
        # What vJoy has now and which ids vJoyConfig calls busy; the script
        # changes these, then calls self._real.reload().
        self.world: dict[str, list] = {"current": [], "busy": []}
        self._real = DriversModel(status_source=lambda: [vjoy], app=lambda: None,
                                  vjoy_reader=lambda: list(self.world["current"]),
                                  busy_reader=lambda: list(self.world["busy"]),
                                  background=lambda n, w, d: d(w()))
        self._real.changed.connect(self.changed)
        self._real.inUseRead.connect(self.inUseRead)
        self._busy = False
        # A vJoy update keeps the devices (06 S185): the info box text, the
        # lost box text and the lost rows; the script sets them.
        self.info = ""
        self.lost = ""
        self.lost_rows: list[dict] = []

    @QtCore.Property(list, notify=changed)
    def rows(self):
        return self._rows

    @QtCore.Property(list, constant=True)
    def presets(self):
        return ["1 device, full", "2 devices, full", "Custom"]

    @QtCore.Property(str, notify=changed)
    def vjoyPreset(self):
        return self._real.vjoyPreset

    @QtCore.Property(list, notify=changed)
    def vjoyDevices(self):
        return self._real.vjoyDevices

    @QtCore.Property(str, notify=changed)
    def addPreview(self):
        return self._real.addPreview

    @QtCore.Property(list, constant=True)
    def vjoyAxes(self):
        return self._real.vjoyAxes

    @QtCore.Property(list, notify=changed)
    def vjoyCurrent(self):
        return [_dev(1, ["x", "y", "z", "rx", "ry", "rz"], 32, 1),
                _dev(2, ["x"], 1, 0), _dev(3, ["sl0", "sl1"], 2, 2),
                _dev(4, ["x", "y", "sl0"], 8, 0)]

    @QtCore.Property(bool, notify=changed)
    def vjoyEdited(self):
        return self._real.vjoyEdited

    @QtCore.Slot(list, int, int, result=str)
    def deviceSummary(self, axes, buttons, hats):
        return self._real.deviceSummary(axes, buttons, hats)

    @QtCore.Slot(int, str, bool)
    def setAxis(self, index, name, on):
        calls.append(f"axis {index} {name} {on}")
        self._real.setAxis(index, name, on)

    @QtCore.Property(str, notify=changed)
    def vjoyWarning(self):
        return ("Running games will lose the vJoy devices until they restart."
                if self._real.vjoyEdited else "")

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
        self._real.setPreset(name)

    @QtCore.Slot(int)
    def setDeviceCount(self, n):
        calls.append(f"count {n}")
        self._real.setDeviceCount(n)

    @QtCore.Slot()
    def addDevice(self):
        calls.append("add")
        self._real.addDevice()

    @QtCore.Slot(int, list, int, int)
    def setDevice(self, index, axes, buttons, hats):
        calls.append(f"device {index} {axes} {buttons} {hats}")
        self._real.setDevice(index, axes, buttons, hats)

    @QtCore.Slot(int)
    def removeDevice(self, index):
        calls.append(f"remove {index}")
        self._real.removeDevice(index)

    @QtCore.Slot(int, int, result=str)
    def showingText(self, first, count):
        return self._real.showingText(first, count)

    @QtCore.Slot(result=str)
    def inUseWarning(self):
        calls.append("inUseWarning")
        return self._real.inUseWarning()

    @QtCore.Slot(result=bool)
    def changesVjoy(self):
        return self._real.changesVjoy()

    @QtCore.Slot()
    def refreshInUse(self):
        calls.append("refreshInUse")
        self._real.refreshInUse()

    def _get_run(self):
        return self._real.runActive

    def _set_run(self, on):
        calls.append(f"runActive {bool(on)}")
        self._real.runActive = on

    runActive = QtCore.Property(bool, fget=_get_run, fset=_set_run, notify=changed)

    @QtCore.Slot(result=str)
    def describe(self):
        return "Install vJoy 2.2.2.0 now."

    @QtCore.Slot(result=str)
    def alikeWarning(self):
        calls.append("alikeWarning")
        return self._real.alikeWarning()

    @QtCore.Slot(result=bool)
    def apply(self):
        calls.append("apply")
        return True

    @QtCore.Slot(result=str)
    def updateInfo(self):
        calls.append("updateInfo")
        return self.info

    @QtCore.Slot(result=str)
    def lostText(self):
        return self.lost

    @QtCore.Slot(result=bool)
    def repairNow(self):
        calls.append("repairNow")
        return True

    @QtCore.Slot()
    def repairLater(self):
        calls.append("repairLater")

    @QtCore.Slot(int, result=bool)
    def repairDevice(self, vjoy_id):
        calls.append(f"repairDevice {vjoy_id}")
        return True

    @QtCore.Property(list, notify=changed)
    def vjoyLost(self):
        return self.lost_rows

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
    activityChanged = QtCore.Signal()
    uiScale = QtCore.Property(int, fget=lambda self: 100, notify=changed)
    active = False
    gremlinActive = QtCore.Property(bool, fget=lambda self: self.active,
                                    notify=activityChanged)

    def set_active(self, on: bool) -> None:
        self.active = on
        self.activityChanged.emit()

    @QtCore.Slot()
    def toggleActiveState(self):
        calls.append(f"toggle {not self.active}")
        self.set_active(not self.active)


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
    """By object name: the visual tree first (a Repeater's items hang only
    from it, and rows it has replaced but not yet deleted are off it), then
    the QObject tree (the prompt, in the overlay)."""
    top = root.contentItem() if isinstance(root, QtQuick.QQuickWindow) else root
    found = _visual(top, name)
    if found is not None:
        return found
    return root.findChild(QtCore.QObject, name)


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
out["oldNowLines"] = child(win, "vjoyCurrentTitle") is not None
out["heading"] = prop(win, "vjoyHeading", "text")
# The rows show for a preset too (not only Custom).
out["presetFirst"] = prop(win, "vjoyPreset", "currentText")
out["rowBeforeCustom"] = prop(win, "vjoyRow_0", "visible")
out["rowName0"] = prop(win, "vjoyName_0", "text")
out["heads"] = [prop(win, f"vjoyHead_{i}", "text") for i in range(8)] + [
    prop(win, "vjoyHeadButtons", "text"), prop(win, "vjoyHeadHats", "text")]
out["hint"] = prop(win, "vjoyHint", "text")
out["showingOne"] = prop(win, "vjoyShowing", "text")
out["warning"] = prop(win, "vjoyWarning", "text")
out["warningVisible"] = prop(win, "vjoyWarning", "visible")
out["result0"] = prop(win, "driverResult_0", "text")
out["restartVisible"] = prop(win, "driversRestart", "visible")
out["applyText"] = prop(win, "driversApply", "text")

out["rowOrder"] = [c.objectName() for c in child(win, "driverRow_vjoy").parentItem()
                   .childItems() if c.objectName().startswith("driverRow_")]

# Tick box.
tick = child(win, "driverTick_vigembus")
assert tick is not None
QtCore.QMetaObject.invokeMethod(tick, "click")
settle()
# Preset to Custom through the model, then the editor shows.
fake = made[0]
fake.setPreset("Custom")
settle(300)
out["customAfter"] = prop(win, "vjoyRow_0", "visible")
out["oldAxesBox"] = child(win, "vjoyAxes_0") is not None
names = ALL_AXES
out["axisBoxes"] = [prop(win, f"vjoyAxis_0_{n}", "text") for n in names]
out["axisChecked"] = [prop(win, f"vjoyAxis_0_{n}", "checked") for n in names]
QtCore.QMetaObject.invokeMethod(child(win, "vjoyAxis_0_rx"), "click")
settle(300)
out["axisCheckedAfter"] = [prop(win, f"vjoyAxis_0_{n}", "checked") for n in names]
out["deviceAxesAfter"] = list(fake.vjoyDevices[0]["axes"])
out["presetAfterAxis"] = prop(win, "vjoyPreset", "currentText")
out["buttonsMax"] = prop(win, "vjoyButtons_0", "count")
out["hatsMax"] = prop(win, "vjoyHats_0", "count")
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

# Alike devices (D-01-VJOY-COUNTDOWN): after OK a Yes/No box; No keeps the
# editor and runs nothing, Yes applies.
fake.setDeviceCount(2)
first = fake.vjoyDevices[0]
fake.setDevice(1, list(first["axes"]), first["buttons"], first["hats"])
settle(300)
calls.clear()
click(win, "driversApply")
settle(300)
click(win, "driverPromptOk")
settle(300)
out["alikeOpen"] = bool(prompt.property("opened")) if prompt else False
out["alikeTitle"] = prop(win, "driverPromptTitle", "text")
out["alikeBody"] = prop(win, "driverPromptBody", "text")
out["alikeOk"] = prop(win, "driverPromptOk", "text")
out["alikeCancel"] = prop(win, "driverPromptCancel", "text")
out["alikeApplyBefore"] = "apply" in calls
click(win, "driverPromptCancel")
settle(300)
out["alikeNoClosed"] = not (prompt.property("opened") if prompt else True)
out["alikeNoApply"] = "apply" in calls
out["alikeNoEditor"] = prop(win, "vjoyRow_1", "visible")
out["alikeNoDevices"] = len(fake.vjoyDevices)
click(win, "driversApply")
settle(300)
click(win, "driverPromptOk")
settle(300)
click(win, "driverPromptOk")
settle(300)
out["alikeYesApply"] = calls.count("apply")

# Grow, then scroll inside the list: 16 devices don't fit at 720 px; the
# window doesn't scroll and Apply stays in view.
from gremlin import drivers  # noqa: E402

win.setProperty("height", 720)
fake.setDeviceCount(16)
settle(400)
rows = child(win, "vjoyRows")
out["rowsScroll"] = rows.property("contentHeight") > rows.property("height") + 1
out["showing16"] = prop(win, "vjoyShowing", "text")
apply_btn = child(win, "driversApply")
pos = apply_btn.mapToItem(win.contentItem(), QtCore.QPointF(0, 0))
out["applyInView"] = 0 <= pos.y() and pos.y() + apply_btn.height() <= win.height()
rows.setProperty("contentY", rows.property("contentHeight") - rows.property("height"))
settle(300)
out["showingEnd"] = prop(win, "vjoyShowing", "text")
fake.setDeviceCount(4)
settle(300)

# The "+ Add device" row: the last row inside the list, scrolls with it,
# gone at 16 devices.
add_row = child(win, "vjoyAddRow")
fake.setDeviceCount(4)
settle(300)
add_row = child(win, "vjoyAddRow")
last_dev = child(win, "vjoyRow_3")
out["addRowVisible4"] = bool(add_row.property("visible"))
out["addRowBelowLast"] = (
    add_row.property("y")
    >= last_dev.property("y") + last_dev.property("height") - 1
)
out["addRowInColumn"] = (
    rows.property("contentHeight")
    >= add_row.property("y") + add_row.property("height") - 1
)
out["addPreview4"] = prop(win, "vjoyAddPreview", "text")
_cur = child(win, "vjoyAddMouse").property("cursorShape")
out["addRowCursor"] = (
    getattr(_cur, "value", _cur) == QtCore.Qt.CursorShape.PointingHandCursor.value
)
fake.setDeviceCount(16)
settle(400)
rows.setProperty("contentY", 0)
settle(200)
out["addRowHidden16"] = not child(win, "vjoyAddRow").property("visible")
out["addPreview16"] = prop(win, "vjoyAddPreview", "text")
fake.setDeviceCount(15)
settle(400)
rows.setProperty("contentY", rows.property("contentHeight") - rows.property("height"))
settle(300)
add_row = child(win, "vjoyAddRow")
p0 = add_row.mapToItem(
    win.contentItem(),
    QtCore.QPointF(add_row.width() / 2, add_row.height() / 2),
)
out["addRowScrolledIn"] = 0 <= p0.y() <= win.height()
out["addPreview15"] = prop(win, "vjoyAddPreview", "text")
calls.clear()
from PySide6 import QtTest  # noqa: E402

QtTest.QTest.mouseClick(win, QtCore.Qt.MouseButton.LeftButton,
                        QtCore.Qt.KeyboardModifier.NoModifier,
                        QtCore.QPoint(int(p0.x()), int(p0.y())))
settle(300)
out["addCalls"] = list(calls)
out["addIdsAfter"] = [d["id"] for d in fake.vjoyDevices]
out["addNewButtons"] = fake.vjoyDevices[-1]["buttons"]
fake.setDeviceCount(4)
settle(300)

# The row's ✕ removes that device; lowering Devices removes the highest.
calls.clear()
click(win, "vjoyRemove_1")
settle(300)
out["removeCalls"] = list(calls)
out["idsAfterRemove"] = [d["id"] for d in fake.vjoyDevices]
fake.setDeviceCount(2)
settle(300)
out["idsAfterLower"] = [d["id"] for d in fake.vjoyDevices]
out["showing2"] = prop(win, "vjoyShowing", "text")
out["listFits2"] = not (rows.property("contentHeight") > rows.property("height") + 1)

# The last ticked axis can't be unticked.
fake.setDevice(0, ["x"], 120, 0)
settle(300)
out["lastAxisEnabled"] = prop(win, "vjoyAxis_0_x", "enabled")
out["otherAxisEnabled"] = prop(win, "vjoyAxis_0_y", "enabled")
fake.setAxis(0, "x", False)
settle(300)
out["lastAxisStill"] = prop(win, "vjoyAxis_0_x", "checked")

# In use by another program: vJoy 2 busy.
fake.world["current"] = [drivers.new_device(1), drivers.new_device(2)]
fake.world["busy"] = [2]
fake._real.reload()
fake.setPreset("2 devices, full")
settle(300)
out["inUseRow"] = [prop(win, f"vjoyName_{i}", "inUse") for i in (0, 1)]
out["inUseColor"] = [prop(win, f"vjoyName_{i}", "color").name() for i in (0, 1)]
out["inUseBold"] = [prop(win, f"vjoyName_{i}", "font").bold() for i in (0, 1)]
out["inUseText"] = prop(win, "vjoyName_1", "text")
out["inUseTip"] = [prop(win, f"vjoyName_{i}", "tip") for i in (0, 1)]
out["oldInUseLabel"] = child(win, "vjoyInUse_1") is not None
_style = engine.singletonInstance("Gremlin.Style", "Style")
out["styleDanger"] = _style.property("danger").name() if _style else None
out["styleFg"] = _style.property("fg").name() if _style else None
fake.setDevice(1, list(drivers.VJOY_AXES), 100, 2)  # vJoy 2 changed
settle(300)
calls.clear()
click(win, "driversApply")
settle(300)
click(win, "driverPromptOk")
settle(300)
out["inUseTitle"] = prop(win, "driverPromptTitle", "text")
out["inUseBody"] = prop(win, "driverPromptBody", "text")
out["inUseButtons"] = [prop(win, "driverPromptOk", "text"),
                       prop(win, "driverPromptCancel", "text")]
click(win, "driverPromptCancel")
settle(300)
out["inUseNoCalls"] = list(calls)
calls.clear()
click(win, "driversApply")
settle(300)
click(win, "driverPromptOk")
settle(300)
click(win, "driverPromptOk")  # Yes on the in-use box
settle(300)
out["inUseYesCalls"] = list(calls)

# Our own Run is on: vJoy 2 isn't marked; Apply asks to stop Run first,
# Yes stops it, the busy ids are read again, then the in-use box.
_backend.set_active(True)
settle(300)
out["runHidesInUse"] = prop(win, "vjoyName_1", "inUse")
calls.clear()
click(win, "driversApply")
settle(300)
click(win, "driverPromptOk")
settle(300)
out["runTitle"] = prop(win, "driverPromptTitle", "text")
out["runBody"] = prop(win, "driverPromptBody", "text")
out["runButtons"] = [prop(win, "driverPromptOk", "text"),
                     prop(win, "driverPromptCancel", "text")]
click(win, "driverPromptCancel")  # No: nothing happens
settle(300)
out["runNoCalls"] = list(calls)
calls.clear()
click(win, "driversApply")
settle(300)
click(win, "driverPromptOk")
settle(300)
click(win, "driverPromptOk")  # Yes: Run stops
settle(500)
out["runYesCalls"] = list(calls)
out["runYesNext"] = prop(win, "driverPromptTitle", "text")
out["runYesBackend"] = _backend.active
click(win, "driverPromptCancel")
settle(300)

# A vJoy update keeps the devices (06 S185). The information box (OK only)
# comes after the what-will-happen prompt, before the in-use box.
_v2 = drivers.VJoyDevice(2, ("x", "y", "z"), 32, 0)
_v4 = drivers.VJoyDevice(4, drivers.VJOY_AXES, 32, 0)
fake.info = drivers.update_info_text([_v2, _v4])
calls.clear()
click(win, "driversApply")
settle(300)
click(win, "driverPromptOk")
settle(300)
out["infoOpen"] = bool(prompt.property("opened"))
out["infoTitle"] = prop(win, "driverPromptTitle", "text")
out["infoBody"] = prop(win, "driverPromptBody", "text")
out["infoOk"] = prop(win, "driverPromptOk", "text")
out["infoCancelVisible"] = prop(win, "driverPromptCancel", "visible")
out["infoCallsBefore"] = list(calls)
click(win, "driverPromptOk")
settle(300)
out["infoNext"] = prop(win, "driverPromptTitle", "text")
out["infoCallsAfter"] = list(calls)
click(win, "driverPromptCancel")
settle(300)
fake.info = ""
calls.clear()
click(win, "driversApply")
settle(300)
click(win, "driverPromptOk")
settle(300)
out["noInfoNext"] = prop(win, "driverPromptTitle", "text")
click(win, "driverPromptCancel")
settle(300)

# After the results: the update lost a device.
fake.lost = drivers.lost_text([_v4])
calls.clear()
fake.finished.emit()
settle(300)
out["lostOpen"] = bool(prompt.property("opened"))
out["lostTitle"] = prop(win, "driverPromptTitle", "text")
out["lostBody"] = prop(win, "driverPromptBody", "text")
out["lostButtons"] = [prop(win, "driverPromptOk", "text"),
                      prop(win, "driverPromptCancel", "text")]
click(win, "driverPromptOk")
settle(300)
out["lostNowCalls"] = list(calls)
calls.clear()
fake.finished.emit()
settle(300)
click(win, "driverPromptCancel")
settle(300)
out["lostLaterCalls"] = list(calls)
fake.lost = ""
calls.clear()
fake.finished.emit()
settle(300)
out["nothingLostOpen"] = bool(prompt.property("opened"))
out["nothingLostCalls"] = list(calls)

# Remembered lost devices: rows marked "lost in the vJoy update", Repair.
out["lostRowBefore"] = child(win, "vjoyLostRow_0") is not None
fake.lost_rows = [{"id": 4, "axes": list(_v4.axes), "buttons": 32, "hats": 0,
                   "summary": "8 axes (X-S2), 32 buttons, 0 hats"}]
fake.changed.emit()
settle(300)
out["lostRowName"] = prop(win, "vjoyLostName_0", "text")
out["lostRowSummary"] = prop(win, "vjoyLostSummary_0", "text")
out["lostRowMark"] = prop(win, "vjoyLostMark_0", "text")
out["lostRowMarkColor"] = prop(win, "vjoyLostMark_0", "color").name()
out["styleWarn"] = _style.property("warn").name() if _style else None
out["lostRowRepair"] = prop(win, "vjoyLostRepair_0", "text")
calls.clear()
click(win, "vjoyLostRepair_0")
settle(300)
out["lostRowCalls"] = list(calls)
fake.lost_rows = []
fake.changed.emit()
settle(300)
out["lostRowGone"] = not prop(win, "vjoyLostRow_0", "visible", False)

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
