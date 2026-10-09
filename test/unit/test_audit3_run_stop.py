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

import contextlib
import sys
import threading
import time
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any
from unittest import mock

sys.path.append(".")

import pytest
from PySide6 import QtCore

from gremlin import code_runner, error, macro, run_scope, sendinput, shared_state
from gremlin.base_classes import Value
from gremlin.event_handler import Event
from gremlin.keyboard import Key, key_from_name
from gremlin.macro import Macro, MacroManager, PauseAction
from gremlin.profile import Profile
from gremlin.types import AxisMode, DataCreationMode, InputType, MouseButton

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
    run_scope.stop()
    run_scope._reset_for_tests()


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


def _macros_in_a_run() -> MacroManager:
    """The macro manager started in a Run whose Stop ends it (as CodeRunner
    registers it): keys are tracked only during a Run (decision R4)."""
    run_scope.stop()
    run_scope.begin()
    mm = MacroManager()
    run_scope.on_stop(run_scope.Stage.END_WORK, "macros", mm.stop)
    mm.start()
    return mm


def test_a_key_a_macro_holds_is_released_at_stop(
    keys: list[tuple[str, bool]],
) -> None:
    mm = _macros_in_a_run()
    held = Macro()
    held.press(key_from_name("a"))
    held.add_action(PauseAction(2.0))
    held.release(key_from_name("a"))
    mm.queue_macro(held)
    assert _wait_for(lambda: keys == [("a", True)])
    run_scope.stop()  # between press and release
    # It used to stay down: Stop ended the macro and released nothing.
    assert keys == [("a", True), ("a", False)]
    run_scope.stop()  # a second Stop (quit after Stop) sends nothing more
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

    mm = _macros_in_a_run()
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
        mm._is_executing_exclusive = False
        run_scope.stop()
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
    data = MapToLogicalDeviceData.create(
        DataCreationMode.Create, InputType.JoystickAxis)
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
        # Lower case, as in keys: a key read back by scan code earlier in the
        # process is cached under its Windows name ("B").
        name = key.name.lower()
        if name == "b":
            entered.set()
            let_go.wait(5.0)
        keys.append((name, True))

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
    mm = _macros_in_a_run()
    steps = Macro()
    steps.press(key_from_name("b"))
    steps.press(key_from_name("d"))
    mm.queue_macro(steps)
    assert entered.wait(2.0)
    start = time.monotonic()
    run_scope.stop()  # the press of "b" is still in the driver
    assert time.monotonic() - start < 4.0  # Stop doesn't wait on it for ever
    let_go.set()
    assert _wait_for(lambda: ("b", True) in keys)
    # "b" went down after Stop: it is let go at once, not left held.
    assert _wait_for(lambda: keys[-1] == ("b", False))
    time.sleep(0.2)
    assert ("d", True) not in keys  # no step after Stop


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


# --- run_scope: one owner of what a Run holds (map 3, GL-046) ---------------


@pytest.fixture
def scope() -> Iterator[Any]:
    """run_scope with nothing left from another test, and nothing left after."""
    from gremlin import run_scope

    run_scope.stop()
    run_scope._reset_for_tests()
    yield run_scope
    run_scope.stop()
    run_scope._reset_for_tests()


def _qt_wait(check: Callable[[], bool], seconds: float = 2.0) -> bool:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        QtCore.QCoreApplication.processEvents()
        if check():
            return True
        time.sleep(0.01)
    return False


def test_stop_runs_the_stages_in_the_maps_order(scope: Any) -> None:  # noqa: ANN401
    order: list[str] = []
    scope.begin()
    # Registered out of order: Stop runs them by stage, in the map's order.
    for stage in reversed(list(scope.Stage)):
        scope.on_stop(stage, stage.name, lambda s=stage: order.append(s.name))
    scope.stop()
    assert order == [
        "CUT_INPUT",
        "CANCEL",
        "FIRE_PENDING",
        "END_WORK",
        "RELEASE_HELD",
        "NEUTRAL",
        "DRIVERS",
    ]


def test_stop_twice_runs_each_step_once(scope: Any) -> None:  # noqa: ANN401
    done: list[str] = []
    scope.begin()
    scope.on_stop(scope.Stage.DRIVERS, "drivers", lambda: done.append("d"))
    scope.stop()
    scope.stop()  # quit after Stop
    assert done == ["d"]


def test_a_failing_step_doesnt_cut_stop_short(scope: Any) -> None:  # noqa: ANN401
    done: list[str] = []

    def broken() -> None:
        raise RuntimeError("driver refused")

    scope.begin()
    scope.on_stop(scope.Stage.CANCEL, "broken", broken)
    scope.on_stop(scope.Stage.DRIVERS, "drivers", lambda: done.append("d"))
    scope.stop()
    assert done == ["d"]


def test_the_run_number_changes_at_run_and_stop(scope: Any) -> None:  # noqa: ANN401
    run = scope.begin()
    assert scope.alive(run) and scope.running()
    assert code_runner.run_number() == run  # the one counter
    scope.stop()
    assert not scope.alive(run) and not scope.running()
    assert scope.begin() != run


def test_a_run_timer_fires_while_running_never_after_stop(
    scope: Any,  # noqa: ANN401
) -> None:
    fired: list[str] = []
    scope.begin()
    scope.timer("kept", 0.01, fired.append, "kept")
    assert _qt_wait(lambda: fired == ["kept"])
    scope.timer("late", 0.05, fired.append, "late")
    scope.stop()
    time.sleep(0.1)
    QtCore.QCoreApplication.processEvents()
    assert fired == ["kept"]
    assert scope.pending_timers() == []


def test_a_pulse_release_timer_fires_at_stop_before_the_drivers(
    scope: Any,  # noqa: ANN401
) -> None:
    order: list[str] = []
    scope.begin()
    scope.on_stop(scope.Stage.DRIVERS, "drivers", lambda: order.append("d"))
    scope.timer("pulse", 5.0, order.append, "release", at_stop="fire")
    scope.stop()
    assert order == ["release", "d"]


def test_held_outputs_are_released_last_pressed_first(
    scope: Any,  # noqa: ANN401
) -> None:
    released: list[str] = []
    scope.begin()
    for name in ("a", "b", "c"):
        scope.hold(None, "key", name, lambda n=name: released.append(n))
    scope.let_go(None, "key", "b")  # released normally
    scope.stop()
    assert released == ["c", "a"]
    assert scope.held() == []


def test_a_macro_ending_early_lets_go_of_its_own_keys(
    scope: Any,  # noqa: ANN401
) -> None:
    released: list[str] = []
    mine, other = object(), object()
    scope.begin()
    scope.hold(mine, "key", "a", lambda: released.append("a"))
    scope.hold(other, "key", "b", lambda: released.append("b"))
    scope.release_owner(mine)
    assert released == ["a"]
    assert scope.held() == [("key", "b")]


def test_keys_sent_with_no_run_are_not_tracked(scope: Any) -> None:  # noqa: ANN401
    scope.hold(None, "key", "a", lambda: None)  # decision R4
    assert scope.held() == []


def test_a_loop_gets_its_run_and_ends_with_it(scope: Any) -> None:  # noqa: ANN401
    seen: list[int] = []

    def loop(run: int) -> None:
        seen.append(run)
        while scope.alive(run):
            time.sleep(0.01)

    run = scope.begin()
    thread = scope.loop("test loop", loop)
    assert _wait_for(lambda: seen == [run])
    scope.stop()
    scope.begin()  # Run again at once
    thread.join(timeout=2.0)
    assert not thread.is_alive()


# --- the main-thread timers are listed and stopped (GL-047) -------------------


def test_main_thread_timers_are_listed_and_shut_down() -> None:
    from gremlin import threads

    fired: list[bool] = []
    timer = threads.main_timer("listed timer", 5.0, lambda: fired.append(True))
    try:
        assert threads.PREFIX + "listed timer" in threads.running()
        threads.shutdown(timeout=0.5)
        assert not timer.is_alive()
        assert threads.PREFIX + "listed timer" not in threads.running()
    finally:
        timer.cancel()
    assert fired == []


# --- what CodeRunner's Run ends (GL-046, GL-052, GL-055, GL-062, GL-084) ------


def test_the_mode_stack_starts_fresh_and_temporary_modes_end_with_stop(
    runner: code_runner.CodeRunner,
) -> None:
    from gremlin import mode_manager

    profile = Profile()
    profile.modes.add_mode("Flight")
    mm = mode_manager.ModeManager()
    stack = list(mm._mode_stack)
    try:
        runner.start(profile, "Default")
        mm.temporary(mode_manager.Mode("Flight", "Default"))
        assert mm.current.name == "Flight"
        runner.stop()
        assert not any(m.is_temporary for m in mm._mode_stack)
        assert mm.current.name == "Default"
        runner.start(profile, "Flight")  # the toolbar mode
        assert [m.name for m in mm._mode_stack] == ["Flight"]
        runner.stop()
    finally:
        mm._mode_stack = stack


def test_output_modules_saved_while_running_apply_at_once(
    runner: code_runner.CodeRunner,
) -> None:
    from gremlin.signal import signal

    refresh = code_runner.output.refresh
    runner.start(Profile(), "Default")
    refresh.reset_mock()
    signal.configChanged.emit()
    assert refresh.call_count == 1
    runner.stop()
    signal.configChanged.emit()
    assert refresh.call_count == 1  # not after Stop


def test_script_folders_are_taken_off_the_path_at_stop(
    runner: code_runner.CodeRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "path", list(sys.path))
    before = list(sys.path)
    runner.start(Profile(), "Default")
    sys.path.append("C:/a script folder")  # as _setup_user_scripts adds one
    runner.stop()
    assert sys.path == before


def test_an_unfinished_action_is_named_when_the_run_is_built(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin import plugin_manager

    profile = Profile()
    monkeypatch.setattr(shared_state, "current_profile", profile)
    item = profile.get_input_item(
        _GUID, InputType.JoystickButton, 1, "Default", create_if_missing=True
    )
    root = item.add_item_binding().root_action
    reference = plugin_manager.PluginManager().create_instance(
        "Reference", InputType.JoystickButton
    )
    assert not reference.is_valid()
    root.insert_action(reference, "children")
    with contextlib.suppress(Exception):  # leaving it out is base_classes' part
        code_runner.CallbackObject(item.action_sequences[0])
    lines = [r.getMessage() for r in caplog.records]
    assert any(line.startswith("not finished: ") for line in lines), lines


# --- Load Profile waits for its event to end (GL-057) -------------------------


@pytest.fixture
def load_action(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    scope: Any,  # noqa: ANN401
) -> Iterator[tuple[Any, list, Any]]:
    from action_plugins.load_profile import LoadProfileFunctor
    from gremlin import plugin_manager
    from gremlin.ui import backend

    monkeypatch.setattr(shared_state, "current_profile", Profile())
    calls: list = []
    fake = mock.MagicMock()
    fake.profile.has_unsaved_changes.return_value = False
    fake.run_profile.side_effect = lambda path: calls.append(("run", path))
    monkeypatch.setattr(backend, "Backend", lambda: fake)
    data = plugin_manager.PluginManager().create_instance(
        "Load Profile", InputType.JoystickButton
    )
    target = tmp_path / "other.xml"
    target.write_text("<profile/>")
    data.profile_filename = str(target)
    yield LoadProfileFunctor(data), calls, scope


def _press_load(functor: Any) -> None:  # noqa: ANN401
    event = Event(InputType.JoystickButton, 1, _GUID, "Default", is_pressed=True)
    functor(event, Value(True), [])


def test_load_profile_runs_the_profile_after_its_event(
    load_action: tuple[Any, list, Any],
) -> None:
    functor, calls, scope = load_action
    scope.begin()
    _press_load(functor)
    assert calls == []  # not from inside the event
    assert _qt_wait(lambda: bool(calls))
    assert calls == [("run", str(functor.data.profile_filename))]


def test_a_stop_before_it_drops_the_load(load_action: tuple[Any, list, Any]) -> None:
    functor, calls, scope = load_action
    scope.begin()
    _press_load(functor)
    scope.stop()
    time.sleep(0.05)
    QtCore.QCoreApplication.processEvents()
    assert calls == []


# --- quitting stops once (GL-063) ---------------------------------------------


def test_quitting_stops_once_and_makes_nothing_to_stop_it(
    monkeypatch: pytest.MonkeyPatch,
    scope: Any,  # noqa: ANN401
) -> None:
    import joystick_gremlin
    from gremlin import event_handler
    from gremlin.modules import output
    from gremlin.ui import backend

    resets: list[bool] = []
    monkeypatch.setattr(output, "reset_drivers", lambda: resets.append(True))
    monkeypatch.setattr(joystick_gremlin, "_shutdown_done", False)
    monkeypatch.setattr(event_handler.EventListener, "instance", None)
    monkeypatch.setattr(backend.Backend, "instance", None)
    joystick_gremlin.shutdown_cleanup()
    joystick_gremlin.shutdown_cleanup()  # aboutToQuit, then after exec
    assert resets == [True]
    # No listener or window was made just to be stopped.
    assert event_handler.EventListener.instance is None
    assert backend.Backend.instance is None


# --- the mode is stamped above the input layer (GL-060, GL-065) ---------------


def test_the_handler_stamps_the_current_mode_on_hardware_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin import event_handler, mode_manager

    mm = mode_manager.ModeManager()
    stack = list(mm._mode_stack)
    try:
        mm._mode_stack = [mode_manager.Mode("Flight", None)]
        event = Event(
            InputType.JoystickButton, 1, _GUID, event_handler.NO_MODE, is_pressed=True
        )
        handler = event_handler.EventHandler()
        monkeypatch.setattr(handler, "_matching_callbacks", lambda e: [])
        handler.process_event(event)
        assert event.mode == "Flight"
        virtual = Event(InputType.JoystickButton, 1, _GUID, "Default", is_pressed=True)
        handler.process_event(virtual)
        assert virtual.mode == "Default"  # an event with its own mode keeps it
    finally:
        mm._mode_stack = stack


def test_the_listener_does_not_ask_the_mode_manager() -> None:
    import ast
    import inspect

    from gremlin import event_handler

    source = inspect.getsource(event_handler.EventListener.klass)
    names = {
        n.attr for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Attribute)
    }
    assert "ModeManager" not in names and "_modes" not in names
