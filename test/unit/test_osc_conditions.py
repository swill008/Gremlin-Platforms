# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""09 S159 / 02 S41: conditions (and scripts) read OSC inputs like stick
inputs, by the input's permanent id."""

from __future__ import annotations

import inspect
from collections.abc import Iterator
from types import SimpleNamespace
from xml.etree import ElementTree

import pytest

from action_plugins.condition import condition as cond_mod
from gremlin import input_cache, osc
from gremlin.base_classes import Value
from gremlin.input_cache import Joystick
from gremlin.modules import inputs
from gremlin.osc import OSC_DEVICE_UUID, OscDevice
from gremlin.types import InputType

AXIS = InputType.JoystickAxis
BUTTON = InputType.JoystickButton


def osc_state() -> input_cache.OscState:
    return input_cache.osc_state()


@pytest.fixture
def rows(qapp: object) -> Iterator[object]:
    rows = OscDevice().rows
    saved = rows.to_dict()
    rows.reset()
    osc_state().clear()
    yield rows
    osc_state().clear()
    rows.load_dict(saved)


def _button_condition(uid: str) -> cond_mod.JoystickCondition:
    cond = cond_mod.JoystickCondition()
    cond.setOscInput(uid)
    return cond


def test_joystick_cache_answers_for_osc(rows: object) -> None:
    btn = rows.create(BUTTON, "/btn")
    fader = rows.create(AXIS, "/fader")
    dev = Joystick()[OSC_DEVICE_UUID]
    assert dev.name == "OSC"
    assert dev.button(btn.input_id).is_pressed is False
    osc_state().set_button(btn.uid, True)
    osc_state().set_axis(fader.uid, 0.25)
    assert dev.button(btn.input_id).is_pressed is True
    assert dev.axis(fader.input_id).value == 0.25
    with pytest.raises(TypeError):
        osc_state().set_button(btn.input_id, True)  # type: ignore[arg-type]
    osc_state().clear()
    assert dev.button(btn.input_id).is_pressed is False


def test_condition_on_osc_button_true_while_held(rows: object) -> None:
    btn = rows.create(BUTTON, "/btn")
    cond = _button_condition(btn.uid)
    assert cond._states[0].osc_uid == btn.uid
    assert cond.states == ["OSC - /btn"]
    assert cond(Value(True)) is False
    osc_state().set_button(btn.uid, True)
    assert cond(Value(True)) is True
    osc_state().set_button(btn.uid, False)
    assert cond(Value(True)) is False


def test_condition_on_osc_axis(rows: object) -> None:
    fader = rows.create(AXIS, "/fader")
    cond = cond_mod.JoystickCondition()
    cond.setOscInput(fader.uid)
    assert isinstance(cond._comparator, cond_mod.RangeComparator)
    osc_state().set_axis(fader.uid, 0.5)
    assert cond._states[0].get(Value(0.0)) == 0.5


def test_renumbered_osc_input_keeps_its_condition(rows: object) -> None:
    btn = rows.create(BUTTON, "/btn")
    uid = btn.uid
    cond = _button_condition(uid)
    node = cond.to_xml()
    assert uid in ElementTree.tostring(node, encoding="unicode")
    # OSC's file now numbers the same input 5 (another input took 1).
    rows.delete(uid)
    rows.create(BUTTON, "/other", input_id=1)
    rows.create(BUTTON, "/btn", uid=uid, input_id=5)
    loaded = cond_mod.JoystickCondition()
    loaded.from_xml(node)
    assert loaded._states[0].input_id == 5
    assert loaded._states[0].osc_uid == uid
    osc_state().set_button(uid, True)
    assert loaded(Value(True)) is True
    # The one already open follows the new number too.
    assert cond(Value(True)) is True


def test_picker_lists_osc_inputs_by_address(rows: object) -> None:
    rows.create(BUTTON, "/b/press")
    rows.create(AXIS, "/a/fader")
    listed = cond_mod.JoystickCondition().oscInputs
    assert [item["text"] for item in listed] == [
        "/a/fader (Axis)",
        "/b/press (Button)",
    ]
    assert all(item["uid"] for item in listed)


def test_scripts_read_osc_without_osc_code(rows: object) -> None:
    btn = rows.create(BUTTON, "/btn")
    joy = inputs.ScriptJoystick()
    assert joy[OSC_DEVICE_UUID].button(btn.input_id).is_pressed is False
    osc_state().set_button(btn.uid, True)
    assert joy[OSC_DEVICE_UUID].button(btn.input_id).is_pressed is True
    assert joy[OSC_DEVICE_UUID].name == "OSC"


@pytest.mark.skipif(
    "osc_state" not in inspect.getsource(osc),
    reason="the OSC runtime does not write osc_state yet (RT3)",
)
def test_runtime_message_reaches_the_condition(
    rows: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin import osc_device_file as odf
    from gremlin import shared_state

    class FakeListener:
        def __init__(self, *args: object) -> None:
            pass

        def start(self) -> None:
            pass

        def stop(self) -> None:
            pass

    monkeypatch.setattr(odf, "read_server", lambda: {"host": "127.0.0.1"})
    monkeypatch.setattr(osc, "OscListener", FakeListener)
    monkeypatch.setattr(
        shared_state,
        "current_profile",
        SimpleNamespace(inputs={OSC_DEVICE_UUID: [object()]}),
    )
    btn = rows.create(BUTTON, "/btn")
    cond = _button_condition(btn.uid)
    runtime = osc.OscRuntime()
    runtime.start()
    try:
        runtime._on_main("/btn", (1.0,), None)
        assert cond(Value(True)) is True
        runtime._on_main("/btn", (0.0,), None)
        assert cond(Value(True)) is False
    finally:
        runtime.stop()
