# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware) and plugs a stick in
and out under the screens that show it; prints what each one holds as JSON.
test_device_reconnect.py runs it in its own process with a fresh user
folder.

    python test/unit/device_reconnect_smoke.py
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

from PySide6 import QtCore, QtQml, QtQuick, QtTest  # noqa: E402

import dill  # noqa: E402
import joystick_gremlin  # noqa: E402
from gremlin import event_handler  # noqa: E402
from gremlin.input_cache import Joystick  # noqa: E402

stick = fake.devices[0]  # "pJoy Pro": 6 axes, 64 buttons, 2 hats
GUID = str(dill.GUID(stick.device_guid).uuid)
UUID = dill.GUID(stick.device_guid).uuid

# The stick's input module (its axes claimed), as Module Setup saves one.
from gremlin.ui import hardware_profile  # noqa: E402

_module = hardware_profile.module_json_path("pJoy Pro", GUID)
_module.parent.mkdir(parents=True, exist_ok=True)
_module.write_text(
    json.dumps({
        "kind": "control.hardware",
        "device": "pJoy Pro",
        "direction": "source",
        "boundGuidLocal": GUID,
        "boundName": "pJoy Pro",
        "claim": {"buttons": [1, 2, 3], "axes": [1, 2, 3, 4, 5, 6], "hats": [1]},
        "nodes": [],
    }),
    encoding="utf-8",
)


def device_change() -> None:
    # What the device thread does after a plug or unplug (on its timer).
    event_handler.EventListener()._run_device_list_update()
    QtTest.QTest.qWait(400)


def unplug() -> None:
    fake.devices.remove(stick)
    device_change()


def plug() -> None:
    fake.devices.insert(0, stick)
    device_change()


def _items(item: QtQuick.QQuickItem) -> list:
    """Every item under this one (list rows have no QObject parent)."""
    found = []
    for child in item.childItems():
        found.append(child)
        found.extend(_items(child))
    return found


def main() -> None:
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    QtTest.QTest.qWait(800)
    out: dict = {}

    from gremlin.ui.device import AxisCalibration, Device, DeviceAxisSeries
    from gremlin.ui.live_input import DeviceLiveState
    from gremlin.ui.module_calibration import CalibrationModuleModel
    from gremlin.ui.module_inputs import ModuleClaimedInputModel
    from gremlin.ui.module_model import DriverInputModel

    # Calibration's list while the stick is there (its module's slug).
    modules = CalibrationModuleModel()
    slugs = [modules.data(modules.index(i, 0), QtCore.Qt.ItemDataRole.UserRole + 2)
             for i in range(modules.rowCount())]
    out["calibration-modules-plugged"] = len(slugs)
    slug = slugs[0] if slugs else ""

    # The screens set to the stick while it is unplugged.
    unplug()
    device = Device()
    device.guid = GUID
    series = DeviceAxisSeries()
    series.guid = GUID
    live = DeviceLiveState()
    live.guid = GUID
    claimed = ModuleClaimedInputModel()
    claimed.guid = GUID
    setup = DriverInputModel()
    setup.loadDevice(GUID, "pJoy Pro")
    calibration = AxisCalibration()
    calibration.moduleSlug = slug

    def look() -> dict:
        return {
            "input-configuration": device.rowCount(),
            "axis-graph": len(series._state),
            "live-values": len(live._kinds),
            "claimed": claimed._device is not None,
            "module-setup-rows": setup.rowCount(),
            "module-setup-save-refused": bool(setup.saveBlockedReason()),
            "calibration-axes": calibration.rowCount(),
            "calibration-modules": modules.rowCount(),
        }

    out["unplugged"] = look()
    plug()
    out["plugged-in"] = look()
    unplug()
    out["unplugged-again"] = look()
    plug()
    out["back"] = look()

    # A button held and a hat pushed as the stick goes: let go of.
    wrapper = Joystick()[UUID]
    wrapper.button(3).update(True)
    from gremlin.types import HatDirection

    wrapper.hat(1).update(HatDirection.North)
    seen: list = []
    event_handler.EventListener().joystick_event.connect(
        lambda e: seen.append(
            (e.event_type.name, e.identifier, e.is_pressed, str(e.value))
        )
        if e.device_guid == UUID
        else None,
        QtCore.Qt.ConnectionType.DirectConnection,
    )
    unplug()
    out["let-go"] = sorted(seen)
    out["held-after"] = [wrapper.button(3).is_pressed, str(wrapper.hat(1).direction)]
    plug()

    # HidHide re-reads its list when a stick comes or goes (its reading of
    # the PC's devices stood in for: counted, not run).
    from gremlin.ui import hidhide

    reads: list[int] = []
    real_reload = hidhide.HidHideModel.reload
    hidhide.HidHideModel.reload = lambda self: reads.append(1)  # type: ignore[method-assign]
    hide = hidhide.HidHideModel()
    unplug()
    plug()
    out["hidhide-reads"] = len(reads)
    hidhide.HidHideModel.reload = real_reload  # type: ignore[method-assign]
    del hide

    # Auto Mapper: a tick stays when a stick plugged in or out rebuilds the list.
    engine = app.engine
    component = QtQml.QQmlComponent(
        engine, QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / "DialogAutoMapper.qml"))
    )
    mapper = component.create()
    if mapper is None:
        out["auto-mapper"] = "failed: " + component.errorString()
    else:
        # Rows are made only for a window on screen (off-screen here).
        mapper.setProperty("visible", True)
        QtTest.QTest.qWait(500)
        boxes = [
            o for o in _items(mapper.contentItem())
            if "CheckBox" in o.metaObject().className()
            and o.property("text") not in (None, "")
            and "claim" not in str(o.property("text")).lower()
        ]
        first = boxes[0] if boxes else None
        name = first.property("text") if first else ""
        if first is not None:
            first.setProperty("checked", True)
        unplug()
        plug()
        QtTest.QTest.qWait(300)
        again = [
            o for o in _items(mapper.contentItem())
            if "CheckBox" in o.metaObject().className()
            and o.property("text") == name
        ]
        out["auto-mapper"] = {
            "box": bool(name),
            "ticked-after-replug": [bool(o.property("checked")) for o in again],
        }
        mapper.close()

    print("RESULT " + json.dumps(out), flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
