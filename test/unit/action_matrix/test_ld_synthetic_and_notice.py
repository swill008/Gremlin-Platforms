# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Map to Logical Device: the input events it sends are program-made
(synthetic), so they never move the Logical Device page (05 S131, to-do 94);
its editor's ⚠ follows the output layer's can't-be-sent notice
(05 S137, D-05-CANT-SEND-LIVE, to-do 93)."""

from __future__ import annotations

from typing import Any
from unittest import mock

import pytest

from gremlin.base_classes import Value
from gremlin.event_handler import Event
from gremlin.logical_device import LogicalDevice
from gremlin.types import ActionProperty, AxisMode, InputType
from gremlin.ui import live_follow
from test.unit.action_matrix.harness import (  # pyright: ignore[reportMissingImports]
    Surface,
    settle,
)

TAG = "map-to-logical-device"


def _functor(kind: InputType, mode: AxisMode = AxisMode.Absolute) -> Any:  # noqa: ANN401
    from action_plugins.map_to_logical_device import (
        MapToLogicalDeviceData,
        MapToLogicalDeviceFunctor,
    )

    LogicalDevice().create(kind)
    data = MapToLogicalDeviceData(kind)
    data.axis_mode = mode
    functor = MapToLogicalDeviceFunctor(data)
    functor._event_listener = mock.MagicMock()  # noqa: SLF001
    return functor


@pytest.fixture
def logical() -> Any:  # noqa: ANN401
    LogicalDevice().reset()
    yield LogicalDevice()
    LogicalDevice().reset()


@pytest.mark.parametrize(
    ("kind", "value"),
    [
        (InputType.JoystickButton, True),
        (InputType.JoystickHat, (1, 0)),
        (InputType.JoystickAxis, 0.5),
    ],
)
def test_sent_events_are_synthetic_and_never_move_the_page(
    logical: Any,  # noqa: ANN401
    kind: InputType,
    value: Any,  # noqa: ANN401
) -> None:
    functor = _functor(kind)
    emit = functor._event_listener.joystick_event.emit  # noqa: SLF001
    event = Event(kind, 1, logical.device_guid, "Default", value=value)
    with mock.patch("action_plugins.map_to_logical_device.mode_manager.ModeManager"):
        # No auto-release registered: it would outlive the test.
        functor(event, Value(value), [ActionProperty.DisableAutoRelease])
    sent = emit.call_args.args[0]
    assert sent.synthetic is True
    # The Logical Device page's follow check, with following allowed:
    # a press from a real input would move it, this one never does.
    with mock.patch.object(live_follow, "may_follow", return_value=True):
        assert live_follow.follows("button", 1.0, 0.0, False)
        assert not live_follow.follows("button", 1.0, 0.0, sent.synthetic)


def test_relative_axis_events_are_synthetic(logical: Any) -> None:  # noqa: ANN401
    functor = _functor(InputType.JoystickAxis, AxisMode.Relative)
    emit = functor._event_listener.joystick_event.emit  # noqa: SLF001
    with mock.patch("action_plugins.map_to_logical_device.mode_manager.ModeManager"):
        assert functor._relative_write(0.25)  # noqa: SLF001
    assert emit.call_args.args[0].synthetic is True


# The deleted control is the point: a missing reference on purpose.
@pytest.mark.validate_off
def test_editor_warning_follows_the_cant_send_notice(matrix: Any) -> None:  # noqa: ANN401
    """The control is deleted without a Logical Device notice; the output
    layer's cantSendChanged alone updates the editor's ⚠."""
    from gremlin.signal import signal

    logical = LogicalDevice()
    logical.create(InputType.JoystickButton)
    case = matrix.open(TAG, "button", Surface.CONFIG_PAGE)
    picker = case.model().controlPicker
    data = case.model().map_data()
    target = next(
        c for c in logical.inputs_of_type([InputType.JoystickButton])
        if c.id == data.logical_input_id
    )
    assert picker.cantSendText == ""
    seen: list[str] = []
    picker.changed.connect(lambda: seen.append(picker.cantSendText))
    logical.delete(target.identifier)
    settle()
    assert seen == []
    signal.cantSendChanged.emit()
    settle()
    assert seen
    assert seen[-1] == f"Logical Device Button {target.id} is not Found."
