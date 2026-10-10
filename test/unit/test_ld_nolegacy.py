# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""No converter for version 14 Logical Device rows (04 S25,
D-04-LD-NOLEGACY): a version 14 profile's <logical-device> is not read or
merged into logical_device.json, no .v14.bak is written, no note is given,
and its Logical Device bindings resolve by permanent id, else by type and
number."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from xml.etree import ElementTree

import pytest

from gremlin import history_modules, shared_state
from gremlin import logical_device_file as ldf
from gremlin.logical_device import LogicalDevice
from gremlin.modules import store
from gremlin.profile import Profile
from gremlin.types import InputType

_FIRE = "a" * 32


@pytest.fixture
def modules(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    """The module files in a temp folder holding Button 1 "Fire"; the
    Logical Device put back after."""
    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    monkeypatch.setattr(store, "folder", lambda: folder)
    monkeypatch.setattr(store, "_saved", lambda: None)
    monkeypatch.setattr(history_modules, "note_write", lambda *a, **k: None)
    monkeypatch.setattr(shared_state, "current_profile", Profile())
    shown = LogicalDevice()
    kept = shown.to_dict()
    fire = {
        "uid": _FIRE,
        "type": "button",
        "id": 1,
        "label": "Fire",
        "user-label": "",
        "group": "",
        "hide-system": False,
    }
    shown.load_dict({"controls": [fire], "groups": []})
    ldf.save()
    yield folder
    shown.load_dict(kept)
    shown.mark_saved()


_V14_ROWS = (
    "<logical-device><input><input-type>button</input-type>"
    "<input-id>1</input-id><label>Button 1</label></input></logical-device>"
)


def as_v14(source: Path, target: Path) -> Path:
    """source (a version 16 profile) written to target as version 14 with
    its own Logical Device Button 1 ("Button 1"), as older files had."""
    text = source.read_text(encoding="utf-8-sig")
    text = text.replace('version="16"', 'version="14"', 1)
    text = text.replace("</settings>", "</settings>" + _V14_ROWS, 1)
    target.write_text(text, encoding="utf-8")
    return target


def _v14(xml_dir: Path) -> Path:
    """A version 14 profile with Logical Device Button 1 ("Button 1") and a
    Map to Logical Device action on button 1 without a uid."""
    path = as_v14(xml_dir / "profile_for_analysis.xml", xml_dir / "old_v14.xml")
    root = ElementTree.parse(path).getroot()
    assert root.get("version") == "14"
    assert root.find("logical-device/input") is not None
    return path


def _uid_of_action(path: Path) -> str | None:
    root = ElementTree.parse(path).getroot()
    (action,) = root.findall(".//action[@type='map-to-logical-device']")
    for node in action.findall("property"):
        if node.findtext("name") == "logical-input-uid":
            return (node.findtext("value") or "").strip()
    return None


def test_opening_a_v14_profile_adds_nothing_and_resolves_by_number(
    modules: Path, xml_dir: Path
) -> None:
    before = ldf.read_layout()
    path = _v14(xml_dir)

    profile = Profile()
    profile.from_xml(path)

    assert ldf.read_layout() == before
    assert LogicalDevice().uid_of(InputType.JoystickButton, 2) is None
    assert not getattr(profile, "logical_migration_note", None)

    profile.to_xml(path)
    assert not path.with_name(path.name + ".v14.bak").exists()
    root = ElementTree.parse(path).getroot()
    assert root.get("version") == "16"
    assert root.find("logical-device") is None
    # Button 1 had no uid: it is the file's Button 1 by type and number.
    assert _uid_of_action(path) == _FIRE
    assert ldf.read_layout() == before


def test_reading_a_v14_profile_without_opening_keeps_nothing_pending(
    modules: Path, xml_dir: Path
) -> None:
    before = ldf.read_layout()
    path = _v14(xml_dir)

    read = Profile(bind=False)
    read.from_xml(path)
    assert getattr(read, "pending_logical_rows", None) is None

    read.to_xml(path)
    assert not path.with_name(path.name + ".v14.bak").exists()
    assert ldf.read_layout() == before
    assert _uid_of_action(path) == _FIRE


def test_the_converters_are_gone() -> None:
    for name in ("merge_profile_rows", "merge_layout", "backup_v14",
                 "current_uid_map", "MergeResult"):
        assert not hasattr(ldf, name), name
    from gremlin.ui import backend

    assert not hasattr(backend, "migration_notes")
    assert not hasattr(backend, "logical_migration_text")


def test_copy_and_swap_save_a_v14_profile_without_its_rows(
    modules: Path, xml_dir: Path
) -> None:
    """The Device Library reads and saves a profile that isn't open
    (library_profiles): its version 14 rows add nothing either."""
    from gremlin import library_profiles

    before = ldf.read_layout()
    path = _v14(xml_dir)
    read = library_profiles.read_profile(path)
    assert isinstance(read, Profile), read
    library_profiles.save_profile(read, path)
    assert ldf.read_layout() == before
    assert not path.with_name(path.name + ".v14.bak").exists()
    assert ElementTree.parse(path).getroot().get("version") == "16"
    assert _uid_of_action(path) == _FIRE
