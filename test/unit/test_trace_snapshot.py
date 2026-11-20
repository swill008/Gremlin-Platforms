# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The trace's state snapshot (01 S146-S150): provider lines written when
tracing turns on, at start and when a section changes; a failing provider;
the text for Save Diagnostics; Keep tracing on."""

from __future__ import annotations

import pathlib
from collections.abc import Iterator

import pytest

from gremlin import config, trace, util


@pytest.fixture(autouse=True)
def _fresh(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(util, "logs_dir", lambda: tmp_path / "logs")
    saved = dict(trace._providers)
    trace._providers.clear()
    trace._reset_for_tests()
    yield
    trace.set_keep_on(False)
    trace._reset_for_tests()
    trace._providers.clear()
    trace._providers.update(saved)


def _state() -> list[str]:
    return [
        f"{line[2]}|{line[3]}" for line in trace.lines() if line[1] == trace.STATE
    ]


def test_lines_written_when_tracing_turns_on() -> None:
    trace.register_snapshot("Demo", lambda: ["Demo: a", "Demo: b"])
    trace.set_enabled(True)
    assert _state() == [
        "EVENT|State (tracing on)",
        "EVENT|Demo: a",
        "EVENT|Demo: b",
    ]


def test_nothing_written_while_off() -> None:
    trace.register_snapshot("Demo", lambda: ["Demo: a"])
    trace.write_snapshot("start")
    trace.snapshot_changed("Demo")
    assert trace.lines() == []


def test_written_at_start_when_tracing_is_on() -> None:
    trace.register_snapshot("Demo", lambda: ["Demo: a"])
    trace.set_enabled(True)
    trace.write_snapshot("start")
    assert "EVENT|State (start)" in _state()


def test_a_changed_section_is_written_again() -> None:
    value = ["one"]
    trace.register_snapshot("Demo", lambda: [f"Demo: {value[0]}"])
    trace.register_snapshot("Other", lambda: ["Other: x"])
    trace.set_enabled(True)
    value[0] = "two"
    trace.snapshot_changed("Demo")
    assert _state()[-2:] == ["EVENT|State (Demo changed)", "EVENT|Demo: two"]


def test_a_failing_provider_reads_not_available() -> None:
    def boom() -> list[str]:
        raise RuntimeError("no")

    trace.register_snapshot("Broken", boom)
    trace.register_snapshot("Fine", lambda: ["Fine: ok"])
    trace.set_enabled(True)
    assert "EVENT|Broken: not available" in _state()
    assert "EVENT|Fine: ok" in _state()
    assert "Broken: not available" in trace.snapshot_text()


def test_snapshot_text_holds_all_sections() -> None:
    trace.register_snapshot("A", lambda: ["A: 1"])
    trace.register_snapshot("B", lambda: ["B: 1", "B: 2"])
    assert trace.snapshot_text() == "A: 1\nB: 1\nB: 2\n"


def test_program_provider_lines() -> None:
    from gremlin.ui import trace_model  # registers "Program"

    trace.register_snapshot("Program", trace_model._program_snapshot)
    text = trace.snapshot_text()
    for start in (
        "Program: version",
        "Profile:",
        "Log When Not Responding:",
        "Diagnostic logs:",
        "Trace rows ticked:",
        "Keep tracing on: off",
    ):
        assert start in text, text


def test_run_events_rewrite_the_program_section() -> None:
    from gremlin.ui import trace_model

    trace.register_snapshot("Program", trace_model._program_snapshot)
    trace.set_enabled(True)
    trace.event("Profile stopped")
    lines = _state()
    assert "EVENT|State (Program changed)" in lines
    assert any(x.endswith("not running") for x in lines)
    trace.event("Profile started (mode Default)")
    assert any(x.endswith("not running") for x in _state())  # no Run in the test


def test_keep_on_restores_tracing_at_start() -> None:
    trace.register_snapshot("Demo", lambda: ["Demo: a"])
    trace.restore_at_start()
    assert not trace.enabled()
    trace.set_keep_on(True)
    assert trace.keep_on()
    trace.restore_at_start()
    assert trace.enabled()
    assert "EVENT|State (tracing on)" in _state()


def test_keep_on_is_not_in_history() -> None:
    trace.set_keep_on(True)
    cfg = config.Configuration()
    key = ("global", "trace", "keep-on")
    assert cfg._view_entry(key, cfg._data[key]) is None
