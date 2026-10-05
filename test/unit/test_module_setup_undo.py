# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Module Setup has Undo and Redo for its checks and names.

Each check, each press that checks a control, and each name is one step
(100 kept); Undo puts the rows back as they were, Redo again; a new edit
drops what Redo had; another device starts with no steps.
"""

from __future__ import annotations

import sys

sys.path.append(".")

from collections.abc import Iterator

import pytest
from PySide6 import QtCore

from gremlin import device_initialization

_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


@pytest.fixture
def model() -> object:
    from gremlin.ui.module_model import DriverInputModel

    devices = device_initialization.physical_devices()
    guid = str(next(d for d in devices if d.name == "pJoy Pro").device_guid)
    made = DriverInputModel()
    made.loadDevice(guid, "pJoy Pro")
    assert made.rowCount() > 3
    return made


def _marks(model: object) -> list[tuple[bool, str]]:
    # In row order (the model keeps its steps by control).
    return [(bool(r["claimed"]), str(r.get("friendly") or "")) for r in model._rows]


def test_undo_and_redo_checks_and_names(model: object) -> None:
    start = _marks(model)
    assert not model.canUndo
    model.setClaimed(0, not start[0][0])
    model.setFriendly(1, "Trigger")
    after = _marks(model)
    assert model.canUndo and not model.canRedo
    model.undo()
    assert _marks(model)[1][1] == start[1][1]
    model.undo()
    assert _marks(model) == start
    assert not model.canUndo and model.canRedo
    model.redo()
    model.redo()
    assert _marks(model) == after


def test_a_press_that_checks_is_a_step(model: object) -> None:
    row = model._rows[2]
    model.setClaimed(2, False)
    before = _marks(model)
    model.markPressed(row["kind"], int(row["hwId"]))
    assert _marks(model)[2][0] is True
    model.undo()
    assert _marks(model) == before


def test_a_new_edit_drops_redo(model: object) -> None:
    model.setFriendly(0, "A")
    model.undo()
    assert model.canRedo
    model.setFriendly(0, "B")
    assert not model.canRedo


def test_another_device_starts_without_steps(model: object) -> None:
    model.setFriendly(0, "A")
    assert model.canUndo
    model.loadDevice("{DEADBEEF-0000-0000-0000-000000000000}", "Gone Stick")
    assert not model.canUndo and not model.canRedo


def test_steps_are_capped(model: object) -> None:
    for i in range(model.UNDO_STEPS + 20):
        model.setFriendly(0, f"name {i}")
    assert len(model._undo) == model.UNDO_STEPS
