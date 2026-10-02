# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Pasting a picture into the Button Map: it is saved beside the device's
layout and in the picture library, under a name that is not taken."""

from __future__ import annotations

import sys

sys.path.append(".")

import pathlib

import pytest
from PySide6 import (
    QtCore,
    QtGui,
)

from gremlin.ui import hardware_profile


@pytest.fixture
def profile(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> hardware_profile.HardwareProfile:
    monkeypatch.setattr(hardware_profile, "_maps_dir", lambda: tmp_path)
    monkeypatch.setattr(
        hardware_profile, "resolve_module_slug", lambda name, guid="": "test_stick"
    )
    return hardware_profile.HardwareProfile()


def _image() -> QtGui.QImage:
    image = QtGui.QImage(QtCore.QSize(8, 6), QtGui.QImage.Format.Format_RGB32)
    image.fill(QtGui.QColor("#336699"))
    return image


def test_saves_under_a_free_name(
    profile: hardware_profile.HardwareProfile, tmp_path: pathlib.Path
) -> None:
    first = profile.savePastedImage(_image(), "Test Stick")
    second = profile.savePastedImage(_image(), "Test Stick")
    assert first == "test_stick/pasted.png"
    assert second == "test_stick/pasted_1.png"
    saved = QtGui.QImage(str(tmp_path / "test_stick" / "pasted.png"))
    assert saved.size() == QtCore.QSize(8, 6)
    assert (tmp_path / "library" / "pasted.png").is_file()


def test_nothing_to_paste(profile: hardware_profile.HardwareProfile) -> None:
    assert profile.savePastedImage(QtGui.QImage(), "Test Stick") == ""


def test_dropped_files_keep_only_pictures(
    profile: hardware_profile.HardwareProfile, tmp_path: pathlib.Path
) -> None:
    source = tmp_path / "from"
    source.mkdir()
    picture = source / "grip.png"
    QtGui.QImage(QtCore.QSize(30, 10), QtGui.QImage.Format.Format_RGB32).save(
        str(picture)
    )
    notes = source / "notes.txt"
    notes.write_text("not a picture", encoding="utf-8")
    urls = [picture.as_uri(), notes.as_uri(), "https://example.com/x.png"]
    assert profile.hasPictureFiles(urls) is True
    assert profile.hasPictureFiles([notes.as_uri()]) is False
    added = profile.importPictureFiles(urls, "Test Stick")
    assert added == ["test_stick/grip.png"]
    assert profile.imageAspect(added[0]) == 3.0
