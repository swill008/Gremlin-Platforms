# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A mode rename keeps the stored last mode of the profile it was made in,
even when the open profile is swapped before the input thread runs it (N2)."""

from __future__ import annotations

import sys

sys.path.append(".")

from pathlib import Path
from typing import Any

import pytest

from gremlin import mode_manager, shared_state
from gremlin.profile import Profile


def test_rename_targets_profile_at_call_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first, second = Profile(), Profile()
    first.fpath, second.fpath = Path("first.xml"), Path("second.xml")
    monkeypatch.setattr(shared_state, "current_profile", first)
    monkeypatch.setattr(shared_state, "running_profile", None)

    stored: dict[Any, Any] = {Path("first.xml"): "Old", Path("second.xml"): "Old"}
    monkeypatch.setattr(mode_manager, "_stored_last_modes", lambda: stored)
    monkeypatch.setattr(
        mode_manager,
        "_last_mode_of",
        lambda data, fpath: data.get(fpath),
    )
    monkeypatch.setattr(
        mode_manager,
        "_put_last_mode",
        lambda data, fpath, name: data.__setitem__(fpath, name),
    )
    monkeypatch.setattr(mode_manager, "_pending_last", {})

    class _Config:
        def set(self, *args: object) -> None:
            pass

    monkeypatch.setattr(mode_manager, "Configuration", _Config)
    monkeypatch.setattr(mode_manager, "_known_modes", lambda: set())

    queued: list[Any] = []
    monkeypatch.setattr(
        mode_manager, "_on_input_thread", lambda fn, *a: queued.append((fn, a))
    )
    mm = mode_manager.ModeManager()
    mm.rename_mode("Old", "New")
    monkeypatch.setattr(shared_state, "current_profile", second)  # profile swap
    monkeypatch.setattr(
        "gremlin.event_handler.EventHandler",
        lambda: type("E", (), {"rename_mode": lambda *a: None})(),
    )
    for fn, args in queued:
        fn(*args)
    assert stored == {Path("first.xml"): "New", Path("second.xml"): "Old"}
