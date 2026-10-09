# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Device Library lists the built-in inputs, Keyboard and OSC, after the
devices, flagged, and refuses Remove, Delete Saved Setups, Copy, Swap and
Change vJoy Output on them (10 S6, D-10-BUILTIN-SECTION). The real store in a
temporary modules folder holding a keyboard, an OSC and stick module files."""

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


def _three(modules: Path) -> dict[str, dict]:
    _write(modules, "keyboard", "Keyboard", KEYBOARD_GUID)
    _write(modules, "osc", "OSC", OSC_GUID)
    _write(modules, "stick_a", "Stick A", STICK_GUID)
    _write(modules, "zed", "Zed Stick", "{22222222-2222-3333-4444-555555555555}")
    return {row["name"]: row for row in library.devices()}


def test_built_ins_listed_last_and_flagged(modules: Path) -> None:
    rows = _three(modules)
    names = [row["name"] for row in library.devices()]
    # Devices first by name, then the built-ins, though "Keyboard" < "Stick A".
    assert names[:2] == ["Stick A", "Zed Stick"]
    assert sorted(names[2:]) == ["Keyboard", "OSC"]
    for name in ("Keyboard", "OSC"):
        assert rows[name]["builtIn"] is True
        assert rows[name]["state"] == "builtin"
    for name in ("Stick A", "Zed Stick"):
        assert rows[name]["builtIn"] is False
        assert rows[name]["state"] == "not_connected"


def test_built_ins_refuse_remove_and_delete(modules: Path) -> None:
    key = _three(modules)["Keyboard"]["key"]
    for answer in (
        library.removal_plan(key),
        library.remove_device(key),
        library.delete_saved_setups(key),
        library.delete(key),
    ):
        assert answer["ok"] is False
        assert "built-in input" in answer["error"]
    assert (modules / "keyboard.json").exists()
    assert library.device(key) is not None


def test_built_ins_refuse_copy_swap_and_change_output(modules: Path) -> None:
    from gremlin import library_copy, library_swap

    rows = _three(modules)
    kb, stick = rows["Keyboard"], rows["Stick A"]
    from_kb = library_copy.plan_copy(
        kb["key"], "Stick A", STICK_GUID, ["module"], [], []
    )
    assert from_kb["ok"] is False and "built-in input" in from_kb["error"]
    onto_kb = library_copy.copy(stick["key"], "OSC", OSC_GUID, ["module"], [], [])
    assert onto_kb["ok"] is False and "built-in input" in onto_kb["error"]
    for call in (library_copy.plan_output, library_copy.change_output):
        answer = call("Keyboard", KEYBOARD_GUID, {1: 2}, False, [modules / "p.xml"])
        assert answer["ok"] is False and "built-in input" in answer["error"]
    swap = library_swap.plan_swap(("OSC", OSC_GUID), ("Stick A", STICK_GUID), [], [])
    assert swap["ok"] is False


def test_built_ins_take_a_description(modules: Path) -> None:
    key = _three(modules)["OSC"]["key"]
    assert library.describe(key, "Touch panel")["ok"] is True
    assert library.device(key)["description"] == "Touch panel"
