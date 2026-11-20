# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""08 (History): troubleshooting settings are saved and persistent but never
recorded in History (user 2026-11-20): Diagnostic logs, the not-responding
log, every Screen Saver Mode setting, HidHide's managed flag and the
keep-on trace. Every other setting (HidHide photos, dark mode) still is."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from gremlin import config, history
from gremlin.types import PropertyType

_NOT_RECORDED = [
    ("global", "general", "log-level", PropertyType.String, "Warning", "Error"),
    ("global", "general", "log-when-not-responding", PropertyType.Bool, False, True),
    ("global", "screen-saver-mode", "devices", PropertyType.String, "a", "b"),
    ("global", "screen-saver-mode", "wake-pc", PropertyType.String, "a", "b"),
    ("global", "screen-saver-mode", "devices-wait-s", PropertyType.Int, 1, 5),
    ("global", "screen-saver-mode", "anything-new", PropertyType.Bool, False, True),
    ("display", "hidhide", "managed", PropertyType.Bool, False, True),
    ("global", "trace", "keep-on", PropertyType.Bool, False, True),
]
_RECORDED = [
    ("display", "hidhide", "photos", PropertyType.String, "a", "b"),
    ("ui", "general", "some-choice", PropertyType.Bool, False, True),
]


@pytest.fixture
def recorded(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[list]:
    path = tmp_path / "c.json"
    monkeypatch.setattr(config, "_config_file_path", str(path))
    calls: list[Any] = []
    monkeypatch.setattr(history, "record", lambda *a, **k: calls.append((a, k)))
    yield calls


def _fresh() -> config.Configuration:
    """A new Configuration reading the file (the real one is a singleton)."""
    cfg = object.__new__(config.Configuration)
    cfg.__init__()
    return cfg


def _change(row: tuple, expose: bool) -> tuple[list, config.Configuration]:
    section, group, name, kind, old, new = row
    cfg = _fresh()
    props = {"min": 0, "max": 100} if kind is PropertyType.Int else {}
    cfg.register(section, group, name, kind, old, "", props, expose=expose)
    cfg._history_view = cfg._settings_view()
    cfg.set(section, group, name, new)
    cfg.save_now()
    return [], cfg


@pytest.mark.parametrize("expose", [False, True])
@pytest.mark.parametrize("row", _NOT_RECORDED, ids=lambda r: "/".join(r[:3]))
def test_saved_and_persistent_but_not_in_history(
    row: tuple, expose: bool, recorded: list
) -> None:
    _change(row, expose)
    assert not recorded, f"{row[:3]} was recorded in History"
    section, group, name, kind, _old, new = row
    old_default = lambda _k: _old  # noqa: E731
    # Persistent: a new Configuration from the same file has the value.
    again = _fresh()
    props = {"min": 0, "max": 100} if kind is PropertyType.Int else {}
    again.register(section, group, name, kind, old_default(kind), "", props)
    assert again.value(section, group, name) == new


@pytest.mark.parametrize("row", _RECORDED, ids=lambda r: "/".join(r[:3]))
def test_other_settings_still_recorded(row: tuple, recorded: list) -> None:
    _change(row, expose=True)
    assert recorded, f"{row[:3]} should still be recorded in History"
