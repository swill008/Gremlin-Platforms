# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Waits that could last forever now end, and tests don't hook the PC.

- A macro waiting while another one runs exclusively stops waiting when
  the macros (or it) are stopped.
- A sound waited for in sequential playback stops being waited for when
  the player stops (a cancelled sound may never say it is done).
- A new relative axis loop waits at most 1 s for the old one; one that
  doesn't end is logged instead of freezing the main thread.
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
    start = time.monotonic()
    manager._wait_while_paused(SimpleNamespace(id=1, is_preempting=False))
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
def test_a_relative_axis_loop_that_does_not_end_is_logged_not_waited_for(
    plugin: str, functor_name: str, caplog: pytest.LogCaptureFixture
) -> None:
    import importlib

    from gremlin import log_once

    module = importlib.import_module(f"action_plugins.{plugin}")
    functor = object.__new__(getattr(module, functor_name))
    stuck = threading.Event()
    functor.thread = threads.start("old loop", stuck.wait, stop=stuck.set)
    functor.thread_running = False
    log_once.reset()
    start = time.monotonic()
    functor._start_loop()
    assert time.monotonic() - start < 2.0
    assert "did not end within 1 s" in caplog.text
    assert threads.running() == ["Gremlin-Platforms: old loop"]  # none started
    stuck.set()


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
