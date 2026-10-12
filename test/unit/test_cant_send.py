# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Bindings the program can't send (D-05-CANT-SEND, 03 S30): the tooltip
text, the profile-wide list, and the Map to vJoy picker's red ⚠ control."""

from __future__ import annotations

import os
import pathlib
import sys
import uuid
from types import SimpleNamespace

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

from gremlin import device_initialization, event_handler, macro
from gremlin.modules import output
from gremlin.types import InputType
from gremlin.ui import output_modules

B = InputType.JoystickButton
A = InputType.JoystickAxis
H = InputType.JoystickHat
_STICK = uuid.UUID("{31111111-2222-3333-4444-555555555555}")


@pytest.fixture
def vjoy(monkeypatch: pytest.MonkeyPatch) -> dict:
    """vJoy 1 (64 buttons, axes 1-8, no hats) and vJoy 4 in the driver;
    claims per vJoy number in state["claims"]; state["on"] the vJoys the
    driver lists."""
    state: dict = {"claims": {}, "on": {1, 4}}

    def devices() -> list[SimpleNamespace]:
        return [
            SimpleNamespace(vjoy_id=v, axis_map=[], button_count=64, hat_count=0)
            for v in sorted(state["on"])
        ]

    monkeypatch.setattr(device_initialization, "vjoy_devices", devices)
    monkeypatch.setattr(device_initialization, "output_vjoy_devices", devices)
    monkeypatch.setattr(
        output,
        "vjoy_layout",
        lambda vid: (8, 64, 0) if int(vid) in state["on"] else (0, 0, 0),
    )
    monkeypatch.setattr(
        output,
        "vjoy_axis_ids",
        lambda vid: set(range(1, 9)) if int(vid) in state["on"] else set(),
    )
    monkeypatch.setattr(output, "_refresh_claims", lambda force=False: None)
    monkeypatch.setattr(output, "_vjoy_claims", state["claims"])
    monkeypatch.setattr(output, "_vjoy_off", set())
    return state


# --- cant_send_text ---------------------------------------------------------


def test_sendable_binding_has_no_text(vjoy: dict) -> None:
    vjoy["claims"][1] = {"buttons": [1, 2, 3]}
    assert output.cant_send_text(1, "button", 2) is None
    assert output.cant_send_text(1, B, 3) is None


def test_not_in_module_lists_the_ranges_with_gaps(vjoy: dict) -> None:
    buttons = [*range(1, 21), 25, *range(30, 57)]
    vjoy["claims"][1] = {"buttons": buttons}
    assert output.cant_send_text(1, "button", 57) == (
        "vJoy 1's Button 57 is not Found (vJoy 1 has Buttons 1–20, 25, 30–56)."
    )


def test_ranges_come_from_the_drop_down_list(vjoy: dict) -> None:
    # Claimed past the driver's 64 buttons: the drop-down (and text) stop at 64.
    vjoy["claims"][1] = {"buttons": [*range(60, 70)]}
    assert output.cant_send_text(1, "button", 66) == (
        "vJoy 1's Button 66 is not Found (vJoy 1 has Buttons 60–64)."
    )


def test_kind_with_none_says_has_no(vjoy: dict) -> None:
    vjoy["claims"][1] = {"buttons": [1]}
    assert output.cant_send_text(1, "hat", 1) == (
        "vJoy 1's Hat 1 is not Found (vJoy 1 has no Hats)."
    )


def test_axis_uses_the_drop_down_word(vjoy: dict) -> None:
    vjoy["claims"][1] = {"axes": [1, 2]}
    assert output.cant_send_text(1, A, 7) == (
        "vJoy 1's Slider is not Found (vJoy 1 has Axes 1–2)."
    )


def test_vjoy_turned_off_says_not_found(vjoy: dict) -> None:
    vjoy["claims"][4] = {"buttons": [1, 2]}
    vjoy["on"] = {1}
    assert output.cant_send_text(4, "button", 1) == "vJoy 4 is not Found."


# --- cant_send_bindings -----------------------------------------------------


def _item(mode: str, input_id: int, root: object) -> SimpleNamespace:
    return SimpleNamespace(
        device_id=_STICK,
        input_type=B,
        input_id=input_id,
        mode=mode,
        action_sequences=[SimpleNamespace(root_action=root)],
    )


def _map(vjoy_id: int, input_type: InputType, input_id: int) -> object:
    from action_plugins.map_to_vjoy import MapToVjoyData

    action = MapToVjoyData(input_type)
    action.vjoy_device_id = vjoy_id
    action.vjoy_input_type = input_type
    action.vjoy_input_id = input_id
    return action


def test_cant_send_bindings_finds_nested_actions(
    vjoy: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    from action_plugins.chain import ChainData
    from action_plugins.macro import MacroData

    monkeypatch.setattr(device_initialization, "device_name", lambda guid: "Stick")
    vjoy["claims"][1] = {"buttons": [1, 2]}
    chain = ChainData(B)
    chain.chain_sequences = [[_map(1, B, 2)], [_map(1, B, 9)]]
    macro_data = MacroData()
    macro_data.actions = [macro.VJoyAction(1, B, 5, True)]
    profile = SimpleNamespace(
        inputs={
            _STICK: [
                _item("Default", 3, chain),
                _item("Flight", 4, macro_data),
                _item("Default", 5, _map(1, B, 1)),
            ]
        }
    )

    found = output.cant_send_bindings(profile)

    assert [(f["input_id"], f["mode"], f["text"]) for f in found] == [
        (3, "Default", "vJoy 1's Button 9 is not Found (vJoy 1 has Buttons 1–2)."),
        (4, "Flight", "vJoy 1's Button 5 is not Found (vJoy 1 has Buttons 1–2)."),
    ]
    assert found[0]["device_guid"] == str(_STICK)
    assert found[0]["device_name"] == "Stick"
    assert found[0]["input_type"] == "button"
    assert found[0]["input_label"] == "Button 3"


def test_cant_send_bindings_with_no_profile_is_empty(
    vjoy: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin import shared_state

    monkeypatch.setattr(shared_state, "current_profile", None)
    assert output.cant_send_bindings() == []


# --- the Map to vJoy picker -------------------------------------------------


_MODULES = [
    {
        "name": "vJoy 3",
        "vjoy_id": 3,
        "claim": {"axes": [1, 2, 3], "buttons": list(range(1, 57)), "hats": []},
        "available": True,
    },
    {
        "name": "vJoy 4",
        "vjoy_id": 4,
        "claim": {"axes": [], "buttons": [1, 2], "hats": []},
        "available": False,
    },
]


@pytest.fixture
def picker(monkeypatch: pytest.MonkeyPatch) -> output_modules.OutputModuleDevices:
    from unittest import mock

    monkeypatch.setattr(output_modules, "_dest_modules", lambda: _MODULES)
    with mock.patch.object(event_handler, "EventListener"):
        devices = output_modules.OutputModuleDevices()
        devices.validTypes = ["button"]
        yield devices


def test_picker_flags_a_control_not_in_the_module(
    picker: output_modules.OutputModuleDevices,
) -> None:
    picker.setInitialState(3, "button", 57)
    assert picker.currentUnclaimed
    assert "⚠ Button 57" in picker.inputChoices
    assert picker.currentReason == (
        "vJoy 3's Button 57 is not Found (vJoy 3 has Buttons 1–56)."
    )
    assert not any("(not claimed)" in label for label in picker.inputChoices)


def test_picker_flags_a_vjoy_that_is_off(
    picker: output_modules.OutputModuleDevices,
) -> None:
    picker.setInitialState(4, "button", 2)
    assert picker.currentUnclaimed
    assert picker.currentReason == "vJoy 4 is not Found."
    # Its listed control shows once, flagged; no "(not available)".
    assert picker.inputChoices == ["Button 1", "⚠ Button 2"]


def test_picker_sendable_has_no_reason(
    picker: output_modules.OutputModuleDevices,
) -> None:
    picker.setInitialState(3, "button", 5)
    assert not picker.currentUnclaimed
    assert picker.currentReason == ""
    assert not any(label.startswith("⚠") for label in picker.inputChoices)


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
    {"name": "vJoy 3", "vjoy_id": 3, "available": True,
     "claim": {"axes": [1, 2, 3], "buttons": list(range(1, 57)), "hats": []}},
]
output_modules._dest_modules = lambda: MODULES
import joystick_gremlin
from PySide6 import QtCore, QtGui, QtQml, QtTest
sys.path.insert(0, os.path.join(ROOT, "test"))
from qt_wait import wait_until
app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
QtTest.QTest.qWait(300)
url = QtCore.QUrl.fromLocalFile(os.path.join(ROOT, "qml", "VJoySelector.qml"))
component = QtQml.QQmlComponent(app.engine, url)
obj = component.createWithInitialProperties({"validTypes": ["button"]})
if obj is None:
    print("NOT CREATED " + component.errorString(), flush=True)
    os._exit(0)
QtTest.QTest.qWait(200)
for target in (57, 5):
    QtCore.QMetaObject.invokeMethod(
        obj, "initialize", QtCore.Q_ARG("QVariant", 3),
        QtCore.Q_ARG("QVariant", "button"), QtCore.Q_ARG("QVariant", target))
    wait_until(lambda: bool(obj.property("cantSend")) == (target == 57),
               f"Button {target}'s can't-send state", fail=False)
    combos = [c for c in obj.findChildren(QtCore.QObject)
              if c.metaObject().indexOfSignal("activated(int)") >= 0
              and c.property("currentText") is not None]
    box = combos[1]
    color = QtGui.QColor(box.property("contentItem").property("color")).name()
    print(f"T{target}|{box.property('currentText')}|{color}|"
          f"{obj.property('cantSend')}|{obj.property('cantSendText')}|"
          f"{box.property('enableTooltips')}", flush=True)
os._exit(0)
"""


def test_vjoy_selector_shows_red_warning_and_tooltip(tmp_path: pathlib.Path) -> None:
    """Off-screen: the real VJoySelector shows "⚠ Button 57" in red with
    the can't-be-sent tooltip, and plain again for a sendable control."""
    root = pathlib.Path(__file__).parents[2]
    home = tmp_path / "home"
    (home / "Gremlin Platforms").mkdir(parents=True)
    env = dict(
        os.environ,
        USERPROFILE=str(home),
        QT_QPA_PLATFORM="offscreen",
        HTTPS_PROXY="http://127.0.0.1:9",
        PYTHONIOENCODING="utf-8",
    )
    done = proc_tree.run(
        [sys.executable, "-c", _QML_CODE, str(root)],
        cwd=root,
        env=env,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    lines = {
        ln.split("|", 1)[0]: ln.split("|")[1:]
        for ln in done.stdout.splitlines()
        if ln.startswith("T")
    }
    assert "T57" in lines, smoke_report.explain(done)
    text, color, cant, tip, tooltips = lines["T57"]
    assert text == "⚠ Button 57"
    assert color == "#dc2626"  # Style.danger
    assert cant == "True"
    assert tip == "vJoy 3's Button 57 is not Found (vJoy 3 has Buttons 1–56)."
    assert tooltips == "False"  # the box's own tooltip gives way to the reason
    text, color, cant, tip, tooltips = lines["T5"]
    assert text == "Button 5"
    assert color != "#dc2626"
    assert (cant, tip, tooltips) == ("False", "", "True")
