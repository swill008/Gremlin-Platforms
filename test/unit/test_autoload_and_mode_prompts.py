# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Auto-load finds the right profile however the program was typed and never
switches over unsaved edits; deleting a mode can say what it takes with it."""

from __future__ import annotations

import sys

sys.path.append(".")

import types
from collections.abc import Callable, Iterator

import pytest

from gremlin import config
from gremlin.profile import ModeHierarchy, Profile
from gremlin.ui import backend

_KEY = ("profile", "automation", "entries-auto-loading")
# Backend is a singleton wrapper; the method lives on the class inside it.
_AUTOLOAD = backend.Backend.klass._active_process_changed_cb


@pytest.fixture
def entries() -> Iterator[Callable[..., None]]:
    cfg = config.Configuration()
    before = cfg.value(*_KEY)
    yield lambda *rows: cfg.set(*_KEY, [list(r) for r in rows])
    cfg.set(*_KEY, before)


def test_typed_path_matches_whatever_the_slashes_and_case(
    entries: Callable[..., None],
) -> None:
    entries(["game.xml", r"C:\Games\Sim\SIM.exe", True])
    assert config.get_profile_with_regex("C:/Games/Sim/sim.exe") == "game.xml"


def test_every_ticked_pattern_is_tried(
    entries: Callable[..., None],
) -> None:
    entries(["a.xml", r"alpha\.exe$", True], ["b.xml", r"bravo\.exe$", True])
    assert config.get_profile_with_regex("C:/x/bravo.exe") == "b.xml"


def test_blank_and_broken_patterns_match_nothing(
    entries: Callable[..., None],
) -> None:
    entries(
        ["blank.xml", "  ", True],
        ["broken.xml", "(unclosed", True],
        ["off.xml", "any", False],
    )
    assert config.get_profile_with_regex("C:/x/anything.exe") is None


def _fake(unsaved: bool) -> types.SimpleNamespace:
    calls: list = []
    return types.SimpleNamespace(
        config=types.SimpleNamespace(value=lambda *key: True),
        profile=types.SimpleNamespace(
            fpath="open.xml", has_unsaved_changes=lambda: unsaved
        ),
        gremlinActive=False,
        _autoload_held=None,
        activate_gremlin=lambda on: calls.append(("active", on)),
        loadProfile=lambda path: calls.append(("load", path)),
        calls=calls,
    )


def test_auto_load_waits_for_unsaved_edits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "get_profile_with_regex", lambda path: "game.xml")
    notes: list = []
    def note(*args: str) -> None:
        notes.append(args)

    backend.signal.showNotification.connect(note)
    fake = _fake(unsaved=True)
    try:
        _AUTOLOAD(fake, "C:/x/game.exe")
        _AUTOLOAD(fake, "C:/x/game.exe")
    finally:
        backend.signal.showNotification.disconnect(note)
    assert fake.calls == []
    assert len(notes) == 1  # Said once, not on every focus change.

    saved = _fake(unsaved=False)
    _AUTOLOAD(saved, "C:/x/game.exe")
    assert ("load", "game.xml") in saved.calls


class _Item:
    def __init__(self, mode: str, bindings: int) -> None:
        self.mode = mode
        self.action_sequences = [object()] * bindings


def test_mode_delete_counts_the_bindings_it_removes() -> None:
    p = Profile()
    mh = ModeHierarchy(p)
    mh.add_mode("Combat")
    p.inputs = {"dev": [_Item("Combat", 2), _Item("Default", 1), _Item("Combat", 1)]}
    assert mh.bindings_in_mode("Combat") == 3
    assert mh.bindings_in_mode("Default") == 1
