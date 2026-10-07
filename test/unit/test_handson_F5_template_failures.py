# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A failed template export or rename names the file, the folder and the
reason, as in Q19 (07 S80, decision D-07-TEMPLATE-FAIL)."""

from __future__ import annotations

import sys

sys.path.append(".")

import json
import os
import pathlib
import stat
from collections.abc import Iterator

import pytest
from PySide6 import QtCore

from gremlin.modules import store
from gremlin.ui import hardware_profile

NODES = json.dumps([{"id": "b1", "kind": "btn", "hwId": 1}])
_ROOT = pathlib.Path(__file__).resolve().parents[2]
_QML = _ROOT / "qml" / "DialogJoystickButtonMap.qml"


@pytest.fixture
def profile(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> hardware_profile.HardwareProfile:
    monkeypatch.setattr(store, "folder", lambda: tmp_path / "maps")
    return hardware_profile.HardwareProfile()


@pytest.fixture
def read_only() -> Iterator[list[pathlib.Path]]:
    """Files made read-only for a test, writable again after it."""
    made: list[pathlib.Path] = []
    yield made
    for path in made:
        if path.exists():
            os.chmod(path, stat.S_IWRITE | stat.S_IREAD)


def _url(path: pathlib.Path) -> str:
    return QtCore.QUrl.fromLocalFile(str(path)).toString()


def test_export_to_a_missing_folder_names_file_folder_and_reason(
    profile: hardware_profile.HardwareProfile, tmp_path: pathlib.Path
) -> None:
    profile.saveTemplate("Shared", NODES, "x")
    out = tmp_path / "nowhere" / "shared.json"
    assert not profile.exportTemplate("Shared", _url(out))
    assert profile.templateError() == (
        f"Export failed. shared.json could not be written to {out.parent}: "
        "the folder does not exist."
    )


def test_export_over_a_read_only_file_says_so(
    profile: hardware_profile.HardwareProfile,
    tmp_path: pathlib.Path,
    read_only: list[pathlib.Path],
) -> None:
    profile.saveTemplate("Shared", NODES, "x")
    out = tmp_path / "shared.json"
    out.write_text("{}", encoding="utf-8")
    os.chmod(out, stat.S_IREAD)
    read_only.append(out)
    assert not profile.exportTemplate("Shared", _url(out))
    assert profile.templateError() == (
        f"Export failed. shared.json could not be written to {tmp_path}: "
        "the file is read-only or open in another program."
    )


def test_an_export_that_worked_leaves_no_error(
    profile: hardware_profile.HardwareProfile, tmp_path: pathlib.Path
) -> None:
    profile.saveTemplate("Shared", NODES, "x")
    assert not profile.exportTemplate("Shared", _url(tmp_path / "no" / "a.json"))
    assert profile.exportTemplate("Shared", _url(tmp_path / "a.json"))
    assert profile.templateError() == ""


def test_rename_to_a_taken_name_names_the_file_and_folder(
    profile: hardware_profile.HardwareProfile, tmp_path: pathlib.Path
) -> None:
    profile.saveTemplate("One", NODES, "x")
    profile.saveTemplate("Two", NODES, "x")
    assert not profile.renameTemplate("One", "Two")
    folder = tmp_path / "maps" / "templates"
    assert profile.templateError() == (
        f"Rename failed. Two.json could not be written to {folder}: "
        "a template already has that name."
    )


def test_rename_of_a_read_only_template_names_it_and_keeps_one_copy(
    profile: hardware_profile.HardwareProfile,
    tmp_path: pathlib.Path,
    read_only: list[pathlib.Path],
) -> None:
    profile.saveTemplate("One", NODES, "x")
    folder = tmp_path / "maps" / "templates"
    old = folder / "One.json"
    os.chmod(old, stat.S_IREAD)
    read_only.append(old)
    assert not profile.renameTemplate("One", "Three")
    assert profile.templateError() == (
        f"Rename failed. One.json could not be removed from {folder}: "
        "the file is read-only or open in another program."
    )
    # Not both: the new name is taken back.
    assert [r["name"] for r in profile.templates()] == ["One"]


def test_the_button_map_shows_the_reason() -> None:
    """The Templates window shows templateError(), not fixed text."""
    text = _QML.read_text(encoding="utf-8")
    assert "Could not write " not in text
    assert "Could not rename " not in text
    assert text.count("_hw.templateError()") >= 2
