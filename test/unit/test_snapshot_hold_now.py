# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The hold in effect now in the Screen Saver Mode state snapshot (01 S185,
D-01-SNAPSHOT-HOLD): the real core's tick begins and ends a hold, the
model's snapshot_lines show it, and the trace is asked to rewrite the
section only when the hold changes. Fake WindowsApi and input clock (from
test_ssm_core); nothing calls Windows."""

from __future__ import annotations

import pathlib
import sys
from collections.abc import Callable
from typing import Any

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import test_ssm_core as core_t  # noqa: E402

from gremlin import clock, threads, trace  # noqa: E402
from gremlin import screen_saver_mode as ssm  # noqa: E402


@pytest.fixture
def held(monkeypatch: pytest.MonkeyPatch) -> tuple[Any, Any, Callable, list[str]]:
    now = [1000.0]
    monkeypatch.setattr(clock, "monotonic", lambda: now[0])

    class _T:
        def cancel(self) -> None:
            pass

    monkeypatch.setattr(threads, "main_timer", lambda *a, **k: _T())
    api = core_t.FakeApi()
    mode = ssm.ScreenSaverMode(api=api, clock_=core_t.FakeClock())
    monkeypatch.setattr(ssm, "_manager", mode)
    changed: list[str] = []
    monkeypatch.setattr(trace, "snapshot_changed", changed.append, raising=False)

    def run(seconds: int) -> None:
        for _ in range(seconds):
            now[0] += 1.0
            mode.tick()

    return mode, api, run, changed


def _hold_line() -> str:
    from gremlin.ui import screen_saver_mode_model as m

    lines = m.snapshot_lines()
    at = next(i for i, t in enumerate(lines) if t.startswith("Hold during full-screen"))
    return lines[at + 1]


def test_hold_now_follows_the_tick_and_asks_for_a_rewrite(held: tuple) -> None:
    mode, api, run, changed = held
    mode.apply(core_t._on())
    run(2)
    assert _hold_line() == "Hold now: none"
    changed.clear()
    run(1)
    assert changed == []  # no change, no rewrite

    api.busy = True
    api.foreground = "x.exe"
    run(1)
    assert _hold_line() == "Hold now: fullscreen (x.exe)"
    assert changed == [ssm.SNAPSHOT_SECTION]
    run(2)
    assert changed == [ssm.SNAPSHOT_SECTION]

    api.foreground = "y.exe"
    run(1)
    assert _hold_line() == "Hold now: fullscreen (y.exe)"
    assert len(changed) == 2

    api.busy = False
    run(1)
    assert _hold_line() == "Hold now: none"
    assert len(changed) == 3

    api.display_flag = True
    run(1)
    assert _hold_line() == "Hold now: display_request"
    assert len(changed) == 4


def test_switching_off_clears_the_hold_and_rewrites(held: tuple) -> None:
    mode, api, run, changed = held
    mode.apply(core_t._on())
    api.busy = True
    api.foreground = "x.exe"
    run(2)
    changed.clear()
    mode.apply(ssm.Settings(enabled=False))
    assert ssm.hold_now() == ("", "")
    assert _hold_line() == "Hold now: none"
    assert changed == [ssm.SNAPSHOT_SECTION]


def test_section_name_matches_the_model() -> None:
    from gremlin.ui import screen_saver_mode_model as m

    assert ssm.SNAPSHOT_SECTION == m.SNAPSHOT_SECTION
