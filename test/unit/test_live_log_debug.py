# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Live Log Reader's Debug tab reads the diagnostic logs by entry."""

from __future__ import annotations

from pathlib import Path

import pytest

from gremlin.ui.live_debug import DebugLog, debug_entries, filter_entries

_ROOT = Path(__file__).resolve().parents[2]

_SYSTEM = (
    "2026-10-03 09:12:01       INFO Loaded profile\n"
    "2026-10-03 09:12:02    WARNING vJoy device 2 has 32 buttons\n"
    "2026-10-03 09:12:05      ERROR Invalid button index - vjoy: 3\n"
    "Traceback (most recent call last):\n"
    "IndexError: button 127 out of range\n"
    "2026-10-03 09:12:06      DEBUG Mode changed\n"
)


def test_a_traceback_belongs_to_its_entry() -> None:
    entries = debug_entries(_SYSTEM)
    assert [rank for rank, _ in entries] == [1, 2, 3, 0]
    assert entries[2][1].endswith("IndexError: button 127 out of range")


def test_levels_and_find() -> None:
    entries = debug_entries(_SYSTEM)
    assert len(filter_entries(entries, "All", "")) == 4
    assert len(filter_entries(entries, "Info", "")) == 3
    assert len(filter_entries(entries, "Warning", "")) == 2
    assert len(filter_entries(entries, "Error", "")) == 1
    # Find also searches the traceback, case-insensitively.
    assert len(filter_entries(entries, "All", "INDEXERROR")) == 1
    assert len(filter_entries(entries, "Warning", "vjoy")) == 2


def test_event_and_script_lines() -> None:
    events = debug_entries("2026-10-03 09:12:01,WARNING,axis 1\n")
    assert events == [(2, "2026-10-03 09:12:01,WARNING,axis 1")]
    # Script lines have no level: they count as Info.
    assert debug_entries("2026-10-03 09:12:01 hello\n")[0][0] == 1


def test_window_has_config_debug_and_input_monitor_tabs() -> None:
    qml = (_ROOT / "qml" / "DialogLiveLog.qml").read_text(encoding="utf-8")
    assert 'TabButton { text: "Config"' in qml
    assert '"Debug ●" : "Debug"' in qml
    assert '"Input Monitor ●" : "Input Monitor"' in qml
    assert "LiveLog {" in qml and "DebugLog {" in qml and "InputMonitor {" in qml
    # Live on the Debug tab, Monitor on the Input Monitor tab.
    assert 'caption: "Live"' in qml and 'caption: "Monitor"' in qml
    assert '{ text: "All logs", value: "all" }' in qml
    # The write level (same setting as Options) sits under the Debug log.
    assert "OptionLogLevel {" in qml


def _debug_log(path: Path, name: str) -> DebugLog:
    log = DebugLog()
    log._file = name
    log._path = lambda: path  # type: ignore[method-assign]
    log._logging_on = lambda: True  # type: ignore[method-assign]
    return log


def test_load_whole_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import gremlin.ui.live_debug as live_debug

    monkeypatch.setattr(live_debug, "_TAIL_BYTES", 200)
    path = tmp_path / "system.log"
    path.write_text("".join(
        f"2026-10-03 09:12:{i:02d}       INFO line {i}\n" for i in range(20)
    ), encoding="utf-8")
    log = _debug_log(path, "test-whole")
    log.refresh()
    assert log.truncated and 0 < log.totalCount < 20
    log.loadWhole()
    assert not log.truncated and log.totalCount == 20


def test_clear_empties_the_file_through_its_handler(tmp_path: Path) -> None:
    import logging

    path = tmp_path / "event.log"
    logger = logging.getLogger("test-clear-log")
    logger.propagate = False
    handler = logging.FileHandler(path, mode="w", encoding="utf-8")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    try:
        logger.info("before")
        handler.flush()
        log = _debug_log(path, "test-clear-log")
        log.refresh()
        assert log.totalCount == 1
        log.clear()
        assert path.read_text(encoding="utf-8") == ""
        assert log.totalCount == 0
        # The handler keeps writing from the start, with no gap.
        logger.info("after")
        handler.flush()
        assert path.read_text(encoding="utf-8") == "after\n"
    finally:
        logger.removeHandler(handler)
        handler.close()


def test_all_logs_merges_every_file_by_time(tmp_path: Path) -> None:
    (tmp_path / "system.log").write_text(
        "2026-10-04 10:00:01       INFO started\n"
        "2026-10-04 10:00:05    WARNING slow\n", encoding="utf-8")
    (tmp_path / "event.log").write_text(
        "2026-10-04 10:00:03 Button 1 pressed\n", encoding="utf-8")
    (tmp_path / "qt.log").write_text(
        "2026-10-04 10:00:02 qrc:/x.qml: a QML warning\n"
        "2026-10-04 10:00:05 later, same second\n", encoding="utf-8")
    log = _debug_log(tmp_path, "all")
    log.refresh()
    texts = [text for _rank, text in log._shown]
    assert texts == [
        "2026-10-04 10:00:01 [System]       INFO started",
        "2026-10-04 10:00:02 [Qt] qrc:/x.qml: a QML warning",
        "2026-10-04 10:00:03 [Events] Button 1 pressed",
        "2026-10-04 10:00:05 [System]    WARNING slow",
        "2026-10-04 10:00:05 [Qt] later, same second",
    ]
    assert log.exists
    # The levels still read: Warning shows only the warning.
    log.setProperty("level", "Warning")
    assert [t for _r, t in log._shown] == [
        "2026-10-04 10:00:05 [System]    WARNING slow"
    ]
    # A new line in any file shows on the next refresh.
    with (tmp_path / "user.log").open("a", encoding="utf-8") as f:
        f.write("2026-10-04 10:00:09 ERROR script failed\n")
    log.setProperty("level", "All")
    log.refresh()
    last = log._shown[-1][1]
    assert last == "2026-10-04 10:00:09 [Scripts] ERROR script failed"


def test_picking_a_log_after_live_stops_shows_that_log(tmp_path: Path) -> None:
    (tmp_path / "qt.log").write_text(
        "2026-10-04 10:00:02 a Qt line\n", encoding="utf-8"
    )
    log = _debug_log(tmp_path, "all")
    log.setProperty("live", True)
    log.setProperty("live", False)
    assert log.session
    log._path = lambda: tmp_path / (  # type: ignore[method-assign]
        "qt.log" if log._file == "qt" else ""
    )
    log.setProperty("file", "qt")
    assert not log.session
    assert [t for _r, t in log._shown] == ["2026-10-04 10:00:02 a Qt line"]
    page = (Path(__file__).parents[2] / "qml" / "DialogLiveLog.qml").read_text(
        encoding="utf-8"
    )
    # The list without Live: All logs and every file, Qt included.
    assert 'model: _debug.live' in page
