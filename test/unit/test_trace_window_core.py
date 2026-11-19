# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Window and Timing ticks, the recent-lines ring and the Screen Saver Mode
ring flag (page 01 S176, S177, S179, S146/S148/S149)."""

from __future__ import annotations

import pathlib
import threading
from collections.abc import Iterator

import pytest

from gremlin import trace, util


@pytest.fixture(autouse=True)
def _fresh(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(util, "logs_dir", lambda: tmp_path / "logs")
    trace._reset_for_tests()
    trace.set_window(False)
    trace.set_timing(False)
    trace.set_screen_saver(False)
    yield
    trace.set_window(False)
    trace.set_timing(False)
    trace._reset_for_tests()


def _of(point: str) -> list[tuple[str, str, str, str, bool]]:
    return [ln for ln in trace.lines() if ln[2] == point]


def test_points_exist() -> None:
    assert trace.WINDOW == "WINDOW" and trace.TIMING == "TIMING"
    assert trace.RECENT_MAX == 200


@pytest.mark.parametrize("name", ["window", "timing"])
def test_ticks_are_saved_and_gate_lines(name: str) -> None:
    from gremlin import config

    ticked = getattr(trace, f"{name}_ticked")
    on = getattr(trace, f"{name}_on")
    setter = getattr(trace, f"set_{name}")
    write = getattr(trace, name)
    point = name.upper()
    args = ("Main window", "x") if name == "window" else ("x",)

    assert not ticked()
    write(*args)
    setter(True)
    assert config.Configuration().value("debug", "trace", name) == "on"
    write(*args)  # ticked, tracing off
    assert _of(point) == [] and not on()
    trace.set_enabled(True)
    assert on()
    write(*args)
    assert len(_of(point)) == 1
    setter(False)
    write(*args)
    assert len(_of(point)) == 1 and ticked() is False
    setter(True)
    trace._reset_for_tests()
    assert ticked()


def test_window_line_has_control_and_timing_warning() -> None:
    trace.set_window(True)
    trace.set_timing(True)
    trace.set_enabled(True)
    trace.window("Library", "loaded")
    trace.timing("slow", warning=True)
    assert _of("WINDOW")[0][1:4] == ("Library", "WINDOW", "loaded")
    assert _of("TIMING")[0][3] == "slow" and _of("TIMING")[0][4] is True


def test_tick_changes_run_hooks() -> None:
    calls: list[int] = []
    trace.on_change(lambda: calls.append(1))
    trace.set_window(True)
    trace.set_timing(True)
    assert len(calls) >= 2


def test_recent_keeps_200_with_tracing_off_and_writes_no_file() -> None:
    assert not trace.enabled()
    for i in range(250):
        trace.recent("Main window", f"line {i}")
    got = trace.recent_lines()
    assert len(got) == 200
    assert got[-1].endswith("Main window  line 249")
    assert got[0].endswith("line 50")
    assert trace.lines() == []
    assert not trace.file_path().exists()


def test_recent_from_threads_never_raises() -> None:
    def work() -> None:
        for i in range(100):
            trace.recent("t", str(i))
            trace.recent_lines()

    ts = [threading.Thread(target=work) for _ in range(4)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(5)
    assert len(trace.recent_lines()) == 200
    trace.recent(None, None)  # type: ignore[arg-type]


def test_screen_saver_ring_flag() -> None:
    trace.screen_saver("kept")  # default ring=True, tracing off
    trace.screen_saver("not kept", ring=False)
    got = trace.recent_lines()
    assert len(got) == 1 and got[0].endswith("Screen Saver Mode  kept")
    assert _of("SCREEN SAVER") == []
    trace.set_screen_saver(True)
    trace.set_enabled(True)
    trace.screen_saver("both")
    assert len(_of("SCREEN SAVER")) == 1
    assert trace.recent_lines()[-1].endswith("both")


def test_closing_hook_can_write_the_last_timing_line() -> None:
    trace.set_timing(True)
    trace.set_enabled(True)
    trace.on_closing(lambda: trace.timing("last summary"))
    trace.set_enabled(False)
    assert [ln[3] for ln in _of("TIMING")] == ["last summary"]
    assert not trace.enabled()
