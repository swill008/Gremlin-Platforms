# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Button Map photo's look: an adjusted copy for brightness, contrast
and greyscale (fade is the photo's opacity)."""

from __future__ import annotations

import sys

sys.path.append(".")

import pathlib

import pytest
from PySide6 import QtCore, QtGui

from gremlin.ui import hardware_profile
from gremlin.ui.hardware_profile import adjust_photo


def _photo(colour: str) -> QtGui.QImage:
    image = QtGui.QImage(20, 10, QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtGui.QColor(colour))
    return image


def _pixel(image: QtGui.QImage) -> QtGui.QColor:
    return image.pixelColor(5, 5)


def test_greyscale_takes_the_colour_out() -> None:
    out = _pixel(adjust_photo(_photo("#FF0000"), 0, 0, 1))
    assert out.red() == out.green() == out.blue()
    half = _pixel(adjust_photo(_photo("#FF0000"), 0, 0, 0.5))
    assert half.red() > half.green() > 0


def test_brightness_both_ways() -> None:
    base = _pixel(_photo("#806040"))
    lighter = _pixel(adjust_photo(_photo("#806040"), 0.5, 0, 0))
    darker = _pixel(adjust_photo(_photo("#806040"), -0.5, 0, 0))
    assert lighter.lightness() > base.lightness() > darker.lightness()


def test_contrast_both_ways() -> None:
    dark = "#303030"
    more = _pixel(adjust_photo(_photo(dark), 0, 1, 0))
    less = _pixel(adjust_photo(_photo(dark), 0, -1, 0))
    assert more.red() < 0x30 < less.red()


def test_transparent_stays_transparent() -> None:
    clear = QtGui.QImage(4, 4, QtGui.QImage.Format.Format_ARGB32)
    clear.fill(QtCore.Qt.GlobalColor.transparent)
    assert adjust_photo(clear, 0.5, 0.5, 1).pixelColor(1, 1).alpha() == 0


@pytest.fixture
def profile(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> hardware_profile.HardwareProfile:
    monkeypatch.setattr(hardware_profile, "_maps_dir", lambda: tmp_path)
    return hardware_profile.HardwareProfile()


def test_cached_copy(
    profile: hardware_profile.HardwareProfile, tmp_path: pathlib.Path
) -> None:
    src = tmp_path / "photo.png"
    _photo("#FF0000").save(str(src))
    url = QtCore.QUrl.fromLocalFile(str(src)).toString()
    assert profile.adjustedPhotoUrl(url, 0, 0, 0) == ""
    first = profile.adjustedPhotoUrl(url, 0, 0, 1)
    assert first.startswith("file:")
    copy = QtGui.QImage(QtCore.QUrl(first).toLocalFile())
    grey = copy.pixelColor(5, 5)
    assert grey.red() == grey.green() == grey.blue()
    # The same look again is the same file; another look another file.
    assert profile.adjustedPhotoUrl(url, 0, 0, 1) == first
    assert profile.adjustedPhotoUrl(url, 0.2, 0, 1) != first
    assert profile.adjustedPhotoUrl(url + "missing", 0, 0, 1) == ""


def test_cache_keeps_only_the_latest(
    profile: hardware_profile.HardwareProfile, tmp_path: pathlib.Path
) -> None:
    src = tmp_path / "photo.png"
    _photo("#00FF00").save(str(src))
    url = QtCore.QUrl.fromLocalFile(str(src)).toString()
    for i in range(hardware_profile._LOOK_CACHE + 5):
        profile.adjustedPhotoUrl(url, i / 100, 0, 0)
    kept = list((tmp_path / "cache").glob("photo-*.png"))
    assert len(kept) <= hardware_profile._LOOK_CACHE
