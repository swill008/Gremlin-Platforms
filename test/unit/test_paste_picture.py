# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Pasting a picture into the Device Mapping Editor: it is staged in the edit's
temporary folder (07 S107) under a name that is not taken, named
"pictures/<file>" (07 S10); Save copies it into the device's pictures/
folder. There is no picture library (07 S81 removed)."""

from __future__ import annotations

import sys

sys.path.append(".")

import pathlib

import pytest
from PySide6 import (
    QtCore,
    QtGui,
)

from gremlin.modules import store
from gremlin.ui import hardware_profile


@pytest.fixture
def profile(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> hardware_profile.HardwareProfile:
    monkeypatch.setattr(store, "folder", lambda: tmp_path)
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
    assert first == "pictures/pasted.png"
    assert second == "pictures/pasted_1.png"
    staged = store.edit_temp_dir("Test Stick") / "added" / "pasted.png"
    saved = QtGui.QImage(str(staged))
    assert saved.size() == QtCore.QSize(8, 6)
    # Not in the device's folder until Save, and no library copy.
    assert not (store.pictures_dir("Test Stick") / "pasted.png").exists()
    assert not (tmp_path / "library").exists()


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
    assert added == ["pictures/grip.png"]
    assert profile.imageAspect(added[0]) == 3.0


def test_image_aspect_reads_through_store_picture_size(
    profile: hardware_profile.HardwareProfile,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """imageAspect reads a picture's size through the shared reader
    store.picture_size; an unreadable or missing file gives 1."""
    picture = tmp_path / "wide.png"
    image = QtGui.QImage(QtCore.QSize(40, 10), QtGui.QImage.Format.Format_RGB32)
    image.fill(QtGui.QColor("#336699"))
    assert image.save(str(picture))
    broken = tmp_path / "broken.png"
    broken.write_text("not a picture", encoding="utf-8")
    calls: list[str] = []
    real = store.picture_size

    def spy(folder: pathlib.Path | None, ref: str) -> tuple[int, int]:
        calls.append(ref)
        return real(folder, ref)

    monkeypatch.setattr(store, "picture_size", spy)
    assert profile.imageAspect(str(picture)) == 4.0
    assert profile.imageAspect(picture.as_uri()) == 4.0
    assert profile.imageAspect(str(broken)) == 1.0
    assert profile.imageAspect(str(tmp_path / "missing.png")) == 1.0
    assert profile.imageAspect("") == 1.0
    assert calls == [str(picture), str(picture), str(broken)]


def test_picture_size_reads_files_through_store_picture_size(
    profile: hardware_profile.HardwareProfile,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """pictureSize reads a file's size through store.picture_size."""
    picture = tmp_path / "tall.png"
    image = QtGui.QImage(QtCore.QSize(6, 18), QtGui.QImage.Format.Format_RGB32)
    image.fill(QtGui.QColor("#336699"))
    assert image.save(str(picture))
    broken = tmp_path / "broken2.png"
    broken.write_text("not a picture", encoding="utf-8")
    calls: list[str] = []
    real = store.picture_size

    def spy(folder: pathlib.Path | None, ref: str) -> tuple[int, int]:
        calls.append(ref)
        return real(folder, ref)

    monkeypatch.setattr(store, "picture_size", spy)
    assert profile.pictureSize(picture.as_uri()) == {"w": 6, "h": 18}
    assert profile.pictureSize(str(broken)) == {"w": 0, "h": 0}
    assert calls == [str(picture), str(broken)]
