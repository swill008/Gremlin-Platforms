# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Live capture (Live Log Reader → Debug → Live) records what the running
profile handles, read-only, and only while it is on."""

from __future__ import annotations

import functools
import uuid
from collections.abc import Iterator

import pytest

from gremlin import live_capture
from gremlin.event_handler import Event, EventHandler
from gremlin.types import InputType

_DEV = uuid.UUID("11111111-2222-3333-4444-555555555555")
_MODE = "Default"


class _Action:
    def __init__(self, name: str, tag: str, **values: object) -> None:
        self.name = name
        self.tag = tag
        self.__dict__.update(values)


class _Root:
    def __init__(self, actions: list[_Action]) -> None:
        self._actions = actions

    def get_actions(self) -> tuple[list[_Action], list[str]]:
        return self._actions, ["children"] * len(self._actions)


class _Binding:
    def __init__(self, actions: list[_Action]) -> None:
        self.root_action = _Root(actions)
        self.virtual_button = None


class _Callback:
    """Like CallbackObject (a _binding), but runs nothing."""

    always_execute = False

    def __init__(self, actions: list[_Action]) -> None:
        self._binding = _Binding(actions)
        self.calls = 0

    def __call__(self, event: Event) -> None:
        self.calls += 1


@pytest.fixture(autouse=True)
def _fresh() -> Iterator[None]:
    live_capture.set_enabled(False)
    live_capture.clear()
    yield
    live_capture.set_enabled(False)
    live_capture.clear()


def _button(pressed: bool, button: int = 3) -> Event:
    return Event(InputType.JoystickButton, button, _DEV, _MODE, is_pressed=pressed)


def test_off_by_default_and_records_nothing() -> None:
    assert not live_capture.enabled()
    handler = EventHandler()
    handler.process_event(_button(True, 77))
    assert live_capture.entries() == []


def test_records_input_and_the_actions_it_ran() -> None:
    handler = EventHandler()
    cb = _Callback([_Action(
        "Map to vJoy", "map-to-vjoy", vjoy_device_id=1,
        vjoy_input_type=InputType.JoystickButton, vjoy_input_id=5,
    )])
    handler.add_callback(_DEV, _MODE, _button(True, 41), cb)
    try:
        live_capture.set_enabled(True)
        handler.process_event(_button(True, 41))
        handler.process_event(_button(True, 42))
    finally:
        handler.callbacks.get(_DEV, {}).get(_MODE, {}).pop(_button(True, 41), None)
    assert cb.calls == 1  # the capture never stops the action
    (kind1, ran), (kind2, unbound) = live_capture.entries()
    assert kind1 == live_capture.RAN and kind2 == live_capture.NONE
    assert "pressed" in ran and "[Default]" in ran
    # The destination label also says when no output module is set up.
    assert "→  Map to vJoy (vJoy 1 B5" in ran
    assert unbound.endswith("→  nothing bound")


def test_axis_bursts_are_coalesced() -> None:
    live_capture.set_enabled(True)
    for i in range(50):
        live_capture.record(
            Event(InputType.JoystickAxis, 1, _DEV, _MODE, value=i / 50), []
        )
    rows = live_capture.entries()
    # The first value and the latest; nothing in between.
    assert len(rows) == 2
    assert "+0.000" in rows[0][1] and "+0.980" in rows[1][1]


def test_wrapped_and_script_callbacks() -> None:
    cb = _Callback([_Action("Macro", "macro"), _Action("Play Sound", "play-sound")])
    assert live_capture.callback_text(functools.partial(cb)) == "Macro, Play Sound"
    assert live_capture.callback_text(lambda event: None) == ""
    live_capture.set_enabled(True)
    live_capture.record(_button(True), [lambda event: None])
    assert live_capture.entries()[0][1].endswith("→  script")


def test_a_capture_problem_never_reaches_the_profile() -> None:
    live_capture.set_enabled(True)
    live_capture.record(object(), [])  # not an event: dropped quietly
    assert live_capture.entries() == []


def test_clear_and_bounded() -> None:
    live_capture.set_enabled(True)
    for i in range(live_capture.MAX_ENTRIES + 10):
        live_capture.record(_button(i % 2 == 0), [])
    assert len(live_capture.entries()) == live_capture.MAX_ENTRIES
    live_capture.clear()
    assert live_capture.entries() == []
