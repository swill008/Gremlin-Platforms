# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Calibration has Undo and Redo for each axis's changes.

A typed value, Reset, and starting Calibrate Center or Calibrate Range are
steps; changes to the same value close together (a spin box held down) are
one; Undo puts the axis back (and stops a capture on it); another device,
or going back to the saved values, starts with no steps.
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
def model() -> Iterator[object]:
    from gremlin.modules import module_file
    from gremlin.ui.device import AxisCalibration
    from gremlin.ui.module_calibration import CalibrationModuleModel
    from gremlin.util import modules_dir

    devices = device_initialization.physical_devices()
    stick = next(d for d in devices if d.name == "pJoy Pro")
    path = modules_dir() / "pjoy_pro.json"
    module_file.write_json(
        path,
        {
            "device": "pJoy Pro",
            "direction": "source",
            "boundGuidLocal": str(stick.device_guid),
            "claim": {"buttons": [], "axes": [1, 2], "hats": [], "keys": []},
        },
    )
    modules = CalibrationModuleModel()
    slugs = [
        modules.data(modules.index(i, 0), QtCore.Qt.ItemDataRole.UserRole + 2)
        for i in range(modules.rowCount())
    ]
    made = AxisCalibration()
    made.moduleSlug = next(slug for slug in slugs if "pjoy" in str(slug))
    assert made.rowCount() > 0
    yield made
    for leftover in path.parent.glob("pjoy_pro.json*"):
        leftover.unlink()


def test_undo_that_stops_a_capture_says_so(model: object) -> None:
    told: list[int] = []
    model.captureStopped.connect(told.append)
    model.calibrateExtrema(0, True)
    model.undo()
    assert told == [0]


def _set(model: object, row: int, name: str, value: object) -> None:
    role = next(r for r, n in model.roles.items() if bytes(n).decode() == name)
    model.setData(model.index(row, 0), value, role)


def test_a_typed_value_undoes_and_redoes(model: object) -> None:
    start = model._limits(0)
    _set(model, 0, "high", 30000)
    assert model.canUndo
    model.undo()
    assert model._limits(0) == start
    assert model.canRedo
    model.redo()
    assert model._state[0]["high"] == 30000


def test_a_held_spin_box_is_one_step(model: object) -> None:
    start = model._limits(0)
    for value in (32000, 31000, 30000):
        _set(model, 0, "high", value)
    assert len(model._undo) == 1
    model.undo()
    assert model._limits(0) == start


def test_reset_and_a_capture_are_steps(model: object) -> None:
    _set(model, 0, "low", -20000)
    before_reset = model._limits(0)
    model.reset(0)
    model.calibrateExtrema(0, True)
    assert model._active_calibrations[0]["extrema"] is True
    model.undo()
    assert model._active_calibrations[0]["extrema"] is False
    model.undo()
    assert model._limits(0) == before_reset


def test_going_back_to_saved_drops_the_steps(model: object) -> None:
    _set(model, 0, "high", 30000)
    model.discard()
    assert not model.canUndo and not model.canRedo
