# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import pathlib
from xml.etree import ElementTree

from gremlin.profile import Profile


def _compact_copy(source: pathlib.Path, target: pathlib.Path) -> pathlib.Path:
    # Same content, different bytes (no pretty printing), like a file written by
    # an older version that the current one would write differently.
    target.write_bytes(ElementTree.tostring(ElementTree.parse(source).getroot()))
    return target


def test_freshly_loaded_older_file_is_not_unsaved(
    xml_dir: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    path = _compact_copy(xml_dir / "profile_simple.xml", tmp_path / "old.xml")
    profile = Profile()
    profile.from_xml(path)
    assert not profile.has_unsaved_changes()


def test_an_edit_is_unsaved_until_saved(
    xml_dir: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    path = _compact_copy(xml_dir / "profile_simple.xml", tmp_path / "old.xml")
    profile = Profile()
    profile.from_xml(path)
    profile.modes.add_mode("Flight")
    assert profile.has_unsaved_changes()
    profile.to_xml(path)
    assert not profile.has_unsaved_changes()


def test_a_new_profile_counts_as_unsaved() -> None:
    assert Profile().has_unsaved_changes()


def test_a_new_profile_marked_clean_has_nothing_to_lose() -> None:
    profile = Profile()
    profile.mark_clean()
    assert not profile.has_unsaved_changes()
    profile.modes.add_mode("Combat")
    assert profile.has_unsaved_changes()
