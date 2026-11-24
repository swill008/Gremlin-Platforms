# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Containers after a mode change: the event that ends an activation reaches
them as Foreign; a Foreign press starts nothing (06 S38, S38a, S38c,
D-06-MODE-RELEASE)."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from unittest import mock

import pytest

from action_plugins.chain import ChainData, ChainFunctor
from action_plugins.condition import ConditionData, ConditionFunctor
from action_plugins.double_tap import DoubleTapData, DoubleTapFunctor
from action_plugins.hat_buttons import HatButtonsData, HatButtonsFunctor
from action_plugins.smart_toggle import SmartToggleData, SmartToggleFunctor
from action_plugins.split_axis import SplitAxisData, SplitAxisFunctor
from action_plugins.tempo import TempoData, TempoFunctor
from gremlin.base_classes import Value
from gremlin.types import (
    ActionActivationMode,
    Event,
    HatDirection,
    InputType,
    ModeType,
)

N, F = ModeType.Native, ModeType.Foreign


class _Recorder:
    """A child action: records (value, mode type) of every call."""

    def __init__(self) -> None:
        self.calls: list[tuple[object, ModeType]] = []
        self.functors: dict = {}

    def __call__(self, event: Event, value: Value, properties: list = []) -> None:
        self.calls.append((value.current, value.mode_type))

    def waits_for_end(self) -> bool:
        return False

    def reset(self) -> None:
        pass


def _event(input_type: InputType, current: object) -> Event:
    return Event(
        input_type,
        1,
        uuid.uuid4(),
        "Default",
        value=current,
        is_pressed=current if isinstance(current, bool) else None,
    )


def _send(functor: object, current: object, mode_type: ModeType = N) -> None:
    input_type = {
        bool: InputType.JoystickButton,
        float: InputType.JoystickAxis,
        HatDirection: InputType.JoystickHat,
    }[type(current)]
    functor(_event(input_type, current), Value(current, mode_type), [])


@pytest.fixture(autouse=True)
def _no_timers() -> Iterator[None]:
    """The FSM timers are not part of these checks."""
    with (
        mock.patch.object(TempoFunctor, "_start_timer", lambda *a: None),
        mock.patch.object(DoubleTapFunctor, "_start_timer", lambda *a: None),
        mock.patch.object(SmartToggleFunctor, "_start_timer", lambda *a: None),
    ):
        yield


def test_chain_foreign_release_ends_the_step_and_advances() -> None:
    functor = ChainFunctor(ChainData())
    functor.data.chain_sequences = [[], []]
    steps = [_Recorder(), _Recorder()]
    functor.functors = {"0": [steps[0]], "1": [steps[1]]}

    _send(functor, True, F)  # a Foreign press starts nothing
    assert steps[0].calls == [] and not functor.waits_for_end()

    _send(functor, True)
    assert functor.waits_for_end()  # even with no action waiting
    _send(functor, False, F)
    assert steps[0].calls == [(True, N), (False, F)]
    assert functor.current_index == 1 and not functor.waits_for_end()

    _send(functor, False, F)  # nothing pressed: no advance
    assert functor.current_index == 1


def test_tempo_foreign_release_ends_the_sequence_in_its_mode() -> None:
    data = TempoData()
    data.activate_on = "press"
    functor = TempoFunctor(data)
    short = _Recorder()
    functor.functors["short"] = [short]

    _send(functor, True, F)
    assert short.calls == [] and functor.fsm.current_state == "wait"

    _send(functor, True)
    assert functor.waits_for_end()
    _send(functor, False, F)
    # The release belongs to the sequence its Native press started.
    assert short.calls == [(True, N), (False, N)]
    assert functor.fsm.current_state == "wait" and not functor.waits_for_end()

    _send(functor, False, F)  # nothing under way: ignored
    assert len(short.calls) == 2


def test_tempo_release_mode_waits_before_any_action_ran() -> None:
    data = TempoData()
    data.activate_on = "release"
    functor = TempoFunctor(data)
    _send(functor, True)
    assert functor.waits_for_end()


def test_double_tap_second_tap_after_a_mode_change_continues() -> None:
    data = DoubleTapData()
    data.activate_on = "exclusive"
    functor = DoubleTapFunctor(data)
    single, double = _Recorder(), _Recorder()
    functor.functors["single"] = [single]
    functor.functors["double"] = [double]

    _send(functor, True, F)  # never starts a sequence
    assert functor.fsm.current_state == "neutral"

    _send(functor, True)
    _send(functor, False, F)
    assert functor.fsm.current_state == "t" and functor.waits_for_end()
    _send(functor, True, F)  # the second tap continues the sequence
    _send(functor, False, F)
    assert double.calls == [(True, N), (False, N)]
    assert single.calls == []
    assert functor.fsm.current_state == "neutral"


def test_smart_toggle_foreign_events_let_go_of_the_toggle() -> None:
    functor = SmartToggleFunctor(SmartToggleData())
    child = _Recorder()
    functor.functors["children"] = [child]

    _send(functor, True, F)
    assert child.calls == [] and functor.fsm.current_state == "wait"

    _send(functor, True)
    _send(functor, False)  # short press: toggled on
    assert functor.fsm.current_state == "toggle" and functor.waits_for_end()
    _send(functor, True, F)
    _send(functor, False, F)
    assert child.calls == [(True, N), (False, N)]
    assert functor.fsm.current_state == "wait" and not functor.waits_for_end()


def test_smart_toggle_native_release_still_lets_go_when_held() -> None:
    functor = SmartToggleFunctor(SmartToggleData())
    child = _Recorder()
    functor.functors["children"] = [child]
    _send(functor, True)
    functor._timeout()  # held past the delay
    _send(functor, False)
    assert child.calls == [(True, N), (False, N)]


def _condition(truth: list[bool]) -> tuple[ConditionFunctor, _Recorder, _Recorder]:
    data = ConditionData(InputType.JoystickButton)
    data.activation_mode = ActionActivationMode.Both
    functor = ConditionFunctor(data)
    yes, no = _Recorder(), _Recorder()
    functor.functors["true"] = [yes]
    functor.functors["false"] = [no]
    functor._condition_truth_state = lambda value: truth[0]  # type: ignore[method-assign]
    return functor, yes, no


def test_condition_foreign_release_goes_to_the_branch_of_the_press() -> None:
    truth = [True]
    functor, yes, no = _condition(truth)
    _send(functor, True)
    truth[0] = False
    _send(functor, False, F)
    assert yes.calls == [(True, N), (False, F)]
    assert no.calls == []


def test_condition_foreign_release_without_a_press_runs_nothing() -> None:
    functor, yes, no = _condition([True])
    _send(functor, False, F)
    _send(functor, True, F)
    assert yes.calls == [] and no.calls == []


def test_condition_not_both_never_waits() -> None:
    truth = [True]
    functor, yes, _ = _condition(truth)
    functor.data.activation_mode = ActionActivationMode.Press
    yes.waits_for_end = lambda: True  # type: ignore[method-assign]
    _send(functor, True)
    assert not functor.waits_for_end()


def test_hat_buttons_foreign_centre_releases_the_pressed_direction() -> None:
    data = HatButtonsData()
    data.button_count = 4
    functor = HatButtonsFunctor(data)
    north, east = _Recorder(), _Recorder()
    functor.functors["North"] = [north]
    functor.functors["East"] = [east]
    with mock.patch("action_plugins.hat_buttons.event_handler.EventListener"):
        _send(functor, HatDirection.North)
        assert functor.waits_for_end()
        _send(functor, HatDirection.East, F)  # nothing pressed in the old mode
        _send(functor, HatDirection.Center, F)
    assert north.calls == [(True, N), (False, F)]
    assert east.calls == []
    assert not functor.waits_for_end()


def test_split_axis_never_gets_a_foreign_axis_value() -> None:
    functor = SplitAxisFunctor(SplitAxisData())
    lower, upper = _Recorder(), _Recorder()
    functor.functors["lower"] = [lower]
    functor.functors["upper"] = [upper]
    _send(functor, 0.5, F)
    assert lower.calls == [] and upper.calls == []
