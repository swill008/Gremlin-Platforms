"""Timing probes: input delay per hop, summarised as TIMING lines in trace.log.

Active only while Tracing is on and the Timing row is ticked
(trace.timing_on()). When off, each hop costs one bool check and no
counter call. No per-event lines: one summary line every INTERVAL seconds
while there were events (and at Tracing off), plus one stall line per
episode when the queue wait passes STALL_MS. Everything here never raises
(S151); it is on the input path.

Stamps (counter() values, ns): t0 driver receive, t1 emitted (both carried
as event.t_rx), t2 dispatch start, t3 wiring start, t4 actions done, t5 first
output write.
"""

from __future__ import annotations

import datetime
import logging
import math
import statistics
import threading
import time
from typing import Any

from gremlin import input_thread, threads, trace

INTERVAL = 10.0  # seconds between summary lines
STALL_MS = 50.0  # queue wait above this is a stall
MAX_SAMPLES = 20000  # per hop and interval; beyond it samples are replaced

HOPS = ("driver to emit", "queue wait", "gate to wiring", "actions", "end to end")

on: bool = False
counter = time.perf_counter_ns

_LOCK = threading.Lock()
_local = threading.local()
_samples: dict[str, list[float]] = {}
_counts: dict[str, int] = {}
_max: dict[str, float] = {}
_events = 0
_devices: set[Any] = set()
_stall: dict[str, Any] | None = None
_timer: Any = None
_mark: tuple[int, float, float] | None = None  # perf ns, thread_time, process_time
_main_thread = threading.main_thread()
# Run start/stop work on the input thread: [name, t_start, t_end or None].
# An event queued meanwhile waits for it, which the stall line says.
_phases: list[list[Any]] = []


def _log() -> logging.Logger:
    return logging.getLogger("system")


def _sync() -> None:
    """Follows trace.timing_on(); flushes when it turns off."""
    global on
    try:
        new = bool(trace.timing_on())
    except Exception:
        new = False
    was = on
    on = new
    if was and not new:
        flush()
        _cancel_timer()
    elif new and not was:
        _reset()


def _reset() -> None:
    global _events, _stall, _mark
    with _LOCK:
        _samples.clear()
        _counts.clear()
        _max.clear()
        _devices.clear()
        _events = 0
        _stall = None
        _mark = None
        _phases.clear()


def _record(hop: str, ms: float) -> None:
    lst = _samples.setdefault(hop, [])
    n = _counts.get(hop, 0)
    if len(lst) < MAX_SAMPLES:
        lst.append(ms)
    else:
        lst[n % MAX_SAMPLES] = ms
    _counts[hop] = n + 1
    if ms > _max.get(hop, -1.0):
        _max[hop] = ms


def phase_begin(name: str) -> None:
    """A Run start ("Run start") or stop ("Run stop") begins on the input thread."""
    if not on:
        return
    try:
        _phases.append([name, counter(), None])
        del _phases[:-8]
    except Exception:
        pass


def phase_end() -> None:
    if not on:
        return
    try:
        for ph in reversed(_phases):
            if ph[2] is None:
                ph[2] = counter()
                break
    except Exception:
        pass


def _phase_for(t1: int, t2: int) -> str | None:
    """The Run phase an event queued at t1 and dispatched at t2 waited for."""
    for name, start, end in reversed(_phases):
        if t1 < (t2 if end is None else end) and t2 > start:
            return name
    return None


def stamp_rx(event: object, t0: int, t1: int) -> None:
    try:
        event.t_rx = (t0, t1)  # type: ignore[attr-defined]
    except Exception:
        pass


def dispatch(event: object) -> None:
    """Dispatch start (t2): driver to emit, queue wait, stall episodes."""
    if not on:
        return
    try:
        t2 = counter()
        rx = getattr(event, "t_rx", None)
        _local.cur = [rx, t2, None, False, event]
        if not rx:
            return
        t0, t1 = rx
        wait = (t2 - t1) / 1e6
        with _LOCK:
            _record("driver to emit", (t1 - t0) / 1e6)
            _record("queue wait", wait)
            global _events
            _events += 1
            dev = getattr(event, "device_guid", None)
            if dev is not None:
                _devices.add(dev)
            _stall_step(wait, _phase_for(t1, t2))
        _arm()
    except Exception:
        _log().debug("trace_timing.dispatch failed", exc_info=True)


def _stall_step(wait: float, why: str | None = None) -> None:
    global _stall
    if wait > STALL_MS:
        if _stall is None:
            first = datetime.datetime.now() - datetime.timedelta(milliseconds=wait)
            _stall = {"max": wait, "held": 0, "first": first, "why": None}
        if why and not _stall.get("why"):
            _stall["why"] = why
        _stall["held"] += 1
        _stall["max"] = max(_stall["max"], wait)
    elif _stall is not None:
        _end_stall()


def _end_stall() -> None:
    global _stall
    s, _stall = _stall, None
    if s is None:
        return
    first = s["first"].strftime("%H:%M:%S.") + f"{s['first'].microsecond // 1000:03d}"
    why = f"; waited for {s['why']}" if s.get("why") else ""
    _write(
        f"queue wait {s['max']:,.0f} ms (events held: {s['held']:,}; "
        f"first held at {first}{why})",
        True,
    )


def begin(event: object) -> None:
    """Wiring start (t3): gate to wiring."""
    if not on:
        return
    try:
        cur = getattr(_local, "cur", None)
        t3 = counter()
        if cur is None or (len(cur) > 4 and cur[4] is not event):
            # Not the event dispatch() stamped (virtual, timer, Logical
            # Device, OSC): no t2 of its own, so no gate-to-wiring figure.
            cur = _local.cur = [getattr(event, "t_rx", None), None, None, False, event]
        cur[2] = t3
        if cur[1] is not None:
            with _LOCK:
                _record("gate to wiring", (t3 - cur[1]) / 1e6)
    except Exception:
        _log().debug("trace_timing.begin failed", exc_info=True)


def end() -> None:
    """Actions done (t4): actions."""
    if not on:
        return
    try:
        cur = getattr(_local, "cur", None)
        if cur is None or cur[2] is None:
            return
        t4 = counter()
        with _LOCK:
            _record("actions", (t4 - cur[2]) / 1e6)
        cur[2] = None
    except Exception:
        _log().debug("trace_timing.end failed", exc_info=True)


def output() -> None:
    """First output write (t5): end to end, once per event."""
    if not on:
        return
    try:
        cur = getattr(_local, "cur", None)
        if cur is None or cur[3] or not cur[0]:
            return
        cur[3] = True
        t5 = counter()
        with _LOCK:
            _record("end to end", (t5 - cur[0][0]) / 1e6)
    except Exception:
        _log().debug("trace_timing.output failed", exc_info=True)


def percentile(values: list[float], p: float) -> float:
    """Nearest-rank percentile of a non-empty list."""
    s = sorted(values)
    return s[max(0, math.ceil(p / 100 * len(s)) - 1)]


def _num(v: float) -> str:
    return f"{v:.2f}" if v < 10 else f"{v:.1f}" if v < 100 else f"{v:,.0f}"


def _cpu() -> str:
    global _mark
    now = (counter(), time.thread_time(), time.process_time())
    mark, _mark = _mark, now
    # thread_time is the calling thread's: the thread whose timer this is
    # (the input thread, where dispatch runs, or the main thread).
    if threading.current_thread() is _main_thread:
        which = "main"
    elif input_thread.is_input_thread():
        which = "input"
    else:
        return ""
    if mark is None:
        return ""
    wall = (now[0] - mark[0]) / 1e9
    if wall <= 0:
        return ""
    cpu = 100 * (now[1] - mark[1]) / wall
    proc = 100 * (now[2] - mark[2]) / wall
    return f" · CPU {which} {cpu:.0f} % · process {proc:.0f} %"


def summary() -> str | None:
    """The summary line text for the samples so far (then cleared), or None."""
    global _events
    with _LOCK:
        if _stall is not None:
            _end_stall()
        if not _events:
            # Hops without a counted event are not reported (no stale figures).
            _samples.clear()
            _counts.clear()
            _max.clear()
            _devices.clear()
            return None
        parts = []
        for hop in HOPS:
            v = _samples.get(hop)
            if v:
                parts.append(
                    f"{hop} median {_num(statistics.median(v))} ms "
                    f"p95 {_num(percentile(v, 95))} p99 {_num(percentile(v, 99))} "
                    f"max {_num(_max[hop])}"
                )
        n, d = _events, len(_devices)
        _samples.clear()
        _counts.clear()
        _max.clear()
        _devices.clear()
        _events = 0
    date = datetime.date.today().isoformat()
    return (
        f"{date} {INTERVAL:.0f} s: {n:,} events ({d} devices)"
        + "".join(" · " + p for p in parts)
        + _cpu()
    )


def _write(text: str, warning: bool = False) -> None:
    try:
        trace.timing(text, warning)
    except Exception:
        _log().debug("trace_timing write failed", exc_info=True)


def flush() -> None:
    """Writes the summary now (interval tick, Tracing off, Stop)."""
    try:
        text = summary()
        if text:
            _write(text)
    except Exception:
        _log().debug("trace_timing.flush failed", exc_info=True)


def _tick() -> None:
    global _timer
    _timer = None
    if not on:
        return
    flush()
    _arm()


def _arm() -> None:
    """Starts the interval timer on the calling thread when it has an event
    loop (the input thread, where dispatch runs, or the main thread); never
    a new thread. Not a Run timer: Tracing owns it (it flushes at Stop)."""
    global _timer, _mark
    if _timer is not None or not threads.has_event_loop():
        return
    try:
        _mark = (counter(), time.thread_time(), time.process_time())
        _timer = threads.thread_timer("trace-timing", INTERVAL, _tick)
    except Exception:
        _timer = None


def _cancel_timer() -> None:
    global _timer
    t, _timer = _timer, None
    try:
        if t is not None:
            t.cancel()
    except Exception:
        pass


trace.on_change(_sync)
trace.on_closing(flush)
