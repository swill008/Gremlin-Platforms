# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Logical Device loop guard (06 S94, S94a, D-06-LD-LOOP,
D-06-LOOP-CHAIN): unit behaviour of gremlin.logical_loop. The real Run path
is test_logical_loop_e2e.py."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Iterator

import pytest

from gremlin import log_once, logical_loop
from gremlin.signal import signal

A = ("axis", 1)
B = ("button", 2)


@pytest.fixture(autouse=True)
def _fresh() -> Iterator[list]:
    logical_loop.reset()
    log_once.reset()
    notices: list[tuple[str, str]] = []

    def notice(title: str, text: str) -> None:
        notices.append((title, text))

    signal.showNotification.connect(notice)
    yield notices
    signal.showNotification.disconnect(notice)
    logical_loop.reset()


def _warnings(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [
        r.getMessage()
        for r in caplog.records
        if r.name == "user" and r.levelno == logging.WARNING
    ]


def _nothing(_path: tuple) -> None:
    pass


def test_self_recursion_stops_at_8_hops(
    _fresh: list, caplog: pytest.LogCaptureFixture
) -> None:
    """06 S94: a control driving itself on one thread: 8 sends, then drop."""
    notices = _fresh
    sent: list[int] = []
    results: list[bool] = []

    def send(path: tuple) -> None:
        sent.append(len(path))
        results.append(logical_loop.guarded(A, "Axis 1", send, path))

    with caplog.at_level(logging.WARNING, logger="user"):
        assert logical_loop.guarded(A, "Axis 1", send) is True
    # Each send gets the chain with its own hop added.
    assert sent == list(range(1, logical_loop.MAX_HOPS + 1))
    assert results.count(False) == 1
    assert _warnings(caplog) == [
        "Logical Device: a loop between controls was stopped "
        "(Axis 1 → Axis 1) (shown once; it may keep happening)"
    ]
    assert notices == [
        ("Logical Device Loop",
         "Logical Device: a loop between controls was stopped (Axis 1 → Axis 1)")
    ]


def test_same_thread_chain_is_followed_without_the_event_chain(
    _fresh: list,
) -> None:
    """S94a: an event rebuilt on the way (its chain lost) is still followed
    on one thread: the send under way is continued."""
    sent: list[int] = []

    def send(_path: tuple) -> None:
        sent.append(1)
        logical_loop.guarded(A, "A", send)  # no chain passed

    logical_loop.guarded(A, "A", send)
    assert len(sent) == logical_loop.MAX_HOPS


def test_a_to_b_to_a_stops(_fresh: list, caplog: pytest.LogCaptureFixture) -> None:
    """06 S94: A -> B -> A on one thread stops within 8 hops."""
    notices = _fresh
    sent: list[str] = []

    def send_a(path: tuple) -> None:
        sent.append("A")
        logical_loop.guarded(B, "Button 2", send_b, path)

    def send_b(path: tuple) -> None:
        sent.append("B")
        logical_loop.guarded(A, "Button 1", send_a, path)

    with caplog.at_level(logging.WARNING, logger="user"):
        logical_loop.guarded(A, "Button 1", send_a)
    assert sent == ["A", "B"] * 4
    assert len(notices) == 1
    assert notices[0][1].endswith("(Button 1 → Button 2 → Button 1)")
    assert len(_warnings(caplog)) == 1


def test_a_chain_without_a_loop_is_not_stopped(_fresh: list) -> None:
    notices = _fresh
    sent: list[str] = []
    logical_loop.guarded(
        A, "A", lambda p: logical_loop.guarded(B, "B", lambda _: sent.append("B"), p)
    )
    # New inputs (empty chains) from one thread are new chains, however many.
    for _ in range(50):
        assert logical_loop.guarded(A, "A", lambda _: sent.append("A"))
    assert sent == ["B"] + ["A"] * 50
    assert notices == []


def _on_new_thread(fn: Callable[[], object]) -> None:
    thread = threading.Thread(target=fn)
    thread.start()
    thread.join(timeout=5)


def test_queued_self_loop_stops_whatever_the_speed(
    _fresh: list, caplog: pytest.LogCaptureFixture
) -> None:
    """06 S94a: a macro step re-triggering its own control: each macro run is
    a new thread continuing the chain of the event that started it; the
    time between runs plays no part (no clock is read)."""
    caplog.set_level(logging.WARNING, logger="user")
    results: list[bool] = []
    chain: list[tuple] = [()]

    def macro_run(started_by: tuple) -> None:
        with logical_loop.continuing(started_by):
            results.append(
                logical_loop.guarded(
                    A, "Button 1", lambda path: chain.__setitem__(0, path)
                )
            )

    for _ in range(12):
        _on_new_thread(lambda: macro_run(chain[0]))
    assert results[:8] == [True] * 8
    assert results[8:] == [False] * 4
    # Told from the macro thread: the notice reaches the main thread through
    # its event loop (none here), so the log line and the told flag are checked.
    assert logical_loop._told is True
    assert [r.getMessage() for r in caplog.records if r.name == "user"] == [
        "Logical Device: a loop between controls was stopped "
        "(Button 1 → Button 1) (shown once; it may keep happening)"
    ]


def test_fast_new_inputs_from_new_threads_are_never_a_loop(_fresh: list) -> None:
    """06 S94a: a button pressed 20 times quickly, each press running a macro
    (a new thread) whose step drives B: every press is a new chain."""
    notices = _fresh
    results: list[bool] = []

    def macro_run() -> None:
        with logical_loop.continuing(()):
            results.append(logical_loop.guarded(B, "B", _nothing))

    for _ in range(20):
        _on_new_thread(macro_run)
    assert results == [True] * 20
    assert notices == []


def test_relative_self_loop_stops_by_the_carried_chain(_fresh: list) -> None:
    """06 S94: a Relative writer sends with the chain of the event that drove
    it; its own event drives it again with one more hop each time."""
    notices = _fresh
    carried: list[tuple] = [()]
    results = []
    for _ in range(10):
        results.append(
            logical_loop.guarded(
                A, "Axis 1", lambda p: carried.__setitem__(0, p), carried[0]
            )
        )
    assert results[:8] == [True] * 8 and results[8] is False
    assert len(notices) == 1


def test_a_writer_from_another_control_is_not_a_loop(_fresh: list) -> None:
    """A -> B Relative, A driven from outside: the chain stays A -> B."""
    notices = _fresh
    for _ in range(30):
        from_a: list[tuple] = []
        logical_loop.guarded(A, "A", from_a.append)  # A moved by its stick
        assert logical_loop.guarded(B, "B", _nothing, from_a[0])
    assert notices == []


def test_chain_of_takes_the_longer_of_event_and_thread(_fresh: list) -> None:
    hop = ((A, "A"),)
    assert logical_loop.chain_of(None) == ()
    assert logical_loop.chain_of(hop) == hop
    with logical_loop.continuing(hop * 3):
        assert logical_loop.chain_of(hop) == hop * 3
        assert logical_loop.chain_of(hop * 4) == hop * 4
    assert logical_loop._stack() == []


def test_reported_once_per_run_and_reset_clears(
    _fresh: list, caplog: pytest.LogCaptureFixture
) -> None:
    notices = _fresh

    def loop(path: tuple = ()) -> None:
        logical_loop.guarded(A, "A", loop, path)

    with caplog.at_level(logging.WARNING, logger="user"):
        loop()
        loop()
        full = ((A, "A"),) * logical_loop.MAX_HOPS
        assert logical_loop.guarded(B, "B", _nothing, full) is False
    assert len(notices) == 1  # one notice per Run
    # Run 2: reset (Run start / Stop) and log_once.reset (Run start).
    logical_loop.reset()
    log_once.reset()
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="user"):
        loop()
    assert len(notices) == 2
    assert len(_warnings(caplog)) == 1


def test_never_raises(_fresh: list, monkeypatch: pytest.MonkeyPatch) -> None:
    unhashable = ["not", "hashable"]
    sent: list[int] = []
    assert logical_loop.guarded(unhashable, "X", lambda _: sent.append(1)) is True  # type: ignore[arg-type]

    def broken(*_a: object) -> None:
        raise RuntimeError("signal gone")

    monkeypatch.setattr(logical_loop, "_report", broken)

    def loop(path: tuple = ()) -> None:
        logical_loop.guarded(A, "A", loop, path)

    loop()  # the drop's report fails: still no error
    assert sent == [1]


def test_send_errors_pass_through_and_leave_no_chain(_fresh: list) -> None:
    def bad(_path: tuple) -> None:
        raise ValueError("boom")

    with pytest.raises(ValueError):
        logical_loop.guarded(A, "A", bad)
    assert logical_loop._stack() == []


def test_no_time_window_is_left() -> None:
    """D-06-LOOP-CHAIN: the 0.1 s cross-thread window is gone."""
    assert not hasattr(logical_loop, "QUEUED_WINDOW")
