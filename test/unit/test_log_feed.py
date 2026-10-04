# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Live log feed (Live Log Reader → Debug → Live): catches every line while
it runs, leaves the log files at their Diagnostic logs level, and the Debug
tab keeps what it showed and adds to it."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path

import pytest

from gremlin import log_feed
from gremlin.ui import debug_mode
from gremlin.ui.live_debug import DIVIDER, DebugLog
from gremlin.ui.log_option import apply_log_level


@pytest.fixture
def system_file(tmp_path: Path) -> Iterator[tuple[logging.Logger, Path]]:
    """The system logger writing to a file at Warning, like the program."""
    path = tmp_path / "system.log"
    logger = logging.getLogger("system")
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    logger.addHandler(handler)
    apply_log_level("Warning")
    log_feed.clear()
    try:
        yield logger, path
    finally:
        log_feed.stop()
        log_feed.clear()
        logger.removeHandler(handler)
        handler.close()
        apply_log_level("Warning")


def _texts() -> list[str]:
    return [entry.text for entry in log_feed.entries()]


def test_feed_catches_everything_files_keep_their_level(
    system_file: tuple[logging.Logger, Path],
) -> None:
    logger, path = system_file
    logger.debug("before Live")
    log_feed.start()
    logger.debug("debug line")
    logger.warning("warning line")
    log_feed.stop()
    logger.debug("after Live")
    texts = _texts()
    assert any("[System]  DEBUG" in t and "debug line" in t for t in texts)
    assert any("warning line" in t for t in texts)
    assert not any("before Live" in t or "after Live" in t for t in texts)
    written = path.read_text(encoding="utf-8")
    assert "warning line" in written and "debug line" not in written
    # Stopped: the logger is back at the Diagnostic logs level.
    assert logger.level == logging.WARNING


def test_feed_runs_with_logs_off_and_through_a_level_change(
    system_file: tuple[logging.Logger, Path],
) -> None:
    logger, path = system_file
    apply_log_level("Off")
    log_feed.start()
    logger.info("while off")
    apply_log_level("Error")  # changed on the fly while Live runs
    logger.info("after change")
    texts = _texts()
    assert any("while off" in t for t in texts)
    assert any("after change" in t for t in texts)
    assert path.read_text(encoding="utf-8") == ""


def test_debug_tab_keeps_the_view_and_adds_live_lines(
    system_file: tuple[logging.Logger, Path], tmp_path: Path,
) -> None:
    logger, _path = system_file
    shown = tmp_path / "shown.log"
    shown.write_text("2026-10-03 09:00:00       INFO earlier line\n", encoding="utf-8")
    log = DebugLog()
    log._path = lambda: shown  # type: ignore[method-assign]
    log._logging_on = lambda: True  # type: ignore[method-assign]
    log.refresh()
    assert not log.session
    log.live = True
    assert log.session and log.file == "all"
    logger.info("live line")
    log.refresh()
    rows = [text for _rank, text in log._shown]
    assert "earlier line" in rows[0]  # kept, not cleared
    assert rows[1].startswith("── Live started")
    assert "[System]" in rows[2] and "live line" in rows[2]
    log.file = "user"  # Scripts only: the System line is filtered out
    assert all("live line" not in t for _r, t in log._shown)
    log.file = "all"
    log.live = False
    assert log.session  # stays on screen after Live stops
    assert log._shown[-1][0] == DIVIDER and "stopped" in log._shown[-1][1]
    # Back to the files: All logs (every file, merged), as the session was.
    log.showFile()
    assert not log.session and log.file == "all"


def test_start_empty_and_clear_view(
    system_file: tuple[logging.Logger, Path], tmp_path: Path,
) -> None:
    logger, _path = system_file
    shown = tmp_path / "shown.log"
    shown.write_text("2026-10-03 09:00:00       INFO earlier line\n", encoding="utf-8")
    log = DebugLog()
    log._path = lambda: shown  # type: ignore[method-assign]
    log._logging_on = lambda: True  # type: ignore[method-assign]
    log._get_start_empty = lambda: True  # type: ignore[method-assign]
    log.refresh()
    try:
        log.live = True
        assert all("earlier line" not in t for _r, t in log._shown)
        logger.warning("one")
        log.refresh()
        assert any("one" in t for _r, t in log._shown)
        log.clearView()  # the view only; Live keeps going
        assert log.live and log.session and log._shown == []
        logger.warning("two")
        log.refresh()
        assert any("two" in t for _r, t in log._shown)
    finally:
        log.live = False


def test_red_mode_follows_all_and_live(
    system_file: tuple[logging.Logger, Path], monkeypatch: pytest.MonkeyPatch,
) -> None:
    import gremlin.config

    levels = {"value": "Warning"}
    monkeypatch.setattr(
        gremlin.config.Configuration, "exists", lambda self, *key: True,
    )
    monkeypatch.setattr(
        gremlin.config.Configuration, "value", lambda self, *key: levels["value"],
    )
    assert not debug_mode.is_active()
    levels["value"] = "ALL"
    assert debug_mode.is_active()
    levels["value"] = "Info"
    log_feed.start()
    assert debug_mode.is_active()
    log_feed.stop()
    assert not debug_mode.is_active()
