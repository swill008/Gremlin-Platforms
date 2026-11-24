# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The event that ends an activation reaches the press mode (06 S38,
S38a-S38d, D-06-MODE-RELEASE; claude/plans/b3-mode-change-release.md).

A real CodeRunner runs a real profile: CallbackObjects built by
_setup_profile, the real EventHandler, ModeManager and MacroManager.
Drivers, sound, speech and network are stand-ins; vJoy writes are recorded
at the output module (gremlin.modules.output), keys at test/fake_input.py
(nothing reaches the PC, no real vJoy).
"""

from __future__ import annotations

import sys
import time
import uuid
from collections.abc import Callable, Iterator
from types import SimpleNamespace
from typing import Any
from unittest import mock

sys.path.append(".")

import fake_input  # pyright: ignore[reportMissingImports]  (test/)
import pytest
from PySide6 import QtCore

from gremlin import (
    code_runner,
    event_handler,
    keyboard,
    macro,
    mode_manager,
    run_scope,
    shared_state,
)
from gremlin import (
    profile as gprofile,
)
from gremlin.profile import Profile
from gremlin.types import ActionActivationMode, Event, HatDirection, InputType

_GUID = uuid.UUID("77777777-5555-2222-3333-383838383838")
_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


class _Bus(QtCore.QObject):
    """The input modules' event bus (nothing is sent through it here)."""

    event = QtCore.Signal(object)  # pyright: ignore[reportAssignmentType]
    key_event = QtCore.Signal(object)

    def reload(self) -> None:
        pass


class _Listener(QtCore.QObject):
    """The event listener: virtual buttons reach the handler through it."""

    virtual_event = QtCore.Signal(object)
    joystick_event = QtCore.Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.gremlin_active = False


@pytest.fixture
def rig(monkeypatch: pytest.MonkeyPatch) -> Iterator[SimpleNamespace]:
    """A real CodeRunner; vJoy output recorded as (kind, id, value)."""
    from gremlin.modules import output

    vjoy: list[tuple] = []
    released: list[tuple] = []
    monkeypatch.setattr(
        output,
        "write_vjoy",
        lambda vid, kind, iid, value: vjoy.append((kind, iid, value)) or True,
    )
    monkeypatch.setattr(
        output,
        "release_vjoy_button",
        lambda vid, iid: released.append(("button", iid)) or True,
    )
    for name in ("output", "OscRuntime", "audio_player", "tts"):
        monkeypatch.setattr(code_runner, name, mock.MagicMock())
    bus = _Bus()
    monkeypatch.setattr(code_runner, "InputModuleRuntime", lambda: bus)
    listener = _Listener()
    fake = mock.MagicMock(return_value=listener)
    fake.instance = None
    monkeypatch.setattr(event_handler, "EventListener", fake)
    monkeypatch.setattr(mode_manager, "_known_modes", lambda: set())
    mm = mode_manager.ModeManager()
    stack = list(mm._mode_stack)
    run = code_runner.CodeRunner()
    monkeypatch.setattr(run, "_refresh_axes", lambda: None)
    fake_input.sent.clear()
    yield SimpleNamespace(run=run, vjoy=vjoy, released=released)
    run.stop()
    run.event_handler.resume()
    shared_state.set_runtime_active(False)
    run_scope._reset_for_tests()
    mm._mode_stack = stack
    mm.mode_changed.emit(mm.current.name)


# --- helpers -----------------------------------------------------------------


def _wait_for(check: Callable[[], bool], seconds: float = 2.0) -> bool:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        QtCore.QCoreApplication.processEvents()
        if check():
            return True
        time.sleep(0.01)
    return check()


def _settle(seconds: float = 0.15) -> None:
    """Lets the macro thread and Qt timers run (for "nothing else" checks)."""
    _wait_for(lambda: False, seconds)


def _profile() -> Profile:
    profile = Profile()
    profile.modes.add_mode("B")
    return profile


def _binding(
    profile: Profile, mode: str, kind: InputType, index: int
) -> gprofile.InputItemBinding:
    item = profile.get_input_item(_GUID, kind, index, mode, create_if_missing=True)
    return item.add_item_binding()


def _bind(
    profile: Profile,
    mode: str,
    kind: InputType,
    index: int,
    action: Any,  # noqa: ANN401
) -> Any:  # noqa: ANN401
    _binding(profile, mode, kind, index).root_action.insert_action(action, "children")
    return action


def _key_action(profile: Profile, name: str) -> Any:  # noqa: ANN401
    action = profile.library.create("Map to Keyboard", InputType.JoystickButton)
    action.keys = [keyboard.key_from_name(name)]
    return action


def _vjoy(profile: Profile, kind: InputType, out_kind: InputType, index: int) -> Any:  # noqa: ANN401
    action = profile.library.create("Map to vJoy", kind)
    action.vjoy_device_id = 1
    action.vjoy_input_type = out_kind
    action.vjoy_input_id = index
    return action


def _keys(name: str) -> list[bool]:
    """Down (True) / up (False) of one key, as sent."""
    key = keyboard.key_from_name(name)
    return [
        s[3]
        for s in fake_input.sent
        if s[0] == "key" and s[1] == key.scan_code and s[2] == key.is_extended
    ]


def _vjoy_values(rig: SimpleNamespace, kind: str, index: int) -> list[Any]:
    """What one vJoy output was set to, by either path."""
    values = [v for k, i, v in rig.vjoy if k == kind and i == index]
    values += [False for k, i in rig.released if k == kind and i == index]
    return values


def _switch(name: str) -> None:
    mode_manager.ModeManager().switch_to(mode_manager.Mode(name, None))


def _button(index: int, pressed: bool) -> Event:
    # No mode, as from the hardware: the handler stamps the current one.
    return Event(
        InputType.JoystickButton,
        index,
        _GUID,
        "",
        is_pressed=pressed,
        raw_value=pressed,
    )


def _hat(index: int, direction: HatDirection) -> Event:
    return Event(
        InputType.JoystickHat, index, _GUID, "", value=direction, raw_value=direction
    )


def _axis(index: int, value: float) -> Event:
    return Event(InputType.JoystickAxis, index, _GUID, "", value=value, raw_value=value)


def _send(rig: SimpleNamespace, event: Event) -> None:
    rig.run.event_handler.process_event(event)


def _pending(handler: Any) -> int:  # noqa: ANN401
    """Entries in the event handler's pending table (D-06-MODE-RELEASE)."""
    table = getattr(handler, "_pending", None)
    assert table is not None, "EventHandler has no pending table (_pending)"
    return sum(len(callbacks) for callbacks in table.values())


# --- 1. Map to Keyboard (S38) ------------------------------------------------


def test_a_key_held_across_a_mode_change_is_released(rig: SimpleNamespace) -> None:
    profile = _profile()
    _bind(profile, "Default", InputType.JoystickButton, 1, _key_action(profile, "F16"))
    rig.run.start(profile, "Default")
    _send(rig, _button(1, True))
    assert _wait_for(lambda: _keys("F16") == [True])
    _switch("B")  # F13-like: unbound in B
    _send(rig, _button(1, False))
    assert _wait_for(lambda: _keys("F16") == [True, False])
    _settle()
    assert _keys("F16") == [True, False]  # once


# --- 2. Map to vJoy hat (S38) ------------------------------------------------


def test_a_vjoy_hat_centres_after_a_mode_change(rig: SimpleNamespace) -> None:
    profile = _profile()
    _bind(
        profile,
        "Default",
        InputType.JoystickHat,
        1,
        _vjoy(profile, InputType.JoystickHat, InputType.JoystickHat, 1),
    )
    rig.run.start(profile, "Default")
    _send(rig, _hat(1, HatDirection.North))
    _switch("B")
    _send(rig, _hat(1, HatDirection.Center))
    assert _vjoy_values(rig, "hat", 1) == [HatDirection.North, HatDirection.Center]


# --- 3. Hold macro (S38) -----------------------------------------------------


def test_a_hold_macro_ends_once_after_a_mode_change(
    rig: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    from action_plugins.macro import MacroRepeatModes

    profile = _profile()
    action = profile.library.create("Macro", InputType.JoystickButton)
    action.repeat_mode = MacroRepeatModes.Hold
    action.activation_mode = ActionActivationMode.Press
    _bind(profile, "Default", InputType.JoystickButton, 2, action)
    ended: list[object] = []
    manager = macro.MacroManager()
    real = manager.terminate_macro
    monkeypatch.setattr(
        manager, "terminate_macro", lambda m: (ended.append(m), real(m))
    )
    rig.run.start(profile, "Default")
    _send(rig, _button(2, True))
    _switch("B")
    assert ended == []
    _send(rig, _button(2, False))
    assert len(ended) == 1


# --- 4. Containers (S38) -----------------------------------------------------


def test_a_chain_step_lets_go_and_the_chain_advances(rig: SimpleNamespace) -> None:
    profile = _profile()
    chain = profile.library.create("Chain", InputType.JoystickButton)
    chain.chain_sequences.append([])
    chain.insert_action(_key_action(profile, "F16"), "0")
    chain.insert_action(_key_action(profile, "F17"), "1")
    _bind(profile, "Default", InputType.JoystickButton, 3, chain)
    rig.run.start(profile, "Default")
    _send(rig, _button(3, True))
    _switch("B")
    _send(rig, _button(3, False))
    assert _wait_for(lambda: _keys("F16") == [True, False])
    _switch("Default")
    _send(rig, _button(3, True))  # the next step
    assert _wait_for(lambda: _keys("F17") == [True])
    _settle()
    assert _keys("F16") == [True, False]


def test_a_tempo_long_press_lets_go_and_nothing_else_runs(
    rig: SimpleNamespace,
) -> None:
    profile = _profile()
    tempo = profile.library.create("Tempo", InputType.JoystickButton)
    tempo.threshold = 0.05
    tempo.activate_on = "release"
    tempo.insert_action(_key_action(profile, "F16"), "long")
    tempo.insert_action(_key_action(profile, "F17"), "short")
    _bind(profile, "Default", InputType.JoystickButton, 4, tempo)
    rig.run.start(profile, "Default")
    _send(rig, _button(4, True))
    assert _wait_for(lambda: _keys("F16") == [True])  # long press
    _switch("B")
    _send(rig, _button(4, False))
    assert _wait_for(lambda: _keys("F16") == [True, False])
    _settle()
    # S38a: only the ending part runs in the old mode; the short list
    # (never pressed) gets nothing.
    assert _keys("F17") == []
    assert _keys("F16") == [True, False]


def test_a_smart_toggle_held_lets_go_once(rig: SimpleNamespace) -> None:
    profile = _profile()
    toggle = profile.library.create("Smart Toggle", InputType.JoystickButton)
    toggle.delay = 0.05
    toggle.insert_action(_key_action(profile, "F16"), "children")
    _bind(profile, "Default", InputType.JoystickButton, 5, toggle)
    rig.run.start(profile, "Default")
    _send(rig, _button(5, True))
    assert _wait_for(lambda: _keys("F16") == [True])
    _settle(0.15)  # past the delay: held, so the release lets go
    _switch("B")
    _send(rig, _button(5, False))
    assert _wait_for(lambda: _keys("F16") == [True, False])
    _settle()
    assert _keys("F16") == [True, False]


def test_a_double_tap_single_lets_go_once(rig: SimpleNamespace) -> None:
    profile = _profile()
    tap = profile.library.create("Double Tap", InputType.JoystickButton)
    tap.threshold = 5.0
    tap.activate_on = "combined"
    tap.insert_action(_key_action(profile, "F16"), "single")
    tap.insert_action(_key_action(profile, "F17"), "double")
    _bind(profile, "Default", InputType.JoystickButton, 6, tap)
    rig.run.start(profile, "Default")
    _send(rig, _button(6, True))
    assert _wait_for(lambda: _keys("F16") == [True])
    _switch("B")
    _send(rig, _button(6, False))
    assert _wait_for(lambda: _keys("F16") == [True, False])
    _settle()
    assert _keys("F16") == [True, False]
    assert _keys("F17") == []


def test_a_condition_branch_lets_go(rig: SimpleNamespace) -> None:
    profile = _profile()
    condition = profile.library.create("Condition", InputType.JoystickButton)
    condition.insert_action(_key_action(profile, "F16"), "true")  # no conditions: true
    condition.insert_action(_key_action(profile, "F17"), "false")
    _bind(profile, "Default", InputType.JoystickButton, 7, condition)
    rig.run.start(profile, "Default")
    _send(rig, _button(7, True))
    assert _wait_for(lambda: _keys("F16") == [True])
    _switch("B")
    _send(rig, _button(7, False))
    assert _wait_for(lambda: _keys("F16") == [True, False])
    _settle()
    assert _keys("F17") == []


def test_a_hat_buttons_direction_lets_go(rig: SimpleNamespace) -> None:
    profile = _profile()
    hat_buttons = profile.library.create("Hat as Buttons", InputType.JoystickHat)
    hat_buttons.button_count = 4
    hat_buttons.insert_action(_key_action(profile, "F16"), "North")
    _bind(profile, "Default", InputType.JoystickHat, 2, hat_buttons)
    rig.run.start(profile, "Default")
    _send(rig, _hat(2, HatDirection.North))
    assert _wait_for(lambda: _keys("F16") == [True])
    _switch("B")
    _send(rig, _hat(2, HatDirection.Center))
    assert _wait_for(lambda: _keys("F16") == [True, False])


# --- 5. Script callback (S38b) -----------------------------------------------


def test_a_script_callback_gets_the_release_once(rig: SimpleNamespace) -> None:
    rig.run.start(_profile(), "Default")
    calls: list[bool] = []

    def callback(event: Event) -> None:
        calls.append(event.is_pressed)

    template = Event(InputType.JoystickButton, 8, _GUID, "Default")
    rig.run.event_handler.add_callback(_GUID, "Default", template, callback)
    _send(rig, _button(8, True))
    _switch("B")
    _send(rig, _button(8, False))
    _send(rig, _button(8, False))  # a repeated release: no second call
    assert calls == [True, False]


def test_a_script_hat_callback_gets_one_centre(rig: SimpleNamespace) -> None:
    rig.run.start(_profile(), "Default")
    calls: list[Any] = []
    template = Event(InputType.JoystickHat, 3, _GUID, "Default")
    rig.run.event_handler.add_callback(
        _GUID, "Default", template, lambda e: calls.append(e.value)
    )
    _send(rig, _hat(3, HatDirection.East))
    _switch("B")
    _send(rig, _hat(3, HatDirection.Center))
    _send(rig, _hat(3, HatDirection.Center))
    assert calls == [HatDirection.East, HatDirection.Center]


# --- 6. Only the ending part runs in the old mode (S38a) ----------------------


def test_a_release_only_action_in_the_old_mode_does_not_run(
    rig: SimpleNamespace,
) -> None:
    profile = _profile()
    on_release = _vjoy(profile, InputType.JoystickButton, InputType.JoystickButton, 9)
    on_release.activation_mode = ActionActivationMode.Release
    _bind(profile, "Default", InputType.JoystickButton, 9, on_release)
    held = _key_action(profile, "F16")  # keeps the binding pending
    _bind(profile, "Default", InputType.JoystickButton, 9, held)
    rig.run.start(profile, "Default")
    _send(rig, _button(9, True))
    _switch("B")
    _send(rig, _button(9, False))
    assert _wait_for(lambda: _keys("F16") == [True, False])
    assert _vjoy_values(rig, "button", 9) == []


def test_an_axis_value_never_goes_to_the_old_mode(rig: SimpleNamespace) -> None:
    profile = _profile()
    _bind(
        profile,
        "Default",
        InputType.JoystickAxis,
        2,
        _vjoy(profile, InputType.JoystickAxis, InputType.JoystickAxis, 2),
    )
    rig.run.start(profile, "Default")
    _send(rig, _axis(2, 0.5))
    _switch("B")
    _send(rig, _axis(2, -0.5))
    assert _vjoy_values(rig, "axis", 2) == [0.5]


# --- 7. No double releases (Risks: double releases) ---------------------------


def test_a_vjoy_button_is_released_once_through_the_output_module(
    rig: SimpleNamespace,
) -> None:
    profile = _profile()
    _bind(
        profile,
        "Default",
        InputType.JoystickButton,
        10,
        _vjoy(profile, InputType.JoystickButton, InputType.JoystickButton, 4),
    )
    rig.run.start(profile, "Default")
    _send(rig, _button(10, True))
    _switch("B")
    _send(rig, _button(10, False))
    _send(rig, _button(10, False))
    assert _vjoy_values(rig, "button", 4) == [True, False]
    # The old mode's own action lets go (Foreign release, write_vjoy), not
    # the ButtonReleaseActions registry.
    assert rig.released == []


def test_every_action_in_a_list_gets_the_release_once(rig: SimpleNamespace) -> None:
    """e30732f8: no short-circuit over children; each output exactly once."""
    profile = _profile()
    binding = _binding(profile, "Default", InputType.JoystickButton, 11)
    for name in ("F16", "F17", "F18"):
        binding.root_action.insert_action(_key_action(profile, name), "children")
    binding.root_action.insert_action(
        _vjoy(profile, InputType.JoystickButton, InputType.JoystickButton, 5),
        "children",
    )
    rig.run.start(profile, "Default")
    _send(rig, _button(11, True))
    _switch("B")
    _send(rig, _button(11, False))
    assert _wait_for(
        lambda: all(_keys(k) == [True, False] for k in ("F16", "F17", "F18"))
    )
    _settle()
    for name in ("F16", "F17", "F18"):
        assert _keys(name) == [True, False], name
    assert _vjoy_values(rig, "button", 5) == [True, False]


# --- 8. Hat turned elsewhere centres the old binding first (S38c) -------------


def test_a_hat_turned_in_the_new_mode_centres_the_old_first(
    rig: SimpleNamespace,
) -> None:
    profile = _profile()
    _bind(
        profile,
        "Default",
        InputType.JoystickHat,
        4,
        _vjoy(profile, InputType.JoystickHat, InputType.JoystickHat, 1),
    )
    _bind(
        profile,
        "B",
        InputType.JoystickHat,
        4,
        _vjoy(profile, InputType.JoystickHat, InputType.JoystickHat, 2),
    )
    rig.run.start(profile, "Default")
    _send(rig, _hat(4, HatDirection.North))
    _switch("B")
    _send(rig, _hat(4, HatDirection.East))  # off centre all along
    hats = [(i, v) for k, i, v in rig.vjoy if k == "hat"]
    assert hats == [
        (1, HatDirection.North),
        (1, HatDirection.Center),  # the old binding first
        (2, HatDirection.East),
    ]


# --- 9. Axis-range button (S38d) ---------------------------------------------


def test_an_axis_range_button_releases_after_a_mode_change(
    rig: SimpleNamespace,
) -> None:
    profile = _profile()
    binding = _binding(profile, "Default", InputType.JoystickAxis, 1)
    binding.virtual_button = gprofile.VirtualAxisButton(0.2, 0.6)
    binding.behavior = InputType.JoystickButton
    binding.root_action.insert_action(
        _vjoy(profile, InputType.JoystickButton, InputType.JoystickButton, 7),
        "children",
    )
    _bind(
        profile,
        "B",
        InputType.JoystickAxis,
        1,
        _vjoy(profile, InputType.JoystickAxis, InputType.JoystickAxis, 1),
    )
    rig.run.start(profile, "Default")
    _send(rig, _axis(1, -0.5))  # the Run's first value: no press
    _send(rig, _axis(1, 0.4))  # into the range: pressed
    assert _vjoy_values(rig, "button", 7) == [True]
    _switch("B")
    _send(rig, _axis(1, 0.9))  # leaves the range, in mode B
    assert _vjoy_values(rig, "button", 7) == [True, False]
    assert _vjoy_values(rig, "axis", 1) == [0.9]  # the new mode has the axis
    _send(rig, _axis(1, 0.5))  # back in range: the old binding is done
    assert _vjoy_values(rig, "button", 7) == [True, False]


# --- 10. The new mode's binding still gets the release (11a) ------------------


def test_the_new_modes_binding_still_gets_the_release(rig: SimpleNamespace) -> None:
    profile = _profile()
    _bind(profile, "Default", InputType.JoystickButton, 12, _key_action(profile, "F16"))
    _bind(
        profile,
        "B",
        InputType.JoystickButton,
        12,
        _vjoy(profile, InputType.JoystickButton, InputType.JoystickButton, 6),
    )
    rig.run.start(profile, "Default")
    _send(rig, _button(12, True))
    _switch("B")
    _send(rig, _button(12, False))
    assert _vjoy_values(rig, "button", 6) == [False]  # as today
    assert _wait_for(lambda: _keys("F16") == [True, False])  # and the old one


# --- 11. The pending table: no stuck entries, cleared at Stop -----------------


def test_same_mode_presses_leave_no_pending_entries(rig: SimpleNamespace) -> None:
    profile = _profile()
    _bind(
        profile,
        "Default",
        InputType.JoystickButton,
        13,
        _vjoy(profile, InputType.JoystickButton, InputType.JoystickButton, 8),
    )
    rig.run.start(profile, "Default")
    handler = rig.run.event_handler
    for _ in range(200):
        _send(rig, _button(13, True))
        _send(rig, _button(13, False))
    assert _pending(handler) == 0
    # A release after a mode change still spends its entry.
    _send(rig, _button(13, True))
    assert _pending(handler) == 1
    _switch("B")
    _send(rig, _button(13, False))
    assert _pending(handler) == 0
    assert _vjoy_values(rig, "button", 8)[-2:] == [True, False]


def test_the_pending_table_is_cleared_at_stop(rig: SimpleNamespace) -> None:
    profile = _profile()
    _bind(profile, "Default", InputType.JoystickButton, 14, _key_action(profile, "F16"))
    rig.run.start(profile, "Default")
    handler = rig.run.event_handler
    _send(rig, _button(14, True))  # held at Stop
    assert _pending(handler) == 1
    rig.run.stop()
    assert _pending(handler) == 0
    rig.run.start(profile, "Default")  # a new Run starts with none
    assert _pending(handler) == 0
