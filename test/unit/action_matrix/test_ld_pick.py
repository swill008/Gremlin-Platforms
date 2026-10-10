# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Map to Logical Device never targets the control it sits on (06 S92, S93)
and its emits go through the loop guard (06 S94, gremlin.logical_loop)."""

from __future__ import annotations

import sys
import types
from collections.abc import Iterator
from typing import Any
from unittest import mock

import pytest

from gremlin.base_classes import Value
from gremlin.event_handler import Event
from gremlin.logical_device import LogicalDevice
from gremlin.types import ActionProperty, AxisMode, InputType
from test.unit.action_matrix.harness import (  # pyright: ignore[reportMissingImports]
    Surface,
    settle,
)

TAG = "map-to-logical-device"
KINDS = {
    "axis": InputType.JoystickAxis,
    "button": InputType.JoystickButton,
    "hat": InputType.JoystickHat,
}


def _target(case: Any) -> tuple:  # noqa: ANN401
    value = case.model().logicalInputIdentifier
    return (value.input_type, value.input_id)


@pytest.mark.parametrize("kind", sorted(KINDS))
def test_new_action_on_the_only_control_gets_a_new_control(
    matrix: Any,  # noqa: ANN401
    kind: str,
) -> None:
    """06 S92: Add Action on Logical axis/button/hat 1 (the only one of its
    type) drives a newly made control, not itself."""
    case = matrix.open(TAG, kind, Surface.PANE_LOGICAL)
    own = (case.key[1], case.key[2])
    assert _target(case) != own
    controls = LogicalDevice().inputs_of_type([KINDS[kind]])
    assert len(controls) == 2
    assert _target(case) in {(c.type, c.id) for c in controls}


@pytest.mark.parametrize("kind", sorted(KINDS))
def test_picker_leaves_out_the_own_control(
    matrix: Any,  # noqa: ANN401
    kind: str,
) -> None:
    """06 S93: the control picker never offers the control the action sits on."""
    logical = LogicalDevice()
    case = matrix.open(TAG, kind, Surface.PANE_LOGICAL)
    logical.create(KINDS[kind])
    settle()
    own = _control(case.key[1], case.key[2])
    picker = case.model().controlPicker
    choices = picker.choices
    assert own.choice_label not in choices
    assert len(choices) == len(logical.inputs_of_type([KINDS[kind]])) - 1
    # The current pick is shown, and choosing a row sets that control.
    assert choices[picker.index] == _control(*_target(case)).choice_label
    picker.pick(len(choices) - 1)
    settle()
    assert _target(case) != (own.type, own.id)
    assert _control(*_target(case)).choice_label == choices[-1]


@pytest.mark.parametrize("kind", sorted(KINDS))
def test_loaded_self_target_shows_selected_and_marked(
    matrix: Any,  # noqa: ANN401
    kind: str,
) -> None:
    """06 S96 (AD10): an action loaded with its own control as the target
    shows that control selected, marked as blocked by the loop guard; once
    another control is picked, its own control isn't offered again (S93)."""
    logical = LogicalDevice()
    case = matrix.open(TAG, kind, Surface.PANE_LOGICAL)
    own = _control(case.key[1], case.key[2])
    # As loaded from a file (from_xml keeps a self-target, see below).
    case.model().map_data().logical_input_id = own.id
    picker = case.model().controlPicker
    picker.refresh()
    settle()
    choices = picker.choices
    marked = f"{own.choice_label} (this control: blocked by the loop guard)"
    assert picker.index >= 0
    assert choices[picker.index] == marked
    assert len(choices) == len(logical.inputs_of_type([KINDS[kind]]))
    # Choosing the marked row changes nothing.
    picker.pick(picker.index)
    settle()
    assert _target(case) == (own.type, own.id)
    # Picking another control drops the own row from the list.
    other = next(i for i, text in enumerate(choices) if text != marked)
    picker.pick(other)
    settle()
    assert _target(case) != (own.type, own.id)
    assert marked not in picker.choices
    assert own.choice_label not in picker.choices


def test_a_logical_device_change_is_not_an_action_edit(
    matrix: Any,  # noqa: ANN401
) -> None:
    """The picker follows Logical Device changes without telling the program
    the action was edited (ActionModel reports property notifies as edits)."""
    from gremlin.signal import signal

    case = matrix.open(TAG, "button", Surface.PANE_LOGICAL)
    picker = case.model().controlPicker
    refreshed: list[int] = []
    edits: list[int] = []
    picker.changed.connect(lambda: refreshed.append(1))

    def edit() -> None:
        edits.append(1)

    signal.actionsChanged.connect(edit)
    try:
        LogicalDevice().create(InputType.JoystickButton)
        signal.logicalDeviceModified.emit()
        settle()
    finally:
        signal.actionsChanged.disconnect(edit)
    assert refreshed
    assert edits == []


def test_other_pages_keep_the_first_control(matrix: Any) -> None:  # noqa: ANN401
    """Off the Logical Device page the default stays the first control of the
    type (S92 is about the Logical Device's own controls only)."""
    logical = LogicalDevice()
    first = logical.create(InputType.JoystickButton)
    logical.create(InputType.JoystickButton)
    case = matrix.open(TAG, "button", Surface.CONFIG_PAGE)
    assert _target(case) == (first.type, first.id)
    assert len(case.model().controlPicker.choices) == 2


def _control(kind: InputType, input_id: int) -> Any:  # noqa: ANN401
    return next(c for c in LogicalDevice().inputs_of_type([kind]) if c.id == input_id)


class _Item:
    def __init__(self, device_id: Any, kind: InputType, input_id: int) -> None:  # noqa: ANN401
        self.device_id = device_id
        self.input_type = kind
        self.input_id = input_id


def test_start_new_moves_to_the_first_other_control() -> None:
    """06 S92: own control is the first of its type, another exists: the
    new action starts on that other one, and nothing new is made."""
    from action_plugins.map_to_logical_device import MapToLogicalDeviceData

    logical = LogicalDevice()
    logical.reset()
    own = logical.create(InputType.JoystickAxis)
    other = logical.create(InputType.JoystickAxis)
    data = MapToLogicalDeviceData(InputType.JoystickAxis)
    assert data.logical_input_id == own.id
    data.start_new(None, _Item(logical.device_guid, own.type, own.id))
    assert data.logical_input_id == other.id
    assert len(logical.inputs_of_type([InputType.JoystickAxis])) == 2
    # Another device's input: unchanged.
    fresh = MapToLogicalDeviceData(InputType.JoystickAxis)
    fresh.start_new(None, _Item(object(), own.type, own.id))
    assert fresh.logical_input_id == own.id
    logical.reset()


def test_loading_keeps_a_saved_self_target() -> None:
    """Never on load: a saved action on its own control loads unchanged."""
    from action_plugins.map_to_logical_device import MapToLogicalDeviceData

    logical = LogicalDevice()
    logical.reset()
    logical.create(InputType.JoystickButton)
    own = logical.create(InputType.JoystickButton)
    data = MapToLogicalDeviceData(InputType.JoystickButton)
    data.logical_input_id = own.id
    fresh = MapToLogicalDeviceData(InputType.JoystickButton)
    fresh.from_xml(data.to_xml(), mock.MagicMock())
    assert fresh.logical_input_id == own.id
    logical.reset()


# +-------------------------------------------------------------------------
# | Loop guard call sites (06 S94)


@pytest.fixture
def guard() -> Iterator[list]:
    """A stand-in gremlin.logical_loop recording calls; allow[0] decides."""
    calls: list = []
    chains: list = []
    allow = [True]

    def guarded(key: tuple, label: str, send: Any, chain: Any = ()) -> bool:  # noqa: ANN401
        calls.append((key, label))
        chains.append(chain)
        if allow[0]:
            send(tuple(chain) + ((key, label),))
        return allow[0]

    fake = types.ModuleType("gremlin.logical_loop")
    fake.guarded = guarded  # type: ignore[attr-defined]
    fake.MAX_HOPS = 8  # type: ignore[attr-defined]
    import gremlin

    with (
        mock.patch.dict(sys.modules, {"gremlin.logical_loop": fake}),
        mock.patch.object(gremlin, "logical_loop", fake, create=True),
    ):
        LogicalDevice().reset()
        yield [calls, allow, chains]
        LogicalDevice().reset()


def _functor(kind: InputType, mode: AxisMode = AxisMode.Absolute) -> Any:  # noqa: ANN401
    from action_plugins.map_to_logical_device import (
        MapToLogicalDeviceData,
        MapToLogicalDeviceFunctor,
    )

    control = LogicalDevice().create(kind)
    data = MapToLogicalDeviceData(kind)
    data.axis_mode = mode
    functor = MapToLogicalDeviceFunctor(data)
    functor._event_listener = mock.MagicMock()  # noqa: SLF001
    return functor, control


@pytest.mark.parametrize(
    ("kind", "value"),
    [
        (InputType.JoystickAxis, 0.5),
        (InputType.JoystickButton, True),
        (InputType.JoystickHat, (1, 0)),
    ],
)
def test_emit_goes_through_the_guard(guard: list, kind: InputType, value: Any) -> None:  # noqa: ANN401
    calls, allow, chains = guard
    functor, control = _functor(kind)
    emit = functor._event_listener.joystick_event.emit  # noqa: SLF001
    # No auto-release registered: it would outlive the test.
    no_release = [ActionProperty.DisableAutoRelease]
    came = (((kind, 1), "Earlier"),)
    with mock.patch("action_plugins.map_to_logical_device.mode_manager.ModeManager"):
        event = Event(
            kind, 1, LogicalDevice().device_guid, "Default", value=value,
            ld_chain=came,
        )
        functor(event, Value(value), no_release)
        own = ((control.type, control.id), control.choice_label)
        assert calls == [own]
        # The guard continues the event's chain; the sent event carries it
        # with this control added (06 S94a).
        assert chains == [came]
        assert emit.call_args.args[0].ld_chain == came + (own,)
        assert emit.call_count == 1
        allow[0] = False
        functor(event, Value(value), no_release)
        assert emit.call_count == 1  # dropped by the guard


def test_relative_write_goes_through_the_guard(guard: list) -> None:
    calls, allow, chains = guard
    functor, control = _functor(InputType.JoystickAxis, AxisMode.Relative)
    emit = functor._event_listener.joystick_event.emit  # noqa: SLF001
    came = (((InputType.JoystickButton, 3), "Button 3"),)
    with mock.patch("action_plugins.map_to_logical_device.mode_manager.ModeManager"):
        functor._relative_chain = came  # noqa: SLF001
        functor._relative_write(0.25)  # noqa: SLF001
        assert chains == [came]
        assert calls == [((control.type, control.id), control.choice_label)]
        assert emit.call_count == 1
        allow[0] = False
        assert not functor._relative_write(0.5)  # noqa: SLF001 - loop ends
        assert emit.call_count == 1
