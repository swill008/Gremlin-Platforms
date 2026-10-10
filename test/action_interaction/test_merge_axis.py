# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import uuid
from pathlib import Path

import gremlin.profile
from action_plugins import merge_axis

from . import input_definitions as inout
from .conftest import JoystickGremlinBot


def set_merge_mode(
    profile: gremlin.profile.Profile, mode: merge_axis.MergeOperation
) -> None:
    k_merge_action_id = uuid.UUID("3c3ab772-a723-4ccb-a4ca-cf09061aa4d1")
    action = profile.library.get_action(k_merge_action_id)
    assert isinstance(action, merge_axis.MergeAxisData)
    action.operation = mode


def test_average(jgbot: JoystickGremlinBot, profile_dir: Path) -> None:
    jgbot.load_profile(profile_dir / "merge_axis.xml")
    set_merge_mode(jgbot._profile, merge_axis.MergeOperation.Average)

    jgbot.set_axis_absolute(inout.IN_AXIS_1, 0.0)
    jgbot.set_axis_absolute(inout.IN_AXIS_2, 0.0)
    assert jgbot.axis(inout.OUT_AXIS_1) == 0.0

    jgbot.set_axis_absolute(inout.IN_AXIS_1, 1.0)
    jgbot.set_axis_absolute(inout.IN_AXIS_2, -1.0)
    assert jgbot.axis(inout.OUT_AXIS_1) == 0.0

    jgbot.set_axis_absolute(inout.IN_AXIS_1, -1.0)
    jgbot.set_axis_absolute(inout.IN_AXIS_2, -1.0)
    assert jgbot.axis(inout.OUT_AXIS_1) == 0.5

    jgbot.set_axis_absolute(inout.IN_AXIS_1, 1.0)
    jgbot.set_axis_absolute(inout.IN_AXIS_2, 1.0)
    assert jgbot.axis(inout.OUT_AXIS_1) == -0.5

    jgbot.set_axis_absolute(inout.IN_AXIS_1, 1.0)
    jgbot.set_axis_absolute(inout.IN_AXIS_2, 0.0)
    assert jgbot.axis(inout.OUT_AXIS_1) == -0.25


def test_maximum(jgbot: JoystickGremlinBot, profile_dir: Path) -> None:
    jgbot.load_profile(profile_dir / "merge_axis.xml")
    set_merge_mode(jgbot._profile, merge_axis.MergeOperation.Maximum)

    jgbot.set_axis_absolute(inout.IN_AXIS_1, 0.0)
    jgbot.set_axis_absolute(inout.IN_AXIS_2, 0.0)
    assert jgbot.axis(inout.OUT_AXIS_1) == 0.0

    jgbot.set_axis_absolute(inout.IN_AXIS_1, 1.0)
    jgbot.set_axis_absolute(inout.IN_AXIS_2, -1.0)
    assert jgbot.axis(inout.OUT_AXIS_1) == -0.5

    jgbot.set_axis_absolute(inout.IN_AXIS_1, -1.0)
    jgbot.set_axis_absolute(inout.IN_AXIS_2, -1.0)
    assert jgbot.axis(inout.OUT_AXIS_1) == 0.5

    jgbot.set_axis_absolute(inout.IN_AXIS_1, 1.0)
    jgbot.set_axis_absolute(inout.IN_AXIS_2, 1.0)
    assert jgbot.axis(inout.OUT_AXIS_1) == -0.5

    jgbot.set_axis_absolute(inout.IN_AXIS_1, 1.0)
    jgbot.set_axis_absolute(inout.IN_AXIS_2, 0.0)
    assert jgbot.axis(inout.OUT_AXIS_1) == -0.5


def test_minimum(jgbot: JoystickGremlinBot, profile_dir: Path) -> None:
    jgbot.load_profile(profile_dir / "merge_axis.xml")
    set_merge_mode(jgbot._profile, merge_axis.MergeOperation.Minimum)

    jgbot.set_axis_absolute(inout.IN_AXIS_1, 0.0)
    jgbot.set_axis_absolute(inout.IN_AXIS_2, 0.0)
    assert jgbot.axis(inout.OUT_AXIS_1) == 0.0

    jgbot.set_axis_absolute(inout.IN_AXIS_1, 1.0)
    jgbot.set_axis_absolute(inout.IN_AXIS_2, -1.0)
    assert jgbot.axis(inout.OUT_AXIS_1) == 0.5

    jgbot.set_axis_absolute(inout.IN_AXIS_1, -1.0)
    jgbot.set_axis_absolute(inout.IN_AXIS_2, -1.0)
    assert jgbot.axis(inout.OUT_AXIS_1) == 0.5

    jgbot.set_axis_absolute(inout.IN_AXIS_1, 1.0)
    jgbot.set_axis_absolute(inout.IN_AXIS_2, 1.0)
    assert jgbot.axis(inout.OUT_AXIS_1) == -0.5

    jgbot.set_axis_absolute(inout.IN_AXIS_1, 1.0)
    jgbot.set_axis_absolute(inout.IN_AXIS_2, 0.0)
    assert jgbot.axis(inout.OUT_AXIS_1) == 0.0


def test_sum(jgbot: JoystickGremlinBot, profile_dir: Path) -> None:
    jgbot.load_profile(profile_dir / "merge_axis.xml")
    set_merge_mode(jgbot._profile, merge_axis.MergeOperation.Sum)

    jgbot.set_axis_absolute(inout.IN_AXIS_1, 0.0)
    jgbot.set_axis_absolute(inout.IN_AXIS_2, 0.0)
    assert jgbot.axis(inout.OUT_AXIS_1) == 0.0

    jgbot.set_axis_absolute(inout.IN_AXIS_1, 1.0)
    jgbot.set_axis_absolute(inout.IN_AXIS_2, -1.0)
    assert jgbot.axis(inout.OUT_AXIS_1) == 0.0

    jgbot.set_axis_absolute(inout.IN_AXIS_1, -1.0)
    jgbot.set_axis_absolute(inout.IN_AXIS_2, -1.0)
    assert jgbot.axis(inout.OUT_AXIS_1) == 0.5

    jgbot.set_axis_absolute(inout.IN_AXIS_1, 1.0)
    jgbot.set_axis_absolute(inout.IN_AXIS_2, 1.0)
    assert jgbot.axis(inout.OUT_AXIS_1) == -0.5

    jgbot.set_axis_absolute(inout.IN_AXIS_1, 1.0)
    jgbot.set_axis_absolute(inout.IN_AXIS_2, 0.0)
    assert jgbot.axis(inout.OUT_AXIS_1) == -0.5

    jgbot.set_axis_absolute(inout.IN_AXIS_1, -0.25)
    jgbot.set_axis_absolute(inout.IN_AXIS_2, 0.75)
    assert jgbot.axis(inout.OUT_AXIS_1) == -0.25


def test_bidirectional(jgbot: JoystickGremlinBot, profile_dir: Path) -> None:
    jgbot.load_profile(profile_dir / "merge_axis.xml")
    set_merge_mode(jgbot._profile, merge_axis.MergeOperation.Bidirectional)

    jgbot.set_axis_absolute(inout.IN_AXIS_1, 0.0)
    jgbot.set_axis_absolute(inout.IN_AXIS_2, 0.0)
    assert jgbot.axis(inout.OUT_AXIS_1) == 0.0

    jgbot.set_axis_absolute(inout.IN_AXIS_1, 1.0)
    jgbot.set_axis_absolute(inout.IN_AXIS_2, -1.0)
    assert jgbot.axis(inout.OUT_AXIS_1) == 0.5

    jgbot.set_axis_absolute(inout.IN_AXIS_1, -1.0)
    jgbot.set_axis_absolute(inout.IN_AXIS_2, 1.0)
    assert jgbot.axis(inout.OUT_AXIS_1) == -0.5

    jgbot.set_axis_absolute(inout.IN_AXIS_1, 1.0)
    jgbot.set_axis_absolute(inout.IN_AXIS_2, 1.0)
    assert jgbot.axis(inout.OUT_AXIS_1) == 0.0

    jgbot.set_axis_absolute(inout.IN_AXIS_1, -1.0)
    jgbot.set_axis_absolute(inout.IN_AXIS_2, -1.0)
    assert jgbot.axis(inout.OUT_AXIS_1) == 0.0

    jgbot.set_axis_absolute(inout.IN_AXIS_1, 1.0)
    jgbot.set_axis_absolute(inout.IN_AXIS_2, 0.0)
    assert jgbot.axis(inout.OUT_AXIS_1) == 0.25

    jgbot.set_axis_absolute(inout.IN_AXIS_1, -0.25)
    jgbot.set_axis_absolute(inout.IN_AXIS_2, 0.75)
    assert jgbot.axis(inout.OUT_AXIS_1) == -0.25


def test_maximum_deflection(jgbot: JoystickGremlinBot, profile_dir: Path) -> None:
    """05 S114 (R7): the axis furthest from centre wins; ties go to axis 2.

    The child Response Curve maps x to -x/2 before the output axis.
    """
    jgbot.load_profile(profile_dir / "merge_axis.xml")
    set_merge_mode(jgbot._profile, merge_axis.MergeOperation.MaximumDeflection)

    jgbot.set_axis_absolute(inout.IN_AXIS_1, 0.0)
    jgbot.set_axis_absolute(inout.IN_AXIS_2, 0.0)
    assert jgbot.axis(inout.OUT_AXIS_1) == 0.0

    # Tie (equal distance from centre): axis 2 (-1.0) wins, not axis 1.
    jgbot.set_axis_absolute(inout.IN_AXIS_1, 1.0)
    jgbot.set_axis_absolute(inout.IN_AXIS_2, -1.0)
    assert jgbot.axis(inout.OUT_AXIS_1) == 0.5

    jgbot.set_axis_absolute(inout.IN_AXIS_1, -0.5)
    jgbot.set_axis_absolute(inout.IN_AXIS_2, 0.5)
    assert jgbot.axis(inout.OUT_AXIS_1) == -0.25

    # Axis 2 further out.
    jgbot.set_axis_absolute(inout.IN_AXIS_1, -0.25)
    jgbot.set_axis_absolute(inout.IN_AXIS_2, 0.75)
    assert jgbot.axis(inout.OUT_AXIS_1) == -0.375

    # Axis 1 further out, and below centre (Maximum would pick axis 2 here).
    jgbot.set_axis_absolute(inout.IN_AXIS_1, -0.75)
    jgbot.set_axis_absolute(inout.IN_AXIS_2, 0.25)
    assert jgbot.axis(inout.OUT_AXIS_1) == 0.375

    jgbot.set_axis_absolute(inout.IN_AXIS_1, 1.0)
    jgbot.set_axis_absolute(inout.IN_AXIS_2, 0.0)
    assert jgbot.axis(inout.OUT_AXIS_1) == -0.5
