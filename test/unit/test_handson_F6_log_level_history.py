# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""08 S15 / S44 (B7): the Diagnostic logs level chosen in Options is
recorded in History and can be put back. Uses the program's own
registration of the setting (joystick_gremlin.register_config_options),
which keeps it out of Options' "Other" rows (it has its own row)."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path

import pytest

import joystick_gremlin
from gremlin import clock, config, deferred_write, history
from gremlin.ui import history_model, log_option, option

_KEY = "global/general/log-level"


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    folder = tmp_path / "history"
    monkeypatch.setattr(history, "folder", lambda: folder)
    monkeypatch.setattr(history, "_pruned", True)
    yield folder
    _settle()


def _settle() -> list[dict]:
    # Bounded: the history writer finishes what is queued.
    deadline = clock.monotonic() + 5
    while history._writer is not None and clock.monotonic() < deadline:
        clock.sleep(0.02)
    return history.entries()


@pytest.fixture
def cfg(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Iterator[config.Configuration]:
    monkeypatch.setattr(config, "_config_file_path", str(tmp_path / "c.json"))
    cfg = config.Configuration()
    # One shared object: its entries go back afterwards.
    monkeypatch.setattr(cfg, "_data", {k: dict(v) for k, v in cfg._data.items()})
    system = logging.getLogger("system")
    old_level, old_disabled = system.level, system.disabled
    # The program's own registration, as at start.
    joystick_gremlin.register_config_options()
    cfg.set("global", "general", "log-level", "Warning")
    log_option.apply_log_level("Warning")
    cfg.save_now()
    monkeypatch.setattr(cfg, "_history_view", cfg._settings_view(), raising=False)
    try:
        yield cfg
    finally:
        # The settings save the change scheduled goes now, into this test's
        # files, not a later test's history.
        deferred_write.flush("configuration")
        log_option.apply_log_level("Warning")
        system.setLevel(old_level)
        system.disabled = old_disabled


def test_diagnostic_logs_from_options_is_recorded_and_restored(
    store: Path, cfg: config.Configuration
) -> None:
    log_option.LogLevelModel().setLevel("Error")
    cfg.save_now()
    entries = [e for e in _settle() if e["area"] == "settings"]
    assert entries, "no History entry for the Diagnostic logs level"
    entry = entries[-1]
    assert entry["before"] == {_KEY: "Warning"}
    assert entry["after"] == {_KEY: "Error"}
    assert logging.getLogger("system").level == logging.ERROR

    ok, _message = history_model._restore_settings(entry["before"])
    assert ok
    assert cfg.value("global", "general", "log-level") == "Warning"
    assert logging.getLogger("system").level == logging.WARNING


def test_diagnostic_logs_shows_only_through_its_own_row(
    cfg: config.Configuration,
) -> None:
    """Why the setting is registered unexposed: Options shows it through the
    "debug" row (Diagnostic logs), never as a raw text row of its own."""
    keys = [k for _s, groups in option.main_layout() for _g, ks in groups for k in ks]
    assert ("global", "general", "debug") in keys
    assert ("global", "general", "log-level") not in keys
