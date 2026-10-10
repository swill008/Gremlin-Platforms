# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Stage 1 safety net for Run and Stop (spec page 06).

Covers gap-list items:

- GL-004: a failed start then Run again (GL-054), the order of CodeRunner's
  start and Stop steps (06 S18, S24, S29), Tempo timers after Stop (GL-047,
  06 S30) and release callbacks left at Stop (GL-051, 06 Q2).
- GL-005: axis-range and hat virtual buttons (06 S39, S40, Q13), a vJoy
  button released after the mode changed (06 S38), vJoy Initial Values at
  Run (GL-056, 06 S8, Q7).
- GL-006: the Xbox pad unplugged at Stop (06 S29, S57), sound and speech
  modes (06 S73, S76) and their late requests (GL-058, 06 Q8), the Paused
  status and a Run starting un-paused (06 S2, S37), the tray label and icon
  (06 S3), device change behaviour (06 S42) and auto-load on focus loss
  (06 S45).

Where today's code differs from the spec the test is written for the spec
and marked xfail(strict=True) with its GL id, so it flips when fixed.

Nothing reaches the PC: drivers, sound, speech and Win32 calls are
stand-ins, keys and mouse go to test/fake_input.py.
"""

from __future__ import annotations

import contextlib
import re
import sys
import threading
import time
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest import mock

sys.path.append(".")

import pytest
from PySide6 import QtCore, QtQml

from gremlin import (
    code_runner,
    event_handler,
    event_helpers,
    shared_state,
    signal,
    threads,
)
from gremlin.base_classes import Value
from gremlin.common import SingletonMetaclass
from gremlin.event_handler import Event
from gremlin.profile import Profile
from gremlin.types import AxisButtonDirection, HatDirection, InputType

_ROOT = Path(__file__).resolve().parents[2]
_GUID = uuid.UUID("77777777-5555-2222-3333-444444444444")
_VJOY_GUID = uuid.UUID("77777777-6666-2222-3333-444444444444")
_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


def _wait_for(check: Callable[[], bool], seconds: float = 5.0) -> bool:
    """Polls check (running Qt events) until it is True or time runs out."""
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        QtCore.QCoreApplication.processEvents()
        if check():
            return True
        time.sleep(0.01)
    return False


def _fake_listener(monkeypatch: pytest.MonkeyPatch, listener: object) -> None:
    fake = mock.MagicMock(return_value=listener)
    fake.instance = None
    monkeypatch.setattr(code_runner.event_handler, "EventListener", fake)


@pytest.fixture
def runner(monkeypatch: pytest.MonkeyPatch) -> Iterator[code_runner.CodeRunner]:
    """A CodeRunner whose drivers, devices, sound and network are stand-ins;
    macros, the mouse controller and the event handler are the real ones."""
    for name in ("output", "OscRuntime", "InputModuleRuntime", "audio_player", "tts"):
        monkeypatch.setattr(code_runner, name, mock.MagicMock())
    _fake_listener(monkeypatch, mock.MagicMock())
    run = code_runner.CodeRunner()
    monkeypatch.setattr(run, "_refresh_axes", lambda: None)
    yield run
    run.stop()
    shared_state.set_runtime_active(False)
    event_handler.EventHandler().resume()


@pytest.fixture
def release_actions() -> Iterator[Any]:
    """The shared release registry, emptied and back in its mode after."""
    bra = event_helpers.ButtonReleaseActions()
    mode = bra._current_mode
    bra.reset()
    yield bra
    bra.reset()
    bra._mode_changed_cb(mode)


# --- GL-004 / GL-054: a failed start, then Run again -------------------------


class _Bus(QtCore.QObject):
    """The input modules' event bus, with real signals."""

    event = QtCore.Signal(object)  # pyright: ignore[reportAssignmentType]
    key_event = QtCore.Signal(object)

    def reload(self) -> None:
        pass


class _Listener(QtCore.QObject):
    virtual_event = QtCore.Signal(object)
    # The axis refresh at a mode change sends physical values through it.
    joystick_event = QtCore.Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.gremlin_active = False


@pytest.fixture
def wired(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[SimpleNamespace]:
    """A CodeRunner wired to real signals; handled events are counted."""
    for name in ("output", "OscRuntime", "audio_player", "tts"):
        monkeypatch.setattr(code_runner, name, mock.MagicMock())
    bus = _Bus()
    listener = _Listener()
    monkeypatch.setattr(code_runner, "InputModuleRuntime", lambda: bus)
    _fake_listener(monkeypatch, listener)
    handled: list[object] = []
    run = code_runner.CodeRunner()
    handler = mock.MagicMock()
    handler.process_event = handled.append
    run.event_handler = handler
    monkeypatch.setattr(run, "_refresh_axes", lambda: None)
    yield SimpleNamespace(run=run, bus=bus, listener=listener, handled=handled)
    run.stop()
    shared_state.set_runtime_active(False)


def _fail_once(target: mock.MagicMock) -> None:
    calls = {"n": 0}

    def maybe_fail() -> None:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("speech engine failed")

    target.side_effect = maybe_fail


def test_a_failed_start_then_run_again_handles_each_event_once(
    wired: SimpleNamespace,
) -> None:
    # The start fails after the input signals were connected.
    _fail_once(cast(Any, code_runner.tts).TTSManager.return_value.start)
    with pytest.raises(RuntimeError):
        wired.run.start(Profile(), "Default")
    wired.run.start(Profile(), "Default")  # Run pressed again
    assert wired.run.is_running()
    wired.bus.event.emit("press")
    assert wired.handled == ["press"]


def test_a_start_failing_late_leaves_the_runner_stopped(
    wired: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken() -> None:
        raise RuntimeError("axis refresh failed")

    monkeypatch.setattr(wired.run, "_refresh_axes", broken)
    with contextlib.suppress(RuntimeError):
        wired.run.start(Profile(), "Default")
    assert not wired.run.is_running()
    assert not shared_state.runtime_active()
    wired.bus.event.emit("press")
    assert wired.handled == []  # nothing connected is left


def test_a_failed_run_shows_one_error_and_reads_stopped(
    wired: SimpleNamespace,
) -> None:
    from gremlin.ui import backend as backend_mod

    # The backend imports display_error by name, so the error is counted
    # where every display_error ends: the showError signal.
    errors: list[tuple] = []

    def shown(message: str, details: str) -> None:
        errors.append((message, details))

    _fail_once(cast(Any, code_runner.tts).TTSManager.return_value.start)
    stub: Any = SimpleNamespace(
        runner=wired.run,
        profile=Profile(),
        ui_state=SimpleNamespace(currentMode="Default"),
        config=SimpleNamespace(value=lambda *_a: True),
        activityChanged=mock.MagicMock(),
        # No window is holding highlighting off (Calibration, OSC Add).
        _highlight_holders=set(),
    )
    highlighting = shared_state.suspend_input_highlighting()
    signal.signal.showError.connect(shown)
    try:
        with contextlib.suppress(Exception):
            backend_mod.Backend.klass.activate_gremlin(stub, True)
        assert stub.activityChanged.emit.called  # the toolbar/status update
        assert not wired.run.is_running()  # "Stopped"
        assert len(errors) == 1
        assert not shared_state.suspend_input_highlighting()
    finally:
        signal.signal.showError.disconnect(shown)
        shared_state.set_suspend_input_highlighting(highlighting)


# --- GL-004: the order of start and Stop -------------------------------------


@pytest.fixture
def recorded(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[code_runner.CodeRunner, mock.MagicMock]]:
    """A CodeRunner whose every subsystem records into one call list."""
    from gremlin import mode_manager

    calls = mock.MagicMock()
    calls.EventListener.instance = None
    monkeypatch.setattr(code_runner.event_handler, "EventListener", calls.EventListener)
    run = code_runner.CodeRunner()
    for name in (
        "output",
        "OscRuntime",
        "InputModuleRuntime",
        "audio_player",
        "tts",
        "macro",
        "sendinput",
        "base_classes",
        "user_script",
        "shared_state",
        "mode_manager",
    ):
        monkeypatch.setattr(code_runner, name, getattr(calls, name))
    monkeypatch.setattr(mode_manager, "flush_last_modes", calls.flush_last_modes)
    run.event_handler = calls.event_handler
    monkeypatch.setattr(run, "_refresh_axes", calls.refresh_axes)
    yield run, calls
    shared_state.set_runtime_active(False)


def _names(calls: mock.MagicMock) -> list[str]:
    """Call names in order, with the instance calls folded in."""
    return [c[0].replace("()", "") for c in calls.mock_calls]


def _index(names: list[str], wanted: str) -> int:
    assert wanted in names, f"{wanted} not called: {names}"
    return names.index(wanted)


def test_start_reads_outputs_then_connects_then_runs(
    recorded: tuple[code_runner.CodeRunner, mock.MagicMock],
) -> None:
    run, calls = recorded
    run.start(Profile(), "Default")
    names = _names(calls)
    order = [
        "output.refresh",  # the output modules are read fresh
        "InputModuleRuntime.reload",
        "InputModuleRuntime.event.connect",
        "macro.MacroManager.start",
        "mode_manager.ModeManager.start_run",  # the toolbar mode, fresh stack
        "event_handler.resume",  # every Run starts un-paused (S37)
        "shared_state.set_runtime_active",
        "sendinput.MouseMotionManager.start",
        "refresh_axes",
    ]
    positions = [_index(names, n) for n in order]
    assert positions == sorted(positions), names
    assert calls.shared_state.set_runtime_active.call_args_list == [mock.call(True)]
    run.stop()


def test_stop_disconnects_first_and_releases_the_drivers_last(
    recorded: tuple[code_runner.CodeRunner, mock.MagicMock],
) -> None:
    run, calls = recorded
    run.start(Profile(), "Default")
    calls.reset_mock()
    run.stop()
    names = _names(calls)
    # The map's Stop stages (run_scope.Stage), in order.
    order = [
        # CUT_INPUT
        "InputModuleRuntime.event.disconnect",  # no new events
        "flush_last_modes",  # S6: the running mode is kept for Last Active
        "shared_state.set_runtime_active",
        # CANCEL
        "user_script.callback_registry.clear",
        "user_script.periodic_registry.stop",
        "OscRuntime.stop",
        # FIRE_PENDING
        "base_classes.flush_pulses",  # S24: before the drivers go
        # END_WORK
        "macro.MacroManager.stop",  # S20: macros end
        "sendinput.MouseMotionManager.stop",  # S22/S23
        # NEUTRAL
        "mode_manager.ModeManager.end_run",  # R3: temporary modes end
        "audio_player.AudioPlayer.stop",  # S28
        "tts.TTSManager.stop",
        # DRIVERS
        "output.reset_drivers",  # S29
    ]
    positions = [_index(names, n) for n in order]
    assert positions == sorted(positions), names
    assert names[-1] == "output.reset_drivers"
    assert calls.shared_state.set_runtime_active.call_args_list == [mock.call(False)]
    assert not run.is_running()


# --- GL-004 / GL-047: Tempo timers after Stop --------------------------------


def _tempo(monkeypatch: pytest.MonkeyPatch) -> tuple[Any, list[str]]:
    import action_plugins.tempo as tempo

    fired: list[str] = []
    monkeypatch.setattr(tempo.TempoFunctor, "_timeout", lambda self: fired.append("t"))
    data = tempo.TempoData(InputType.JoystickButton)
    data.threshold = 0.05
    return tempo.TempoFunctor(data), fired


def _press(functor: Any) -> None:  # noqa: ANN401
    functor(
        Event(InputType.JoystickButton, 3, _GUID, "Default", is_pressed=True),
        Value(True),
    )


def _after_main_timers(seconds: float) -> bool:
    """Runs Qt events until a main-thread timer set now for seconds fired:
    any shorter one set before it has had its turn by then."""
    done: list[bool] = []
    sentinel = threads.main_timer("test sentinel", seconds, lambda: done.append(True))
    try:
        return _wait_for(lambda: bool(done))
    finally:
        sentinel.cancel()


def test_a_tempo_timer_fires_while_running(
    runner: code_runner.CodeRunner,
    monkeypatch: pytest.MonkeyPatch,
    release_actions: Any,  # noqa: ANN401
) -> None:
    runner.start(Profile(), "Default")
    functor, fired = _tempo(monkeypatch)
    try:
        _press(functor)
        assert _after_main_timers(0.2)
        assert fired == ["t"]
    finally:
        functor.timer.cancel()


def test_a_tempo_timer_never_fires_after_stop(
    runner: code_runner.CodeRunner,
    monkeypatch: pytest.MonkeyPatch,
    release_actions: Any,  # noqa: ANN401
) -> None:
    runner.start(Profile(), "Default")
    functor, fired = _tempo(monkeypatch)
    try:
        _press(functor)  # held: the long-press timer runs
        runner.stop()
        assert _after_main_timers(0.2)
        assert fired == []
    finally:
        functor.timer.cancel()


# --- GL-005 / GL-051 / S38: release callbacks --------------------------------


def _map_to_vjoy_button(monkeypatch: pytest.MonkeyPatch) -> tuple[Any, list]:
    from action_plugins.map_to_vjoy import MapToVjoyData, MapToVjoyFunctor
    from gremlin.modules import output

    sent: list[tuple] = []
    monkeypatch.setattr(
        output, "write_vjoy", lambda *a: sent.append(("write",) + a) or True
    )
    monkeypatch.setattr(
        output, "release_vjoy_button", lambda *a: sent.append(("release",) + a) or True
    )
    data = MapToVjoyData(InputType.JoystickButton)
    data.vjoy_device_id = 1
    data.vjoy_input_id = 4
    return MapToVjoyFunctor(data), sent


def _button(mode: str, pressed: bool) -> Event:
    return Event(InputType.JoystickButton, 5, _GUID, mode, is_pressed=pressed)


def test_a_vjoy_button_pressed_before_a_mode_change_is_released(
    monkeypatch: pytest.MonkeyPatch,
    release_actions: Any,  # noqa: ANN401
) -> None:
    functor, sent = _map_to_vjoy_button(monkeypatch)
    release_actions._mode_changed_cb("Default")
    functor(_button("Default", True), Value(True))
    release_actions._mode_changed_cb("Flight")  # the mode changes, held
    # The physical release reaches the event handler in the new mode: the
    # old mode's Map to vJoy doesn't run, the release registry lets go.
    event_handler.EventHandler().process_event(_button("Flight", False))
    assert sent == [("write", 1, "button", 4, True), ("release", 1, 4)]


def test_in_the_same_mode_the_action_releases_the_button_itself(
    monkeypatch: pytest.MonkeyPatch,
    release_actions: Any,  # noqa: ANN401
) -> None:
    functor, sent = _map_to_vjoy_button(monkeypatch)
    release_actions._mode_changed_cb("Default")
    functor(_button("Default", True), Value(True))
    event_handler.EventHandler().process_event(_button("Default", False))
    assert ("release", 1, 4) not in sent  # no second, doubled release


def test_release_callbacks_waiting_at_stop_are_dropped(
    runner: code_runner.CodeRunner,
    monkeypatch: pytest.MonkeyPatch,
    release_actions: Any,  # noqa: ANN401
) -> None:
    runner.start(Profile(), "Default")
    functor, _sent = _map_to_vjoy_button(monkeypatch)
    functor(_button("Default", True), Value(True))
    assert any(release_actions._registry.values())  # one is waiting
    runner.stop()
    assert not any(release_actions._registry.values())


# --- GL-005: axis-range and hat virtual buttons ------------------------------


def _axis_button(
    lower: float, upper: float, direction: AxisButtonDirection
) -> tuple[code_runner.VirtualButtonFunctor, list[bool]]:
    emitted: list[bool] = []
    listener = SimpleNamespace(
        virtual_event=SimpleNamespace(emit=lambda e: emitted.append(e.is_pressed))
    )
    template = Event(InputType.VirtualButton, 1, _GUID, "Default", is_pressed=False)
    with mock.patch.object(
        code_runner.event_handler, "EventListener", return_value=listener
    ):
        functor = code_runner.VirtualButtonFunctor(
            code_runner.VirtualAxisButton(lower, upper, direction), template
        )
    return functor, emitted


def _move(functor: code_runner.VirtualButtonFunctor, value: float) -> None:
    functor(
        Event(InputType.JoystickAxis, 1, _GUID, "Default", value=value), Value(value)
    )


def test_an_axis_entering_its_range_presses_and_leaving_releases() -> None:
    functor, emitted = _axis_button(0.2, 0.6, AxisButtonDirection.Anywhere)
    _move(functor, -0.5)  # first value at Run, outside
    _move(functor, 0.0)
    assert emitted == []
    _move(functor, 0.4)
    _move(functor, 0.5)  # still inside: no second press
    assert emitted == [True]
    _move(functor, 0.9)
    assert emitted == [True, False]


def test_an_axis_already_in_its_range_at_run_gives_no_press() -> None:
    functor, emitted = _axis_button(0.2, 0.6, AxisButtonDirection.Anywhere)
    _move(functor, 0.4)  # the first value seen in this Run
    _move(functor, 0.45)
    assert True not in emitted  # Q13: kept, no surprise press at Run


def test_leaving_a_range_the_axis_started_in_sends_no_release() -> None:
    # 06 S39 (user, 2026-10-06): no release without a press.
    functor, emitted = _axis_button(0.2, 0.6, AxisButtonDirection.Anywhere)
    _move(functor, 0.4)  # already inside at Run: no press (Q13)
    _move(functor, 0.9)  # leaves the range
    assert emitted == []


def test_an_axis_jumping_across_its_range_presses_and_releases() -> None:
    functor, emitted = _axis_button(0.2, 0.6, AxisButtonDirection.Anywhere)
    _move(functor, -0.8)
    _move(functor, 0.9)  # one step from below to above
    assert emitted == [True, False]
    _move(functor, -0.9)  # and back across
    assert emitted == [True, False, True, False]


def test_an_axis_range_presses_only_in_the_chosen_direction() -> None:
    # "Below": entered from below (the axis moving up).
    functor, emitted = _axis_button(0.2, 0.6, AxisButtonDirection.Below)
    _move(functor, 0.9)
    _move(functor, 0.4)  # entered from above: no press
    assert True not in emitted
    _move(functor, -0.5)
    _move(functor, 0.3)  # entered from below
    assert emitted[-1] is True


def test_a_set_of_hat_directions_is_one_button() -> None:
    emitted: list[bool] = []
    listener = SimpleNamespace(
        virtual_event=SimpleNamespace(emit=lambda e: emitted.append(e.is_pressed))
    )
    template = Event(InputType.VirtualButton, 2, _GUID, "Default", is_pressed=False)
    with mock.patch.object(
        code_runner.event_handler, "EventListener", return_value=listener
    ):
        functor = code_runner.VirtualButtonFunctor(
            code_runner.VirtualHatButton(
                [HatDirection.North, HatDirection.NorthEast, HatDirection.NorthWest]
            ),
            template,
        )

    def hat(direction: HatDirection) -> None:
        functor(
            Event(InputType.JoystickHat, 1, _GUID, "Default", value=direction),
            Value(direction),
        )

    hat(HatDirection.North)
    hat(HatDirection.NorthEast)  # still one of the set: held, no new press
    hat(HatDirection.NorthWest)
    assert emitted == [True]
    hat(HatDirection.East)
    hat(HatDirection.Center)
    assert emitted == [True, False]


# --- GL-005 / GL-056: vJoy Initial Values at Run -----------------------------


@pytest.fixture
def initial_values(
    runner: code_runner.CodeRunner, monkeypatch: pytest.MonkeyPatch
) -> Callable[[float], mock.MagicMock]:
    """Runs a profile with vJoy 1 axis 1 Initial Value 0.5, the vJoy axis
    reading `reading` back; returns the recorded output and refresh calls."""

    def run(reading: float) -> mock.MagicMock:
        calls = mock.MagicMock()
        entry = SimpleNamespace(axis_index=1)
        vjoy = SimpleNamespace(
            vjoy_id=1,
            device_guid=SimpleNamespace(uuid=_VJOY_GUID),
            axis_map=[entry],
        )
        cache = {
            _VJOY_GUID: SimpleNamespace(axis=lambda _i: SimpleNamespace(value=reading))
        }
        monkeypatch.setattr(
            code_runner,
            "device_initialization",
            SimpleNamespace(vjoy_devices=lambda: [vjoy]),
            raising=False,  # the runner no longer reads the vJoy axis back
        )
        monkeypatch.setattr(
            code_runner,
            "input_cache",
            SimpleNamespace(Joystick=lambda: cache),
            raising=False,
        )
        monkeypatch.setattr(code_runner, "RefreshPhysicalInputs", calls.physical)
        monkeypatch.setattr(
            code_runner,
            "Configuration",
            lambda: SimpleNamespace(value=lambda *_a: True),
        )
        monkeypatch.setattr(code_runner, "output", calls.output)
        profile = Profile()
        profile.settings.vjoy_initial_values = {1: {1: 0.5}}
        # The real axis refresh, not the fixture's stand-in.
        runner._refresh_axes = code_runner.CodeRunner._refresh_axes.__get__(runner)
        runner.start(profile, "Default")
        return calls

    return run


def _initial_writes(calls: mock.MagicMock) -> list:
    return [c for c in calls.mock_calls if c[0] == "output.write_vjoy_axis_linear"]


def test_an_initial_value_is_written_at_run_through_the_output_module(
    initial_values: Callable[[float], mock.MagicMock],
) -> None:
    calls = initial_values(0.0)  # the axis reads 0 (nothing moved it)
    assert _initial_writes(calls) == [
        mock.call.output.write_vjoy_axis_linear(1, 1, 0.5)
    ]


def test_an_initial_value_is_written_whatever_the_axis_reads(
    initial_values: Callable[[float], mock.MagicMock],
) -> None:
    calls = initial_values(0.3)  # a value left from before
    assert _initial_writes(calls) == [
        mock.call.output.write_vjoy_axis_linear(1, 1, 0.5)
    ]


def test_the_physical_refresh_comes_after_the_initial_values(
    initial_values: Callable[[float], mock.MagicMock],
) -> None:
    calls = initial_values(0.0)
    names = [c[0] for c in calls.mock_calls]
    write = names.index("output.write_vjoy_axis_linear")
    refresh = names.index("physical.refresh_axes")
    assert write < refresh  # a moved stick then overrides the Initial Value


# --- GL-006: the Xbox pad at Stop --------------------------------------------


class _FakeVigem:
    """ViGEmClient.dll stand-in: records plug and unplug."""

    def __init__(self) -> None:
        from vigem.xbox import VIGEM_OK

        self.ok = VIGEM_OK
        self.log: list[str] = []

    def vigem_alloc(self) -> int:
        return 11

    def vigem_connect(self, _bus: int) -> int:
        return self.ok

    def vigem_disconnect(self, _bus: int) -> None:
        self.log.append("disconnect")

    def vigem_free(self, _bus: int) -> None:
        pass

    def vigem_target_x360_alloc(self) -> int:
        return 22

    def vigem_target_add(self, _bus: int, _dev: int) -> int:
        self.log.append("plug")
        return self.ok

    def vigem_target_x360_update(self, *_a: object) -> int:
        return self.ok

    def vigem_target_remove(self, _bus: int, _dev: int) -> None:
        self.log.append("unplug")

    def vigem_target_free(self, _dev: int) -> None:
        pass


def test_the_xbox_pad_plugs_in_on_first_send_and_unplugs_at_stop(
    runner: code_runner.CodeRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    from action_plugins.map_to_xbox import MapToXboxData, MapToXboxFunctor
    from gremlin.modules import output
    from vigem import own_pads, vigem_client, xbox

    lib = _FakeVigem()
    monkeypatch.setattr(vigem_client, "client", lambda: lib)
    monkeypatch.setattr(own_pads, "before_plug", lambda: None)
    monkeypatch.setattr(output, "reset_vjoy", lambda: None)  # no vJoy driver
    fresh = object.__new__(xbox.XboxProxy)
    fresh.__init__()
    monkeypatch.setitem(SingletonMetaclass._instances, xbox.XboxProxy, fresh)
    # Stop's driver reset is the real one (the runner's output is a stand-in).
    code_runner.output.reset_drivers.side_effect = output.reset_drivers

    runner.start(Profile(), "Default")
    assert lib.log == []  # Run alone plugs nothing in
    functor = MapToXboxFunctor(MapToXboxData(InputType.JoystickButton))
    functor(_button("Default", True), Value(True))
    functor(_button("Default", False), Value(False))
    assert lib.log == ["plug"]  # once, on the first send
    runner.stop()
    assert lib.log[1:] == ["unplug", "disconnect"]
    assert fresh._pads == {}


# --- GL-006 / GL-058: sound --------------------------------------------------


@pytest.fixture
def sounds(monkeypatch: pytest.MonkeyPatch) -> Iterator[SimpleNamespace]:
    """A fresh AudioPlayer (the shared one is put back) with stand-in
    samples: nothing is decoded or played on the PC."""
    from gremlin import audio_player

    log: list[tuple[str, str]] = []
    samples: dict[str, Any] = {}

    class Sample:
        def __init__(self, name: str, volume: int) -> None:
            self.name = name
            self.volume = volume
            self.blocking = False
            self._done = threading.Event()
            samples[name] = self
            log.append(("decode", name))

        @property
        def done(self) -> bool:
            return self._done.is_set()

        def play(self) -> None:
            log.append(("play", self.name))

        def cancel(self) -> None:
            log.append(("cancel", self.name))
            self._done.set()

        def finish(self) -> None:
            self._done.set()

        def block(self, still_wanted: Callable[[], bool]) -> None:
            self.blocking = True
            while not self._done.wait(0.02):
                if not still_wanted():
                    return

    monkeypatch.setattr(audio_player, "AudioSample", Sample)
    player = object.__new__(audio_player.AudioPlayer)
    player.__init__()
    monkeypatch.setitem(SingletonMetaclass._instances, audio_player.AudioPlayer, player)
    yield SimpleNamespace(player=player, log=log, samples=samples)
    player.stop()


def _played(log: list[tuple[str, str]]) -> list[str]:
    return [name for what, name in log if what == "play"]


def test_sequential_sounds_wait_for_the_one_playing(sounds: SimpleNamespace) -> None:
    sounds.player._playback_mode = "Sequential"
    sounds.player.start()
    sounds.player.enqueue("a.wav", 80)
    sounds.player.enqueue("b.wav", 80)
    assert _wait_for(
        lambda: "a.wav" in sounds.samples and sounds.samples["a.wav"].blocking
    )
    assert _played(sounds.log) == ["a.wav"]  # b waits behind a
    sounds.samples["a.wav"].finish()
    assert _wait_for(lambda: _played(sounds.log) == ["a.wav", "b.wav"])
    assert sounds.samples["a.wav"].volume == 80


def test_interrupt_stops_the_sound_playing(sounds: SimpleNamespace) -> None:
    sounds.player._playback_mode = "Interrupt"
    sounds.player.start()
    sounds.player.enqueue("a.wav", 50)
    assert _wait_for(lambda: _played(sounds.log) == ["a.wav"])
    sounds.player.enqueue("b.wav", 50)
    assert _wait_for(lambda: _played(sounds.log) == ["a.wav", "b.wav"])
    assert sounds.log.index(("cancel", "a.wav")) < sounds.log.index(("play", "b.wav"))


def test_overlap_plays_sounds_together(sounds: SimpleNamespace) -> None:
    sounds.player._playback_mode = "Overlap"
    sounds.player.start()
    sounds.player.enqueue("a.wav", 50)
    sounds.player.enqueue("b.wav", 50)
    assert _wait_for(lambda: _played(sounds.log) == ["a.wav", "b.wav"])
    assert not [e for e in sounds.log if e[0] == "cancel"]


def test_stop_cancels_the_sounds_and_empties_the_queue(sounds: SimpleNamespace) -> None:
    sounds.player._playback_mode = "Sequential"
    sounds.player.start()
    sounds.player.enqueue("a.wav", 50)
    sounds.player.enqueue("b.wav", 50)
    assert _wait_for(
        lambda: "a.wav" in sounds.samples and sounds.samples["a.wav"].blocking
    )
    sounds.player.stop()  # S28
    assert ("cancel", "a.wav") in sounds.log
    assert sounds.player._play_list == []


def test_a_sound_queued_with_no_run_never_plays(
    sounds: SimpleNamespace, tmp_path: Path
) -> None:
    from action_plugins.play_sound import PlaySoundData, PlaySoundFunctor

    late = tmp_path / "late.wav"
    late.write_bytes(b"RIFF")
    data = PlaySoundData(InputType.JoystickButton)
    data.sound_filename = str(late)
    sounds.player._playback_mode = "Overlap"
    shared_state.set_runtime_active(False)
    PlaySoundFunctor(data)(_button("Default", True), Value(True))  # a late timer
    shared_state.set_runtime_active(True)  # the next Run
    try:
        sounds.player.start()
        sounds.player.enqueue("next-run.wav", 50)
        assert _wait_for(lambda: "next-run.wav" in _played(sounds.log))
        assert str(late) not in _played(sounds.log)
    finally:
        shared_state.set_runtime_active(False)


# --- GL-006 / GL-058: speech -------------------------------------------------


class _Voice:
    def __init__(self, name: str) -> None:
        self._name = name

    def name(self) -> str:
        return self._name


@pytest.fixture
def speech(monkeypatch: pytest.MonkeyPatch) -> Iterator[SimpleNamespace]:
    """A fresh TTSManager (the shared one is put back) with a stand-in
    engine: nothing is spoken on the PC."""
    from gremlin import tts

    engines: list[Any] = []

    class Engine:
        def __init__(self, backend: str) -> None:
            self.backend = backend
            self.said: list[tuple[str, float]] = []
            self.voice = ""
            self.stops = 0
            self._state = tts.QTextToSpeech.State.Ready
            self._volume = 1.0
            self.stateChanged = mock.MagicMock()
            engines.append(self)

        def availableVoices(self) -> list[_Voice]:  # noqa: N802
            return [_Voice("Voice A"), _Voice("Voice B")]

        def setVoice(self, voice: _Voice) -> None:  # noqa: N802
            self.voice = voice.name()

        def state(self) -> Any:  # noqa: ANN401
            return self._state

        def setRate(self, _v: float) -> None:  # noqa: N802
            pass

        def setPitch(self, _v: float) -> None:  # noqa: N802
            pass

        def setVolume(self, v: float) -> None:  # noqa: N802
            self._volume = v

        def say(self, text: str) -> None:
            self.said.append((text, self._volume))
            self._state = tts.QTextToSpeech.State.Speaking

        def stop(self) -> None:
            self.stops += 1
            self._state = tts.QTextToSpeech.State.Ready

        def finish(self) -> None:
            self._state = tts.QTextToSpeech.State.Ready
            manager._on_state_changed(self._state)

    monkeypatch.setattr(tts, "QTextToSpeech", mock.MagicMock(side_effect=Engine))
    cast(Any, tts.QTextToSpeech).State = type(
        "State", (), {"Ready": "ready", "Speaking": "speaking"}
    )
    monkeypatch.setattr(
        tts, "Configuration", lambda: SimpleNamespace(value=lambda *_a: "Voice B")
    )
    manager = object.__new__(tts.TTSManager)
    manager.__init__()
    monkeypatch.setitem(SingletonMetaclass._instances, tts.TTSManager, manager)
    yield SimpleNamespace(manager=manager, engines=engines)
    manager.stop()


def _say(text: str, mode: str, volume: float = 1.0) -> None:
    from action_plugins.text_to_speech import TextToSpeechData, TextToSpeechFunctor

    data = TextToSpeechData(InputType.JoystickButton)
    data.text = text
    data.queue_mode = mode
    data.playback_volume = volume
    TextToSpeechFunctor(data)(_button("Default", True), Value(True))


def test_speech_uses_the_options_voice_and_the_queue_modes(
    speech: SimpleNamespace,
) -> None:
    speech.manager.start()
    engine = speech.engines[0]
    assert engine.backend == "winrt"
    assert engine.voice == "Voice B"  # Options > Text to Speech voice
    _say("one", "queue-back", 0.4)  # idle: spoken at once
    _say("two", "queue-back")
    _say("three", "queue-back")
    _say("zero", "queue-front")  # ahead of the waiting ones
    assert engine.said == [("one", 0.4)]
    engine.finish()
    assert [t for t, _v in engine.said] == ["one", "zero"]
    _say("now", "interrupt")  # cuts in at once
    assert engine.stops == 1
    assert [t for t, _v in engine.said] == ["one", "zero", "now"]
    engine.finish()
    engine.finish()
    assert [t for t, _v in engine.said] == ["one", "zero", "now", "two", "three"]


def test_stop_ends_speech_and_empties_its_queue(speech: SimpleNamespace) -> None:
    speech.manager.start()
    engine = speech.engines[0]
    _say("one", "queue-back")
    _say("two", "queue-back")
    speech.manager.stop()  # S28
    assert engine.stops == 1
    engine.finish()
    assert [t for t, _v in engine.said] == ["one"]


def test_speech_asked_for_with_no_run_is_ignored(speech: SimpleNamespace) -> None:
    speech.manager.start()  # a Run ...
    speech.manager.stop()  # ... and Stop: the engine stays
    shared_state.set_runtime_active(False)
    _say("late", "interrupt")  # a late timer
    assert speech.engines[0].said == []


# --- GL-006: Paused status and a Run starting un-paused ----------------------


def test_each_run_starts_unpaused(runner: code_runner.CodeRunner) -> None:
    eh = event_handler.EventHandler()
    runner.start(Profile(), "Default")
    eh.pause()
    runner.stop()
    runner.start(Profile(), "Default")
    assert eh.process_callbacks  # S37 / Q11


def _status_text(active: bool, paused: bool, dirty: bool) -> str:
    """The status bar text, from Main.qml's own binding."""
    main = (_ROOT / "qml" / "Main.qml").read_text(encoding="utf-8")
    found = re.search(r'text: ("<B>Status: </B>" \+.*?)\n\s*\}', main, re.S)
    assert found, "the status bar binding moved"
    helpers = (_ROOT / "qml" / "helpers.js").as_uri()
    qml = (
        "import QtQml\n"
        f'import "{helpers}" as Helpers\n'
        "QtObject {\n"
        f"    property var backend: ({{gremlinActive: {str(active).lower()}, "
        f"gremlinPaused: {str(paused).lower()}}})\n"
        f"    property var _root: ({{profileDirty: {str(dirty).lower()}}})\n"
        f"    property string text: {found.group(1)}\n"
        "}\n"
    )
    engine = QtQml.QQmlEngine()
    component = QtQml.QQmlComponent(engine)
    component.setData(qml.encode("utf-8"), QtCore.QUrl())
    obj = component.create()
    assert obj is not None, component.errorString()
    text = obj.property("text")
    obj.deleteLater()
    engine.deleteLater()
    return re.sub(r"<[^>]+>", "", text)


def test_the_status_bar_says_running_paused(runner: code_runner.CodeRunner) -> None:
    from gremlin.ui import backend as backend_mod

    def paused() -> bool:
        return backend_mod.Backend.klass.gremlinPaused.fget(None)

    eh = event_handler.EventHandler()
    runner.start(Profile(), "Default")
    assert _status_text(True, paused(), False) == "Status: Running"
    eh.pause()
    assert _status_text(True, paused(), False) == "Status: Running (Paused)"
    assert (
        _status_text(True, paused(), True)
        == "Status: Running (Paused) (unsaved changes)"
    )
    runner.stop()
    assert _status_text(False, paused(), True) == "Status: Stopped"


# --- GL-006: tray menu label and icon ----------------------------------------


class _Win32:
    """win32gui stand-in for the tray: records menu items and icon changes."""

    error = Exception
    NIM_MODIFY = 1
    NIF_ICON = 2

    def __init__(self) -> None:
        self.items: list[str] = []
        self.icons: list[int] = []

    def CreatePopupMenu(self) -> int:  # noqa: N802
        self.items = []
        return 1

    def AppendMenu(self, _menu: int, _flags: int, _id: int, text: str) -> None:  # noqa: N802
        if text:
            self.items.append(text)

    def SetForegroundWindow(self, _hwnd: int) -> None:  # noqa: N802
        pass

    def TrackPopupMenu(self, *_a: object) -> None:  # noqa: N802
        pass

    def PostMessage(self, *_a: object) -> None:  # noqa: N802
        pass

    def DestroyMenu(self, _menu: int) -> None:  # noqa: N802
        pass

    def Shell_NotifyIcon(self, _what: int, data: tuple) -> None:  # noqa: N802
        self.icons.append(data[4])


def test_the_tray_offers_run_or_stop_and_changes_its_icon(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin.ui import system_tray

    win = _Win32()
    monkeypatch.setattr(system_tray, "win32gui", win)
    backend = SimpleNamespace(gremlinActive=False)

    def toggle() -> None:
        backend.gremlinActive = not backend.gremlinActive
        tray._gremlin_status_change_cb()  # activityChanged

    backend.toggleActiveState = toggle
    cls = system_tray.SystemTrayIcon
    tray: Any = SimpleNamespace(
        _backend=backend,
        _window=SimpleNamespace(isVisible=lambda: True),
        _hwnd=5,
        _idle_icon=100,
        _active_icon=200,
    )
    tray._current_icon = lambda: cls._current_icon(tray)
    tray._gremlin_status_change_cb = lambda: cls._gremlin_status_change_cb(tray)
    tray._toggle_run = lambda: cls._toggle_run(tray)
    # No main window here: toggleRun can't be reached, so the tray falls back
    # to the backend (with a window, Main.qml toggleRun asks first, 06 Q6).
    monkeypatch.setattr(
        system_tray,
        "QtCore",
        SimpleNamespace(QMetaObject=SimpleNamespace(invokeMethod=lambda *a: False)),
    )

    cls._show_menu(tray, 0, 0)
    assert "Run Profile" in win.items
    assert "Stop Profile" not in win.items
    toggle_id = system_tray.win32api.MAKELONG(system_tray._ID_TOGGLE, 0)
    cls._handle_context_menu_cb(tray, 5, 0, toggle_id, 0)  # Run Profile clicked
    assert win.icons == [200]  # the running icon
    cls._show_menu(tray, 0, 0)
    assert "Stop Profile" in win.items
    assert "Run Profile" not in win.items
    cls._handle_context_menu_cb(tray, 5, 0, toggle_id, 0)
    assert win.icons == [200, 100]


# --- GL-006: device change behaviour and auto-load ---------------------------


def _backend_stub(running: bool, options: dict[tuple, Any]) -> Any:  # noqa: ANN401
    calls: list[bool] = []

    def activate(on: bool) -> None:
        calls.append(on)
        stub.gremlinActive = on

    stub: Any = SimpleNamespace(
        gremlinActive=running,
        activate_gremlin=activate,
        calls=calls,
        config=SimpleNamespace(value=lambda *key: options.get(key)),
        _autoload_held=None,
    )
    return stub


@pytest.mark.parametrize(
    ("behaviour", "running", "expected"),
    [
        ("Reload", True, [False, True]),  # Stop and Run
        ("Reload", False, []),  # nothing runs: nothing to reload
        ("Ignore", True, []),
        ("Disable", True, [False]),  # Stop
    ],
)
def test_device_change_follows_the_option(
    behaviour: str, running: bool, expected: list[bool]
) -> None:
    from gremlin.ui import backend as backend_mod

    key = ("global", "general", "device-change-behavior")
    stub = _backend_stub(running, {key: behaviour})
    backend_mod.Backend.klass._device_change(stub)
    assert stub.calls == expected


@pytest.mark.parametrize(("keep_running", "expected"), [(False, [False]), (True, [])])
def test_auto_load_stops_on_focus_loss_unless_kept_running(
    keep_running: bool, expected: list[bool], monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.ui import backend as backend_mod

    options = {
        ("profile", "automation", "enable-auto-loading"): True,
        ("profile", "automation", "remain-active-on-focus-loss"): keep_running,
    }
    stub = _backend_stub(True, options)
    # The program now in front has no profile.
    monkeypatch.setattr(backend_mod.config, "get_profile_with_regex", lambda _p: None)
    backend_mod.Backend.klass._active_process_changed_cb(stub, "C:/other.exe")
    assert stub.calls == expected
