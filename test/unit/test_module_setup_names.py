# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Module Setup's Save writes only the names changed in its window (AD3,
AUD-FILES-01).

The window is non-modal: a name saved elsewhere while it is open (a page's
Rename) was written over at its Save with the names it read when it opened.
"""

from __future__ import annotations

import sys

sys.path.append(".")

import json
import pathlib
from collections.abc import Iterator
from typing import TYPE_CHECKING

import pytest
from PySide6 import QtCore

from gremlin import device_initialization
from gremlin.modules import store
from gremlin.util import modules_dir

if TYPE_CHECKING:
    from gremlin.ui.module_model import DriverInputModel

_APPS: list[QtCore.QCoreApplication] = []


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
    path.write_text(
        json.dumps(
            {
                "device": "pJoy Pro",
                "direction": "source",
                "boundGuidLocal": guid,
                "claim": {
                    "buttons": [1, 2, 3],
                    "axes": [1],
                    "hats": [],
                    "keys": [],
                    "friendly": {
                        "button:1": "Fire",
                        "button:2": "Gear",
                        "axis:1": "Pitch",
                    },
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    yield path, guid
    for leftover in path.parent.glob("pjoy_pro.json*"):
        leftover.unlink()


def _open(guid: str) -> DriverInputModel:
    from gremlin.ui.module_model import DriverInputModel

    model = DriverInputModel()
    model.loadDevice(guid, "pJoy Pro")
    assert model.saveBlockedReason() == ""
    return model


def _row(model: DriverInputModel, kind: str, hw_id: int) -> int:
    for i in range(model.rowCount()):
        ix = model.index(i, 0)
        if (
            model.data(ix, QtCore.Qt.ItemDataRole.UserRole + 1) == kind
            and int(model.data(ix, QtCore.Qt.ItemDataRole.UserRole + 2)) == hw_id
        ):
            return i
    raise AssertionError(f"no row {kind} {hw_id}")


def _names(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))["claim"]["friendly"]


def test_save_keeps_a_name_saved_elsewhere_while_open(
    saved: tuple[pathlib.Path, str],
) -> None:
    path, guid = saved
    model = _open(guid)
    # Renamed on a page (written straight to the file) while the window is open.
    assert store.set_friendly_name(guid, "button:2", "Flaps", "pJoy Pro")
    model.setFriendly(_row(model, "button", 1), "Trigger")
    assert model.saveClaim("pJoy Pro", "source") is True
    # was: "Gear" (the name read at open) written over "Flaps"
    assert _names(path) == {
        "button:1": "Trigger",
        "button:2": "Flaps",
        "axis:1": "Pitch",
    }


def test_a_name_added_elsewhere_while_open_is_kept(
    saved: tuple[pathlib.Path, str],
) -> None:
    path, guid = saved
    model = _open(guid)
    assert store.set_friendly_name(guid, "button:3", "Brake", "pJoy Pro")
    assert model.saveClaim("pJoy Pro", "source") is True
    assert _names(path)["button:3"] == "Brake"  # was: dropped


def test_clearing_a_name_removes_only_that_one(saved: tuple[pathlib.Path, str]) -> None:
    path, guid = saved
    model = _open(guid)
    assert store.set_friendly_name(guid, "axis:1", "Roll", "pJoy Pro")
    model.setFriendly(_row(model, "button", 1), "")
    assert model.saveClaim("pJoy Pro", "source") is True
    assert _names(path) == {"button:2": "Gear", "axis:1": "Roll"}


def test_a_name_changed_here_wins_over_one_saved_elsewhere(
    saved: tuple[pathlib.Path, str],
) -> None:
    path, guid = saved
    model = _open(guid)
    assert store.set_friendly_name(guid, "button:1", "Elsewhere", "pJoy Pro")
    model.setFriendly(_row(model, "button", 1), "Here")
    assert model.saveClaim("pJoy Pro", "source") is True
    assert _names(path)["button:1"] == "Here"


def test_unclaiming_a_control_drops_its_name(saved: tuple[pathlib.Path, str]) -> None:
    """03 S42: a friendly name is saved only for a claimed control, also a
    name written elsewhere while the window was open."""
    path, guid = saved
    model = _open(guid)
    assert store.set_friendly_name(guid, "button:2", "Flaps", "pJoy Pro")
    model.setClaimed(_row(model, "button", 2), False)
    assert model.saveClaim("pJoy Pro", "source") is True
    assert "button:2" not in _names(path)
    assert _names(path)["button:1"] == "Fire"
