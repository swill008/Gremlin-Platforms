# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Screen Saver Mode step lines reach the recent-events ring with Tracing
off (page 12 S16, page 01 S177), while per-press lines ("press:" and
"not counted:") stay out of the ring and are only traced. Drives the real
_trace and _drain_events paths with a fake WindowsApi (device names only)."""

from __future__ import annotations

import pathlib
from collections.abc import Iterator

import pytest

from gremlin import screen_saver_mode as ssm
from gremlin import trace, util


class _NamesApi(ssm.WindowsApi):
    def __init__(self) -> None:
        self.names: dict[int, str] = {7: "Keyboard"}

    def device_name(self, handle: int) -> str:
        return self.names.get(handle, "")


@pytest.fixture(autouse=True)
def _fresh(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(util, "logs_dir", lambda: tmp_path / "logs")
    trace._reset_for_tests()
    trace.set_screen_saver(False)
    yield
    trace.set_screen_saver(False)
    trace._reset_for_tests()


def _mode() -> ssm.ScreenSaverMode:
    return ssm.ScreenSaverMode(api=_NamesApi(), clock_=ssm.InputClock())


def _in_ring(text: str) -> bool:
    return any(text in line for line in trace.recent_lines())


def test_step_line_reaches_the_ring_with_tracing_off() -> None:
    assert not trace.screen_saver_on()
    ssm._trace("listener started")
    assert _in_ring("Screen Saver Mode  listener started")
    assert not any(ln[2] == trace.SCREEN_SAVER for ln in trace.lines())


def test_resend_step_from_the_listener_reaches_the_ring() -> None:
    mode = _mode()
    mode._events.append(("resend", 2, "", 0.0))  # noqa: SLF001
    mode._drain_events()  # noqa: SLF001
    assert _in_ring("keep off: Windows turned the displays back on")


def test_press_line_stays_out_of_the_ring_and_is_traced_when_on() -> None:
    mode = _mode()
    mode._events.append(("press", 7, "keyboard\tPHYS-1", 0.0))  # noqa: SLF001
    mode._drain_events()  # noqa: SLF001
    assert not _in_ring("press:")  # tracing off: not in the ring either

    trace.set_enabled(True)
    trace.set_screen_saver(True)
    mode._events.append(("press", 7, "keyboard\tPHYS-1", 0.0))  # noqa: SLF001
    mode._events.append(("not_counted", 7, "keyboard\tPHYS-1", 0.0))  # noqa: SLF001
    mode._drain_events()  # noqa: SLF001
    details = [ln[3] for ln in trace.lines() if ln[2] == trace.SCREEN_SAVER]
    assert "press: Keyboard (keyboard)" in details
    assert "not counted: Keyboard (keyboard) is not ticked" in details
    assert not _in_ring("press:")
    assert not _in_ring("not counted:")
