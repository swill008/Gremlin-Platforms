# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Device Library in a deep user folder (todo 104): Swap's autosaves are
kept although the Library folder is near Windows' 260-character limit
(10 S16-S20, S26). The real autosave, store and module file writes."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

from gremlin import device_library as library
from gremlin import library_swap, shared_state
from gremlin.modules import module_file, store
from test.unit._device_folders import put_module

LEFT = ("Left stick", "{97B77B40-07D8-11F0-8028-444553540000}")
RIGHT = ("Right stick", "{12345678-1234-1234-1234-1234567890AB}")
HAS = {g: {"button": {1, 2}, "axis": {1}, "hat": set()} for _, g in (LEFT, RIGHT)}
# The longest autosave path the Library makes here: <folder>\<device>\
# "Autosave YYYY-MM-DD HHMMSS.gmap". 250 leaves the temporary file's
# suffix (".xxxxxxxx.tmp") past 260.
_TARGET = 250


def _deep(base: Path, length: int) -> Path:
    pad = length - len(str(base)) - 1
    if pad < 1:
        pytest.skip("the temporary folder is already too deep")
    return base / ("d" * pad)


@pytest.fixture
def deep(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    modules = tmp_path / "m"
    modules.mkdir()
    longest = max(len(name) for name, _ in (LEFT, RIGHT))
    file = r"\\Autosave 2026-10-12 105558.gmap"
    folder = _deep(tmp_path, _TARGET - longest - len(file))
    monkeypatch.setattr(store, "folder", lambda: modules)
    monkeypatch.setattr(library, "folder", lambda: folder)
    monkeypatch.setattr(library, "_photo_cache", lambda: tmp_path / "photos")
    monkeypatch.setattr(library, "_connected", lambda: [])
    monkeypatch.setattr(library, "_alias", lambda guid, default: default)
    monkeypatch.setattr(store, "connected_input_ids", _has)
    monkeypatch.setattr(library_swap, "_controls", _has)
    for name, guid in (LEFT, RIGHT):
        put_module(
            modules,
            name,
            {
                "kind": "control.hardware",
                "device": name,
                "boundGuidLocal": guid,
                "claim": {"buttons": [1], "axes": [], "hats": []},
                "nodes": [],
            },
            guid,
        )
    before = shared_state.current_profile
    shared_state.current_profile = None
    yield folder
    shared_state.current_profile = before


def _has(guid: str) -> dict | None:
    key = str(uuid.UUID(str(guid).strip("{}"))).upper()
    for _, g in (LEFT, RIGHT):
        if g.strip("{}").upper() == key:
            return HAS[g]
    return None


def test_swap_keeps_both_autosaves_in_a_deep_user_folder(deep: Path) -> None:
    out = library_swap.swap(LEFT, RIGHT, ["setup"], [])
    assert out["ok"], out.get("error")
    kept = sorted(deep.rglob("*.gmap"))
    assert len(kept) == 2
    # The file is "Autosave <time>"; the list keeps the full reason.
    assert all(p.name.startswith("Autosave 20") for p in kept)
    rows = library._read()["devices"]
    names = {s["name"] for d in rows for s in d.get("setups") or []}
    assert "Autosave: before Swap with Right stick" in names


def test_a_file_near_the_limit_is_written_whole(tmp_path: Path) -> None:
    """The temporary file's suffix alone must not push a write past 260."""
    dest = _deep(tmp_path, 240) / "file.json"
    module_file.write_bytes(dest, b"{}")
    assert dest.read_bytes() == b"{}"
    assert [p.name for p in dest.parent.iterdir()] == ["file.json"]
