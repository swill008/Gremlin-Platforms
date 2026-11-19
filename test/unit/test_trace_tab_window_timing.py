# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Trace tab's Window and Timing rows (01 S146, S149, S176, S179): the
Window row sits with HidHide and Screen Saver Mode, the Timing row after the
OSC rows; their ticks are saved through trace.set_window / set_timing; the
Points filter lists WINDOW and TIMING beside Screen Saver Mode."""

from __future__ import annotations

import pathlib
from collections.abc import Iterator

import pytest
from PySide6 import QtCore

from gremlin import trace, util


@pytest.fixture(autouse=True)
def _fresh(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(util, "logs_dir", lambda: tmp_path / "logs")
    trace._reset_for_tests()
    yield
    trace.set_window(False)
    trace.set_timing(False)
    trace._reset_for_tests()


def _tab(monkeypatch: pytest.MonkeyPatch):  # noqa: ANN202
    from gremlin.ui import trace_model

    monkeypatch.setattr(trace_model, "_devices", lambda: [])
    return trace_model.TraceView()


def _row(tab, kind: str) -> dict:  # noqa: ANN001
    return next(r for r in tab._tree._rows if r["kind"] == kind)  # noqa: SLF001


def test_rows_are_where_the_spec_puts_them(
    qapp: QtCore.QCoreApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    tab = _tab(monkeypatch)
    kinds = [r["kind"] for r in tab._tree._rows]  # noqa: SLF001
    assert kinds.index("hidhide") < kinds.index("window") < kinds.index("osc")
    assert "screen-saver" in kinds
    # Timing is after the last OSC area row.
    last_area = max(i for i, k in enumerate(kinds) if k == "osc-area")
    assert kinds.index("timing") > last_area
    assert _row(tab, "window")["text"].startswith("Window")
    assert _row(tab, "timing")["text"].startswith("Timing")


def test_ticks_call_trace_and_are_saved(
    qapp: QtCore.QCoreApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin import config

    tab = _tab(monkeypatch)
    assert _row(tab, "window")["check"] == 0 and _row(tab, "timing")["check"] == 0
    tab.setWindow(True)
    tab.setTiming(True)
    assert trace.window_ticked() and trace.timing_ticked()
    assert _row(tab, "window")["check"] == 2 and _row(tab, "timing")["check"] == 2
    cfg = config.Configuration()
    assert cfg.value("debug", "trace", "window") == "on"
    assert cfg.value("debug", "trace", "timing") == "on"
    tab.setWindow(False)
    tab.setTiming(False)
    assert not trace.window_ticked() and not trace.timing_ticked()
    assert _row(tab, "window")["check"] == 0 and _row(tab, "timing")["check"] == 0


def test_points_filter_lists_window_and_timing(
    qapp: QtCore.QCoreApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.ui import trace_model

    tab = _tab(monkeypatch)
    names = tab.property("pointNames")
    assert "Window" in names and "Timing" in names and "Screen Saver Mode" in names
    assert trace_model.POINTS["Window"] == (trace.WINDOW,)
    assert trace_model.POINTS["Timing"] == (trace.TIMING,)
    trace.set_enabled(True)
    trace.event("Profile Start")
    trace.set_window(True)
    trace.window("Main window", "hidden")
    tab.refresh()
    for name in trace_model.POINTS:
        tab.setPoint(name, name == "Window")
    assert {r[2] for r in tab._lines.rows} == {trace.WINDOW}  # noqa: SLF001
