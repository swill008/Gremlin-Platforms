"""Timing probes (S179): off costs nothing, exact percentiles, one stall line
per episode, never raises, summary line format."""

import types
from collections.abc import Iterator
from typing import NoReturn

import pytest

from gremlin import trace
from gremlin import trace_timing as tt


@pytest.fixture
def lines(monkeypatch: pytest.MonkeyPatch) -> Iterator[list]:
    out = []
    monkeypatch.setattr(
        tt.trace,
        "timing",
        lambda text, warning=False: out.append((text, warning)),
        raising=False,
    )
    monkeypatch.setattr(tt, "_arm", lambda: None)
    tt._reset()
    yield out
    monkeypatch.setattr(tt, "on", False)
    tt._reset()


def _clock(monkeypatch: pytest.MonkeyPatch, values: list[int]) -> list[int]:
    it = iter(values)
    calls = []

    def counter() -> int:
        calls.append(1)
        return next(it)

    monkeypatch.setattr(tt, "counter", counter)
    return calls


def _ev(t0: int, t1: int) -> types.SimpleNamespace:
    e = types.SimpleNamespace()
    tt.stamp_rx(e, t0, t1)
    return e


def test_off_costs_one_check(monkeypatch: pytest.MonkeyPatch, lines: list) -> None:
    monkeypatch.setattr(tt, "on", False)
    calls = _clock(monkeypatch, [])
    e = _ev(0, 1)
    tt.dispatch(e)
    tt.begin(e)
    tt.end()
    tt.output()
    tt.flush()
    assert not calls and not lines


def test_percentiles_exact() -> None:
    v = [float(i) for i in range(1, 1001)]
    assert tt.percentile(v, 95) == 950
    assert tt.percentile(v, 99) == 990
    assert tt.percentile(v, 100) == 1000


def test_summary_line(monkeypatch: pytest.MonkeyPatch, lines: list) -> None:
    monkeypatch.setattr(tt, "on", True)
    for i in range(1, 1001):
        tt._record("queue wait", float(i))
    tt._events = 1000
    text = tt.summary()
    assert text.startswith("20") and "10 s: 1,000 events (0 devices)" in text
    assert "queue wait median 500 ms p95 950 p99 990 max 1,000" in text
    assert tt.summary() is None  # cleared


def test_stall_once_per_episode(monkeypatch: pytest.MonkeyPatch, lines: list) -> None:
    monkeypatch.setattr(tt, "on", True)
    ms = 1_000_000
    # three held events (waits 200, 150, 100 ms), then a fast one, then a new stall
    waits = [200, 150, 100, 1, 300]
    seq = []
    evs = []
    for w in waits:
        evs.append(_ev(0, 0))
        seq.append(w * ms)
    _clock(monkeypatch, seq)
    for e in evs:
        tt.dispatch(e)
    tt.flush()
    stalls = [t for t, w in lines if w]
    assert len(stalls) == 2
    assert "queue wait 200 ms (events held: 3; first held at " in stalls[0]
    assert "queue wait 300 ms (events held: 1;" in stalls[1]


def test_hops_and_end_to_end(monkeypatch: pytest.MonkeyPatch, lines: list) -> None:
    monkeypatch.setattr(tt, "on", True)
    ms = 1_000_000
    _clock(monkeypatch, [3 * ms, 4 * ms, 6 * ms, 9 * ms])  # t2, t3, t4, t5
    e = _ev(0, 1 * ms)
    tt.dispatch(e)
    tt.begin(e)
    tt.end()
    tt.output()
    tt.output()  # once per event
    assert tt._samples["queue wait"] == [2.0]
    assert tt._samples["gate to wiring"] == [1.0]
    assert tt._samples["actions"] == [2.0]
    assert tt._samples["end to end"] == [9.0]


def test_never_raises(monkeypatch: pytest.MonkeyPatch, lines: list) -> None:
    monkeypatch.setattr(tt, "on", True)

    def boom() -> NoReturn:
        raise RuntimeError("x")

    monkeypatch.setattr(tt, "counter", boom)
    e = _ev(0, 1)
    tt.dispatch(e)
    tt.begin(e)
    tt.end()
    tt.output()
    tt.stamp_rx(object(), 1, 2)  # no attribute assignment possible
    monkeypatch.setattr(tt.trace, "timing", lambda *a, **k: boom())
    tt._events = 1
    tt.flush()


def test_bounded_samples() -> None:
    tt._reset()
    for i in range(tt.MAX_SAMPLES * 2):
        tt._record("actions", float(i))
    assert len(tt._samples["actions"]) == tt.MAX_SAMPLES
    assert tt._max["actions"] == tt.MAX_SAMPLES * 2 - 1
    tt._reset()


def test_hooked_to_trace() -> None:
    assert tt._sync in trace._hooks


def test_flush_runs_before_tracing_goes_off() -> None:
    assert tt.flush in trace._closing_hooks


def test_final_partial_line_written_at_tracing_off(
    monkeypatch: pytest.MonkeyPatch, lines: list
) -> None:
    monkeypatch.setattr(tt, "on", True)
    tt._record("actions", 1.0)
    tt._events = 1
    for hook in list(trace._closing_hooks):
        hook()
    assert any("10 s: 1 events" in t for t, _ in lines)


def test_undispatched_event_records_no_stale_gate_to_wiring(
    monkeypatch: pytest.MonkeyPatch, lines: list
) -> None:
    monkeypatch.setattr(tt, "on", True)
    ms = 1_000_000
    _clock(monkeypatch, [3 * ms, 4 * ms, 6 * ms, 30_000 * ms, 30_001 * ms])
    e = _ev(0, 1 * ms)
    tt.dispatch(e)
    tt.begin(e)
    tt.end()
    other = types.SimpleNamespace()  # virtual/timer event: never dispatched
    tt.begin(other)
    tt.end()
    assert tt._samples["gate to wiring"] == [1.0]  # only the dispatched one
    assert tt._samples["actions"] == [2.0, 1.0]


def test_summary_with_no_counted_events_reports_no_hops(
    monkeypatch: pytest.MonkeyPatch, lines: list
) -> None:
    monkeypatch.setattr(tt, "on", True)
    _clock(monkeypatch, [10, 20])
    other = types.SimpleNamespace()
    tt.begin(other)
    tt.end()
    assert tt.summary() is None
    assert not tt._samples


def test_stall_during_run_start_says_so(
    monkeypatch: pytest.MonkeyPatch, lines: list
) -> None:
    monkeypatch.setattr(tt, "on", True)
    ms = 1_000_000
    # Run start from 10 ms to 400 ms; the event queued at 20 ms, dispatched at 420
    _clock(monkeypatch, [10 * ms, 400 * ms, 420 * ms])
    tt.phase_begin("Run start")
    tt.phase_end()
    e = _ev(0, 20 * ms)
    tt.dispatch(e)
    tt.flush()
    stalls = [t for t, w in lines if w]
    assert stalls[0].endswith("; waited for Run start)")


def test_stall_without_a_run_phase_has_no_label(
    monkeypatch: pytest.MonkeyPatch, lines: list
) -> None:
    monkeypatch.setattr(tt, "on", True)
    ms = 1_000_000
    _clock(monkeypatch, [10 * ms, 20 * ms, 420 * ms])
    tt.phase_begin("Run stop")
    tt.phase_end()  # over before the event was queued
    tt.dispatch(_ev(0, 100 * ms))
    tt.flush()
    stalls = [t for t, w in lines if w]
    assert "waited for" not in stalls[0]
