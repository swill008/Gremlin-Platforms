# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""10 Device Library, the fix wave (agent FM): Copy, Swap and Change vJoy
Output always offer the open profile, ticked, even with no bindings for
the sticks (S23, 08 S89, D-10-PROFILES), e.g. a deleted stick's "stick
deleted" autosave copied onto a new stick. The open profile and the saved
ones can be listed apart (the open one on the main thread, the saved ones
in the background)."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

from gremlin import history, library_profiles, shared_state, util
from gremlin.profile import DeviceInfo, Profile
from gremlin.types import InputType

_DELETED = uuid.UUID("33333333-4444-5555-6666-777777777777")
_NEW = uuid.UUID("88888888-4444-5555-6666-777777777777")
_OTHER = uuid.UUID("99999999-4444-5555-6666-777777777777")


@pytest.fixture
def folders(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    monkeypatch.setattr(history, "folder", lambda: tmp_path / "history")
    monkeypatch.setattr(history, "_pruned", True)
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    monkeypatch.setattr(util, "profiles_dir", lambda: profiles)
    monkeypatch.setattr(library_profiles, "_recent", lambda: [])
    yield profiles
    shared_state.current_profile = None


def _map(profile: Profile, device: uuid.UUID, button: int) -> None:
    action = profile.library.create("Map to vJoy", InputType.JoystickButton)
    assert action is not None
    action.vjoy_device_id = 1
    action.vjoy_input_id = button
    action.vjoy_input_type = InputType.JoystickButton
    item = profile.get_input_item(
        device, InputType.JoystickButton, button, "Default", create_if_missing=True
    )
    item.add_item_binding().root_action.insert_action(action, "children")


def _open(path: Path | None) -> Profile:
    # Delete Device took the deleted stick's bindings out (03 S92); only
    # another stick has bindings in it.
    made = Profile()
    made.device_database.devices[_OTHER] = DeviceInfo(_OTHER, "Other")
    _map(made, _OTHER, 1)
    if path is not None:
        made.to_xml(path)
        made.fpath = path
    shared_state.current_profile = made
    made.bind_devices()
    return made


def _guids() -> list[str]:
    return [str(_DELETED), str(_NEW)]


def test_the_open_profile_is_offered_with_no_bindings_for_the_sticks(
    folders: Path,
) -> None:
    _open(folders / "open.xml")
    assert library_profiles.profiles_using(_guids()) == []
    rows = library_profiles.profiles_using(_guids(), always_open=True)
    assert rows == [
        {"path": str(folders / "open.xml"), "name": "open", "open": True, "actions": 0}
    ]


def test_the_never_saved_open_profile_is_offered_too(folders: Path) -> None:
    _open(None)
    rows = library_profiles.profiles_using(_guids(), always_open=True)
    assert rows == [{"path": "", "name": "Untitled", "open": True, "actions": 0}]
    assert library_profiles.open_profile_row(_guids()) is None
    assert library_profiles.open_profile_row(_guids(), True) == rows[0]


def test_saved_profiles_are_listed_apart_leaving_out_the_open_one(
    folders: Path,
) -> None:
    _open(folders / "open.xml")
    saved = Profile(bind=False)
    saved.device_database.devices[_NEW] = DeviceInfo(_NEW, "New")
    _map(saved, _NEW, 2)
    saved.to_xml(folders / "saved.xml")
    # The open file on disk is the open profile's: never listed twice.
    found = library_profiles.saved_profiles_using(
        [str(_OTHER), str(_NEW)], str(folders / "open.xml")
    )
    assert [(r["name"], r["open"]) for r in found] == [("saved", False)]
    assert library_profiles.is_open_path(folders / "open.xml")
    assert not library_profiles.is_open_path(folders / "saved.xml")
    rows = library_profiles.profiles_using(_guids(), always_open=True)
    assert [(r["name"], r["open"], r["actions"]) for r in rows] == [
        ("open", True, 0),
        ("saved", False, 1),
    ]


def test_no_open_profile_nothing_to_offer(folders: Path) -> None:
    shared_state.current_profile = None
    assert library_profiles.profiles_using(_guids(), always_open=True) == []
