# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Device Library, Copy and Swap ask the device classes (03 S90b) and give
the same answers as before: Keyboard and OSC are its built-in inputs (10 S6),
Swap refuses the Keyboard, the Logical Device, OSC and the Xbox pad with the
same words (S26, S29), and a stick that Windows names "Keyboard" with its own
id is a normal device that can be copied (S22)."""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

import dill
from gremlin import device_library as library
from gremlin import library_copy, library_swap, shared_state, swap_devices
from gremlin.modules import ids, module_file, store

KEYBOARD_STICK = "{11111111-2222-3333-4444-555555555555}"
STICK_GUID = "{6C3D1E20-1111-2222-3333-444455556666}"
OTHER = uuid.UUID("22222222-2222-3333-4444-555555555555")


def test_built_in_guid_is_keyboard_osc_and_logical_device() -> None:
    assert library.is_built_in_guid(str(ids.KEYBOARD))
    assert library.is_built_in_guid("{" + str(ids.OSC).upper() + "}")
    # The Logical Device has its own module file (03 S90b, D-04-LD-FILE).
    assert library.is_built_in_guid(str(ids.LOGICAL_DEVICE))
    assert not library.is_built_in_guid(str(ids.XBOX))
    assert not library.is_built_in_guid(KEYBOARD_STICK)
    assert not library.is_built_in_guid("")


@pytest.mark.parametrize(
    ("ident", "words"),
    [
        (ids.KEYBOARD, "the Keyboard"),
        (ids.LOGICAL_DEVICE, "the Logical Device"),
        (ids.OSC, "OSC"),
        (ids.XBOX, "the Xbox controller"),
    ],
)
def test_swap_refuses_non_sticks_with_the_same_words(
    ident: uuid.UUID, words: str
) -> None:
    answer = library_swap._refusal(("X", str(ident)), ("Stick A", STICK_GUID))
    assert answer == f"Swap can't be used with {words}."
    assert swap_devices.not_swappable(ident)


def test_swap_takes_a_stick_named_keyboard() -> None:
    assert not swap_devices.not_swappable(uuid.UUID(KEYBOARD_STICK))
    assert not swap_devices.not_swappable(OTHER)


def test_copy_skips_internal_inputs_and_placeholders_only() -> None:
    for uid in (
        ids.KEYBOARD,
        ids.OSC,
        ids.LOGICAL_DEVICE,
        dill.UUID_Invalid,
        dill.UUID_Virtual,
    ):
        assert library_copy._special(uid)
    assert not library_copy._special(ids.XBOX)
    assert not library_copy._special(uuid.UUID(KEYBOARD_STICK))


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


def test_stick_named_keyboard_is_a_normal_library_device(modules: Path) -> None:
    _write(modules, "keyboard_stick", "Keyboard", KEYBOARD_STICK)
    _write(modules, "stick_a", "Stick A", STICK_GUID)
    rows = {row["name"]: row for row in library.devices()}
    assert rows["Keyboard"]["builtIn"] is False
    assert rows["Keyboard"]["state"] != "builtin"
    # Copy from it and onto it: never refused as a built-in input; it is
    # refused only because nothing is plugged in here.
    for source, name, guid in (
        (rows["Keyboard"]["key"], "Stick A", STICK_GUID),
        (rows["Stick A"]["key"], "Keyboard", KEYBOARD_STICK),
    ):
        answer = library_copy.plan_copy(source, name, guid, ["module"], [], [])
        assert answer["ok"] is False
        assert "built-in input" not in answer["error"]
        assert "isn't plugged in" in answer["error"]
