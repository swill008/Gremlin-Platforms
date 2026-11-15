# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Screen Saver Mode tracing (page 12 S16, page 01 S146): the Trace tab's
Screen Saver Mode row is saved like HidHide's and off by default;
trace.screen_saver writes one SCREEN SAVER line, control "Screen Saver Mode",
only while tracing is on and the row is ticked, and never raises; the row,
its slot and its Points filter are on the Trace tab's model. The click on
the row is in test_trace_tab.py."""

from __future__ import annotations

import pathlib
import threading
from collections.abc import Iterator

import pytest
from PySide6 import QtCore

from gremlin import trace, util


@pytest.fixture(autouse=True)
def _fresh(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(util, "logs_dir", lambda: tmp_path / "logs")
    trace._reset_for_tests()
    trace.set_screen_saver(False)
    yield
    trace.set_screen_saver(False)
    trace._reset_for_tests()


def _ssm_lines() -> list[tuple[str, str, str, str, bool]]:
    return [ln for ln in trace.lines() if ln[2] == trace.SCREEN_SAVER]


def test_the_tick_is_off_by_default_and_saved() -> None:
    from gremlin import config

    assert not trace.screen_saver_ticked()
    trace.set_screen_saver(True)
    assert config.Configuration().value("debug", "trace", "screen-saver-mode") == "on"
    trace._reset_for_tests()  # a fresh start reads it back
    assert trace.screen_saver_ticked()
    assert not trace.screen_saver_on()  # tracing itself always starts off
    trace.set_screen_saver(False)
    assert config.Configuration().value("debug", "trace", "screen-saver-mode") == ""
    trace._reset_for_tests()
    assert not trace.screen_saver_ticked()


def test_writes_only_while_tracing_and_ticked() -> None:
    trace.screen_saver("off and unticked")
    trace.set_screen_saver(True)
    trace.screen_saver("ticked, tracing off")
    assert _ssm_lines() == [] and not trace.screen_saver_on()
    trace.set_screen_saver(False)
    trace.set_enabled(True)
    trace.screen_saver("tracing, unticked")
    assert _ssm_lines() == [] and not trace.screen_saver_on()
    trace.set_screen_saver(True)
    assert trace.screen_saver_on()
    trace.screen_saver("listener started")
    lines = _ssm_lines()
    assert len(lines) == 1
    _, control, point, detail, warning = lines[0]
    assert (control, point, detail, warning) == (
        "Screen Saver Mode", trace.SCREEN_SAVER, "listener started", False
    )
    log = (util.logs_dir() / trace.FILE_NAME).read_text("utf-8")
    assert "Screen Saver Mode  SCREEN SAVER  listener started" in log
    trace.set_enabled(False)
    trace.screen_saver("after off")
    assert len(_ssm_lines()) == 1


def test_never_raises_and_is_thread_safe() -> None:
    trace.set_screen_saver(True)
    trace.set_enabled(True)

    class Bad:
        def __str__(self) -> str:
            raise RuntimeError("no text")

    trace.screen_saver(Bad())  # type: ignore[arg-type]
    workers = [
        threading.Thread(
            target=lambda n=n: [trace.screen_saver(f"t{n} {i}") for i in range(50)]
        )
        for n in range(4)
    ]
    for t in workers:
        t.start()
    for t in workers:
        t.join(5)
    assert len(_ssm_lines()) == 200


def test_the_row_slot_and_points_filter_on_the_trace_tab(
    qapp: QtCore.QCoreApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.ui import trace_model

    monkeypatch.setattr(trace_model, "_devices", lambda: [])  # no device read
    tab = trace_model.TraceView()
    tree = tab._tree  # noqa: SLF001
    kinds = [r["kind"] for r in tree._rows]  # noqa: SLF001
    # Right after HidHide's row.
    assert kinds[kinds.index("hidhide") + 1] == "screen-saver"
    row = next(r for r in tree._rows if r["kind"] == "screen-saver")  # noqa: SLF001
    assert row["text"].startswith("Screen Saver Mode") and row["check"] == 0
    tab.setScreenSaver(True)
    row = next(r for r in tree._rows if r["kind"] == "screen-saver")  # noqa: SLF001
    assert row["check"] == 2 and trace.screen_saver_ticked()
    # The Points filter shows its lines alone.
    trace.set_enabled(True)
    trace.event("Profile Start")
    trace.screen_saver("countdown started: 300 s from Windows")
    tab.refresh()
    assert "Screen Saver Mode" in tab.property("pointNames")
    shown = lambda: [r[2] for r in tab._lines.rows]  # noqa: E731, SLF001
    for name in trace_model.POINTS:
        tab.setPoint(name, name == "Screen Saver Mode")
    assert set(shown()) == {trace.SCREEN_SAVER}
    tab.setScreenSaver(False)
    row = next(r for r in tree._rows if r["kind"] == "screen-saver")  # noqa: SLF001
    assert row["check"] == 0 and not trace.screen_saver_ticked()
