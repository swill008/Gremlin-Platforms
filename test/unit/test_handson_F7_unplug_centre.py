# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Every action that reads an unplugged stick's axis reads it centred
(05 S105, 02 S28, decision D-05-UNPLUG-CENTRE); what the stick itself
reports keeps its last values, and reads follow the stick again once it is
plugged back in.

Hands-on finding (claude/hands-on-results/05-actions-editors.md): a Merge
Axis kept reading the unplugged stick's last value, because the shared read
(gremlin/modules/inputs.py) went straight to the input cache.
"""

from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace
from unittest import mock

import pytest

import dill
from gremlin import device_initialization, input_cache
from gremlin.modules import inputs


@pytest.fixture
def stick() -> Iterator[tuple[object, object]]:
    """The fake "pJoy Pro" (axes claimed) and a way to unplug / plug it."""
    fake = dill.DILL._dll
    device = next(d for d in fake.devices if d.name == b"pJoy Pro")
    guid = dill.GUID(device.device_guid).uuid

    def plugged(on: bool) -> None:
        # What the device thread does on a plug or unplug: a new device list.
        if on and device not in fake.devices:
            fake.devices.insert(0, device)
        elif not on and device in fake.devices:
            fake.devices.remove(device)
        device_initialization.joystick_devices_initialization()

    wrapper = input_cache.Joystick()[guid]
    kept = {aid: wrapper.axis(aid).value for aid in (1, 2)}
    with mock.patch.object(inputs, "_allows", return_value=True):
        try:
            yield guid, plugged
        finally:
            plugged(True)
            for aid, value in kept.items():
                wrapper.axis(aid).update(value)


def _merge_sum(guid: object) -> float:
    from action_plugins.merge_axis import MergeAxisFunctor, MergeOperation

    functor = MergeAxisFunctor.__new__(MergeAxisFunctor)
    functor.data = SimpleNamespace(
        axis_in1=SimpleNamespace(device_guid=guid, input_id=1),
        axis_in2=SimpleNamespace(device_guid=guid, input_id=2),
        operation=MergeOperation.Sum,
    )
    functor.functors = {"children": []}
    value = SimpleNamespace(current=None)
    functor(None, value)
    return value.current


def test_an_unplugged_sticks_axes_read_centred(stick: tuple) -> None:
    guid, plugged = stick
    wrapper = input_cache.Joystick()[guid]
    wrapper.axis(1).update(0.6)
    wrapper.axis(2).update(0.3)
    assert inputs.axis_value(guid, 1) == pytest.approx(0.6)
    assert _merge_sum(guid) == pytest.approx(0.9)

    plugged(False)

    assert inputs.axis_value(guid, 1) == 0.0
    assert inputs.axis_value(guid, 2) == 0.0
    assert _merge_sum(guid) == 0.0
    # The script "joy" object reads through the same place.
    assert inputs.ScriptJoystick()[guid].axis(1).value == 0.0
    # What the stick itself reports keeps its last values (02 S28).
    assert wrapper.axis(1).value == pytest.approx(0.6)


def test_reads_follow_the_stick_again_once_it_is_back(stick: tuple) -> None:
    guid, plugged = stick
    wrapper = input_cache.Joystick()[guid]
    wrapper.axis(1).update(0.6)
    plugged(False)
    assert inputs.axis_value(guid, 1) == 0.0

    plugged(True)

    assert inputs.axis_value(guid, 1) == pytest.approx(0.6)
    wrapper.axis(1).update(-0.4)  # the stick moves
    assert inputs.axis_value(guid, 1) == pytest.approx(-0.4)
