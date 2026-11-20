# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""tools/latency_report.py: fixtures -> expected tables, stall correlation,
--legacy pairing, --compare, and the command line. Pure text, no Qt."""

# ruff: noqa: E501
from __future__ import annotations

import datetime as dt
import importlib.util
import sys
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parents[2] / "tools" / "latency_report.py"
_spec = importlib.util.spec_from_file_location("latency_report", _PATH)
lr = importlib.util.module_from_spec(_spec)
sys.modules["latency_report"] = lr
_spec.loader.exec_module(lr)

TRACE = """\
10:00:00.000  -  EVENT  Tracing on
10:00:10.000  Timing  TIMING  2026-11-19 10 s: 100 events (2 devices) · queue wait median 0.10 ms p95 0.50 p99 1.0 max 2.0 · end to end median 0.20 ms p95 0.60 p99 1.2 max 4.0 · CPU main 7 % · process 11 %
10:00:15.500  Timing  TIMING  queue wait 2,340 ms (events held: 1,204; first held at 10:00:12.000)
10:00:20.000  Timing  TIMING  2026-11-19 10 s: 300 events (2 devices) · queue wait median 0.30 ms p95 1.50 p99 3.0 max 9.0 · end to end median 0.40 ms p95 1.00 p99 2.0 max 5.0
10:00:30.000  -  EVENT  Tracing off
11:00:00.000  -  EVENT  Tracing on
11:00:10.000  Timing  TIMING  2026-11-19 10 s: 50 events (1 devices) · queue wait median 1.00 ms p95 2.00 p99 3.0 max 4.0
"""

SYSTEM = """\
2026-11-19 10:00:14       INFO Something else
2026-11-19 10:00:17    WARNING Not responding for 5 s. Where every thread is:
2026-11-19 10:00:20    WARNING Responding again after 8 s
2026-11-19 11:30:00    WARNING Not responding for 6 s. Where every thread is:
"""

LEGACY = """\
12:00:00.100  Dev  Button 1  RAW  pressed
12:00:00.102  Dev  Button 1  WIRING  claimed
12:00:00.105  Dev  Button 1  OUTPUT  vJoy 1 button 1 = on
12:00:01.000  Dev  Button 2  RAW  pressed
12:00:05.000  Dev  Button 2  WIRING  claimed
12:00:05.001  Dev  Button 2  OUTPUT  vJoy 1 button 2 = on
"""


def test_sessions_split_and_aggregate() -> None:
    ses = lr.parse_trace(TRACE.splitlines())
    assert len(ses) == 2
    assert ses[0].date == dt.date(2026, 11, 19)
    assert ses[0].events == 400 and ses[0].intervals == 2
    n, med, p95, p99, mx = lr.aggregate([ses[0]])["queue wait"]
    assert n == 400
    assert abs(med - (100 * 0.10 + 300 * 0.30) / 400) < 1e-9
    assert abs(p95 - (100 * 0.5 + 300 * 1.5) / 400) < 1e-9
    assert mx == 9.0
    assert "gate to wiring" not in lr.aggregate([ses[0]])


def test_report_tables_and_stall_correlation() -> None:
    ses = lr.parse_trace(TRACE.splitlines())
    text = lr.report(ses, lr.parse_system(SYSTEM.splitlines()))
    assert "Session 1: 2026-11-19 10:00:00.000 - 10:00:30.000" in text
    assert "queue wait" in text and "end to end" in text
    assert "400" in text
    # the 2,340 ms stall at 10:00:12 sits inside the watchdog stall 10:00:12-10:00:20
    line = next(ln for ln in text.splitlines() if "2,340 ms" in ln)
    assert "held 1,204" in line and "<- watchdog 2026-11-19 10:00:12 for 8 s" in line
    # the 11:30 watchdog stall (never recovered) is outside both sessions
    assert "11:30:00" not in text


def test_stall_without_watchdog_has_no_marker() -> None:
    ses = lr.parse_trace(TRACE.splitlines())
    text = lr.report(ses, [])
    line = next(ln for ln in text.splitlines() if "2,340 ms" in ln)
    assert "watchdog" not in line


def test_watchdog_event_lines_in_trace_count() -> None:
    trace = TRACE.replace(
        "10:00:30.000  -  EVENT  Tracing off",
        "10:00:21.000  -  EVENT  Not responding for 5 s. Where every thread is:\n"
        "10:00:25.000  -  EVENT  Responding again after 9 s\n"
        "10:00:30.000  -  EVENT  Tracing off",
    )
    ses = lr.parse_trace(trace.splitlines())
    assert [(w.length, w.source) for w in ses[0].watch] == [(9.0, "trace")]
    assert "[trace]" in lr.report(ses, [])


def test_never_recovered_watchdog_text() -> None:
    w = lr.parse_system(
        ["2026-11-16 02:59:25    WARNING Not responding for 7 s. Where"]
    )
    assert w[0].length is None
    assert "never recovered" in lr._wtext(w[0])
    assert w[0].start == dt.datetime(2026, 11, 16, 2, 59, 18)


def test_midnight_rollover_stays_one_session() -> None:
    lines = [
        "23:59:55.000  Timing  TIMING  2026-11-19 10 s: 10 events (1 devices) · queue wait median 1 ms p95 1 p99 1 max 1",
        "00:00:05.000  Timing  TIMING  queue wait 100 ms (events held: 3; first held at 00:00:04.900)",
    ]
    ses = lr.parse_trace(lines)
    assert len(ses) == 1
    assert ses[0].stalls[0][0] == dt.datetime(2026, 11, 20, 0, 0, 4, 900000)


def test_legacy_pairs_at_ms_resolution() -> None:
    text = lr.legacy(LEGACY.splitlines())
    lines = {
        ln.split()[0] + " " + ln.split()[1] + " " + ln.split()[2]: ln
        for ln in text.splitlines()
    }
    raw = next(ln for ln in text.splitlines() if ln.startswith("RAW to WIRING"))
    out = next(ln for ln in text.splitlines() if ln.startswith("WIRING to OUTPUT"))
    assert (
        "Button" in raw and raw.split()[-5] == "1"
    )  # one pair; the 4 s one is dropped
    assert raw.split()[-4] == "2.00"  # median 2 ms
    assert out.split()[-5] == "2"  # both WIRING -> OUTPUT pairs
    assert lines


def test_legacy_empty() -> None:
    assert "No RAW" in lr.legacy(["garbage"])


def test_compare_side_by_side() -> None:
    after = TRACE.replace("median 0.10 ms", "median 0.05 ms")
    text = lr.compare(
        lr.parse_trace(TRACE.splitlines()), lr.parse_trace(after.splitlines())
    )
    assert "before" in text and "after" in text and "-0.0" in text
    assert "TIMING stalls: before 1, after 1" in text


def test_main_cli_reads_rotated_file_and_system(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "trace.log.1").write_text(TRACE.split("11:00")[0], encoding="utf-8")
    (tmp_path / "trace.log").write_text(
        "11:00:00.000  -  EVENT  Tracing on\n"
        "11:00:10.000  Timing  TIMING  2026-11-19 10 s: 50 events (1 devices) · queue wait median 1.00 ms p95 2.00 p99 3.00 max 4.0\n",
        encoding="utf-8",
    )
    (tmp_path / "system.log").write_text(SYSTEM, encoding="utf-8")
    assert lr.main([str(tmp_path / "trace.log")]) == 0
    out = capsys.readouterr().out
    assert "Session 1" in out and "Session 2" in out
    assert "<- watchdog" in out
    assert lr.main([str(tmp_path / "missing.log")]) == 2


def test_new_split_hops_are_parsed_and_old_queue_wait_still_read() -> None:
    line = (
        "10:00:10.000  Timing  TIMING  2026-11-20 10 s: 6 events (1 devices) "
        "· waited behind earlier events median 19.0 ms p95 30.0 p99 40.0 max 49.0 "
        "· hand-over median 0.20 ms p95 0.50 p99 1.0 max 2.0"
    )
    ses = lr.parse_trace([line])
    agg = lr.aggregate(ses)
    assert agg["waited behind earlier events"][1] == 19.0
    assert agg["hand-over"][4] == 2.0
    assert "queue wait" not in agg
    text = lr.report(ses, [])
    assert "waited behind earlier events" in text and "hand-over" in text
