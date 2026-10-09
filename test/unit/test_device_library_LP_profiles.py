# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device Library: profiles that aren't open (10 S33-S34).

profiles_using finds the open profile and the saved ones (profiles folder,
Recent list) with bindings for a device. A Batch changes the open profile in
memory (left unsaved, 08 S74) and the saved ones on disk (a History entry
each); one that can't be read or written is named and left exactly as it
was, the rest still change; a change that raises leaves that file, or the
open profile, as it was.
"""

from __future__ import annotations

import os
import stat
import time
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

from gremlin import history, library_profiles, shared_state, util
from gremlin.logical_device import LogicalDevice
from gremlin.profile import DeviceInfo, Profile
from gremlin.types import InputType

_STICK = uuid.UUID("33333333-4444-5555-6666-777777777777")
_OTHER = uuid.UUID("88888888-4444-5555-6666-777777777777")


def _settle() -> list[dict]:
    deadline = time.monotonic() + 5
    while history._writer is not None and time.monotonic() < deadline:
        time.sleep(0.02)
    return history.entries()


@pytest.fixture
def folders(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[dict]:
    store = tmp_path / "history"
    monkeypatch.setattr(history, "folder", lambda: store)
    monkeypatch.setattr(history, "_pruned", True)
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.setattr(util, "profiles_dir", lambda: profiles)
    recent: list[str] = []
    monkeypatch.setattr(library_profiles, "_recent", lambda: list(recent))
    yield {"profiles": profiles, "elsewhere": elsewhere, "recent": recent}
    _settle()
    shared_state.current_profile = None


def _map(profile: Profile, device: uuid.UUID, button: int, out: int) -> None:
    action = profile.library.create("Map to vJoy", InputType.JoystickButton)
    assert action is not None
    action.vjoy_device_id = 1
    action.vjoy_input_id = out
    action.vjoy_input_type = InputType.JoystickButton
    item = profile.get_input_item(
        device, InputType.JoystickButton, button, "Default", create_if_missing=True
    )
    item.add_item_binding().root_action.insert_action(action, "children")


def _saved(path: Path, device: uuid.UUID, buttons: int) -> Path:
    # A file on disk, not the open profile: never shown (Profile(bind=False)).
    made = Profile(bind=False)
    made.device_database.devices[device] = DeviceInfo(device, "Test Stick")
    for button in range(1, buttons + 1):
        _map(made, device, button, button)
    made.to_xml(path)
    return path


def _open(path: Path | None, buttons: int = 1) -> Profile:
    made = Profile()
    made.device_database.devices[_STICK] = DeviceInfo(_STICK, "Test Stick")
    for button in range(1, buttons + 1):
        _map(made, _STICK, button, button)
    if path is not None:
        made.to_xml(path)
        made.fpath = path  # as Save Profile leaves it
    shared_state.current_profile = made
    made.bind_devices()
    return made


def _add_button(profile: Profile, is_open: bool) -> dict:
    _map(profile, _STICK, 9, 9)
    return {"notes": [f"added ({'open' if is_open else 'saved'})"]}


def test_profiles_using_lists_open_saved_and_recent(folders: dict) -> None:
    profiles, elsewhere = folders["profiles"], folders["elsewhere"]
    _open(profiles / "open.xml", buttons=2)
    _saved(profiles / "saved.xml", _STICK, 3)
    _saved(profiles / "other.xml", _OTHER, 2)
    (profiles / "damaged.xml").write_text("<profile", encoding="utf-8")
    recent = _saved(elsewhere / "recent.xml", _STICK, 1)
    folders["recent"].extend([str(recent), str(elsewhere / "gone.xml")])

    rows = library_profiles.profiles_using([f"{{{_STICK}}}".upper()])

    assert [(r["name"], r["open"], r["actions"]) for r in rows] == [
        ("open", True, 2),
        ("saved", False, 3),
        ("recent", False, 1),
    ]
    assert rows[1]["path"] == str(profiles / "saved.xml")
    assert library_profiles.profiles_using([]) == []


def test_profiles_using_sees_the_open_profile_as_it_is_in_memory(
    folders: dict,
) -> None:
    current = _open(folders["profiles"] / "open.xml", buttons=1)
    _map(current, _STICK, 5, 5)  # not saved yet
    rows = library_profiles.profiles_using([str(_STICK)])
    assert rows == [
        {"path": str(folders["profiles"] / "open.xml"), "name": "open",
         "open": True, "actions": 2}
    ]


def test_read_profile_reasons_and_shared_logical_device_kept(folders: dict) -> None:
    profiles = folders["profiles"]
    _open(None)
    before = LogicalDevice().to_dict()
    try:
        LogicalDevice().load_dict({"controls": [], "groups": []})
        LogicalDevice().create(InputType.JoystickButton, label="Fire")
        LogicalDevice().mark_saved()
        shown = LogicalDevice().to_dict()
        missing = library_profiles.read_profile(profiles / "gone.xml")
        assert isinstance(missing, str) and "gone.xml" in missing
        (profiles / "damaged.xml").write_text("<profile", encoding="utf-8")
        damaged = library_profiles.read_profile(profiles / "damaged.xml")
        assert isinstance(damaged, str) and "damaged.xml" in damaged
        good = library_profiles.read_profile(_saved(profiles / "good.xml", _STICK, 2))
        assert isinstance(good, Profile)
        assert len(good.inputs[_STICK]) == 2
        # A version 14 profile with rows of its own: read, not merged.
        old = profiles / "old.xml"
        text = (profiles / "good.xml").read_text(encoding="utf-8-sig")
        text = text.replace('version="16"', 'version="14"', 1).replace(
            "</profile>",
            "<logical-device><input><input-type>button</input-type>"
            "<input-id>5</input-id><label>Old</label></input></logical-device>"
            "</profile>",
        )
        old.write_text(text, encoding="utf-8")
        older = library_profiles.read_profile(old)
        assert isinstance(older, Profile), older
        assert older.pending_logical_rows is not None
        assert not old.with_name("old.xml.v14.bak").exists()
        # Reading other profiles doesn't change the shared Logical Device
        # (one layout in its own module file, D-04-LD-FILE).
        assert LogicalDevice().to_dict() == shown
        assert LogicalDevice().dirty is False
    finally:
        LogicalDevice().load_dict(before)


def test_batch_changes_each_and_names_the_ones_it_cant(folders: dict) -> None:
    profiles = folders["profiles"]
    current = _open(profiles / "open.xml")
    open_bytes = (profiles / "open.xml").read_bytes()
    good = _saved(profiles / "good.xml", _STICK, 1)
    damaged = profiles / "damaged.xml"
    damaged.write_text("<profile", encoding="utf-8")
    locked = _saved(profiles / "locked.xml", _STICK, 1)
    known = {e["id"] for e in _settle()}
    before = {p: p.read_bytes() for p in (damaged, locked)}
    os.chmod(locked, stat.S_IREAD)
    try:
        result = library_profiles.Batch(
            [profiles / "open.xml", good, damaged, locked, good], "Copy"
        ).apply(_add_button)
    finally:
        os.chmod(locked, stat.S_IREAD | stat.S_IWRITE)

    assert result["ok"] is True
    assert result["changed"] == [str(profiles / "open.xml"), str(good)]
    assert result["failed"] == [str(damaged), str(locked)]
    assert any("damaged.xml" in w for w in result["warnings"])
    assert any("locked.xml" in w for w in result["warnings"])
    assert result["notes"] == ["added (open)", "added (saved)"]
    # Left exactly as they were.
    for path, data in before.items():
        assert path.read_bytes() == data
    # The open profile: changed in memory, unsaved, its file untouched.
    assert len(current.inputs[_STICK]) == 2
    assert current.has_unsaved_changes()
    assert (profiles / "open.xml").read_bytes() == open_bytes
    # The saved one: changed on disk, with a History entry.
    reread = library_profiles.read_profile(good)
    assert isinstance(reread, Profile) and len(reread.inputs[_STICK]) == 2
    titles = [
        e["title"]
        for e in _settle()
        if e["kind"] == "profile" and e["id"] not in known
    ]
    assert titles == ["Saved good.xml (1 input)"]


def test_a_change_that_raises_leaves_the_file_as_it_was(folders: dict) -> None:
    profiles = folders["profiles"]
    _open(None)
    first = _saved(profiles / "first.xml", _STICK, 1)
    second = _saved(profiles / "second.xml", _STICK, 1)
    data = first.read_bytes()

    def change(profile: Profile, is_open: bool) -> dict:
        _map(profile, _STICK, 9, 9)
        if profile.fpath == first:
            raise ValueError("broken halfway")
        return {}

    result = library_profiles.Batch([first, second], "Swap").apply(change)
    assert result["ok"] is True
    assert result["failed"] == [str(first)]
    assert any("first.xml" in w and "broken halfway" in w for w in result["warnings"])
    assert first.read_bytes() == data
    assert result["changed"] == [str(second)]


def test_a_change_that_raises_leaves_the_open_profile_as_it_was(
    folders: dict,
) -> None:
    current = _open(folders["profiles"] / "open.xml", buttons=2)
    before = current._xml_text()

    def change(profile: Profile, is_open: bool) -> dict:
        # An edit in place (an existing action renumbered), then an added
        # input, then a failure.
        for item in profile.inputs[_STICK]:
            for action in Profile.roots_of([item])[0].get_actions()[0]:
                action.vjoy_device_id = 2
        _map(profile, _STICK, 9, 9)
        raise RuntimeError("no")

    result = library_profiles.Batch(
        [folders["profiles"] / "open.xml"], "Change vJoy Output"
    ).apply(change)
    assert result["ok"] is False
    assert result["changed"] == []
    assert any("(open)" in w and "no" in w for w in result["warnings"])
    assert current._xml_text() == before
    assert not current.has_unsaved_changes()


def test_a_refused_change_counts_as_failed(folders: dict) -> None:
    profiles = folders["profiles"]
    current = _open(None)
    saved = _saved(profiles / "saved.xml", _STICK, 1)
    data = saved.read_bytes()
    before = current._xml_text()

    def change(profile: Profile, is_open: bool) -> dict:
        _map(profile, _STICK, 9, 9)
        return {"ok": False, "error": "lacks button 9"}

    # The unsaved open profile is the empty path.
    result = library_profiles.Batch([Path(""), saved], "Copy").apply(change)
    assert result["ok"] is False
    assert len(result["failed"]) == 2
    assert all("lacks button 9" in w for w in result["warnings"])
    assert saved.read_bytes() == data
    assert current._xml_text() == before
