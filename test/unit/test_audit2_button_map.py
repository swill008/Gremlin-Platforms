# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Button Map (audit 2, group E): the kept photo says a photo change is
unsaved."""

from __future__ import annotations

import sys
from collections.abc import Iterator

sys.path.append(".")

import pytest
from PySide6 import QtCore

from gremlin.ui.hardware_profile import HardwareProfile

_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


def test_the_kept_photo_says_a_change_is_unsaved() -> None:
    hw = HardwareProfile()
    name = "Photo Stick"
    try:
        assert not hw.hasPhotoStash(name)
        hw.stashPhoto(name)
        assert hw.hasPhotoStash(name)
        hw.dropPhotoStash(name)
        assert not hw.hasPhotoStash(name)
    finally:
        hw.deleteLater()
