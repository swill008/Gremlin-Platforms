# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Catalog rows name what an action really does, new logical inputs get a
readable name when theirs is taken, and the dual deadzone takes the nearest
allowed value instead of ignoring an edit."""

from __future__ import annotations

import sys

sys.path.append(".")

import types

from gremlin.logical_device import LogicalDevice
from gremlin.types import InputType
from gremlin.ui.binding_catalog import summarize_action


def _act(tag: str, **fields: object) -> types.SimpleNamespace:
    return types.SimpleNamespace(tag=tag, **fields)


def test_catalog_names_the_file_or_program() -> None:
    assert summarize_action(
        _act("load-profile", profile_filename=r"C:\p\Flight.xml")
    )[1] == "Flight.xml"
    assert summarize_action(
        _act("run-command", executable="C:/tools/obs.exe")
    )[1] == "obs.exe"
    assert summarize_action(
        _act("play-sound", sound_filename="D:/s/gear.wav")
    )[1] == "gear.wav"
    assert summarize_action(_act("play-sound", sound_filename=""))[1] == "Sound"


def test_catalog_motion_mouse_is_not_a_button() -> None:
    motion = types.SimpleNamespace(name="Motion")
    button = types.SimpleNamespace(name="Button")
    left = types.SimpleNamespace(name="Left")
    mouse = "map-to-mouse"
    assert summarize_action(_act(mouse, mode=motion, button=left))[1] == "Motion"
    assert summarize_action(_act(mouse, mode=button, button=left))[1] == "Left"


def test_taken_default_label_gets_a_number_not_a_timestamp() -> None:
    dev = LogicalDevice()
    first = dev.create(InputType.JoystickAxis)
    dev.set_label(first.label, "Axis 2")  # A rename takes the next default.
    second = dev.create(InputType.JoystickAxis)
    assert second.label == "Axis 2 (2)"
    third = dev.create(InputType.JoystickAxis, label=None)
    assert third.label == "Axis 3"


def test_dual_deadzone_takes_the_nearest_allowed_value() -> None:
    from action_plugins.dual_axis_deadzone import DualAxisDeadzoneModel

    data = types.SimpleNamespace(inner_deadzone=0.2, outer_deadzone=0.8)
    changed = types.SimpleNamespace(emit=lambda: None)
    model = types.SimpleNamespace(_data=data, modelChanged=changed)
    inner = DualAxisDeadzoneModel.innerDeadzone.fset
    outer = DualAxisDeadzoneModel.outerDeadzone.fset
    inner(model, 0.85)  # Past outer: stops just below it.
    assert data.inner_deadzone == 0.79
    outer(model, 0.5)  # Below inner: stops just above it.
    assert data.outer_deadzone == 0.8
    inner(model, 0.3)
    assert data.inner_deadzone == 0.3

