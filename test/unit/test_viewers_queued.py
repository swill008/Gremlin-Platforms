# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The viewers follow the input module feed on the main thread (thread batch
THR-VIEWERS, thread-ui.md 1.1): emitted from the input thread, each slot
runs queued on the main thread, and a burst is one update (R7)."""

from __future__ import annotations

import threading
import types
from collections.abc import Callable, Iterator

import pytest
from PySide6 import QtCore

from gremlin import input_thread, threads
from gremlin.modules.runtime import InputModuleRuntime
from gremlin.types import InputType


def _event() -> types.SimpleNamespace:
    return types.SimpleNamespace(
        device_guid="{AAAA}",
        event_type=InputType.JoystickAxis,
        identifier=1,
        value=0.5,
        is_pressed=False,
        synthetic=False,
    )


@pytest.fixture
def queued(qapp: object, monkeypatch: pytest.MonkeyPatch) -> Iterator[list[bool]]:
    """Not inline (the program's mode); the thread each guarded slot ran on
    is recorded: True when it was the main thread."""
    ran: list[bool] = []
    monkeypatch.setattr(
        threads,
        "assert_main",
        lambda what: ran.append(threading.current_thread() is threading.main_thread()),
    )
    input_thread.set_inline(False)
    yield ran
    input_thread.set_inline(True)


def _emit_from_worker(signal: object, count: int = 1) -> None:
    def work() -> None:
        for _ in range(count):
            signal.emit(_event())  # type: ignore[attr-defined]

    worker = threading.Thread(target=work)
    worker.start()
    worker.join(5.0)
    assert not worker.is_alive()
    QtCore.QCoreApplication.processEvents()


def _make_live() -> object:
    from gremlin.ui.live_input import DeviceLiveState

    return DeviceLiveState()


def _make_pair() -> object:
    from gremlin.ui.pair_live import PairLiveThrottle

    return PairLiveThrottle()


def _make_xbox() -> object:
    from gremlin.ui.xbox_viewer import XboxPadLive

    return XboxPadLive()


def _make_logical() -> object:
    from gremlin.ui.logical_layout import LogicalLayoutModel

    return LogicalLayoutModel()


def _make_modules() -> object:
    from gremlin.ui.module_model import ModuleListModel

    return ModuleListModel()


@pytest.mark.parametrize(
    ("make", "name"),
    [
        (_make_live, "_on_event"),
        (_make_pair, "_on_event"),
        (_make_xbox, "_on_event"),
        (_make_logical, "_on_input"),
        (_make_modules, "_on_joy"),
    ],
)
def test_event_slot_runs_on_the_main_thread(
    queued: list[bool], make: Callable[[], object], name: str
) -> None:
    # Old: a direct connection, so the slot ran on the emitting thread.
    viewer = make()
    try:
        _emit_from_worker(InputModuleRuntime().event)
        assert queued, f"{name} never ran"
        assert all(queued), f"{name} ran off the main thread"
    finally:
        InputModuleRuntime().event.disconnect(getattr(viewer, name))


def test_keyboard_slot_runs_on_the_main_thread(queued: list[bool]) -> None:
    from gremlin.ui.keyboard_layout import KeyboardLayoutModel

    model = KeyboardLayoutModel()
    try:
        _emit_from_worker(InputModuleRuntime().key_event)
        assert queued
        assert all(queued)
    finally:
        InputModuleRuntime().key_event.disconnect(model._on_key)  # noqa: SLF001


def test_a_burst_for_one_device_is_applied_once(
    queued: list[bool], monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.ui.module_model import ModuleListModel

    model = ModuleListModel()
    applied: list[object] = []
    monkeypatch.setattr(model, "_apply_joy", applied.append)
    try:
        _emit_from_worker(InputModuleRuntime().event, count=500)
        QtCore.QCoreApplication.processEvents()
        # Old: one update per event (500).
        assert len(applied) == 1
    finally:
        InputModuleRuntime().event.disconnect(model._on_joy)  # noqa: SLF001
