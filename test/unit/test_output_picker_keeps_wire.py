# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import os
import pathlib
import sys
from unittest import mock

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

from gremlin import event_handler
from gremlin.ui import output_modules

# vjoy_3 claims 3 axes and 56 buttons, like the user's file.
_MODULES = [
    {
        "name": "vJoy 3",
        "vjoy_id": 3,
        "claim": {"axes": [1, 2, 3], "buttons": list(range(1, 57)), "hats": []},
    }
]


@pytest.fixture
def picker() -> output_modules.OutputModuleDevices:
    with (
        mock.patch.object(output_modules, "_dest_modules", return_value=_MODULES),
        mock.patch.object(event_handler, "EventListener"),
    ):
        devices = output_modules.OutputModuleDevices()
        devices.validTypes = ["button"]
        yield devices


def _writes(devices: output_modules.OutputModuleDevices) -> list[tuple]:
    seen: list[tuple] = []
    devices.currentSelectionChanged.connect(lambda *args: seen.append(args))
    return seen


def test_saved_unclaimed_output_is_kept_and_flagged(
    picker: output_modules.OutputModuleDevices,
) -> None:
    writes = _writes(picker)
    picker.setInitialState(3, "button", 57)

    assert writes == []  # the wire is not re-pointed or written back
    assert picker.currentUnclaimed
    assert "⚠ Button 57" in picker.inputChoices
    assert "vJoy 3" in picker.vjoyDevices


def test_claimed_output_still_selects_normally(
    picker: output_modules.OutputModuleDevices,
) -> None:
    writes = _writes(picker)
    picker.setInitialState(3, "button", 5)

    assert writes == [(3, "button", 5)]
    assert not picker.currentUnclaimed
    assert not any(label.startswith("⚠") for label in picker.inputChoices)


def test_type_change_still_moves_to_a_claimed_output(
    picker: output_modules.OutputModuleDevices,
) -> None:
    picker.setInitialState(3, "button", 57)
    writes = _writes(picker)
    picker.validTypes = ["axis"]  # e.g. the action became an axis action

    assert writes and writes[-1][1] == "axis"
    assert not picker.currentUnclaimed
    assert not any(label.startswith("⚠") for label in picker.inputChoices)


def test_vjoy_without_an_output_module_is_labelled(
    picker: output_modules.OutputModuleDevices,
) -> None:
    writes = _writes(picker)
    picker.setInitialState(4, "button", 2)

    assert writes == []
    assert "vJoy 4 (no output module)" in picker.vjoyDevices
    assert picker.currentUnclaimed


# vJoy 3 (buttons 1-56) and vJoy 4 (buttons 1-32, axes 1-8): D-05-VJOY-SWITCH.
_TWO_MODULES = [
    _MODULES[0],
    {
        "name": "vJoy 4",
        "vjoy_id": 4,
        "claim": {"axes": list(range(1, 9)), "buttons": list(range(1, 33)), "hats": []},
    },
]


@pytest.fixture
def two_vjoys() -> output_modules.OutputModuleDevices:
    with (
        mock.patch.object(output_modules, "_dest_modules", return_value=_TWO_MODULES),
        mock.patch.object(event_handler, "EventListener"),
    ):
        devices = output_modules.OutputModuleDevices()
        devices.validTypes = ["button"]
        yield devices


def test_switching_vjoy_moves_to_first_claimed_when_input_missing(
    two_vjoys: output_modules.OutputModuleDevices,
) -> None:
    two_vjoys.setInitialState(3, "button", 40)
    writes = _writes(two_vjoys)
    # The device box's text changed; the input box still says Button 40.
    two_vjoys.setState("vJoy 4", "Button 40")

    assert writes == [(4, "button", 1)]
    assert two_vjoys.inputChoices[0] == "Button 1"


def test_switching_vjoy_from_unclaimed_wire_moves_and_clears_flag(
    two_vjoys: output_modules.OutputModuleDevices,
) -> None:
    two_vjoys.setInitialState(3, "button", 57)
    assert two_vjoys.currentUnclaimed
    writes = _writes(two_vjoys)
    two_vjoys.setState("vJoy 4", "⚠ Button 57")

    assert writes == [(4, "button", 1)]
    assert not two_vjoys.currentUnclaimed
    assert not any(label.startswith("⚠") for label in two_vjoys.inputChoices)


def test_switching_vjoy_keeps_same_control_when_claimed(
    two_vjoys: output_modules.OutputModuleDevices,
) -> None:
    two_vjoys.setInitialState(3, "button", 5)
    writes = _writes(two_vjoys)
    two_vjoys.setState("vJoy 4", "Button 5")

    assert writes == [(4, "button", 5)]


_QML_CODE = r"""
import importlib.util, os, sys
ROOT = sys.argv[1]
sys.path.insert(0, ROOT)
spec = importlib.util.spec_from_file_location(
    "fake_hardware", os.path.join(ROOT, "test", "fake_hardware.py"))
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake_hardware.install()
import gremlin.ui.update_model as um
um.UpdateModel.startup = lambda self, *a, **k: None
from gremlin.ui import output_modules
MODULES = [
    {"name": "vJoy 3", "vjoy_id": 3,
     "claim": {"axes": [1, 2, 3], "buttons": list(range(1, 57)), "hats": []}},
    {"name": "vJoy 4", "vjoy_id": 4,
     "claim": {"axes": list(range(1, 9)), "buttons": list(range(1, 33)),
               "hats": []}},
]
output_modules._dest_modules = lambda: MODULES
import joystick_gremlin
from PySide6 import QtCore, QtQml, QtTest
app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
QtTest.QTest.qWait(300)
url = QtCore.QUrl.fromLocalFile(os.path.join(ROOT, "qml", "VJoySelector.qml"))
component = QtQml.QQmlComponent(app.engine, url)
obj = component.createWithInitialProperties({"validTypes": ["button"]})
if obj is None:
    print("NOT CREATED " + component.errorString(), flush=True)
    os._exit(0)
QtTest.QTest.qWait(200)
QtCore.QMetaObject.invokeMethod(
    obj, "initialize", QtCore.Q_ARG("QVariant", 3),
    QtCore.Q_ARG("QVariant", "button"), QtCore.Q_ARG("QVariant", 40))
QtTest.QTest.qWait(100)
picker = obj.findChildren(output_modules.OutputModuleDevices)[0]
combos = [c for c in obj.findChildren(QtCore.QObject)
          if c.metaObject().indexOfSignal("activated(int)") >= 0
          and c.property("currentText") is not None]
device = combos[0]
print("BEFORE", device.property("currentText"),
      picker._current_selection.vjoy_id, flush=True)
device.setProperty("currentIndex", picker.vjoyDevices.index("vJoy 4"))
# What the device box's onActivated runs.
QtCore.QMetaObject.invokeMethod(obj, "updateState")
QtTest.QTest.qWait(100)
sel = picker._current_selection
print("AFTER", device.property("currentText"), sel.vjoy_id,
      sel.input_type.name, sel.input_id, combos[1].property("currentText"), flush=True)
os._exit(0)
"""


def test_vjoy_selector_device_box_moves_the_binding(tmp_path: pathlib.Path) -> None:
    """Off-screen: the real VJoySelector's device box switched to vJoy 4."""
    root = pathlib.Path(__file__).parents[2]
    home = tmp_path / "home"
    (home / "Gremlin Platforms").mkdir(parents=True)
    env = dict(
        os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen",
        HTTPS_PROXY="http://127.0.0.1:9",
    )
    done = proc_tree.run(
        [sys.executable, "-c", _QML_CODE, str(root)],
        cwd=root, env=env, text=True, timeout=120,
    )
    after = [ln for ln in done.stdout.splitlines() if ln.startswith("AFTER")]
    assert after, smoke_report.explain(done)
    assert after[0] == "AFTER vJoy 4 4 JoystickButton 1 Button 1"
