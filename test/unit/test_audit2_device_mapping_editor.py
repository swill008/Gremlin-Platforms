# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device Mapping Editor (audit 2, group E): an open edit (its temporary folder, where
a chosen photo waits until Save, 07 S107) is known while it lasts and gone
after Save or Cancel."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

sys.path.append(".")

import pytest
from PySide6 import QtCore

from gremlin.modules import store
from gremlin.ui.hardware_profile import HardwareProfile

_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


def test_an_open_edit_is_known_until_cancel(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(store, "folder", lambda: tmp_path)
    hw = HardwareProfile()
    name = "Photo Stick"
    try:
        assert not hw.editActive(name)
        hw.beginEdit(name)
        assert hw.editActive(name)
        assert hw.cancelEdit(name)
        assert not hw.editActive(name)
        assert not hw.cancelEdit(name)  # nothing left to cancel
    finally:
        hw.deleteLater()
