# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""OSC tracing core (gremlin/trace.py, D-09-OSC-TRACE; 01 S146 S148 S149):
area ticks saved, nothing written while off or unticked, per-key rate limit
with "(N messages between)" and the timer flush, the 10-then-quiet repeat
rule for errors only (D-09-OSC-TRACE-ERRORS), osc_reset (also at tracing
on), log_limited bounded, never raises."""

from __future__ import annotations

import json
import logging
import pathlib
from collections.abc import Iterator
from types import SimpleNamespace

import pytest

from gremlin import clock, config, trace, util


@pytest.fixture(autouse=True)
def _fresh(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(util, "logs_dir", lambda: tmp_path / "logs")
    trace._reset_for_tests()
    trace.set_osc_all(False)  # saved ticks from an earlier test don't count
    yield
    trace.set_osc_all(False)
    trace._reset_for_tests()


def _osc_lines() -> list[tuple[str, str, str, str, bool]]:
    return [line for line in trace.lines() if line[1].startswith("OSC ")]


def test_off_writes_nothing_and_opens_no_file(tmp_path: pathlib.Path) -> None:
    trace.set_osc_all(True)
    assert not trace.osc_on("receive")
    trace.osc("receive", "in 127.0.0.1:9000 /a ,f 0.5", rate=True, key="/a")
    trace.osc("output", "BLOCKED send refused", blocked=True, key="t", warning=True)
    assert trace.lines() == []
    assert trace.notice() == ""
    assert not (tmp_path / "logs" / "trace.log").exists()


def test_off_is_cheap_no_config_read(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom() -> None:
        raise AssertionError("config read while tracing is off")

    with monkeypatch.context() as m:
        m.setattr(trace, "_load", boom)
        for _ in range(1000):
            trace.osc("receive", "x", rate=True, key="/a")
        assert not trace.osc_on("receive")


def test_area_ticks_choose_lines_and_are_saved(tmp_path: pathlib.Path) -> None:
    trace.set_osc("receive", True)
    trace.set_osc("bogus", True)  # ignored
    assert trace.osc_ticked() == ["receive"]
    trace.set_enabled(True)
    assert trace.osc_on("receive") and not trace.osc_on("output")
    trace.osc("receive", "in 127.0.0.1:9000 /a ,f 0.5")
    trace.osc("output", "out t 127.0.0.1:9001 /b ,f 1.0")
    lines = _osc_lines()
    assert [(ln[1], ln[2], ln[3]) for ln in lines] == [
        ("OSC Receive", trace.OSC, "in 127.0.0.1:9000 /a ,f 0.5")
    ]
    assert "OSC Receive  OSC  in 127.0.0.1:9000" in (
        tmp_path / "logs" / "trace.log"
    ).read_text(encoding="utf-8")
    saved = json.loads(config.Configuration().value("debug", "trace", "osc"))
    assert saved == ["receive"]
    trace.set_osc_all(True)
    assert trace.osc_ticked() == list(trace.OSC_AREAS)
    trace.set_enabled(False)
    trace._reset_for_tests()  # a fresh start reads them back
    assert trace.osc_ticked() == list(trace.OSC_AREAS)
    trace.set_osc_all(False)
    assert trace.osc_ticked() == []


def test_blocked_and_warning(tmp_path: pathlib.Path) -> None:
    trace.set_osc_all(True)
    trace.set_enabled(True)
    trace.osc("setup", "row 3 unreadable: bad port (kept in the file)", warning=True)
    trace.osc("output", "send refused: OSC output is Off", blocked=True)
    lines = _osc_lines()
    assert lines[0][1] == "OSC Setup and files" and lines[0][4] is True
    assert "row 3 unreadable" in trace.notice()
    assert lines[1][2] == trace.BLOCKED and lines[1][4] is False


def test_rate_limit_counts_between_and_flush(monkeypatch: pytest.MonkeyPatch) -> None:
    now = [1000.0]
    monkeypatch.setattr(clock, "monotonic", lambda: now[0])
    monkeypatch.setattr(trace, "_schedule_flush", lambda: None)
    trace.set_osc("receive", True)
    trace.set_enabled(True)
    gap = 1.0 / trace.axis_rate()
    for i in range(6):  # six messages inside one interval
        trace.osc("receive", f"in /a ,f {i}", rate=True, key="/a")
        now[0] += gap / 10
    trace.osc("receive", "in /b ,f 9", rate=True, key="/b")  # another key: own limit
    details = [ln[3] for ln in _osc_lines()]
    assert details == ["in /a ,f 0", "in /b ,f 9"]
    # The next message after the interval says how many were skipped.
    now[0] += gap
    trace.osc("receive", "in /a ,f 7", rate=True, key="/a")
    assert _osc_lines()[-1][3] == "in /a ,f 7  (5 messages between)"
    # Messages then stop: the timer writes the latest held one.
    now[0] += gap / 10
    trace.osc("receive", "in /a ,f 8", rate=True, key="/a")
    now[0] += gap / 10
    trace.osc("receive", "in /a ,f 9", rate=True, key="/a")
    now[0] += gap
    trace._on_flush()
    assert _osc_lines()[-1][3] == "in /a ,f 9  (1 message between)"
    assert not trace._osc_pending


def test_repeat_rule_errors_ten_then_one_note_until_reset() -> None:
    # D-09-OSC-TRACE-ERRORS: the cap is for errors (warning=True) only.
    trace.set_osc_all(True)
    trace.set_enabled(True)
    for _ in range(25):
        trace.osc(
            "receive", "malformed packet from 10.0.0.5 (bad)",
            blocked=True, warning=True, key="10.0.0.5",
        )
    lines = _osc_lines()
    assert len(lines) == trace.REPEAT_LIMIT + 1
    assert all(ln[2] == trace.BLOCKED for ln in lines)
    assert lines[-1][3].endswith(trace.OSC_REPEAT_NOTE)
    assert sum(trace.OSC_REPEAT_NOTE in ln[3] for ln in lines) == 1
    # Another key (or reason) has its own count.
    trace.osc("receive", "malformed packet from 10.0.0.6 (bad)",
              blocked=True, warning=True, key="10.0.0.6")
    assert len(_osc_lines()) == trace.REPEAT_LIMIT + 2
    # Run start resets the counts.
    trace.osc_reset()
    trace.osc("receive", "malformed packet from 10.0.0.5 (bad)",
              blocked=True, warning=True, key="10.0.0.5")
    assert len(_osc_lines()) == trace.REPEAT_LIMIT + 3


def test_blocked_lines_never_capped_only_rate_limited(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # D-09-OSC-TRACE-ERRORS: an expected refusal is never capped; per key it
    # goes at the Axis lines rate with "(N messages between)".
    now = [1000.0]
    monkeypatch.setattr(clock, "monotonic", lambda: now[0])
    monkeypatch.setattr(trace, "_schedule_flush", lambda: None)
    trace.set_osc_all(True)
    trace.set_enabled(True)
    gap = 1.0 / trace.axis_rate()
    text = "sender 10.0.0.5 not on Allowed senders"
    for _ in range(15):  # spaced: every one is written
        trace.osc("receive", text, blocked=True, key="10.0.0.5")
        now[0] += gap
    lines = _osc_lines()
    assert len(lines) == 15
    assert all(ln[2] == trace.BLOCKED and ln[3] == text for ln in lines)
    assert not any(trace.OSC_REPEAT_NOTE in ln[3] for ln in lines)
    assert not trace._osc_repeat
    # Inside one interval: counted, the next line says how many.
    for _ in range(4):
        trace.osc("receive", text, blocked=True, key="10.0.0.5")
        now[0] += gap / 10
    now[0] += gap
    trace.osc("receive", text, blocked=True, key="10.0.0.5")
    assert _osc_lines()[-1][3] == f"{text}  (3 messages between)"
    assert _osc_lines()[-1][2] == trace.BLOCKED
    # A blocked line and a rate line with the same key don't share a limit.
    trace.osc("receive", "in /a ,f 1", rate=True, key="10.0.0.5")
    assert _osc_lines()[-1][3] == "in /a ,f 1"


def test_tracing_on_resets_counts() -> None:
    trace.set_osc_all(True)
    trace.set_enabled(True)
    for _ in range(12):
        trace.osc("output", "send error t 127.0.0.1:9: boom",
                  warning=True, key="x")
    trace.log_limited("system", "x", logging.ERROR, "send failed")
    assert trace._osc_repeat and trace._log_counts
    trace.set_enabled(False)
    trace.set_enabled(True)
    assert not trace._osc_repeat and not trace._log_counts


def test_log_limited_bound(caplog: pytest.LogCaptureFixture) -> None:
    # Works whether tracing is on or off.
    with caplog.at_level(logging.WARNING, logger="system"):
        for i in range(30):
            trace.log_limited("system", "target t", logging.ERROR, f"send failed {i}")
        trace.log_limited("system", "target u", logging.ERROR, "other")
    texts = [r.getMessage() for r in caplog.records if r.name == "system"]
    assert len(texts) == trace.REPEAT_LIMIT + 2
    assert texts[trace.REPEAT_LIMIT].endswith(trace.LOG_REPEAT_NOTE)
    assert texts[-1] == "other"
    trace.osc_reset()
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="system"):
        trace.log_limited("system", "target t", logging.ERROR, "again")
    assert [r.getMessage() for r in caplog.records] == ["again"]


def test_never_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    trace.set_osc_all(True)
    trace.set_enabled(True)

    def broken(*_a: object, **_k: object) -> None:
        raise RuntimeError("disk gone")

    with monkeypatch.context() as m:
        m.setattr(trace, "_add", broken)
        trace.osc("receive", "x")
        trace.osc("receive", "x", rate=True, key="/a")
        trace.osc("receive", "x", blocked=True, key="k", warning=True)
        trace.osc("unknown-area", object())  # type: ignore[arg-type]
    with monkeypatch.context() as m:
        m.setattr(trace, "logging", SimpleNamespace(getLogger=broken))
        trace.log_limited("system", "k", logging.ERROR, "x")
