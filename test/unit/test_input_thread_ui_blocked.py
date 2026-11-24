# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""End to end with the real input thread (thread batches 2-5,
claude/plans/fix-plans/thread-ui.md section 3, thread-input.md batch 2).

A fake dill event goes through EventListener -> InputModuleRuntime (claim
gate) -> EventHandler.process_event -> an action callback -> a faked vJoy
write, with the Run started through RunControl on the input thread. The
window (main) thread is blocked on purpose: controls must keep working.

Everything waits with a limit. The main thread is the test's own thread.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any
from unittest import mock

import pytest
from PySide6 import QtCore

import dill
from gremlin import (
    clock,
    code_runner,
    event_handler,
    input_thread,
    mode_manager,
    profile,
    run_scope,
    shared_state,
)
from gremlin.modules import output, runtime
from gremlin.types import Event, InputType
from test import fake_hardware

fake_hardware.install(vjoy_ids=(1,))

_STICK = dill.GUID(fake_hardware.raw_guid(is_virtual=False)).uuid
_BUTTON = 6
_LIMIT = 3.0


def _dill_input() -> dill._JoystickInputData:
    return dill._JoystickInputData(
        device_guid=fake_hardware.raw_guid(is_virtual=False),
        input_type=2, input_index=_BUTTON, value=1,
    )


def _pump(until: Callable[[], bool], limit: float = _LIMIT) -> bool:
    """Runs the main thread's event loop until `until()` or `limit` s."""
    end = clock.monotonic() + limit
    while clock.monotonic() < end:
        QtCore.QCoreApplication.processEvents()
        if until():
            return True
        time.sleep(0.005)
    QtCore.QCoreApplication.processEvents()
    return until()


def _block_main(seconds: float) -> float:
    """A busy window: no event loop for `seconds`, in bounded steps.
    Returns the time it let go."""
    end = clock.monotonic() + seconds
    while clock.monotonic() < end:
        time.sleep(0.01)
    return clock.monotonic()


def _after(delay: float, fn: Callable[[], None]) -> threading.Thread:
    """The listener side: fn runs on another thread after `delay` s."""

    def run() -> None:
        time.sleep(delay)
        fn()

    thread = threading.Thread(target=run, name="test-listener", daemon=True)
    thread.start()
    return thread


class Recorder:
    """What the action and the faked vJoy saw, and on which thread."""

    def __init__(self) -> None:
        self.writes: list[tuple[float, bool]] = []  # (time, on input thread)
        self.actions: list[tuple[float, bool]] = []

    def action(self, _event: Event) -> None:
        self.actions.append((clock.monotonic(), input_thread.is_input_thread()))
        output.write_vjoy(1, "button", 1, True)


@pytest.fixture
def rig(
    input_thread_running: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Iterator[SimpleRig]:
    """A started Run (empty profile) with one Map to vJoy style binding on
    the fake stick's button, on the real input thread."""
    rec = Recorder()
    monkeypatch.setattr(runtime, "should_forward", lambda *a, **k: True)
    monkeypatch.setattr(
        output, "_write_vjoy",
        lambda *a, **k: rec.writes.append((clock.monotonic(),
                                           input_thread.is_input_thread())) or "ok",
    )
    adopt = getattr(code_runner, "adopt_runtime_objects", None)
    assert adopt is not None, "code_runner.adopt_runtime_objects is missing"
    adopt()
    control = code_runner.run_control()
    prof = profile.Profile()
    prof.modes.add_mode("Bravo")  # for the mode pick test
    mode = prof.modes.first_mode
    handler = event_handler.EventHandler()
    input_thread.call_wait(control.start, prof, mode, timeout=5.0)

    def inject() -> None:
        key = Event(
            InputType.JoystickButton, _BUTTON, _STICK, mode, is_pressed=True
        )
        handler.callbacks = {_STICK: {mode: {key: [rec.action]}}}
        handler.process_callbacks = True

    input_thread.call_wait(inject, timeout=_LIMIT)
    saved = shared_state.current_profile
    yield SimpleRig(rec, control, handler, mode, prof)
    try:
        input_thread.call_wait(control.stop, timeout=5.0)
    finally:
        shared_state.current_profile = saved
        run_scope._reset_for_tests()


class SimpleRig:
    def __init__(
        self,
        rec: Recorder,
        control: Any,  # noqa: ANN401
        handler: event_handler.EventHandler,
        mode: str,
        prof: profile.Profile,
    ) -> None:
        self.rec = rec
        self.control = control
        self.handler = handler
        self.mode = mode
        self.prof = prof

    def fire(self) -> None:
        """The listener side: one button press arrives from the driver."""
        event_handler.EventListener()._joystick_event_handler(_dill_input())


# 1 ---------------------------------------------------------------------------


def test_output_written_while_main_thread_blocked(rig: SimpleRig) -> None:
    feeder = _after(0.3, rig.fire)
    unblocked_at = _block_main(2.0)
    feeder.join(_LIMIT)
    assert rig.rec.writes, "no vJoy write at all while the window was blocked"
    written_at, on_input_thread = rig.rec.writes[0]
    assert on_input_thread, "the output was written off the input thread"
    # Within 100 ms of the press (0.3 s in), long before the window woke.
    assert written_at < unblocked_at - 1.0, (
        f"vJoy written {unblocked_at - written_at:.2f} s before the window "
        "unblocked; it must not wait for it"
    )


# 2 ---------------------------------------------------------------------------


class _Viewer(QtCore.QObject):
    """Stands for a Live viewer / the highlight: lives on the main thread."""

    def __init__(self) -> None:
        super().__init__()
        self.seen: list[bool] = []  # True when its slot ran on the main thread
        self.pressed = 0  # the test's own button press

    @QtCore.Slot(object)
    def on_event(self, event: Event) -> None:
        main = QtCore.QCoreApplication.instance().thread()
        self.seen.append(QtCore.QThread.currentThread() == main)
        # The Run start's axis refresh (synthetic, from the macro thread)
        # may still be arriving; only the fired press is counted.
        if (
            event.event_type == InputType.JoystickButton
            and event.identifier == _BUTTON
            and not getattr(event, "synthetic", False)
        ):
            self.pressed += 1


def test_highlight_and_viewers_on_main_action_on_input(rig: SimpleRig) -> None:
    bus = runtime.InputModuleRuntime()
    viewer = _Viewer()
    bus.event.connect(viewer.on_event, QtCore.Qt.ConnectionType.QueuedConnection)
    try:
        rig.fire()
        assert _pump(lambda: bool(viewer.pressed) and bool(rig.rec.actions))
    finally:
        bus.event.disconnect(viewer.on_event)
    assert rig.rec.actions[0][1], "the action did not run on the input thread"
    assert viewer.pressed == 1, "the press reached the viewer more than once"
    assert all(viewer.seen), "a viewer slot did not run on the main thread"


# 3 ---------------------------------------------------------------------------


def test_load_profile_action_runs_backend_on_main(
    rig: SimpleRig, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from action_plugins.load_profile import LoadProfileFunctor
    from gremlin import plugin_manager
    from gremlin.base_classes import Value
    from gremlin.ui import backend

    seen: list[bool] = []
    app_thread = QtCore.QCoreApplication.instance().thread()
    fake = mock.MagicMock()
    fake.profile.has_unsaved_changes.return_value = False
    fake.run_profile.side_effect = lambda path: seen.append(
        QtCore.QThread.currentThread() == app_thread
    )
    monkeypatch.setattr(backend, "Backend", lambda: fake)
    # An open profile for the new action to be added to.
    monkeypatch.setattr(shared_state, "current_profile", profile.Profile())
    data = plugin_manager.PluginManager().create_instance(
        "Load Profile", InputType.JoystickButton
    )
    target = tmp_path / "other.xml"
    target.write_text("<profile/>")
    data.profile_filename = str(target)
    functor = LoadProfileFunctor(data)
    event = Event(
        InputType.JoystickButton, 1, _STICK, rig.mode, is_pressed=True
    )

    def press() -> None:
        assert input_thread.is_input_thread()
        functor(event, Value(True), [])

    input_thread.call_wait(press, timeout=_LIMIT)
    assert _pump(lambda: bool(seen)), "Backend.run_profile was never called"
    assert seen == [True], "Backend.run_profile ran off the main thread"


# 4 ---------------------------------------------------------------------------


def test_stop_drops_queued_events(rig: SimpleRig) -> None:
    gate = threading.Event()
    input_thread.call(gate.wait, _LIMIT)  # the input thread is busy
    for _ in range(50):
        rig.fire()  # queued behind it
    input_thread.call(rig.control.stop)  # Stop is asked
    for _ in range(50):
        rig.fire()  # arrive after Stop in the queue
    gate.set()
    input_thread.call_wait(lambda: None, timeout=_LIMIT)  # Stop has run
    seen_at_stop = len(rig.rec.actions)
    assert seen_at_stop <= 50, "events queued after Stop still ran their actions"
    time.sleep(0.2)
    QtCore.QCoreApplication.processEvents()
    input_thread.call_wait(lambda: None, timeout=_LIMIT)
    assert len(rig.rec.actions) == seen_at_stop, "a callback ran after Stop returned"
    assert not run_scope.running()


# 5 ---------------------------------------------------------------------------


def test_ui_mode_select_goes_through_command_queue(
    rig: SimpleRig, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin import process_monitor
    from gremlin.ui import backend

    monkeypatch.setattr(process_monitor.ProcessMonitor, "start", lambda self: None)
    monkeypatch.setattr(backend, "display_error", lambda *a, **k: None)
    prof = rig.prof
    be = backend.Backend.klass(None)  # type: ignore[arg-type]
    be.profile = prof
    shared_state.current_profile = prof
    mm = mode_manager.ModeManager()
    changed_on: list[bool] = []
    mm.mode_changed.connect(
        lambda name: changed_on.append(input_thread.is_input_thread()),
        QtCore.Qt.ConnectionType.DirectConnection,
    )
    be.selectMode("Bravo")
    assert _pump(lambda: bool(changed_on)), "ModeManager never changed mode"
    assert changed_on[0], "the mode changed off the input thread"
    assert _pump(lambda: be.ui_state.currentMode == "Bravo")
    assert mm.current.name == "Bravo"


# 6 ---------------------------------------------------------------------------


def test_tempo_long_press_fires_while_main_thread_blocked(rig: SimpleRig) -> None:
    fired: list[tuple[float, bool]] = []

    def arm() -> None:
        # What Tempo does: a Run timer for the long press, made on the thread
        # the action runs on.
        run_scope.timer(
            "tempo", 0.2,
            lambda: fired.append((clock.monotonic(), input_thread.is_input_thread())),
        )

    input_thread.call_wait(arm, timeout=_LIMIT)
    unblocked_at = _block_main(1.5)
    assert fired, "the timer never fired while the window was blocked"
    at, on_input_thread = fired[0]
    assert on_input_thread, "the timer ran its function off the input thread"
    assert at < unblocked_at - 0.8, "the timer waited for the window"
