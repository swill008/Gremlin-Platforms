# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A Run's timers on the input thread (thread batch 3,
claude/plans/fix-plans/contract-THR.md): Tempo-like run_scope timers fire on
the input thread while the main thread is blocked, a pulse's release there
doesn't block it for 50 ms, Stop cancels them on their own thread, the vJoy
keep-alive belongs to it, and speech and notices still hop to the main
thread. These tests start the real input thread.
"""

from __future__ import annotations

import sys

sys.path.append(".")

import threading
import time
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from PySide6 import QtCore

from gremlin import base_classes, input_thread, run_scope, threads, tts
from gremlin.modules import output


def _wait_for(check: Callable[[], bool], seconds: float = 2.0) -> bool:
    """Runs the main thread's events until check() or the limit."""
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        QtCore.QCoreApplication.processEvents()
        if check():
            return True
        time.sleep(0.005)
    return check()


@pytest.fixture
def run(input_thread_running: None) -> Iterator[None]:
    """A Run is on (its timers run), ended and forgotten afterwards."""
    run_scope._reset_for_tests()
    input_thread.call_wait(run_scope.begin, timeout=2.0)
    yield
    input_thread.call_wait(run_scope.stop, timeout=3.0)
    run_scope._reset_for_tests()


@pytest.fixture
def keep_alive_on() -> Iterator[None]:
    """The vJoy keep-alive's Options switch on (off at first, 06 S54)."""
    from gremlin.config import Configuration

    before = Configuration().value("global", "vjoy", "keep-alive")
    Configuration().set("global", "vjoy", "keep-alive", True)
    yield
    Configuration().set("global", "vjoy", "keep-alive", before)


@pytest.fixture
def qt_warnings() -> Iterator[list[str]]:
    seen: list[str] = []

    def handler(_mode: object, _context: object, message: str) -> None:
        seen.append(message)

    previous = QtCore.qInstallMessageHandler(handler)
    yield seen
    QtCore.qInstallMessageHandler(previous)


def test_a_tempo_timer_fires_on_the_input_thread_while_main_is_blocked(
    run: None,
) -> None:
    fired: list[tuple[bool, float]] = []
    started = time.monotonic()
    input_thread.call_wait(
        lambda: run_scope.timer(
            "tempo",
            0.1,
            lambda: fired.append(
                (input_thread.is_input_thread(), time.monotonic() - started)
            ),
        ),
        timeout=2.0,
    )
    time.sleep(0.5)  # the main thread is blocked: no events here
    assert len(fired) == 1
    on_input, after = fired[0]
    assert on_input
    assert after < 0.45


class _Event:
    is_pressed = True
    raw_value: object = True

    def clone(self) -> _Event:
        copy = _Event()
        copy.is_pressed = self.is_pressed
        copy.raw_value = self.raw_value
        return copy


class _Pulser:
    """What _pulse_event needs of a functor: _process_event."""

    def __init__(self) -> None:
        self.seen: list[tuple[bool, bool]] = []

    def _process_event(
        self, _functors: list, event: _Event, _value: object, _props: list
    ) -> None:
        self.seen.append((event.is_pressed, input_thread.is_input_thread()))


def test_a_pulse_release_on_the_input_thread_does_not_block_it(run: None) -> None:
    pulser = _Pulser()

    def pulse() -> float:
        started = time.monotonic()
        base_classes.AbstractFunctor._pulse_event(
            pulser,  # type: ignore[arg-type]
            [],
            _Event(),  # type: ignore[arg-type]
            base_classes.Value(True),
        )
        return time.monotonic() - started

    took = input_thread.call_wait(pulse, timeout=2.0)
    assert took < 0.04, f"the input thread waited {took * 1000:.0f} ms"
    assert pulser.seen == [(True, True)]
    time.sleep(0.25)
    assert pulser.seen == [(True, True), (False, True)]


@pytest.mark.parametrize("stopped_on", ["input", "main"])
def test_stop_cancels_input_thread_timers_on_their_thread(
    input_thread_running: None, qt_warnings: list[str], stopped_on: str
) -> None:
    run_scope._reset_for_tests()
    input_thread.call_wait(run_scope.begin, timeout=2.0)
    fired: list[bool] = []
    made: list[run_scope.Timer] = []
    input_thread.call_wait(
        lambda: made.append(run_scope.timer("tempo", 0.15, lambda: fired.append(True))),
        timeout=2.0,
    )
    inner = made[0]._inner
    assert isinstance(inner, threads.QtTimer)
    assert inner._ident == input_thread.call_wait(threading.get_ident, timeout=2.0)
    if stopped_on == "input":
        input_thread.call_wait(run_scope.stop, timeout=3.0)
    else:
        run_scope.stop()
    assert not made[0].is_alive()
    assert not inner.is_alive()
    input_thread.call_wait(lambda: None, timeout=2.0)
    assert inner._timer is None or not inner._timer.isActive()
    time.sleep(0.3)
    assert fired == []
    assert run_scope.pending_timers() == []
    assert not [w for w in qt_warnings if "another thread" in w]
    run_scope._reset_for_tests()


def test_the_vjoy_keep_alive_is_armed_on_the_input_thread(
    run: None, keep_alive_on: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    vid = 15
    monkeypatch.setattr(output, "_opened_vjoy", lambda _vid: object())
    monkeypatch.setitem(output._keep_alive, vid, None)  # restored afterwards
    output._keep_alive.pop(vid)
    output._arm_keep_alive(vid)  # opened on the main thread
    input_thread.call_wait(lambda: None, timeout=2.0)
    _, timer = output._keep_alive[vid]
    inner = timer._inner
    assert isinstance(inner, threads.QtTimer)
    assert inner._ident == input_thread.call_wait(threading.get_ident, timeout=2.0)
    input_thread.call_wait(timer.cancel, timeout=2.0)


def test_the_keep_alive_stays_on_the_main_thread_in_inline_mode(
    qapp: object, keep_alive_on: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    vid = 15
    monkeypatch.setattr(output, "_opened_vjoy", lambda _vid: object())
    monkeypatch.setitem(output._keep_alive, vid, None)
    output._keep_alive.pop(vid)
    output._arm_keep_alive(vid)
    _, timer = output._keep_alive[vid]
    assert isinstance(timer._inner, threads.QtTimer)
    assert timer._inner._ident == threading.main_thread().ident
    timer.cancel()


class _FakeEngine:
    def __init__(self) -> None:
        self.stopped_on: list[bool] = []

    def stop(self) -> None:
        self.stopped_on.append(threading.current_thread() is threading.main_thread())


def _manager() -> Any:  # noqa: ANN401 - a fresh TTSManager, not the singleton
    manager = object.__new__(tts.TTSManager)
    tts.TTSManager.__init__(manager)
    return manager


def test_speech_asked_on_the_input_thread_is_spoken_on_main(
    input_thread_running: None,
) -> None:
    manager = _manager()
    manager._running = True
    seen: list[bool] = []
    manager._enqueue_now = lambda _request, _mode: seen.append(
        threading.current_thread() is threading.main_thread()
    )
    request = tts.TTSRequest("hello", 0.0, 1.0, 0.0)
    input_thread.call_wait(
        manager.enqueue, request, tts.TTSQueueMode.QueueBack, timeout=2.0
    )
    assert _wait_for(lambda: seen == [True])


def test_speech_stopped_on_the_input_thread_stops_on_main(
    input_thread_running: None,
) -> None:
    manager = _manager()
    manager._running = True
    engine = _FakeEngine()
    manager._engine = engine
    manager._queue.append(tts.TTSRequest("left", 0.0, 1.0, 0.0))
    input_thread.call_wait(manager.stop, timeout=2.0)
    assert not manager._running  # later requests are dropped at once
    assert _wait_for(lambda: engine.stopped_on == [True])
    assert not manager._queue


def test_the_cant_send_notice_from_the_input_thread_goes_out_on_main(
    input_thread_running: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent: list[bool] = []
    monkeypatch.setattr(
        output,
        "_send_cant_send",
        lambda: sent.append(threading.current_thread() is threading.main_thread()),
    )
    input_thread.call_wait(output.notify_cant_send, timeout=2.0)
    assert _wait_for(lambda: bool(sent))
    assert all(sent)


def test_the_timing_summary_fires_when_dispatch_runs_on_the_input_thread(
    input_thread_running: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin import trace_timing as tt

    written: list[tuple[str, bool]] = []
    monkeypatch.setattr(
        tt.trace,
        "timing",
        lambda text, warning=False: written.append(
            (text, input_thread.is_input_thread())
        ),
        raising=False,
    )
    monkeypatch.setattr(tt, "INTERVAL", 0.1)
    monkeypatch.setattr(tt, "on", True)
    tt._cancel_timer()
    tt._reset()
    event = type("E", (), {})()
    now = tt.counter()
    tt.stamp_rx(event, now - 1000, now)
    try:
        input_thread.call_wait(tt.dispatch, event, timeout=2.0)
        time.sleep(0.4)  # the main thread is blocked: the input thread ticks
        assert written, "no summary line"
        text, on_input = written[0]
        assert on_input
        assert "1 events" in text
        assert "CPU input" in text
    finally:
        monkeypatch.setattr(tt, "on", False)
        input_thread.call_wait(tt._cancel_timer, timeout=2.0)
        tt._reset()
