# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Configuration page's groups, order and Rename follow the Logical
Device's file rule (CS1 (a), D-04-LD-FILE pattern): held unsaved per device,
the title's "*" shows, File > Save Profile writes each device's module file
once (one History entry), Discard drops them.

Spec: 05 S121-S131 (S122, S127, S129); D-04-LD-FILE.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from gremlin import history_modules, shared_state
from gremlin.modules import module_file, store
from gremlin.profile import Profile
from gremlin.ui.backend import Backend

GUID = "{11111111-2222-3333-4444-555555555555}"
NAME = "Test Stick"
LAYOUT = {
    "groups": ["Weapons"],
    "order": ["button:2", "button:1"],
    "group_of": {"button:2": "Weapons"},
}


@pytest.fixture
def device(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """A module file for the device, found by its id."""
    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setattr(store, "folder", lambda: folder)
    path = folder / "test_stick.json"
    module_file.write_json(
        path,
        {
            "kind": "control.hardware",
            "device": NAME,
            "direction": "source",
            "claim": {"buttons": [1, 2], "friendly": {"button:1": "Fire"}},
            "nodes": [],
        },
    )
    monkeypatch.setattr(
        store, "_layout_path", lambda guid, name="": path if guid == GUID else None
    )
    store.discard_pending()
    yield path
    store.discard_pending()


@pytest.fixture
def writes(monkeypatch: pytest.MonkeyPatch, device: Path) -> list[str]:
    """Each module file write (History entry) of the device's file."""
    got: list[str] = []
    monkeypatch.setattr(
        history_modules,
        "note_write",
        lambda path, text, old=None: got.append(Path(path).name),
    )
    return got


@pytest.fixture
def profile(
    qapp: object, tmp_path: Path, device: Path
) -> Iterator[tuple[Profile, Path]]:
    saved = shared_state.current_profile
    shown = Profile()
    shared_state.current_profile = shown
    fpath = tmp_path / "cfg_layout_save.xml"
    shown.to_xml(fpath)
    assert not shown.has_unsaved_changes()
    yield shown, fpath
    shared_state.current_profile = saved


def _doc(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_a_group_change_waits_for_save_and_saves_once(
    device: Path, writes: list[str], profile: tuple[Profile, Path]
) -> None:
    shown, fpath = profile
    before = device.read_text(encoding="utf-8")
    store.set_pending_layout(GUID, LAYOUT)
    # Held, not written: the file is as it was; the page sees the change.
    assert device.read_text(encoding="utf-8") == before
    assert writes == []
    assert store.layout_for(GUID) == LAYOUT
    assert store.read_layout(GUID) == store.empty_layout()
    # The title's "*".
    assert shown.has_unsaved_changes()
    assert shown.looks_unsaved()
    # File > Save Profile writes it, once.
    shown.to_xml(fpath)
    assert writes == ["test_stick.json"]
    assert _doc(device)["layout"] == LAYOUT
    assert not store.has_pending()
    assert not shown.has_unsaved_changes()


def test_names_follow_the_same_rule_and_share_the_one_write(
    device: Path, writes: list[str], profile: tuple[Profile, Path]
) -> None:
    shown, fpath = profile
    store.set_pending_name(GUID, "button:2", "Pinkie")
    store.set_pending_layout(GUID, LAYOUT, {"button:1": ""})
    assert writes == []
    assert store.friendly_name_for(GUID, "button:2") == "Pinkie"
    assert store.friendly_name_for(GUID, "button:1") == ""
    assert store.friendly_name(GUID, "button:1") == "Fire"
    assert shown.looks_unsaved()
    shown.to_xml(fpath)
    # Layout and both names: one write, one History entry.
    assert writes == ["test_stick.json"]
    doc = _doc(device)
    assert doc["claim"]["friendly"] == {"button:2": "Pinkie"}
    assert doc["layout"] == LAYOUT


def test_discard_drops_the_changes(
    device: Path, writes: list[str], profile: tuple[Profile, Path]
) -> None:
    shown, fpath = profile
    heard: list[tuple[str, str]] = []
    listener = lambda what, guid: heard.append((what, guid))  # noqa: E731
    store.add_pending_listener(listener)
    try:
        store.set_pending_layout(GUID, LAYOUT, {"button:2": "Pinkie"})
        assert shown.has_unsaved_changes()
        Backend.klass.discardConfigurationLayouts(None)  # type: ignore[attr-defined]
    finally:
        store.remove_pending_listener(listener)
    assert ("discarded", "") in heard
    assert not store.has_pending()
    assert store.layout_for(GUID) == store.empty_layout()
    assert store.friendly_name_for(GUID, "button:2") == ""
    assert not shown.has_unsaved_changes()
    shown.to_xml(fpath)
    assert writes == []
    assert "layout" not in _doc(device)


def test_undo_back_to_the_saved_layout_clears_the_star(
    device: Path, writes: list[str], profile: tuple[Profile, Path]
) -> None:
    shown, _ = profile
    store.set_pending_layout(GUID, LAYOUT)
    assert store.pending_layout(GUID) == {"layout": LAYOUT, "names": {}}
    # Page Undo before Save: the step puts the earlier layout back.
    store.set_pending_layout(GUID, store.empty_layout())
    assert store.pending_layout(GUID) is None
    assert not shown.has_unsaved_changes()
    assert writes == []
