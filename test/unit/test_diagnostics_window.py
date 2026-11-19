# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Save Diagnostics adds window-state.txt and recent-window-events.txt
(01 S132, S177)."""

from __future__ import annotations

import sys
import types
import zipfile
from pathlib import Path

import pytest

from gremlin import diagnostics, trace


def test_the_zip_has_the_window_state_and_the_recent_events(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = types.ModuleType("gremlin.ui.window_trace")
    fake.state_text = lambda: "Main window: visible, Normal"  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "gremlin.ui.window_trace", fake)
    trace.recent("Main window", "tray: left (tray click)")
    plan = diagnostics.collect(False)
    dest = tmp_path / "d.zip"
    diagnostics.write_zip(plan, dest)
    with zipfile.ZipFile(dest) as zf:
        names = zf.namelist()
        assert "window-state.txt" in names
        assert "recent-window-events.txt" in names
        assert "visible, Normal" in zf.read("window-state.txt").decode()
        assert "tray: left (tray click)" in zf.read(
            "recent-window-events.txt"
        ).decode()
