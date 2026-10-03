# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Module Setup for a device that isn't plugged in.

It showed no controls, and Save then wrote empty claims and names over the
saved ones. Save is now refused until the device is back, with the reason.
"""

from __future__ import annotations

import sys

sys.path.append(".")

import json
import pathlib
from collections.abc import Iterator

import pytest
from PySide6 import QtCore

from gremlin import device_initialization
from gremlin.util import modules_dir

_APPS: list[QtCore.QCoreApplication] = []
_UNPLUGGED = "{DEADBEEF-0000-0000-0000-000000000000}"


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


@pytest.fixture
def saved() -> Iterator[tuple[pathlib.Path, str]]:
    devices = device_initialization.physical_devices()
    guid = str(next(d for d in devices if d.name == "pJoy Pro").device_guid)
    path = modules_dir() / "pjoy_pro.json"
    path.write_text(json.dumps({
        "device": "pJoy Pro",
        "direction": "source",
        "boundGuidLocal": guid,
        "claim": {
            "buttons": [1, 2], "axes": [1], "hats": [], "keys": [],
            "friendly": {"button:1": "Fire"},
        },
    }, indent=2), encoding="utf-8")
    yield path, guid
    for leftover in path.parent.glob("pjoy_pro.json*"):
        leftover.unlink()


def test_unplugged_device_save_is_refused(saved: tuple[pathlib.Path, str]) -> None:
    from gremlin.ui.module_model import DriverInputModel

    path, _guid = saved
    before = path.read_bytes()
    model = DriverInputModel()
    model.loadDevice(_UNPLUGGED, "pJoy Pro")
    assert model.rowCount() == 0
    assert model.saveBlockedReason().startswith("Plug in pJoy Pro")
    assert model.saveClaim("pJoy Pro", "source") is False
    assert path.read_bytes() == before  # was: claims and names emptied


def test_connected_device_saves(saved: tuple[pathlib.Path, str]) -> None:
    from gremlin.ui.module_model import DriverInputModel

    path, guid = saved
    model = DriverInputModel()
    model.loadDevice(guid, "pJoy Pro")
    assert model.saveBlockedReason() == ""
    assert model.rowCount() > 0
    assert model.saveClaim("pJoy Pro", "source") is True
    claim = json.loads(path.read_text(encoding="utf-8"))["claim"]
    assert claim["buttons"] == [1, 2] and claim["friendly"] == {"button:1": "Fire"}


@pytest.mark.parametrize("name", ["Keyboard", "OSC"])
def test_keyboard_and_osc_are_never_blocked(name: str) -> None:
    from gremlin.ui.module_model import DriverInputModel

    model = DriverInputModel()
    model.loadDevice("", name)
    assert model.saveBlockedReason() == ""
