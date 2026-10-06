# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Every program thread is named, listed while it runs, and can be stopped.

(gremlin/threads.py.) Also the stop races found while moving the threads
onto it: a stop() right after start() used to be undone by the starting
thread (audio player, mouse controller) or lost (keyboard and mouse hooks),
and the wait for the thread then never ended; and a vJoy keep-alive timer
firing as the device was released armed a new one that nothing cancelled.

The keep-alive test waits for the timer's results, not a fixed time
(GL-001, AU-119).
"""

from __future__ import annotations

import sys

sys.path.append(".")

import contextlib
import threading
import time
from collections.abc import Callable, Iterator
from unittest import mock

import pytest

from gremlin import threads


@pytest.fixture(autouse=True)
def _own_thread_list(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Each test sees only the threads it starts: earlier tests leave shared
    ones running (the event listener, its keyboard hook), which a test must
    neither count nor stop."""
    monkeypatch.setattr(threads, "_live", {})
    yield
    assert threads.shutdown(timeout=2.0) == []


@contextlib.contextmanager
def _put_back(running: bool, start: Callable[[], None]) -> Iterator[None]:
    """Starts a shared component again if it was running before the test."""
    try:
        yield
    finally:
        if running:
            start()


def _wait_for(check: Callable[[], bool], seconds: float = 10.0) -> bool:
    """Polls check() up to seconds (generous: a busy PC is slow)."""
    end = time.monotonic() + seconds
    while not check():
        if time.monotonic() > end:
            return False
        time.sleep(0.005)
    return True


def test_a_thread_is_named_and_listed_while_it_runs() -> None:
    release = threading.Event()
    thread = threads.start("sample", release.wait)
    assert thread.name == "Gremlin-Platforms: sample"
    assert threads.running() == ["Gremlin-Platforms: sample"]
    release.set()
    thread.join(2.0)
    assert threads.running() == []


def test_a_timer_leaves_the_list_when_it_fires_or_is_cancelled() -> None:
    fired = threading.Event()
    t = threads.timer("quick", 0.01, fired.set)
    assert fired.wait(2.0)
    t.join(2.0)
    later = threads.timer("later", 60, fired.set)
    assert "Gremlin-Platforms: later" in threads.running()
    later.cancel()
    later.join(2.0)
    assert threads.running() == []


def test_shutdown_asks_each_thread_to_stop_and_waits() -> None:
    stop = threading.Event()
    threads.start("loop", stop.wait, stop=stop.set)
    threads.timer("timer", 60, lambda: None)
    start = time.monotonic()
    assert threads.shutdown(timeout=20.0) == []
    assert time.monotonic() - start < 10.0  # asked, not waited out


def test_shutdown_names_a_thread_that_will_not_stop(
    caplog: pytest.LogCaptureFixture,
) -> None:
    release = threading.Event()
    threads.start("stubborn", release.wait)  # no stop request
    assert threads.shutdown(timeout=0.2) == ["Gremlin-Platforms: stubborn"]
    assert "Still running" in caplog.text and "stubborn" in caplog.text
    release.set()


def test_an_error_in_a_thread_still_takes_it_off_the_list() -> None:
    def fail() -> None:
        raise RuntimeError("boom")

    with mock.patch.object(threading, "excepthook"):
        thread = threads.start("failing", fail)
        thread.join(2.0)
    assert threads.running() == []


@pytest.mark.parametrize("hook_name", ["KeyboardHook", "MouseHook"])
def test_a_hook_stopped_right_after_starting_does_not_hang(
    hook_name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin import windows_event_hook

    monkeypatch.setattr(windows_event_hook, "enabled", True)
    hook = getattr(windows_event_hook, hook_name)()
    with _put_back(hook._running, hook.start):
        hook.stop()
        for _ in range(20):
            hook.start()
            hook.stop()
            assert threads.running() == [], hook_name


def test_the_audio_player_stopped_right_after_starting_ends() -> None:
    from gremlin.audio_player import AudioPlayer

    player = AudioPlayer()
    with _put_back(player._is_ready, player.start):
        player.stop()
        for _ in range(20):
            player.start()
            player.stop()
            assert threads.running() == []


def test_the_mouse_controller_stopped_right_after_starting_ends() -> None:
    from gremlin.sendinput import MouseController

    controller = MouseController()
    with _put_back(controller._is_running, controller.start):
        controller.stop()
        for _ in range(20):
            controller.start()
            controller.stop()
            assert threads.running() == []


def test_a_released_vjoy_device_arms_no_new_keep_alive() -> None:
    from vjoy import vjoy

    device = object.__new__(vjoy.VJoy)
    device.vjoy_id = 1
    device._last_active = time.time()
    device._keep_alive_lock = threading.Lock()
    device._keep_alive_timer = None
    name = "Gremlin-Platforms: vJoy 1 keep-alive"
    with (
        mock.patch.object(vjoy.VJoy, "keep_alive_timeout", 0.01),
        mock.patch.object(vjoy.VJoy, "reset") as reset,
        mock.patch.object(vjoy.VJoyInterface, "RelinquishVJD"),
    ):
        device._arm_keep_alive()
        # It fires and re-arms several times (one timer, or two for a moment
        # while one hands over to the next).
        assert _wait_for(lambda: reset.call_count >= 3)
        assert set(threads.running()) == {name}
        device.invalidate()
        # The last one ends and none is armed after it.
        assert _wait_for(lambda: threads.running() == [])
