# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A device map picture's look (07 S43): an adjusted copy for brightness,
contrast and greyscale, from the picture node's "look"; its Opacity is the
node's own "opacity" (the old photo "fade" became Opacity)."""

from __future__ import annotations

import sys

sys.path.append(".")

import pathlib

import pytest
from PySide6 import QtCore, QtGui

from gremlin.modules import store
from gremlin.ui import hardware_profile
from gremlin.ui.hardware_profile import _look_values, adjust_photo


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


def test_look_values_clamped_and_neutral_when_missing() -> None:
    # 07 S43: a picture's look keys; missing or bad values are neutral.
    assert _look_values(None) == (0.0, 0.0, 0.0)
    assert _look_values({"bright": 0.3, "contrast": -2, "grey": True}) == (
        0.3, -1.0, 1.0,
    )
    assert _look_values({"bright": "bad", "grey": False}) == (0.0, 0.0, 0.0)


@pytest.fixture
def profile(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> hardware_profile.HardwareProfile:
    monkeypatch.setattr(store, "folder", lambda: tmp_path)
    return hardware_profile.HardwareProfile()


def test_cached_copy(
    profile: hardware_profile.HardwareProfile, tmp_path: pathlib.Path
) -> None:
    src = tmp_path / "photo.png"
    _photo("#FF0000").save(str(src))
    url = QtCore.QUrl.fromLocalFile(str(src)).toString()
    assert profile.adjustedPhotoUrl(url, {}) == ""
    first = profile.adjustedPhotoUrl(url, {"grey": True})
    assert first.startswith("file:")
    copy = QtGui.QImage(QtCore.QUrl(first).toLocalFile())
    grey = copy.pixelColor(5, 5)
    assert grey.red() == grey.green() == grey.blue()
    # The same look again is the same file; another look another file.
    assert profile.adjustedPhotoUrl(url, {"grey": True}) == first
    assert profile.adjustedPhotoUrl(url, {"bright": 0.2, "grey": True}) != first
    assert profile.adjustedPhotoUrl(url + "missing", {"grey": True}) == ""


def test_cache_keeps_only_the_latest(
    profile: hardware_profile.HardwareProfile, tmp_path: pathlib.Path
) -> None:
    src = tmp_path / "photo.png"
    _photo("#00FF00").save(str(src))
    url = QtCore.QUrl.fromLocalFile(str(src)).toString()
    for i in range(hardware_profile._LOOK_CACHE + 5):
        profile.adjustedPhotoUrl(url, {"bright": (i + 1) / 100})
    kept = list((tmp_path / "cache" / "look").glob("photo-*.png"))
    assert kept
    assert len(kept) <= hardware_profile._LOOK_CACHE
