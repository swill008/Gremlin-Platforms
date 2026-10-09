# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Profiles and the Logical Device's own module file (D-04-LD-FILE, 04 S2,
S25, R3): version 14 profiles have their rows moved into the file (match by
type, number and label, else added), references repointed by uid, a backup
kept, and are saved as version 16 (15 before D-09-OSC-FILE) without a
<logical-device> section; a profile only read (bind=False) changes nothing
until it is saved."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from xml.etree import ElementTree

import pytest

from gremlin import error, history_modules, shared_state
from gremlin import logical_device_file as ldf
from gremlin.logical_device import LogicalDevice
from gremlin.modules import store
from gremlin.profile import Profile
from gremlin.types import InputType

_FIRE = "a" * 32


@pytest.fixture
def modules(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    """The module files in a temp folder; the Logical Device put back after."""
    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    monkeypatch.setattr(store, "folder", lambda: folder)
    monkeypatch.setattr(store, "_saved", lambda: None)
    monkeypatch.setattr(history_modules, "note_write", lambda *a, **k: None)
    # Actions made while reading (Change Mode) look at the open profile.
    monkeypatch.setattr(shared_state, "current_profile", Profile())
    shown = LogicalDevice()
    kept = shown.to_dict()
    yield folder
    shown.load_dict(kept)
    ldf.current_uid_map = None


def _file_layout(controls: list[dict]) -> None:
    """The Logical Device file (and the shown rows) hold these controls."""
    LogicalDevice().load_dict({"controls": controls, "groups": []})
    ldf.save()


def _button(uid: str, number: int, label: str) -> dict:
    return {
        "uid": uid,
        "type": "button",
        "id": number,
        "label": label,
        "user-label": "",
        "group": "",
        "hide-system": False,
    }


def _v14(xml_dir: Path) -> Path:
    """A version 14 profile: Logical Device Button 1 ("Button 1") and a Map
    to Logical Device action pointing at it (no uid, old data)."""
    path = xml_dir / "profile_for_analysis.xml"
    root = ElementTree.parse(path).getroot()
    assert root.get("version") == "14"
    assert root.find("logical-device/input") is not None
    return path


def _map_action(path: Path) -> ElementTree.Element:
    root = ElementTree.parse(path).getroot()
    found = root.findall(".//action[@type='map-to-logical-device']")
    assert len(found) == 1
    return found[0]


def _prop(action: ElementTree.Element, name: str) -> str | None:
    for node in action.findall("property"):
        if node.findtext("name") == name:
            return (node.findtext("value") or "").strip()
    return None


def test_v14_rows_added_to_file_refs_repointed_backup_saved_as_15(
    modules: Path, xml_dir: Path
) -> None:
    # The file's Button 1 is another control: the profile's is added as 2.
    _file_layout([_button(_FIRE, 1, "Fire")])
    path = _v14(xml_dir)
    original = path.read_bytes()

    profile = Profile()
    profile.from_xml(path)

    shown = LogicalDevice()
    assert shown.uid_of(InputType.JoystickButton, 1) == _FIRE
    added = shown.uid_of(InputType.JoystickButton, 2)
    assert added and added != _FIRE
    labels = sorted(c["label"] for c in ldf.read_layout()["controls"])
    assert labels == ["Button 1", "Fire"]
    assert profile.logical_migration_note == ["Button 1"]
    assert ldf.current_uid_map is None
    backup = path.with_name(path.name + ".v14.bak")
    # Opening writes nothing beside the profile; the first save backs it up.
    assert not backup.exists()
    assert profile.has_unsaved_changes()

    profile.to_xml(path)
    root = ElementTree.parse(path).getroot()
    assert root.get("version") == "16"
    assert root.find("logical-device") is None
    action = _map_action(path)
    assert _prop(action, "logical-input-uid") == added
    assert _prop(action, "logical-input-id") == "2"
    assert backup.read_bytes() == original
    assert not profile.has_unsaved_changes()

    # Read again as version 16: the reference still finds the added control.
    again = Profile()
    again.from_xml(path)
    assert again.logical_migration_note == []
    assert not again.has_unsaved_changes()


def test_v14_matching_control_reuses_file_uid(modules: Path, xml_dir: Path) -> None:
    same = "b" * 32
    _file_layout([_button(same, 1, "Button 1")])
    path = _v14(xml_dir)

    profile = Profile()
    profile.from_xml(path)

    assert profile.logical_migration_note == []
    assert len(ldf.read_layout()["controls"]) == 1
    profile.to_xml(path)
    assert _prop(_map_action(path), "logical-input-uid") == same


def test_v14_read_without_opening_changes_nothing_until_saved(
    modules: Path, xml_dir: Path
) -> None:
    _file_layout([_button(_FIRE, 1, "Fire")])
    path = _v14(xml_dir)
    before = ldf.read_layout()

    read = Profile(bind=False)
    read.from_xml(path)

    assert ldf.read_layout() == before
    assert LogicalDevice().uid_of(InputType.JoystickButton, 2) is None
    assert read.pending_logical_rows is not None
    assert not path.with_name(path.name + ".v14.bak").exists()

    read.to_xml(path)
    assert path.with_name(path.name + ".v14.bak").exists()
    added = LogicalDevice().uid_of(InputType.JoystickButton, 2)
    assert added
    assert any(c["uid"] == added for c in ldf.read_layout()["controls"])
    assert _prop(_map_action(path), "logical-input-uid") == added
    assert ElementTree.parse(path).getroot().get("version") == "16"


def test_other_versions_refused(modules: Path, tmp_path: Path) -> None:
    bad = tmp_path / "old.xml"
    bad.write_text("<profile version='13'><inputs/></profile>", encoding="utf-8")
    with pytest.raises(error.ProfileError, match="14 and 15"):
        Profile().from_xml(bad)


def test_logical_device_edits_count_as_unsaved_and_save_writes_file(
    modules: Path, tmp_path: Path
) -> None:
    _file_layout([])
    profile = Profile()
    profile.mark_clean()
    assert not profile.has_unsaved_changes()
    LogicalDevice().create(InputType.JoystickButton)
    assert profile.has_unsaved_changes()
    assert profile.looks_unsaved()
    profile.to_xml(tmp_path / "p.xml")
    assert not LogicalDevice().dirty
    assert len(ldf.read_layout()["controls"]) == 1
    assert not profile.has_unsaved_changes()


def test_library_change_rollback_restores_logical_rows(modules: Path) -> None:
    _file_layout([_button(_FIRE, 1, "Fire")])
    profile = Profile()
    with pytest.raises(RuntimeError), profile.library.change():
        LogicalDevice().create(InputType.JoystickButton)
        raise RuntimeError("undo")
    assert [c["uid"] for c in LogicalDevice().to_dict()["controls"]] == [_FIRE]
    assert not LogicalDevice().dirty


def test_history_has_no_logical_device_section() -> None:
    from gremlin import history_profile

    assert "logical-device" not in history_profile.SECTIONS
