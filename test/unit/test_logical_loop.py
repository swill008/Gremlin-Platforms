# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Logical Device loop guard (06 S94, D-06-LD-LOOP): unit behaviour of
gremlin.logical_loop. The real Run path is test_logical_loop_e2e.py."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Iterator

import pytest

from gremlin import clock, log_once, logical_loop
from gremlin.signal import signal

A = ("axis", 1)
B = ("button", 2)


@pytest.fixture(autouse=True)
def _fresh(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[list, list]]:
    logical_loop.reset()
    log_once.reset()
    notices: list[tuple[str, str]] = []

    def notice(title: str, text: str) -> None:
        notices.append((title, text))

    signal.showNotification.connect(notice)
    now = [1000.0]
    monkeypatch.setattr(clock, "monotonic", lambda: now[0])
    yield notices, now
    signal.showNotification.disconnect(notice)
    logical_loop.reset()


def _warnings(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [
        r.getMessage()
        for r in caplog.records
        if r.name == "user" and r.levelno == logging.WARNING
    ]


def test_self_recursion_stops_at_8_hops(
    _fresh: tuple, caplog: pytest.LogCaptureFixture
) -> None:
    """06 S94: a control driving itself on one thread: 8 sends, then drop."""
    notices, _ = _fresh
    sent: list[int] = []
    results: list[bool] = []

    def send() -> None:
        sent.append(1)
        results.append(logical_loop.guarded(A, "Axis 1", send))

    with caplog.at_level(logging.WARNING, logger="user"):
        assert logical_loop.guarded(A, "Axis 1", send) is True
    assert len(sent) == logical_loop.MAX_HOPS == 8
    assert results.count(False) == 1
    assert _warnings(caplog) == [
        "Logical Device: a loop between controls was stopped "
        "(Axis 1 -> Axis 1) (shown once; it may keep happening)"
    ]
    assert notices == [
        ("Logical Device Loop",
         "Logical Device: a loop between controls was stopped (Axis 1 -> Axis 1)")
    ]


def test_a_to_b_to_a_stops(_fresh: tuple, caplog: pytest.LogCaptureFixture) -> None:
    """06 S94: A -> B -> A on one thread stops within 8 hops."""
    notices, _ = _fresh
    sent: list[str] = []

    def send_a() -> None:
        sent.append("A")
        logical_loop.guarded(B, "Button 2", send_b)

    def send_b() -> None:
        sent.append("B")
        logical_loop.guarded(A, "Button 1", send_a)

    with caplog.at_level(logging.WARNING, logger="user"):
        logical_loop.guarded(A, "Button 1", send_a)
    assert sent == ["A", "B"] * 4
    assert len(notices) == 1
    assert notices[0][1].endswith("(Button 1 -> Button 2 -> Button 1)")
    assert len(_warnings(caplog)) == 1


def test_a_chain_without_a_loop_is_not_stopped(_fresh: tuple) -> None:
    notices, _ = _fresh
    sent: list[str] = []
    logical_loop.guarded(
        A, "A", lambda: logical_loop.guarded(B, "B", lambda: sent.append("B"))
    )
    # Repeated sends from one thread (a stick, a repeating macro) are new chains.
    for _ in range(50):
        assert logical_loop.guarded(A, "A", lambda: sent.append("A"))
    assert sent == ["B"] + ["A"] * 50
    assert notices == []


def _on_new_thread(fn: Callable[[], object]) -> None:
    thread = threading.Thread(target=fn)
    thread.start()
    thread.join(timeout=5)


def test_queued_macro_self_loop_stops(
    _fresh: tuple, caplog: pytest.LogCaptureFixture
) -> None:
    """06 S94: a macro step re-triggering its own control: each run is a new
    thread, the send is queued; the chain is carried on the control."""
    _, now = _fresh
    caplog.set_level(logging.WARNING, logger="user")
    results: list[bool] = []
    for _ in range(12):
        now[0] += 0.01
        _on_new_thread(
            lambda: results.append(logical_loop.guarded(A, "Button 1", lambda: None))
        )
    assert results[:8] == [True] * 8
    assert results[8] is False
    # Told from the macro thread: the notice reaches the main thread through
    # its event loop (none here), so the log line and the told flag are checked.
    assert logical_loop._told is True
    assert [r.getMessage() for r in caplog.records if r.name == "user"] == [
        "Logical Device: a loop between controls was stopped "
        "(Button 1 -> Button 1) (shown once; it may keep happening)"
    ]


def test_slow_repeats_from_new_threads_are_not_a_loop(_fresh: tuple) -> None:
    """A button mashed slower than QUEUED_WINDOW: each press a new chain."""
    notices, now = _fresh
    for _ in range(20):
        now[0] += logical_loop.QUEUED_WINDOW + 0.05
        _on_new_thread(lambda: logical_loop.guarded(A, "A", lambda: None))
    assert notices == []


def test_queued_relative_self_loop_stops_by_source(_fresh: tuple) -> None:
    """06 S94: a Relative writer (one long-lived thread) whose source is its
    own target: the chain continues from the source's chain each step."""
    notices, _ = _fresh
    results = [
        logical_loop.guarded(A, "Axis 1", lambda: None, source=A) for _ in range(10)
    ]
    assert results[:8] == [True] * 8 and results[8] is False
    assert len(notices) == 1


def test_queued_a_b_a_by_source(_fresh: tuple) -> None:
    notices, _ = _fresh
    results: list[bool] = []
    for _ in range(6):
        results.append(logical_loop.guarded(B, "B", lambda: None, source=A))
        results.append(logical_loop.guarded(A, "A", lambda: None, source=B))
    assert False in results and results.index(False) == 8
    assert len(notices) == 1


def test_a_writer_from_another_control_is_not_a_loop(_fresh: tuple) -> None:
    """A -> B Relative, A driven from outside: the chain stays A -> B."""
    notices, _ = _fresh
    for _ in range(30):
        logical_loop.guarded(A, "A", lambda: None)  # A moved by its stick
        assert logical_loop.guarded(B, "B", lambda: None, source=A)
    assert notices == []


def test_reported_once_per_run_and_reset_clears(
    _fresh: tuple, caplog: pytest.LogCaptureFixture
) -> None:
    notices, _ = _fresh

    def loop() -> None:
        logical_loop.guarded(A, "A", loop)

    with caplog.at_level(logging.WARNING, logger="user"):
        loop()
        loop()
        logical_loop.guarded(
            B, "B", lambda: logical_loop.guarded(B, "B", lambda: None), source=A
        )
    assert len(notices) == 1  # one notice per Run
    # Run 2: reset (Run start / Stop) and log_once.reset (Run start).
    logical_loop.reset()
    log_once.reset()
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="user"):
        loop()
    assert len(notices) == 2
    assert len(_warnings(caplog)) == 1


def test_reset_clears_carried_chains(_fresh: tuple) -> None:
    for _ in range(7):
        logical_loop.guarded(A, "A", lambda: None, source=A)
    logical_loop.reset()
    assert logical_loop.guarded(A, "A", lambda: None, source=A) is True


def test_never_raises(_fresh: tuple, monkeypatch: pytest.MonkeyPatch) -> None:
    unhashable = ["not", "hashable"]
    sent: list[int] = []
    assert logical_loop.guarded(unhashable, "X", lambda: sent.append(1)) is True  # type: ignore[arg-type]

    def broken(*_a: object) -> None:
        raise RuntimeError("signal gone")

    monkeypatch.setattr(logical_loop, "_report", broken)

    def loop() -> None:
        logical_loop.guarded(A, "A", loop)

    loop()  # the drop's report fails: still no error
    assert sent == [1]


def test_send_errors_pass_through_and_leave_no_chain(_fresh: tuple) -> None:
    def bad() -> None:
        raise ValueError("boom")

    with pytest.raises(ValueError):
        logical_loop.guarded(A, "A", bad)
    assert logical_loop._stack() == []
