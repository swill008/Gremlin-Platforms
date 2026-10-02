# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Actions that would do nothing say so, as warnings: a save keeps them
(only errors are pruned)."""

from __future__ import annotations

import sys

sys.path.append(".")

import pytest

from action_plugins.chain import ChainData
from action_plugins.change_mode import ChangeModeData, ChangeType
from action_plugins.description import DescriptionData
from action_plugins.tempo import TempoData
from gremlin import shared_state
from gremlin.base_classes import UserFeedback
from gremlin.profile import Profile
from gremlin.types import InputType

_WARNING = UserFeedback.FeedbackType.Warning


def _kinds(action: object) -> list:
    return [f.feedback_type for f in action.user_feedback()]  # type: ignore[attr-defined]


def test_empty_containers_warn_and_stay_valid() -> None:
    chain = ChainData(InputType.JoystickButton)
    assert _kinds(chain) == [_WARNING]
    assert chain.is_valid()
    chain.chain_sequences = [[DescriptionData()], []]
    assert _kinds(chain) == []

    tempo = TempoData(InputType.JoystickButton)
    assert _kinds(tempo) == [_WARNING]
    tempo.short_actions = [DescriptionData()]
    assert _kinds(tempo) == []


@pytest.fixture
def profile(monkeypatch: pytest.MonkeyPatch) -> Profile:
    p = Profile()
    p.modes.add_mode("Combat")
    monkeypatch.setattr(shared_state, "current_profile", p)
    return p


def test_change_mode_warns_about_a_missing_mode(profile: Profile) -> None:
    action = ChangeModeData(InputType.JoystickButton)
    action.target_modes = ["Combat"]
    assert _kinds(action) == []
    profile.modes.delete_mode("Combat")
    feedback = action.user_feedback()
    assert [f.feedback_type for f in feedback] == [_WARNING]
    assert "'Combat' no longer exists" in feedback[0].message
    assert action.is_valid()


def test_change_mode_cycle_without_modes_warns(profile: Profile) -> None:
    action = ChangeModeData(InputType.JoystickButton)
    action.change_type = ChangeType.Cycle
    assert _kinds(action) == [_WARNING]
    action.change_type = ChangeType.Previous
    assert _kinds(action) == []
