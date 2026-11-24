# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Run, Stop and the toolbar mode go from the window to the input thread as
commands (contract-THR.md, THR-UI; thread-ui.md 1.3).

With the real input thread (fixture input_thread_running):
- Run sends RunControl.start to the input thread with a copy of the open
  profile and returns at once; the status reads Starting until runStarted
  comes back (queued), then Running.
- Stop goes the same way.
- The toolbar mode pick changes ModeManager on the input thread, and
  ui_state.currentMode follows through mode_changed on the main thread.
- The window's Run/Stop/mode entry points raise off the main thread.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, cast

import pytest
from PySide6 import QtCore

from gremlin import code_runner, input_thread, mode_manager, shared_state, threads
from gremlin.profile import Profile

_KEEP: list[object] = []


class _Runner:
    def __init__(self) -> None:
        self.running = False

    def is_running(self) -> bool:
        return self.running


class _FakeRunControl(QtCore.QObject):
    """RunControl's interface (contract-THR.md); start waits for `gate` so
    the test can look at the window while the Run is starting."""

    runStarted = QtCore.Signal(bool, str)
    runStopped = QtCore.Signal()

    def __init__(self) -> None:
        super().__init__()
        self.runner = _Runner()
        self.gate = threading.Event()
        self.calls: list[tuple[str, str, object]] = []

    def start(self, running: object, mode: str) -> None:
        self.calls.append(("start", threading.current_thread().name, running))
        self.gate.wait(5.0)
        self.runner.running = True
        self.runStarted.emit(True, "")

    def stop(self) -> None:
        self.calls.append(("stop", threading.current_thread().name, None))
        self.runner.running = False
        self.runStopped.emit()


def _pump_until(check: Callable[[], bool], seconds: float = 3.0) -> bool:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        QtCore.QCoreApplication.processEvents()
        if check():
            return True
        time.sleep(0.01)
    return False


@pytest.fixture
def control(monkeypatch: pytest.MonkeyPatch) -> _FakeRunControl:
    fake = _FakeRunControl()
    _KEEP.append(fake)
    monkeypatch.setattr(code_runner, "run_control", lambda: fake, raising=False)
    return fake


@pytest.fixture
def be(
    control: _FakeRunControl, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Iterator[Any]:
    """The program's Backend class (not the shared instance) with a profile
    of two modes; puts back the open profile and the mode stack."""
    from gremlin import process_monitor
    from gremlin.ui import backend

    monkeypatch.setattr(process_monitor.ProcessMonitor, "start", lambda self: None)
    before = shared_state.current_profile
    mm = mode_manager.ModeManager()
    stack = list(mm._mode_stack)
    made = backend.Backend.klass(cast(Any, None))
    _KEEP.append(made)
    path = tmp_path / "flight.xml"
    p = Profile()
    p.modes.add_mode("Alpha")
    p.modes.add_mode("Bravo")
    p.to_xml(path)
    made.profile = Profile()
    made.profile.from_xml(path)
    made.profileChanged.emit()
    yield made
    control.gate.set()
    shared_state.release_input_highlighting("run")
    shared_state.current_profile = before
    mm._mode_stack = stack


def test_run_starts_on_the_input_thread_and_status_follows_runStarted(
    input_thread_running: None, be: Any, control: _FakeRunControl  # noqa: ANN401
) -> None:
    be.activate_gremlin(True)
    # Returned without waiting for the Run (start is held at the gate).
    assert be.gremlinStarting and not be.gremlinActive
    assert _pump_until(lambda: bool(control.calls))
    kind, thread_name, running = control.calls[0]
    assert kind == "start" and thread_name.endswith(input_thread.NAME)
    # A copy taken at Run: edits made while it runs apply at the next Run.
    assert isinstance(running, Profile) and running is not be.profile
    assert running.modes.mode_names() == be.profile.modes.mode_names()
    assert running.fpath == be.profile.fpath
    control.gate.set()
    assert _pump_until(lambda: not be.gremlinStarting)
    assert be.gremlinActive
    assert shared_state.suspend_input_highlighting()  # Run's hold (03 S114)


def test_stop_goes_to_the_input_thread(
    input_thread_running: None, be: Any, control: _FakeRunControl  # noqa: ANN401
) -> None:
    control.gate.set()
    be.activate_gremlin(True)
    assert _pump_until(lambda: be.gremlinActive and not be.gremlinStarting)
    be.activate_gremlin(False)
    assert _pump_until(lambda: not be.gremlinActive)
    kind, thread_name, _ = control.calls[-1]
    assert kind == "stop" and thread_name.endswith(input_thread.NAME)


def test_toggle_while_starting_stops(
    input_thread_running: None, be: Any, control: _FakeRunControl  # noqa: ANN401
) -> None:
    """Run pressed, then Stop before the Run said it started: a Stop, not a
    second Run."""
    be.toggleActiveState()
    be.toggleActiveState()
    control.gate.set()
    assert _pump_until(lambda: len(control.calls) == 2)
    assert [c[0] for c in control.calls] == ["start", "stop"]


def test_select_mode_changes_the_stack_on_the_input_thread(
    input_thread_running: None, be: Any  # noqa: ANN401
) -> None:
    mm = mode_manager.ModeManager()
    seen: list[tuple[str, str]] = []

    def note(name: str) -> None:
        seen.append((name, threading.current_thread().name))

    # Direct: records the thread that emitted it (where the stack changed).
    mm.mode_changed.connect(note, QtCore.Qt.ConnectionType.DirectConnection)
    try:
        be.selectMode("Bravo")
        assert _pump_until(lambda: mm.current.name == "Bravo")
        assert _pump_until(lambda: bool(seen))
    finally:
        mm.mode_changed.disconnect(note)
    assert seen[0][0] == "Bravo" and seen[0][1].endswith(input_thread.NAME)
    assert be.ui_state.currentMode == "Bravo"
    # The stack's own change, back on the main thread through mode_changed.
    be.ui_state.setCurrentMode("Alpha")
    mm.mode_changed.emit("Bravo")
    assert _pump_until(lambda: be.ui_state.currentMode == "Bravo")


def test_auto_load_restarts_the_run_after_the_profile_change(
    input_thread_running: None,
    be: Any,  # noqa: ANN401
    control: _FakeRunControl,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Auto-load stops the Run, opens the game's profile and runs it: the
    decision to run again reads what was asked (Stop), not the status that
    still says Running until the input thread answers (THR-AUDIT item 2)."""
    from gremlin import config

    game = tmp_path / "game.xml"
    Profile().to_xml(game)
    real_value = be.config.value
    wanted = {
        ("profile", "automation", "enable-auto-loading"): True,
        ("profile", "automation", "no-profile-action"): "stop",
        ("profile", "automation", "default-profile"): "",
    }
    # On the class: patching the singleton's instance would leave a bound
    # "value" attribute on it after the test (monkeypatch puts the old bound
    # method back as an instance attribute), over every later class patch.
    monkeypatch.setattr(
        type(be.config), "value",
        lambda _self, *key: wanted.get(key, real_value(*key)),
    )
    monkeypatch.setattr(config, "get_profile_with_regex", lambda _path: str(game))
    monkeypatch.setattr(be, "_record_profile_use", lambda _path: None)
    monkeypatch.setattr(be, "_opened_by_user", lambda _path: None)
    control.gate.set()
    be.activate_gremlin(True)
    assert _pump_until(lambda: be.gremlinActive and not be.gremlinStarting)
    control.calls.clear()

    be._active_process_changed_cb("C:/Games/game.exe")

    assert be.profile.fpath == game
    # Stop (auto-load), Stop (the profile load), then Run, in that order.
    assert _pump_until(lambda: len(control.calls) >= 3), control.calls
    assert [c[0] for c in control.calls] == ["stop", "stop", "start"]
    assert _pump_until(lambda: be.gremlinActive and not be.gremlinStarting)
    running = control.calls[-1][2]
    assert isinstance(running, Profile) and running.fpath == game


@pytest.mark.parametrize(
    "call",
    [
        lambda b: b.activate_gremlin(False),
        lambda b: b.selectMode("Bravo"),
        lambda b: b.run_profile("nowhere.xml"),
        lambda b: b._on_mode_changed("Bravo"),
    ],
)
def test_window_entry_points_raise_off_the_main_thread(
    be: Any, call: Callable[[Any], None]  # noqa: ANN401
) -> None:
    raised: list[BaseException] = []

    def off_main() -> None:
        try:
            call(be)
        except BaseException as error:  # noqa: BLE001
            raised.append(error)

    worker = threading.Thread(target=off_main)
    worker.start()
    worker.join(5.0)
    assert raised and isinstance(raised[0], threads.WrongThread)
