# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

""""Can't be sent" covers every output action (D-05-CANT-SEND-ALL, 05
S137-S139, 03 S78a): Map to Xbox ("<pad> is not Found."), Map to Logical
Device ("Logical Device <Control> is not Found.") and Send OSC ("OSC target
<id> is not Found." / "OSC output is Off."), nested ones too. The texts go
through output.cant_send_action_texts to the profile list (Home card), the
page rows and Find tick (control_layout.input_scan), and each editor
shows the red ⚠ with the text as its tooltip."""

from __future__ import annotations

import os
import pathlib
import sys
import uuid
from collections.abc import Iterator
from types import SimpleNamespace

sys.path.append(".")

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

from gremlin import device_initialization, macro, shared_state
from gremlin.logical_device import LogicalDevice
from gremlin.modules import output
from gremlin.types import InputType

B = InputType.JoystickButton
_STICK = uuid.UUID("{31111111-2222-3333-4444-555555555555}")
_TARGET = "a1b2c3"


@pytest.fixture
def world(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict]:
    """Xbox driver state, the Xbox output modules and OSC's settings, all
    stand-ins; the Logical Device is the real shared one (conftest puts it
    back)."""
    state: dict = {
        "xbox": True,
        "pads": {},
        "server": {"output_enabled": True},
        "targets": [{"id": _TARGET, "name": "Sim", "host": "127.0.0.1", "port": 9}],
    }
    monkeypatch.setattr(output, "xbox_available", lambda: state["xbox"])
    monkeypatch.setattr(output, "xbox_modules", lambda: dict(state["pads"]))
    monkeypatch.setattr(
        output, "osc_settings", lambda: (state["server"], state["targets"])
    )
    monkeypatch.setattr(device_initialization, "device_name", lambda guid: "Stick")
    yield state


def _xbox(pad: int = 1) -> object:
    from action_plugins.map_to_xbox import MapToXboxData

    action = MapToXboxData(B)
    action.xbox_device_id = pad
    return action


def _osc(target: str = _TARGET) -> object:
    from action_plugins.send_osc import SendOscData

    action = SendOscData(B)
    action.target = target
    return action


def _logical() -> tuple[object, LogicalDevice.Input]:
    from action_plugins.map_to_logical_device import MapToLogicalDeviceData

    control = LogicalDevice().create(B)
    action = MapToLogicalDeviceData(B)
    action.logical_input_type = B
    action.logical_input_id = control.id
    return action, control


# --- the texts --------------------------------------------------------------


def test_xbox_driver_missing_names_the_pad(world: dict) -> None:
    assert output.cant_send_action_texts(_xbox(1)) == []
    world["xbox"] = False
    assert output.cant_send_action_texts(_xbox(1)) == [
        "Xbox 360 Controller is not Found."
    ]
    # The pad's output module name, as the editor lists it.
    world["pads"] = {1: SimpleNamespace(name="Cockpit Pad")}
    assert output.xbox_cant_send_text(1) == "Cockpit Pad is not Found."


def test_xbox_pad_outside_the_driver_is_not_found(world: dict) -> None:
    assert output.xbox_cant_send_text(5) == "Xbox 360 5 is not Found."
    world["pads"] = {2: SimpleNamespace(name="Xbox 360 2")}
    assert output.xbox_cant_send_text(2) is None


def test_logical_device_control_deleted(world: dict) -> None:
    action, control = _logical()
    assert output.cant_send_action_texts(action) == []
    LogicalDevice().delete(control.identifier)
    assert output.cant_send_action_texts(action) == [
        f"Logical Device Button {control.id} is not Found."
    ]


def test_macro_logical_step_on_a_deleted_control(world: dict) -> None:
    from action_plugins.macro import MacroData

    control = LogicalDevice().create(B)
    data = MacroData()
    data.actions = [macro.LogicalDeviceAction(B, control.id, True)]
    assert output.cant_send_action_texts(data) == []
    LogicalDevice().delete(control.identifier)
    assert output.cant_send_action_texts(data) == [
        f"Logical Device Button {control.id} is not Found."
    ]


def test_osc_target_missing_and_output_off(world: dict) -> None:
    assert output.cant_send_action_texts(_osc()) == []
    assert output.cant_send_action_texts(_osc("gone")) == [
        "OSC target gone is not Found."
    ]
    world["server"]["output_enabled"] = False
    assert output.cant_send_action_texts(_osc()) == ["OSC output is Off."]
    # Reply to sender is never a missing target.
    world["server"]["output_enabled"] = True
    assert output.cant_send_action_texts(_osc("reply")) == []


# --- the profile list (Home card) and the rows (Find tick) ------------------


def _chain(*actions: object) -> object:
    from action_plugins.chain import ChainData

    chain = ChainData(B)
    chain.chain_sequences = [[a] for a in actions]
    return chain


def _item(input_id: int, root: object) -> SimpleNamespace:
    return SimpleNamespace(
        device_id=_STICK,
        input_type=B,
        input_id=input_id,
        mode="Default",
        action_sequences=[SimpleNamespace(root_action=root)],
    )


def _profile(world: dict) -> tuple[SimpleNamespace, list[str]]:
    world["xbox"] = False
    logical, control = _logical()
    LogicalDevice().delete(control.identifier)
    texts = [
        "Xbox 360 Controller is not Found.",
        f"Logical Device Button {control.id} is not Found.",
        "OSC target gone is not Found.",
    ]
    profile = SimpleNamespace(
        inputs={
            _STICK: [
                _item(1, _chain(_xbox(1))),
                _item(2, logical),
                _item(3, _chain(_osc("gone"))),
                _item(4, _osc()),
            ]
        }
    )
    return profile, texts


def test_profile_list_has_xbox_logical_and_osc_nested(world: dict) -> None:
    profile, texts = _profile(world)
    found = output.cant_send_bindings(profile)
    assert [(f["input_id"], f["text"]) for f in found] == [
        (1, texts[0]),
        (2, texts[1]),
        (3, texts[2]),
    ]


def test_home_card_counts_them(
    world: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.ui import module_model

    profile, texts = _profile(world)
    monkeypatch.setattr(shared_state, "current_profile", profile)
    row = SimpleNamespace(
        guid=str(_STICK), direction="source", cant_send_count=0, cant_send_tip=""
    )
    module_model.apply_cant_send([row])
    assert row.cant_send_count == 3
    assert module_model.cant_send_line(row.cant_send_count) == (
        "⚠ 3 binding outputs not found"
    )
    assert all(text in row.cant_send_tip for text in texts)


def test_rows_and_find_tick_show_them(world: dict) -> None:
    from gremlin.ui import control_layout

    profile, texts = _profile(world)
    items = profile.inputs[_STICK]
    assert [control_layout.input_scan(item).cant for item in items] == [
        {0: texts[0]},
        {0: texts[1]},
        {0: texts[2]},
        {},
    ]


# --- the editors (off-screen) -----------------------------------------------


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
from gremlin.modules import output
output.xbox_available = lambda: False
output.osc_settings = lambda: ({"output_enabled": True}, [])
import joystick_gremlin
from PySide6 import QtCore, QtGui, QtQml, QtTest
sys.path.insert(0, os.path.join(ROOT, "test"))
from qt_wait import wait_until
app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
QtTest.QTest.qWait(300)
from action_plugins.root import RootData
from gremlin import plugin_manager
from gremlin.logical_device import LogicalDevice
from gremlin.profile import InputItem, InputItemBinding, Profile
from gremlin.types import InputType
from gremlin.ui.profile import InputItemBindingModel
B = InputType.JoystickButton
profile = Profile()
item = InputItem(profile.library)
binding = InputItemBinding(item)
binding.root_action = RootData(B)
binding.behavior = B
profile.library.add_action(binding.root_action)
control = LogicalDevice().create(B)
made = {}
for name in ("Map to Xbox", "Map to Logical Device", "Send OSC"):
    action = plugin_manager.PluginManager().create_instance(name, B)
    profile.library.add_action(action)
    binding.root_action.insert_action(action, "children")
    made[action.tag] = action
made["map-to-logical-device"].logical_input_id = control.id
made["send-osc"].target = "gone"
LogicalDevice().delete(control.identifier)
model = InputItemBindingModel(binding)
CASES = [
    ("map-to-xbox", "MapToXboxAction.qml"),
    ("map-to-logical-device", "MapToLogicalDeviceAction.qml"),
    ("send-osc", "SendOscAction.qml"),
]
keep = []
for tag, qml in CASES:
    am = next(m for m in model._action_models.values() if m.action_data.tag == tag)
    url = QtCore.QUrl.fromLocalFile(os.path.join(ROOT, "action_plugins",
                                                 tag.replace("-", "_"), qml))
    component = QtQml.QQmlComponent(app.engine, url)
    obj = component.createWithInitialProperties({"action": am})
    if obj is None:
        print(f"E|{tag}|NOT CREATED {component.errorString()}", flush=True)
        continue
    keep.append(obj)

    def boxes(obj=obj):
        return [c for c in obj.findChildren(QtCore.QObject)
                if c.metaObject().indexOfSignal("activated(int)") >= 0
                and c.property("displayText") is not None]

    wait_until(lambda: boxes() and str(boxes()[0].property("displayText"))
               .startswith("⚠"), f"{tag}'s warning", fail=False)
    combos = boxes()
    box = combos[0]
    color = QtGui.QColor(box.property("contentItem").property("color")).name()
    tips = [t.property("text") for t in obj.findChildren(QtCore.QObject)
            if t.metaObject().className().startswith("WrappingTooltip")]
    tip = next((t for t in tips if "not Found" in (t or "")), "")
    print(f"E|{tag}|{box.property('displayText')}|{color}|{tip}", flush=True)
os._exit(0)
"""


def test_editors_show_red_warning_and_tooltip(tmp_path: pathlib.Path) -> None:
    """Off-screen: each real editor shows "⚠ <name>" in red (Style.danger)
    with the can't-be-sent text as the tooltip."""
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
        ln.split("|")[1]: ln.split("|")[2:]
        for ln in done.stdout.splitlines()
        if ln.startswith("E|")
    }
    assert set(lines) == {"map-to-xbox", "map-to-logical-device", "send-osc"}, (
        smoke_report.explain(done)
    )
    text, color, tip = lines["map-to-xbox"]
    assert (text, color, tip) == (
        "⚠ Xbox 360 Controller",
        "#dc2626",
        "Xbox 360 Controller is not Found.",
    ), smoke_report.explain(done)
    text, color, tip = lines["map-to-logical-device"]
    assert text.startswith("⚠ Button ") and color == "#dc2626", (
        smoke_report.explain(done)
    )
    assert tip.startswith("Logical Device Button ") and tip.endswith(" is not Found.")
    text, color, tip = lines["send-osc"]
    assert (text, color, tip) == (
        "⚠ Missing target",
        "#dc2626",
        "OSC target gone is not Found.",
    ), smoke_report.explain(done)
