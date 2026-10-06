# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Waits that could last forever now end, and tests don't hook the PC.

- A macro waiting while another one runs exclusively stops waiting when
  the macros (or it) are stopped.
- A sound waited for in sequential playback stops being waited for when
  the player stops (a cancelled sound may never say it is done).
- A new relative axis loop doesn't wait for the old one (it ends with its
  Run or when a newer loop replaced it), so the main thread never freezes.
- A device scan that is still busy after a while is reported instead of
  waited for forever.
- With windows_event_hook.enabled off (tests), no keyboard or mouse hook is
  installed.
"""

from __future__ import annotations

import sys

sys.path.append(".")

import threading
import time
from collections.abc import Iterator
from types import SimpleNamespace

import pytest

from gremlin import error, threads


@pytest.fixture(autouse=True)
def _own_thread_list(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(threads, "_live", {})
    yield
    assert threads.shutdown(timeout=2.0) == []


def test_a_macro_stops_waiting_for_an_exclusive_one_when_stopped() -> None:
    from gremlin.macro import MacroManager

    manager = object.__new__(MacroManager)
    manager._preemptive_condition = threading.Condition()
    manager._is_executing_preemptive = True  # another macro runs exclusively
    manager._is_running = False  # the macros were stopped
    manager._executing_macro = {}
    manager._run = 0
    start = time.monotonic()
    # False: the macro stops instead of running its next step.
    assert not manager._wait_while_paused(SimpleNamespace(id=1, is_preempting=False), 0)
    assert time.monotonic() - start < 2.0


def test_a_sound_is_not_waited_for_once_the_player_stops() -> None:
    from gremlin.audio_player import AudioSample

    sample = object.__new__(AudioSample)
    sample._playback_done_event = threading.Event()  # never set
    start = time.monotonic()
    sample.block(lambda: False)
    assert time.monotonic() - start < 2.0


@pytest.mark.parametrize(
    ("plugin", "functor_name"),
    [
        ("map_to_vjoy", "MapToVjoyFunctor"),
        ("map_to_logical_device", "MapToLogicalDeviceFunctor"),
    ],
)
def test_a_new_relative_axis_loop_does_not_wait_for_the_old_one(
    plugin: str, functor_name: str
) -> None:
    import importlib

    module = importlib.import_module(f"action_plugins.{plugin}")
    functor = object.__new__(getattr(module, functor_name))
    stuck = threading.Event()
    old = threads.start("old loop", stuck.wait, stop=stuck.set)
    functor.thread = old
    functor.thread_running = False
    functor.relative_axis_thread = lambda run, token=None: None
    start = time.monotonic()
    functor._start_loop()  # the old one is not joined (06 RB20, GL-061)
    assert time.monotonic() - start < 0.5
    assert functor.thread is not old
    stuck.set()
    functor.thread.join(timeout=2.0)


def test_a_busy_device_scan_is_reported_not_waited_for(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin import device_initialization

    monkeypatch.setattr(device_initialization, "SCAN_WAIT_S", 0.1)
    with device_initialization._joystick_init_lock:  # a scan is still busy
        with pytest.raises(error.GremlinError, match="still busy"):
            device_initialization.joystick_devices_initialization()


def test_with_hooks_turned_off_none_is_installed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin import windows_event_hook

    monkeypatch.setattr(windows_event_hook, "enabled", False)
    for hook in (windows_event_hook.KeyboardHook(), windows_event_hook.MouseHook()):
        was_running = hook._running
        hook.start()
        assert hook._running == was_running
    assert threads.running() == []
