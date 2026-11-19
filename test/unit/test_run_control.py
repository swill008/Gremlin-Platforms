# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""RunControl: Run and Stop on the input thread, and the profile copy a Run
uses (contract-THR.md, thread-input.md batch 2, answer 6a).

Every wait has a limit. Drivers are the fakes of test/fake_hardware.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable, Iterator

import pytest
from PySide6 import QtCore

from action_plugins.root import RootData
from gremlin import (
    clock,
    code_runner,
    event_handler,
    input_thread,
    mode_manager,
    run_scope,
    shared_state,
)
from gremlin.modules import runtime
from gremlin.profile import InputItemBinding, Profile
from gremlin.types import InputType
from test import fake_hardware

fake_hardware.install(vjoy_ids=(1,))

_STICK = uuid.UUID("77777777-5555-2222-3333-444444444001")
_LIMIT = 3.0


def _pump(until: Callable[[], bool], limit: float = _LIMIT) -> bool:
    end = clock.monotonic() + limit
    while clock.monotonic() < end:
        QtCore.QCoreApplication.processEvents()
        if until():
            return True
        time.sleep(0.005)
    QtCore.QCoreApplication.processEvents()
    return until()


def _profile_with_binding() -> tuple[Profile, str]:
    prof = Profile()
    mode = prof.modes.first_mode
    item = prof.get_input_item(
        _STICK, InputType.JoystickButton, 6, mode, create_if_missing=True
    )
    assert item is not None
    binding = InputItemBinding(item)
    binding.root_action = RootData(InputType.JoystickButton)
    binding.behavior = InputType.JoystickButton
    prof.library.add_action(binding.root_action)
    item.action_sequences.append(binding)
    return prof, mode


def _bindings(prof: Profile) -> int:
    return sum(len(i.action_sequences) for items in prof.inputs.values() for i in items)


class _Window(QtCore.QObject):
    """Stands for the Backend: lives on the main thread."""

    def __init__(self) -> None:
        super().__init__()
        self.started: list[tuple[bool, str, bool]] = []
        self.stopped: list[bool] = []

    def _on_main(self) -> bool:
        app = QtCore.QCoreApplication.instance()
        return app is not None and QtCore.QThread.currentThread() == app.thread()

    @QtCore.Slot(bool, str)
    def on_started(self, ok: bool, error: str) -> None:
        self.started.append((ok, error, self._on_main()))

    @QtCore.Slot()
    def on_stopped(self) -> None:
        self.stopped.append(self._on_main())


@pytest.fixture
def adopted(input_thread_running: None) -> Iterator[code_runner.RunControl]:
    saved = shared_state.current_profile
    code_runner.adopt_runtime_objects()
    control = code_runner.run_control()
    try:
        yield control
    finally:
        try:
            input_thread.call_wait(control.stop, timeout=5.0)
        finally:
            code_runner.release_runtime_objects()
            shared_state.current_profile = saved
            run_scope._reset_for_tests()


# Profile copy (answer 6a) -----------------------------------------------------


def test_snapshot_is_a_separate_copy() -> None:
    prof, mode = _profile_with_binding()
    snap = code_runner.profile_snapshot(prof)
    assert snap is not prof
    assert _bindings(snap) == 1
    assert snap.modes.mode_names() == prof.modes.mode_names()
    assert snap.fpath == prof.fpath
    # Scripts are shared, not read again (their top-level code would run).
    assert snap.scripts is prof.scripts
    # An edit to the open profile does not reach the copy.
    for items in prof.inputs.values():
        for item in items:
            item.action_sequences.clear()
    assert _bindings(prof) == 0
    assert _bindings(snap) == 1


# RunControl on the input thread ---------------------------------------------


def test_objects_adopted_to_input_thread(adopted: code_runner.RunControl) -> None:
    target = input_thread.call_wait(QtCore.QThread.currentThread, timeout=_LIMIT)
    for obj in (
        event_handler.EventHandler(),
        runtime.InputModuleRuntime(),
        mode_manager.ModeManager(),
        adopted,
    ):
        assert obj.thread() == target, type(obj).__name__


def test_run_and_stop_signal_the_window(adopted: code_runner.RunControl) -> None:
    window = _Window()
    queued = QtCore.Qt.ConnectionType.QueuedConnection
    adopted.runStarted.connect(window.on_started, queued)
    adopted.runStopped.connect(window.on_stopped, queued)
    prof, mode = _profile_with_binding()
    shared_state.current_profile = prof
    ran_on: list[bool] = []
    real_start = adopted.runner.start

    def start(p: Profile, m: str) -> None:
        ran_on.append(input_thread.is_input_thread())
        real_start(p, m)

    adopted.runner.start = start  # type: ignore[method-assign]
    try:
        input_thread.call(adopted.start, code_runner.profile_snapshot(prof), mode)
        assert _pump(lambda: bool(window.started)), "runStarted never arrived"
        assert ran_on == [True], "Run did not start on the input thread"
        assert window.started[0] == (True, "", True)
        input_thread.call(adopted.stop)
        assert _pump(lambda: bool(window.stopped)), "runStopped never arrived"
        assert window.stopped == [True]
        assert not adopted.is_running()
    finally:
        del adopted.runner.start


def test_ui_edit_during_run_does_not_reach_running_profile(
    adopted: code_runner.RunControl,
) -> None:
    prof, mode = _profile_with_binding()
    shared_state.current_profile = prof
    input_thread.call_wait(
        adopted.start, code_runner.profile_snapshot(prof), mode, timeout=5.0
    )
    assert adopted.is_running()
    running = adopted.runner._profile
    assert running is not prof
    # The window edits the open profile while the Run goes on.
    for items in prof.inputs.values():
        for item in items:
            item.action_sequences.clear()
    assert _bindings(running) == 1


def test_failed_start_reports_its_error(
    adopted: code_runner.RunControl, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = _Window()
    adopted.runStarted.connect(
        window.on_started, QtCore.Qt.ConnectionType.QueuedConnection
    )

    def broken(_running: Profile, _mode: str) -> None:
        raise RuntimeError("broken start")

    monkeypatch.setattr(adopted.runner, "_start", broken)
    prof, mode = _profile_with_binding()
    shared_state.current_profile = prof
    input_thread.call(adopted.start, code_runner.profile_snapshot(prof), mode)
    assert _pump(lambda: bool(window.started)), "runStarted never arrived"
    assert window.started[0][:2] == (False, "broken start")
    assert not adopted.is_running()


# The Run's profile for the input thread (thread-audit.md item 5) -------------


def test_running_profile_is_the_runs_copy_until_stop(
    adopted: code_runner.RunControl,
) -> None:
    prof, mode = _profile_with_binding()
    shared_state.current_profile = prof
    assert shared_state.profile_for_runtime() is prof
    snap = code_runner.profile_snapshot(prof)
    input_thread.call_wait(adopted.start, snap, mode, timeout=5.0)
    assert shared_state.running_profile is snap
    assert shared_state.profile_for_runtime() is snap
    input_thread.call_wait(adopted.stop, timeout=5.0)
    assert shared_state.running_profile is None
    assert shared_state.profile_for_runtime() is prof


def test_vjoy_as_input_read_from_the_running_copy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ui, run = Profile(), Profile()
    ui.settings.vjoy_as_input = {1: True}
    run.settings.vjoy_as_input = {2: True}
    monkeypatch.setattr(shared_state, "current_profile", ui)
    monkeypatch.setattr(shared_state, "running_profile", run)
    assert runtime._vjoy_as_input_ids() == {2}
    monkeypatch.setattr(shared_state, "running_profile", None)
    assert runtime._vjoy_as_input_ids() == {1}


# The claim gate's reload (thread-audit.md item 4) ---------------------------


def test_failed_reload_keeps_the_previous_claims(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bus = runtime.InputModuleRuntime()
    kept = bus._gate
    gate = ({"stick": {"buttons": [1]}}, {"dest"}, {"pass"})
    try:
        bus._gate = gate

        def broken() -> list:
            raise OSError("module folder busy")

        monkeypatch.setattr(runtime.registry, "modules", broken)
        bus.reload()
        assert bus._gate is gate, "a failed reload emptied the claims"
    finally:
        bus._gate = kept


def test_reload_publishes_the_gate_in_one_assignment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bus = runtime.InputModuleRuntime()
    kept = bus._gate
    new = ({"a": {}}, {"b"}, {"c"})
    seen: list[str] = []
    real_setattr = type(bus).__setattr__

    def spy(obj: object, name: str, value: object) -> None:
        if obj is bus and name in ("_gate", "_claims", "_dest_guids", "_passthrough"):
            seen.append(name)
        real_setattr(obj, name, value)

    monkeypatch.setattr(bus, "_read_gate", lambda: new)
    monkeypatch.setattr(type(bus), "__setattr__", spy)
    try:
        bus.reload()
    finally:
        monkeypatch.undo()
        bus._gate = kept
    assert seen == ["_gate"]
