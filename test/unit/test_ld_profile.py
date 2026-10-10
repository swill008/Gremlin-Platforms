# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Profiles and the Logical Device's own module file (D-04-LD-FILE, 04 S2,
R3): Logical Device edits count as unsaved and Save writes the file; only
versions 14 to 16 are read (a version 14 profile's own rows are not,
D-04-LD-NOLEGACY: test_ld_nolegacy)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

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
