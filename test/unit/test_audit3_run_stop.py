# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Run -> Stop -> Run leaves nothing behind (audit 3).

- Keys a macro holds at Stop are released (Map to Keyboard: also when its
  release macro was still queued and Stop dropped it).
- Mouse buttons held at Stop (Map to Mouse, a macro) are released.
- Mouse motion of the last Run doesn't move the cursor in the next one.
- The Logical Device relative axis loop ends with Stop and doesn't feed the
  next Run.
- A Condition on a stick plugged in after the profile loaded works.

No real input reaches the PC: key and mouse output is recorded here (and
test/fake_input.py keeps it in the process anyway).
"""

from __future__ import annotations

import sys
import threading
import time
import uuid
from collections.abc import Callable, Iterator
from unittest import mock

sys.path.append(".")

import pytest
from PySide6 import QtCore

from gremlin import code_runner, error, macro, sendinput, shared_state
from gremlin.base_classes import Value
from gremlin.event_handler import Event
from gremlin.keyboard import Key, key_from_name
from gremlin.macro import Macro, MacroManager, PauseAction
from gremlin.profile import Profile
from gremlin.types import AxisMode, InputType, MouseButton

_GUID = uuid.UUID("77777777-1111-2222-3333-444444444444")
_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


@pytest.fixture
def keys(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, bool]]:
    """Key output as (name, is_pressed), in order."""
    sent: list[tuple[str, bool]] = []
    # Lower case: a key's name is "a" or "A" depending on whether the full
    # key table was loaded by an earlier test.
    monkeypatch.setattr(
        macro, "send_key_down", lambda k: sent.append((k.name.lower(), True))
    )
    monkeypatch.setattr(
        macro, "send_key_up", lambda k: sent.append((k.name.lower(), False))
    )
    return sent


_DOWN = {
    sendinput.MOUSEEVENTF_LEFTDOWN: ("left", True),
    sendinput.MOUSEEVENTF_LEFTUP: ("left", False),
    sendinput.MOUSEEVENTF_RIGHTDOWN: ("right", True),
    sendinput.MOUSEEVENTF_RIGHTUP: ("right", False),
}


@pytest.fixture
def mouse(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[tuple]]:
    """Mouse output: ("left"/"right", is_pressed) or ("move", dx, dy)."""
    sent: list[tuple] = []

    def record(*inputs: sendinput._INPUT) -> int:
        for item in inputs:
            mi = item.union.mi
            if mi.dwFlags == sendinput.MOUSEEVENTF_MOVE:
                sent.append(("move", mi.dx, mi.dy))
            else:
                sent.append(_DOWN.get(mi.dwFlags, ("other", mi.dwFlags)))
        return len(inputs)

    monkeypatch.setattr(sendinput, "_send_input", record)
    yield sent
    getattr(sendinput, "_held_buttons", []).clear()


@pytest.fixture
def runner(monkeypatch: pytest.MonkeyPatch) -> Iterator[code_runner.CodeRunner]:
    """A CodeRunner whose drivers, devices, sound and network are stand-ins;
    macros and the mouse controller are the real ones."""
    for name in ("output", "OscRuntime", "InputModuleRuntime", "audio_player", "tts"):
        monkeypatch.setattr(code_runner, name, mock.MagicMock())
    listener = mock.MagicMock()
    fake_listener = mock.MagicMock(return_value=listener)
    fake_listener.instance = None
    monkeypatch.setattr(code_runner.event_handler, "EventListener", fake_listener)
    run = code_runner.CodeRunner()
    monkeypatch.setattr(run, "_refresh_axes", lambda: None)
    yield run
    run.stop()
    shared_state.set_runtime_active(False)


def _wait_for(check: Callable[[], bool], seconds: float = 2.0) -> bool:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if check():
            return True
        time.sleep(0.02)
    return False


# --- keys and mouse buttons held at Stop -------------------------------------


def test_a_key_a_macro_holds_is_released_at_stop(
    keys: list[tuple[str, bool]],
) -> None:
    mm = MacroManager()
    mm.start()
    held = Macro()
    held.press(key_from_name("a"))
    held.add_action(PauseAction(2.0))
    held.release(key_from_name("a"))
    mm.queue_macro(held)
    assert _wait_for(lambda: keys == [("a", True)])
    mm.stop()  # between press and release
    # It stayed down: Stop ended the macro and released nothing.
    assert keys == [("a", True), ("a", False)]
    mm.stop()  # a second Stop (quit after Stop) sends nothing more
    assert keys == [("a", True), ("a", False)]


def test_map_to_keyboard_keys_are_released_when_stop_drops_the_release(
    keys: list[tuple[str, bool]],
) -> None:
    from action_plugins.map_to_keyboard import MapToKeyboardData, MapToKeyboardFunctor

    data = MapToKeyboardData()
    data.keys = [key_from_name("leftcontrol"), key_from_name("a")]
    functor = MapToKeyboardFunctor(data)
    press = Event(InputType.JoystickButton, 1, _GUID, "Default", is_pressed=True)
    release = Event(InputType.JoystickButton, 1, _GUID, "Default", is_pressed=False)

    mm = MacroManager()
    mm.start()
    try:
        functor(press, Value(True))
        assert _wait_for(lambda: len(keys) == 2)
        # The release (a flushed pulse release does the same) only queues a
        # macro; here it waits behind an exclusive one, and Stop drops it.
        mm._is_executing_exclusive = True
        functor(release, Value(False))
        time.sleep(0.1)
        assert len(keys) == 2  # the release hasn't run
    finally:
        mm.stop()
    downs = [k for k, pressed in keys if pressed]
    ups = [k for k, pressed in keys if not pressed]
    assert sorted(ups) == sorted(downs)  # both used to stay down
    assert ups[0] == downs[-1]  # last pressed, first released


def test_mouse_buttons_held_at_stop_are_released(
    runner: code_runner.CodeRunner,
    mouse: list[tuple],
    keys: list[tuple[str, bool]],
) -> None:
    from action_plugins.map_to_mouse import MapToMouseData, MapToMouseFunctor

    runner.start(Profile(), "Default")
    data = MapToMouseData()
    data.button = MouseButton.Left
    MapToMouseFunctor(data)(
        Event(InputType.JoystickButton, 2, _GUID, "Default", is_pressed=True),
        Value(True),
    )
    right = Macro()
    right.add_action(macro.MouseButtonAction(MouseButton.Right, True))
    right.add_action(PauseAction(2.0))
    right.add_action(macro.MouseButtonAction(MouseButton.Right, False))
    MacroManager().queue_macro(right)
    assert _wait_for(lambda: ("right", True) in mouse)
    runner.stop()
    buttons = [m for m in mouse if m[0] in ("left", "right")]
    assert buttons == [
        ("left", True),
        ("right", True),
        ("right", False),
        ("left", False),
    ]


def test_mouse_motion_of_the_last_run_stops_with_it(
    runner: code_runner.CodeRunner, mouse: list[tuple]
) -> None:
    runner.start(Profile(), "Default")
    controller = sendinput.MouseController()
    controller.set_absolute_motion(500, 0)  # an axis held over at Stop
    assert _wait_for(lambda: any(m[0] == "move" for m in mouse))
    runner.stop()
    mouse.clear()
    runner.start(Profile(), "Default")  # Run again, the axis untouched
    time.sleep(0.3)
    runner.stop()
    # The cursor used to go on moving at the old speed.
    assert [m for m in mouse if m[0] == "move"] == []


# --- action loops end per Run ------------------------------------------------


def test_the_logical_device_relative_loop_ends_with_stop(
    runner: code_runner.CodeRunner,
) -> None:
    from action_plugins.map_to_logical_device import (
        MapToLogicalDeviceData,
        MapToLogicalDeviceFunctor,
    )

    runner.start(Profile(), "Default")
    data = MapToLogicalDeviceData(InputType.JoystickAxis)
    data.axis_mode = AxisMode.Relative
    functor = MapToLogicalDeviceFunctor(data)
    functor._event_listener = mock.MagicMock()  # counts this loop's events only
    emit = functor._event_listener.joystick_event.emit
    try:
        axis = Event(InputType.JoystickAxis, 1, _GUID, "Default", value=0.5)
        functor(axis, Value(0.5))  # held over: the loop keeps moving it
        assert _wait_for(lambda: emit.call_count > 3)
        runner.stop()
        runner.start(Profile(), "Default")  # Run again
        thread = functor.thread
        assert thread is not None
        assert _wait_for(lambda: not thread.is_alive(), 1.0)
        count = emit.call_count
        time.sleep(0.2)
        # It used to go on sending into the new Run.
        assert emit.call_count == count
    finally:
        functor.thread_running = False
        if functor.thread is not None:
            functor.thread.join(timeout=2.0)


# --- Condition on a stick plugged in later -----------------------------------


def test_a_condition_on_a_stick_plugged_in_later_works(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from action_plugins.condition import condition as ca

    plugged: dict[uuid.UUID, object] = {}

    class Sticks:
        def __getitem__(self, guid: uuid.UUID) -> object:
            if guid not in plugged:
                raise error.GremlinError(f"No device with guid '{guid}' exists")
            return plugged[guid]

    monkeypatch.setattr(ca, "Joystick", Sticks)
    monkeypatch.setattr(ca.inputs, "button_pressed", lambda guid, ident: True)
    state = ca.JoystickCondition.State(_GUID, InputType.JoystickButton, 3)
    with pytest.raises(error.GremlinError):
        state.get(Value(True))  # not plugged in yet
    assert state.display_name().startswith("Unknown Joystick")

    stick = mock.MagicMock()
    stick.name = "Late Stick"
    plugged[_GUID] = stick
    # It refused on every press until the profile was loaded again.
    assert state.get(Value(True)) is True
    assert state.display_name().startswith("Late Stick")


# --- a step stuck in a driver, a release that fails --------------------------


@pytest.fixture
def stuck_key(
    monkeypatch: pytest.MonkeyPatch, keys: list[tuple[str, bool]]
) -> Iterator[tuple[threading.Event, threading.Event]]:
    """Pressing "b" hangs (a driver that doesn't return) until let go.
    Yields (entered, let_go)."""
    entered = threading.Event()
    let_go = threading.Event()

    def down(key: Key) -> None:
        if key.name == "b":
            entered.set()
            let_go.wait(5.0)
        keys.append((key.name, True))

    monkeypatch.setattr(macro, "send_key_down", down)
    yield entered, let_go
    let_go.set()


def test_a_step_stuck_in_a_driver_ends_the_other_macros(
    monkeypatch: pytest.MonkeyPatch,
    keys: list[tuple[str, bool]],
    stuck_key: tuple[threading.Event, threading.Event],
) -> None:
    entered, let_go = stuck_key
    monkeypatch.setattr(macro, "_STEP_LOCK_TIMEOUT", 0.3)
    mm = MacroManager()
    mm.start()
    try:
        stuck = Macro()
        stuck.press(key_from_name("b"))
        mm.queue_macro(stuck)
        assert entered.wait(2.0)
        other = Macro()
        other.press(key_from_name("c"))
        mm.queue_macro(other)
        assert _wait_for(lambda: other.id in mm._scheduled_macro)
        # It used to wait on the stuck step without end (and every macro
        # after it too).
        assert _wait_for(lambda: other.id not in mm._scheduled_macro, 2.0)
        let_go.set()
        assert _wait_for(lambda: ("b", True) in keys)
        time.sleep(0.2)
        assert ("c", True) not in keys  # it ended, not ran late
    finally:
        let_go.set()
        mm.stop()


def test_stop_during_a_step_in_progress_ends_the_macro(
    keys: list[tuple[str, bool]],
    stuck_key: tuple[threading.Event, threading.Event],
) -> None:
    entered, let_go = stuck_key
    mm = MacroManager()
    mm.start()
    steps = Macro()
    steps.press(key_from_name("b"))
    steps.press(key_from_name("d"))
    mm.queue_macro(steps)
    assert entered.wait(2.0)
    start = time.monotonic()
    mm.stop()  # the press of "b" is still in the driver
    assert time.monotonic() - start < 4.0  # Stop doesn't wait on it for ever
    let_go.set()
    assert _wait_for(lambda: ("b", True) in keys)
    time.sleep(0.2)
    assert ("d", True) not in keys  # no step after Stop
    mm.stop()  # lets go of "b", which went down after the first Stop
    assert keys[-1] == ("b", False)


def test_a_failing_mouse_release_doesnt_cut_stop_short(
    monkeypatch: pytest.MonkeyPatch,
    runner: code_runner.CodeRunner,
    mouse: list[tuple],
) -> None:
    runner.start(Profile(), "Default")
    sendinput.mouse_press(MouseButton.Left)
    sendinput.mouse_press(MouseButton.Right)
    record = sendinput._send_input

    def send(*inputs: sendinput._INPUT) -> int:
        if inputs[0].union.mi.dwFlags == sendinput.MOUSEEVENTF_RIGHTUP:
            raise OSError("driver refused")
        return record(*inputs)

    monkeypatch.setattr(sendinput, "_send_input", send)
    reset = code_runner.output.reset_drivers
    reset.reset_mock()
    # The failing release (Right, released first) used to end Stop there:
    # Left stayed down and the drivers weren't reset.
    runner.stop()
    assert ("left", False) in mouse
    reset.assert_called()
