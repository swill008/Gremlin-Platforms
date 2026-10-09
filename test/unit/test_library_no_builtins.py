# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Device Library never lists the built-in inputs, Keyboard and OSC, as
devices (10 S6, D-10-NO-BUILTINS). The real store in a temporary modules
folder holding a keyboard, an OSC and a stick module file."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest

from gremlin import device_library as library
from gremlin import shared_state
from gremlin.modules import ids, module_file, registry, store

STICK_GUID = "{6C3D1E20-1111-2222-3333-444455556666}"
KEYBOARD_GUID = "{" + str(ids.KEYBOARD).upper() + "}"
OSC_GUID = "{" + str(ids.OSC).upper() + "}"


@pytest.fixture
def modules(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setattr(store, "folder", lambda: folder)
    monkeypatch.setattr(library, "folder", lambda: tmp_path / "device library")
    monkeypatch.setattr(library, "_photo_cache", lambda: tmp_path / "photo cache")
    monkeypatch.setattr(library, "_connected", lambda: [])
    monkeypatch.setattr(library, "_alias", lambda guid, default: default)
    before = shared_state.current_profile
    shared_state.current_profile = None
    yield folder
    shared_state.current_profile = before


def _write(folder: Path, slug: str, name: str, guid: str) -> None:
    doc = {"kind": "control.hardware", "device": name, "nodes": [], "claim": {}}
    if guid:
        doc["boundGuidLocal"] = guid
    module_file.write_bytes(folder / f"{slug}.json", json.dumps(doc).encode("utf-8"))


def _by_slug(slug: str) -> registry.Module:
    return next(m for m in registry.modules() if m.slug == slug)


def test_built_in_inputs_by_id_and_by_name(modules: Path) -> None:
    _write(modules, "keyboard", "Keyboard", KEYBOARD_GUID)
    _write(modules, "osc", "OSC", OSC_GUID)
    _write(modules, "keys_unbound", "Keyboard", "")
    _write(modules, "stick_a", "Stick A", STICK_GUID)
    # A stick that Windows names "Keyboard" is still a stick: its id decides.
    other = "{11111111-2222-3333-4444-555555555555}"
    _write(modules, "keyboard_stick", "Keyboard", other)
    assert registry.is_built_in_input(_by_slug("keyboard"))
    assert registry.is_built_in_input(_by_slug("osc"))
    assert registry.is_built_in_input(_by_slug("keys_unbound"))
    assert not registry.is_built_in_input(_by_slug("stick_a"))
    assert not registry.is_built_in_input(_by_slug("keyboard_stick"))


def test_library_lists_sticks_not_keyboard_or_osc(modules: Path) -> None:
    _write(modules, "keyboard", "Keyboard", KEYBOARD_GUID)
    _write(modules, "osc", "OSC", OSC_GUID)
    _write(modules, "stick_a", "Stick A", STICK_GUID)
    names = [row["name"] for row in library.devices()]
    assert "Stick A" in names
    assert "Keyboard" not in names
    assert "OSC" not in names
