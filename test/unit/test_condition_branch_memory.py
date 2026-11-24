# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A Condition sends the release to the list its press chose; an axis
branch change resets the old list (05 S145, upstream a448e3f3, d1cd7e1b)."""

from __future__ import annotations

import uuid

from action_plugins.common import RelativeAxisLoop
from action_plugins.condition import ConditionData, ConditionFunctor
from gremlin.base_classes import AbstractFunctor, Value, reset_functor_tree
from gremlin.types import Event, HatDirection, InputType


class _BranchRecorder:
    def __init__(self) -> None:
        self.values: list[bool | float | HatDirection] = []
        self.resets = 0
        self.functors: dict = {}

    def __call__(self, event: Event, value: Value, properties: list = []) -> None:
        self.values.append(value.current)

    def reset(self) -> None:
        self.resets += 1


def _make_functor(
    behavior_type: InputType, truth: list[bool]
) -> tuple[ConditionFunctor, _BranchRecorder, _BranchRecorder]:
    functor = ConditionFunctor(ConditionData(behavior_type))
    true_branch = _BranchRecorder()
    false_branch = _BranchRecorder()
    functor.functors["true"] = [true_branch]
    functor.functors["false"] = [false_branch]
    functor._condition_truth_state = lambda value: truth[0]  # type: ignore[method-assign]
    return functor, true_branch, false_branch


def _send(
    functor: ConditionFunctor,
    input_type: InputType,
    current: bool | float | HatDirection,
) -> None:
    event = Event(input_type, 1, uuid.uuid4(), "Default", value=current)
    functor(event, Value(current))


def test_functor_button_release_follows_press() -> None:
    truth = [True]
    functor, true_branch, false_branch = _make_functor(InputType.JoystickButton, truth)

    _send(functor, InputType.JoystickButton, True)
    truth[0] = False
    _send(functor, InputType.JoystickButton, False)
    assert true_branch.values == [True, False]
    assert false_branch.values == []

    _send(functor, InputType.JoystickButton, True)
    truth[0] = True
    _send(functor, InputType.JoystickButton, False)
    assert true_branch.values == [True, False]
    assert false_branch.values == [True, False]


def test_functor_key_release_follows_press() -> None:
    truth = [True]
    functor, true_branch, false_branch = _make_functor(InputType.Keyboard, truth)
    _send(functor, InputType.Keyboard, True)
    truth[0] = False
    _send(functor, InputType.Keyboard, False)
    assert true_branch.values == [True, False]
    assert false_branch.values == []


def test_functor_button_release_without_press_evaluates() -> None:
    truth = [False]
    functor, true_branch, false_branch = _make_functor(InputType.JoystickButton, truth)

    _send(functor, InputType.JoystickButton, False)
    assert true_branch.values == []
    assert false_branch.values == [False]


def test_functor_hat_branch_change_centres_old_branch() -> None:
    truth = [True]
    functor, true_branch, false_branch = _make_functor(InputType.JoystickHat, truth)

    _send(functor, InputType.JoystickHat, HatDirection.North)
    truth[0] = False
    _send(functor, InputType.JoystickHat, HatDirection.NorthEast)
    truth[0] = True
    _send(functor, InputType.JoystickHat, HatDirection.Center)
    assert true_branch.values == [HatDirection.North, HatDirection.Center]
    assert false_branch.values == [HatDirection.NorthEast, HatDirection.Center]


def test_functor_axis_evaluates_every_event() -> None:
    truth = [True]
    functor, true_branch, false_branch = _make_functor(InputType.JoystickAxis, truth)

    _send(functor, InputType.JoystickAxis, 0.5)
    truth[0] = False
    _send(functor, InputType.JoystickAxis, 0.25)
    assert true_branch.values == [0.5]
    assert false_branch.values == [0.25]


def test_functor_axis_branch_change_resets_old_branch() -> None:
    truth = [True]
    functor, true_branch, false_branch = _make_functor(InputType.JoystickAxis, truth)

    _send(functor, InputType.JoystickAxis, 0.5)
    _send(functor, InputType.JoystickAxis, 0.6)
    assert true_branch.resets == 0
    truth[0] = False
    _send(functor, InputType.JoystickAxis, 0.25)
    assert true_branch.resets == 1
    assert false_branch.resets == 0


def test_functor_error_runs_neither_list() -> None:
    from gremlin import error

    functor, true_branch, false_branch = _make_functor(InputType.JoystickButton, [True])

    def broken(value: Value) -> bool:
        raise error.GremlinError("broken")

    functor._condition_truth_state = broken  # type: ignore[method-assign]
    _send(functor, InputType.JoystickButton, True)
    _send(functor, InputType.JoystickButton, False)
    assert true_branch.values == [] and false_branch.values == []


def test_abstract_functor_reset_is_a_no_op_and_tree_reset_reaches_children() -> None:
    assert AbstractFunctor.reset is not None
    child = _BranchRecorder()
    parent = _BranchRecorder()
    parent.functors = {"true": [child]}
    reset_functor_tree(parent)  # type: ignore[arg-type]
    assert parent.resets == 1 and child.resets == 1

    functor = ConditionFunctor(ConditionData(InputType.JoystickButton))
    functor.reset()  # the base no-op


def test_relative_axis_loop_reset_stops_the_loop() -> None:
    class Axis(RelativeAxisLoop):
        def __init__(self) -> None:
            self._init_relative()

    axis = Axis()
    axis.thread_running = True
    axis.reset()
    assert axis.thread_running is False
