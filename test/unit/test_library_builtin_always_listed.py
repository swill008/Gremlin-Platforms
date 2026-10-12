# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""10 S6 (item 61): Keyboard, OSC and the Logical Device are always listed
under INTERNAL INPUTS, even with no module file and no saved setup. Such a
row shows the empty line, Save is greyed, and nothing is written to disk."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from gremlin import device_library as library
from gremlin import shared_state
from gremlin.modules import ids, store
from gremlin.ui import device_library_model
from test.unit._device_folders import put_module

KEYBOARD_GUID = "{" + str(ids.KEYBOARD).upper() + "}"
STICK_GUID = "{6C3D1E20-1111-2222-3333-444455556666}"
_BUILT_INS = ["Keyboard", "Logical Device", "OSC"]


@pytest.fixture
def fresh(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setattr(store, "folder", lambda: folder)
    monkeypatch.setattr(library, "folder", lambda: tmp_path / "device library")
    monkeypatch.setattr(library, "_photo_cache", lambda: tmp_path / "photo cache")
    monkeypatch.setattr(library, "_connected", lambda: [])
    monkeypatch.setattr(library, "_alias", lambda guid, default: default)
    before = shared_state.current_profile
    shared_state.current_profile = None
    yield tmp_path
    shared_state.current_profile = before


def _files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*"))


def test_fresh_profile_lists_the_three_built_ins(fresh: Path) -> None:
    before = _files(fresh)
    rows = library.devices()
    assert sorted(r["name"] for r in rows) == _BUILT_INS
    for row in rows:
        assert row["builtIn"] is True
        assert row["state"] == "builtin"
        assert row["module"] == ""
        assert row["setups"] == []
    # Display only: nothing created on disk.
    assert _files(fresh) == before


def test_empty_built_in_shows_the_line_and_save_is_greyed(fresh: Path) -> None:
    model = device_library_model.DeviceLibraryModel(api=None, watch_devices=False)
    for row in library.devices():
        details = model._device_details(row)
        assert details["emptyText"] == device_library_model.NOTHING_SAVED
        assert details["hasCurrent"] is False
        assert details["builtIn"] is True
    assert "File › Import Device…" in device_library_model.NOTHING_SAVED


def test_a_built_in_with_a_file_is_listed_once_and_can_save(fresh: Path) -> None:
    doc = {
        "kind": "control.hardware",
        "device": "Keyboard",
        "nodes": [],
        "claim": {},
        "boundGuidLocal": KEYBOARD_GUID,
    }
    put_module(fresh / "modules", "Keyboard", doc, KEYBOARD_GUID)
    stick = dict(doc, device="Stick A", boundGuidLocal=STICK_GUID)
    put_module(fresh / "modules", "Stick A", stick, STICK_GUID)
    rows = library.devices()
    names = [r["name"] for r in rows]
    assert names[0] == "Stick A"
    assert sorted(names[1:]) == _BUILT_INS
    keyboard = next(r for r in rows if r["name"] == "Keyboard")
    assert keyboard["module"]
    model = device_library_model.DeviceLibraryModel(api=None, watch_devices=False)
    details = model._device_details(keyboard)
    assert details["emptyText"] == ""
    assert details["hasCurrent"] is True
