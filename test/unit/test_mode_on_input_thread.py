# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Mode changes and Load Profile with the real input thread (THR-MODE).

Change Mode runs on the input thread: the next event reads the new mode, and
mode_changed reaches a main-thread receiver queued. Load Profile hands its
whole job to the main thread (Backend is never touched from the input
thread)."""

from __future__ import annotations

import sys

sys.path.append(".")

import threading
import time
import types
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from PySide6 import QtCore

from gremlin import input_thread, mode_manager, run_scope, threads
from gremlin.base_classes import Value
from gremlin.types import Event, InputType

_GUID = uuid.UUID("77777777-5555-2222-3333-666666666666")


def _event() -> Event:
    return Event(
        InputType.JoystickButton, 1, _GUID, "Default", is_pressed=True
    )


def _until(cond: Callable[[], bool], seconds: float = 2.0) -> bool:
    end = time.monotonic() + seconds
    while not cond() and time.monotonic() < end:
        QtCore.QCoreApplication.processEvents()
        time.sleep(0.01)
    return cond()


@pytest.fixture(autouse=True)
def _open_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    from gremlin import shared_state
    from gremlin.profile import Profile

    monkeypatch.setattr(shared_state, "current_profile", Profile())


@pytest.fixture
def modes(monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    monkeypatch.setattr(mode_manager, "_known_modes", lambda: set())
    mm = mode_manager.ModeManager()
    stack = list(mm._mode_stack)
    mm._mode_stack = [mode_manager.Mode("Default", None)]
    yield mm
    mm._mode_stack = stack


class _Receiver(QtCore.QObject):
    def __init__(self) -> None:
        super().__init__()
        self.got: list[tuple[str, int]] = []

    @QtCore.Slot(str)
    def on_mode(self, name: str) -> None:
        self.got.append((name, threading.get_ident()))


def test_change_mode_on_input_thread(
    input_thread_running: None,
    modes: Any,  # noqa: ANN401
) -> None:
    from action_plugins.change_mode import ChangeModeData, ChangeModeFunctor, ChangeType

    data = ChangeModeData(InputType.JoystickButton)
    data.change_type = ChangeType.Switch
    data._target_modes = ["Combat"]
    functor = ChangeModeFunctor(data)

    receiver = _Receiver()
    modes.mode_changed.connect(
        receiver.on_mode, QtCore.Qt.ConnectionType.QueuedConnection
    )
    ran_on: list[int] = []

    def press() -> str:
        ran_on.append(threading.get_ident())
        functor(_event(), Value(True), [])
        # The next event on this thread reads the new mode.
        return mode_manager.ModeManager().current.name

    try:
        assert input_thread.call_wait(press, timeout=2.0) == "Combat"
        assert ran_on[0] != threading.get_ident()
        assert modes.current.name == "Combat"  # snapshot read from main
        assert _until(lambda: bool(receiver.got))
        name, ident = receiver.got[0]
        assert name == "Combat"
        assert ident == threading.get_ident()  # delivered on main, queued
    finally:
        modes.mode_changed.disconnect(receiver.on_mode)


def test_previous_and_unwind_swap_the_stack_whole(
    modes: Any,  # noqa: ANN401
) -> None:
    modes.switch_to(mode_manager.Mode("A", "Default"))
    before = modes._mode_stack
    modes.unwind()
    assert modes._mode_stack is not before  # replaced, never edited in place
    assert modes.current.name == "Default"
    assert [m.name for m in before] == ["Default", "A"]


@pytest.mark.skipif(not hasattr(threads, "main_call"), reason="needs threads.main_call")
def test_load_profile_from_input_thread_runs_on_main(
    input_thread_running: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from action_plugins.load_profile import LoadProfileFunctor
    from gremlin import plugin_manager
    from gremlin.ui import backend

    seen: list[tuple[str, int]] = []
    fake = types.SimpleNamespace(
        profile=types.SimpleNamespace(
            has_unsaved_changes=lambda: (
                seen.append(("unsaved", threading.get_ident())) or False
            )
        ),
        run_profile=lambda path: seen.append((path, threading.get_ident())),
    )
    monkeypatch.setattr(backend, "Backend", lambda: fake)
    target = tmp_path / "next.xml"
    target.write_text("<profile/>")
    data = plugin_manager.PluginManager().create_instance(
        "Load Profile", InputType.JoystickButton
    )
    data.profile_filename = str(target)
    functor = LoadProfileFunctor(data)
    run_scope.stop()
    run_scope._reset_for_tests()
    run_scope.begin()
    try:
        input_thread.call_wait(lambda: functor(_event(), Value(True), []), timeout=2.0)
        assert _until(lambda: (str(target), threading.get_ident()) in seen)
        main = threading.get_ident()
        assert all(ident == main for _, ident in seen)
    finally:
        run_scope.stop()
        run_scope._reset_for_tests()


def test_reset_replaces_the_stack_on_the_input_thread(
    input_thread_running: None,
    modes: Any,  # noqa: ANN401
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin import shared_state

    monkeypatch.setattr(shared_state, "current_profile", object())
    monkeypatch.setattr(mode_manager, "resolve_start_mode", lambda _p: "Start")
    ran_on: list[int] = []
    real = modes._set_stack
    monkeypatch.setattr(
        modes, "_set_stack", lambda s: (ran_on.append(threading.get_ident()), real(s))
    )
    assert modes.reset() == "Start"
    assert _until(lambda: modes.current.name == "Start")
    assert ran_on and ran_on[0] != threading.get_ident()


def test_the_input_thread_reads_the_run_copy_of_the_profile(
    modes: Any,  # noqa: ANN401
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin import shared_state

    live = types.SimpleNamespace(
        modes=types.SimpleNamespace(mode_names=lambda: ["Live"])
    )
    copy = types.SimpleNamespace(
        modes=types.SimpleNamespace(mode_names=lambda: ["Copy"])
    )
    monkeypatch.undo()  # the real _known_modes, not the fixture's stub
    monkeypatch.setattr(shared_state, "current_profile", live)
    monkeypatch.setattr(shared_state, "running_profile", copy, raising=False)
    assert mode_manager._known_modes() == {"Copy"}
    monkeypatch.setattr(shared_state, "running_profile", None, raising=False)
    assert mode_manager._known_modes() == {"Live"}
