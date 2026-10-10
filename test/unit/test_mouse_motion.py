# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Map to Mouse motion (R9, R9b, G-c).

- 06 S72 (rewritten): motion from several inputs adds up; each button/hat
  ramps on its own; speeds are delivered as set (fixed 100 Hz, R9c).
- 06 S88: a mode change stops motion the new mode doesn't route to the same
  binding (an inherited child mode keeps it).
- 06 S89: Stop drops motion at the first Stop stage (cut input).
- 06 S90: Pause stops motion.
- 06 S86 (changed, G-c): Trace OUTPUT lines for Map to Mouse, one per change,
  never per motion tick.

SendInput is faked: mouse output is recorded, nothing reaches the PC.
"""

from __future__ import annotations

import sys
import threading
import time
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path
from unittest import mock

sys.path.append(".")

import pytest
from PySide6 import QtCore

from action_plugins.map_to_mouse import (
    MapToMouseData,
    MapToMouseFunctor,
    MapToMouseMode,
)
from gremlin import (
    code_runner,
    event_helpers,
    mode_manager,
    run_scope,
    sendinput,
    shared_state,
    threads,
    trace,
    util,
)
from gremlin.base_classes import Value
from gremlin.event_handler import Event
from gremlin.profile import Profile
from gremlin.types import HatDirection, InputType, MouseButton

_GUID = uuid.UUID("77777777-1111-2222-3333-555555555555")
_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


_BUTTONS = {
    sendinput.MOUSEEVENTF_LEFTDOWN: ("left", True),
    sendinput.MOUSEEVENTF_LEFTUP: ("left", False),
}


@pytest.fixture
def mouse(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[tuple]]:
    """Mouse output: ("move", dx, dy) or ("left", is_pressed)."""
    sent: list[tuple] = []

    def record(*inputs: sendinput._INPUT) -> int:
        for item in inputs:
            mi = item.union.mi
            if mi.dwFlags == sendinput.MOUSEEVENTF_MOVE:
                sent.append(("move", mi.dx, mi.dy))
            else:
                sent.append(_BUTTONS.get(mi.dwFlags, ("other", mi.dwFlags)))
        return len(inputs)

    monkeypatch.setattr(sendinput, "_send_input", record)
    yield sent
    run_scope.stop()
    run_scope._reset_for_tests()


def _profile() -> Profile:
    """Modes: Default, Child (inherits Default) and Other."""
    profile = Profile()
    profile.modes.add_mode("Child")
    profile.modes.set_parent("Child", "Default")
    profile.modes.add_mode("Other")
    return profile


class _Bindings:
    """Callbacks the runner installs as if the profile held them."""

    def __init__(self) -> None:
        self.items: list[tuple[str, Event, Callable[[Event], None]]] = []

    def add(self, mode: str, event: Event, functor: MapToMouseFunctor) -> None:
        def callback(evt: Event) -> None:
            value = evt.value if evt.event_type != InputType.JoystickButton else (
                evt.is_pressed
            )
            functor(evt, Value(value))

        self.items.append((mode, event, callback))


@pytest.fixture
def runner(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[code_runner.CodeRunner, _Bindings]]:
    """A real CodeRunner; drivers, devices, sound and network stand-ins."""
    for name in ("output", "OscRuntime", "InputModuleRuntime", "audio_player", "tts"):
        monkeypatch.setattr(code_runner, name, mock.MagicMock())
    listener = mock.MagicMock()
    fake_listener = mock.MagicMock(return_value=listener)
    fake_listener.instance = None
    monkeypatch.setattr(code_runner.event_handler, "EventListener", fake_listener)
    run = code_runner.CodeRunner()
    monkeypatch.setattr(run, "_refresh_axes", lambda: None)
    bindings = _Bindings()

    def setup() -> int:
        for mode, event, callback in bindings.items:
            run.event_handler.add_callback(event.device_guid, mode, event, callback)
        return len(bindings.items)

    monkeypatch.setattr(run, "_setup_profile", setup)
    yield run, bindings
    run.stop()
    run.event_handler.resume()
    shared_state.set_runtime_active(False)


def _wait_for(check: Callable[[], bool], seconds: float = 2.0) -> bool:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if check():
            return True
        time.sleep(0.02)
    return False


def _moves(mouse: list[tuple]) -> list[tuple]:
    return [m for m in mouse if m[0] == "move"]


def _button_data(direction: int = 90, speed: int = 400) -> MapToMouseData:
    data = MapToMouseData(InputType.JoystickButton)
    data.mode = MapToMouseMode.Motion
    data.direction = direction
    data.min_speed = speed
    data.max_speed = speed
    data.time_to_max_speed = 0.0
    return data


def _axis_data(direction: int = 90, speed: int = 400) -> MapToMouseData:
    data = MapToMouseData(InputType.JoystickAxis)
    data.direction = direction
    data.min_speed = 0
    data.max_speed = speed
    return data


def _button(index: int, pressed: bool) -> Event:
    return Event(
        InputType.JoystickButton, index, _GUID, "", is_pressed=pressed,
        raw_value=pressed,
    )


def _axis(index: int, value: float) -> Event:
    return Event(InputType.JoystickAxis, index, _GUID, "", value=value,
                 raw_value=value)


def _hat(index: int, direction: HatDirection) -> Event:
    return Event(InputType.JoystickHat, index, _GUID, "", value=direction,
                 raw_value=direction)


def _switch(name: str) -> None:
    mode_manager.ModeManager().switch_to(mode_manager.Mode(name, None))


def _still(mouse: list[tuple], seconds: float = 0.25) -> bool:
    """No cursor motion for seconds (after what was in flight)."""
    time.sleep(0.05)
    mouse.clear()
    time.sleep(seconds)
    return _moves(mouse) == []


# --- S88: a mode change stops motion the new mode doesn't route --------------


def test_s88_a_mode_change_stops_a_held_buttons_motion(
    runner: tuple[code_runner.CodeRunner, _Bindings], mouse: list[tuple]
) -> None:
    run, bindings = runner
    bindings.add("Default", _button(1, True), MapToMouseFunctor(_button_data()))
    run.start(_profile(), "Default")
    run.event_handler.process_event(_button(1, True))
    assert _wait_for(lambda: bool(_moves(mouse)))
    _switch("Other")  # the release never reaches this binding
    # It used to go on moving until Stop.
    assert _still(mouse)


def test_s88_a_mode_change_stops_an_axis_motion(
    runner: tuple[code_runner.CodeRunner, _Bindings], mouse: list[tuple]
) -> None:
    run, bindings = runner
    bindings.add("Default", _axis(1, 0.0), MapToMouseFunctor(_axis_data()))
    run.start(_profile(), "Default")
    run.event_handler.process_event(_axis(1, 1.0))
    assert _wait_for(lambda: bool(_moves(mouse)))
    _switch("Other")
    assert _still(mouse)


def test_s88_an_inherited_child_mode_keeps_moving(
    runner: tuple[code_runner.CodeRunner, _Bindings], mouse: list[tuple]
) -> None:
    run, bindings = runner
    bindings.add("Default", _button(1, True), MapToMouseFunctor(_button_data()))
    run.start(_profile(), "Default")
    run.event_handler.process_event(_button(1, True))
    assert _wait_for(lambda: bool(_moves(mouse)))
    _switch("Child")  # same binding, inherited from Default
    mouse.clear()
    assert _wait_for(lambda: bool(_moves(mouse)))
    run.event_handler.process_event(_button(1, False))
    assert _still(mouse)


def test_s88_the_new_modes_own_motion_starts_after_the_change(
    runner: tuple[code_runner.CodeRunner, _Bindings], mouse: list[tuple]
) -> None:
    run, bindings = runner
    bindings.add("Default", _button(1, True), MapToMouseFunctor(_button_data(90)))
    bindings.add("Other", _button(2, True), MapToMouseFunctor(_button_data(270)))
    run.start(_profile(), "Default")
    run.event_handler.process_event(_button(1, True))
    assert _wait_for(lambda: bool(_moves(mouse)))
    _switch("Other")
    run.event_handler.process_event(_button(2, True))
    time.sleep(0.05)
    mouse.clear()
    assert _wait_for(lambda: bool(_moves(mouse)))
    assert all(m[1] < 0 for m in _moves(mouse))  # only the Other mode's, left


# --- S89 / S90: Stop and Pause -----------------------------------------------


def test_s89_no_motion_after_the_first_stop_stage(
    runner: tuple[code_runner.CodeRunner, _Bindings], mouse: list[tuple]
) -> None:
    run, bindings = runner
    bindings.add("Default", _button(1, True), MapToMouseFunctor(_button_data()))
    run.start(_profile(), "Default")
    run.event_handler.process_event(_button(1, True))
    assert _wait_for(lambda: bool(_moves(mouse)))
    seen: list[int] = []
    # Stop stages after CUT_INPUT see the motion gone and the cursor still.
    run_scope.on_stop(
        run_scope.Stage.CANCEL, "probe",
        lambda: seen.append(len(sendinput.MouseMotionManager()._sources)),
    )
    count: list[int] = []
    run_scope.on_stop(
        run_scope.Stage.CANCEL, "count", lambda: count.append(len(_moves(mouse)))
    )
    run_scope.on_stop(
        run_scope.Stage.NEUTRAL, "count", lambda: count.append(len(_moves(mouse)))
    )
    run.stop()
    assert seen == [0]
    assert count[0] == count[1]


def test_s90_pause_stops_motion(
    runner: tuple[code_runner.CodeRunner, _Bindings], mouse: list[tuple]
) -> None:
    run, bindings = runner
    bindings.add("Default", _button(1, True), MapToMouseFunctor(_button_data()))
    bindings.add("Default", _axis(1, 0.0), MapToMouseFunctor(_axis_data(0)))
    run.start(_profile(), "Default")
    run.event_handler.process_event(_button(1, True))
    run.event_handler.process_event(_axis(1, 1.0))
    assert _wait_for(lambda: bool(_moves(mouse)))
    run.event_handler.pause()
    assert _still(mouse)
    run.event_handler.resume()
    run.event_handler.process_event(_button(1, True))
    assert _wait_for(lambda: bool(_moves(mouse)))


def test_s90_toggled_pause_stops_motion(
    runner: tuple[code_runner.CodeRunner, _Bindings], mouse: list[tuple]
) -> None:
    run, bindings = runner
    bindings.add("Default", _button(1, True), MapToMouseFunctor(_button_data()))
    run.start(_profile(), "Default")
    run.event_handler.process_event(_button(1, True))
    assert _wait_for(lambda: bool(_moves(mouse)))
    run.event_handler.toggle_active()
    assert _still(mouse)


# --- S72: pieces add up, ramps per input, speeds as set ----------------------


@pytest.fixture
def manager() -> Iterator[sendinput.MouseMotionManager]:
    """The manager without its thread: tests drive _step themselves."""
    motion = sendinput.MouseMotionManager()
    motion.stop()
    yield motion
    motion.reset()


def _key(n: int) -> sendinput.MotionKey:
    return (uuid.UUID(int=n), _button(n, True))


def _run_steps(motion: sendinput.MouseMotionManager, steps: int,
               dt: float = 0.01) -> tuple[int, int]:
    x = y = 0
    for _ in range(steps):
        dx, dy = motion._step(dt)
        x += dx
        y += dy
    return x, y


def test_s72_150_px_per_second_is_delivered_as_set(
    manager: sendinput.MouseMotionManager,
) -> None:
    manager.set_velocity(_key(1), sendinput.Vector2(150.0, 0.0))
    assert _run_steps(manager, 100) == (150, 0)  # sub-pixel carry, 1 s
    manager.set_velocity(_key(1), sendinput.Vector2(0.0, -37.0))
    assert _run_steps(manager, 300) == (0, -111)


def test_s72_two_buttons_same_direction_double_the_speed(
    manager: sendinput.MouseMotionManager,
) -> None:
    right = sendinput.Vector2(1.0, 0.0)
    manager.set_accelerated_motion(_key(1), right, 100, 100, 0.0)
    manager.set_accelerated_motion(_key(2), right, 100, 100, 0.0)
    assert _run_steps(manager, 100) == (200, 0)


def test_s72_axis_and_held_button_both_move(
    manager: sendinput.MouseMotionManager,
) -> None:
    manager.set_velocity(_key(1), sendinput.Vector2(100.0, 0.0))
    manager.set_accelerated_motion(
        _key(2), sendinput.Vector2(0.0, 1.0), 50, 50, 0.0
    )
    assert _run_steps(manager, 100) == (100, 50)
    manager.clear(_key(2))  # button released: the axis keeps its speed
    assert _run_steps(manager, 100) == (100, 0)


def test_s72_each_button_ramps_on_its_own(
    manager: sendinput.MouseMotionManager,
) -> None:
    right = sendinput.Vector2(1.0, 0.0)
    down = sendinput.Vector2(0.0, 1.0)
    manager.set_accelerated_motion(_key(1), right, 0, 100, 1.0)
    _run_steps(manager, 100)  # 1 s: button 1 at full speed
    manager.set_accelerated_motion(_key(2), down, 0, 100, 1.0)
    x, y = _run_steps(manager, 10)
    # Button 1 stays at 100 px/s; button 2 starts its own ramp from 0.
    assert x == 10
    assert 0 <= y <= 1
    # A held button's repeat press keeps its ramp.
    manager.set_accelerated_motion(_key(1), right, 0, 100, 1.0)
    assert _run_steps(manager, 10)[0] == 10


def test_s72_two_actions_on_one_input_are_cleared_independently(
    manager: sendinput.MouseMotionManager,
) -> None:
    event = _button(1, True)
    first = (uuid.UUID(int=1), event)
    second = (uuid.UUID(int=2), event)
    manager.set_velocity(first, sendinput.Vector2(100.0, 0.0))
    manager.set_velocity(second, sendinput.Vector2(0.0, 100.0))
    manager.clear(first)
    assert _run_steps(manager, 100) == (0, 100)


def test_s72_catch_up_is_capped_at_five_ticks() -> None:
    delta_t, next_tick = sendinput._integration_step(10.0, 9.0, 9.0, 0.01)
    assert delta_t == pytest.approx(0.05)
    assert next_tick == pytest.approx(10.0)


def test_s72_hat_center_leaves_a_buttons_motion(
    manager: sendinput.MouseMotionManager,
) -> None:
    button = MapToMouseFunctor(_button_data(90, 100))
    hat_data = MapToMouseData(InputType.JoystickHat)
    hat_data.min_speed = hat_data.max_speed = 100
    hat_data.time_to_max_speed = 0.0
    hat = MapToMouseFunctor(hat_data)
    button(_button(1, True), Value(True))
    hat(_hat(1, HatDirection.North), Value(HatDirection.North))
    assert _run_steps(manager, 100) == (100, -100)
    hat(_hat(1, HatDirection.Center), Value(HatDirection.Center))
    # The old Center set all motion to 0, a held button's too.
    assert _run_steps(manager, 100) == (100, 0)


def test_s72_axis_direction_and_sign(manager: sendinput.MouseMotionManager) -> None:
    horizontal = MapToMouseFunctor(_axis_data(90, 100))
    vertical = MapToMouseFunctor(_axis_data(0, 100))
    horizontal(_axis(1, -0.5), Value(-0.5))
    vertical(_axis(2, 1.0), Value(1.0))
    assert _run_steps(manager, 100) == (-50, 100)
    horizontal(_axis(1, 0.0), Value(0.0))  # back to rest: its piece goes
    assert _run_steps(manager, 100) == (0, 100)


# --- thread rules ------------------------------------------------------------


def _motion_threads() -> list[str]:
    alive = [t.name for t in threading.enumerate() if t.is_alive()]
    return [name for name in alive if name.endswith("mouse motion")]


def test_the_motion_thread_is_bounded_and_shutdown_stops_it(
    mouse: list[tuple],
) -> None:
    motion = sendinput.MouseMotionManager()
    motion.stop()
    for _ in range(10):
        motion.start()
        motion.stop()
        assert not _motion_threads()
    motion.start()
    motion.set_velocity(_key(1), sendinput.Vector2(500.0, 0.0))
    assert _wait_for(lambda: bool(_moves(mouse)))
    # What threads.shutdown() does for this thread (shutdown itself would
    # stop every other thread in the test process too).
    with threads._LOCK:
        mine = [(t, stop) for t, stop in threads._live.items()
                if t.name.endswith("mouse motion")]
    assert len(mine) == 1 and mine[0][1] is not None
    thread, stop = mine[0]
    stop()
    thread.join(1.0)
    assert not thread.is_alive()
    motion.stop()


def test_an_idle_motion_thread_stops_in_time() -> None:
    motion = sendinput.MouseMotionManager()
    motion.stop()
    motion.start()
    time.sleep(0.05)  # idle: waiting for motion
    started = time.monotonic()
    motion.stop()
    assert time.monotonic() - started < 1.0
    assert not _motion_threads()


# --- ModeChangeActions -------------------------------------------------------


def test_mode_change_actions_fire_and_drop_what_ran() -> None:
    actions = event_helpers.ModeChangeActions()
    actions.reset()
    seen: list[tuple[str, str]] = []

    def keep(old: str, new: str) -> bool:
        seen.append((old, new))
        return False

    actions.register("a", keep)
    actions.register("b", lambda old, new: True)
    actions.fire("Default", "Other")
    actions.fire("Other", "Default")
    assert seen == [("Default", "Other"), ("Other", "Default")]
    actions.unregister("a")
    actions.fire("Default", "Other")
    assert len(seen) == 2
    actions.reset()


# --- G-c: Trace OUTPUT lines on change only ----------------------------------


@pytest.fixture
def traced(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(util, "logs_dir", lambda: tmp_path / "logs")
    trace._reset_for_tests()
    trace.set_tick(_GUID, "button", 1, True)
    trace.set_tick(_GUID, "button", 2, True)
    trace.set_tick(_GUID, "axis", 1, True)
    trace.set_enabled(True)
    yield
    trace._reset_for_tests()


def _mouse_lines() -> list[tuple[str, str, str, str, bool]]:
    return [
        line for line in trace.lines()
        if line[2] == trace.OUTPUT and line[3].startswith("Mouse")
    ]


def test_gc_trace_has_one_mouse_output_line_per_change(
    runner: tuple[code_runner.CodeRunner, _Bindings],
    mouse: list[tuple],
    traced: None,
) -> None:
    run, bindings = runner
    bindings.add("Default", _button(1, True), MapToMouseFunctor(_button_data()))
    click = MapToMouseData(InputType.JoystickButton)
    click.button = MouseButton.Left
    bindings.add("Default", _button(2, True), MapToMouseFunctor(click))
    run.start(_profile(), "Default")
    run.event_handler.process_event(_button(1, True))
    assert _wait_for(lambda: len(_moves(mouse)) > 5)  # many ticks
    run.event_handler.process_event(_button(1, False))
    run.event_handler.process_event(_button(2, True))
    run.event_handler.process_event(_button(2, False))
    texts = [line[3] for line in _mouse_lines()]
    assert len(texts) == 4, texts
    assert "motion" in texts[0] and "400" in texts[0]
    assert "stopped" in texts[1]
    assert texts[2] == "Mouse Left = pressed"
    assert texts[3] == "Mouse Left = released"


def test_gc_untraced_input_writes_no_mouse_line(
    runner: tuple[code_runner.CodeRunner, _Bindings],
    mouse: list[tuple],
    traced: None,
) -> None:
    run, bindings = runner
    bindings.add("Default", _button(3, True), MapToMouseFunctor(_button_data()))
    run.start(_profile(), "Default")
    run.event_handler.process_event(_button(3, True))
    run.event_handler.process_event(_button(3, False))
    assert _mouse_lines() == []
