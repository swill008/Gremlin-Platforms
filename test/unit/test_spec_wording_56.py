# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Wording of three refused saves (to-do 56).

Module Setup said "to save its setup" when the stick was unplugged after
it opened (03 S46 says "to change its setup" either way); Calibration said
the lowest and highest values were the same when the lowest was above the
highest (03 S103); the Button Map's refusal of a damaged module file names
the damage (07 S12).
"""

from __future__ import annotations

import sys

sys.path.append(".")

import json
import pathlib
import uuid
from collections.abc import Iterator
from types import SimpleNamespace

import pytest
from PySide6 import QtCore

from gremlin import device_initialization
from gremlin.signal import signal
from gremlin.util import modules_dir

_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


def _pjoy_guid() -> str:
    devices = device_initialization.physical_devices()
    return str(next(d for d in devices if d.name == "pJoy Pro").device_guid)


@pytest.fixture
def module_path() -> Iterator[pathlib.Path]:
    path = modules_dir() / "pjoy_pro.json"
    yield path
    for leftover in path.parent.glob("pjoy_pro.json*"):
        leftover.unlink()


# 03 S46 ------------------------------------------------------------------------

_S46 = "Plug in pJoy Pro to change its setup. Nothing was saved."


def test_unplugged_after_module_setup_opened_says_change_its_setup(
    module_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.ui import module_model

    guid = _pjoy_guid()
    model = module_model.DriverInputModel()
    model.loadDevice(guid, "pJoy Pro")
    assert model.saveBlockedReason() == ""
    # The stick is pulled out while Module Setup is open.
    monkeypatch.setattr(module_model, "_device_connected", lambda _guid: False)
    model._device_list_changed()
    assert model.saveBlockedReason() == _S46  # was "...to save its setup..."
    assert model.saveClaim("pJoy Pro", "source") is False
    assert not module_path.exists()


def test_unplugged_before_module_setup_opened_says_the_same() -> None:
    from gremlin.ui.module_model import DriverInputModel

    model = DriverInputModel()
    model.loadDevice("{DEADBEEF-0000-0000-0000-000000000000}", "pJoy Pro")
    assert model.saveBlockedReason() == _S46


# 03 S103 -----------------------------------------------------------------------


def _calibration(low: int, high: int) -> SimpleNamespace:
    from gremlin.ui.device import AxisCalibration

    model = SimpleNamespace(
        _device=SimpleNamespace(
            axis_lookup={1: 1}, axis_map=[SimpleNamespace(axis_index=1)]
        ),
        _device_uuid=uuid.uuid4(),
        _module_slug="stick",
        _state=[{
            "low": low, "centerLow": 0, "centerHigh": 0, "high": high,
            "withCenter": False, "unsavedChanges": True,
        }],
        _active_calibrations=[{"center": False, "extrema": False}],
        _calibration_fn=[lambda raw: 0.0],
        _update_calibration=lambda index: None,
        emit_update=lambda index: None,
    )
    model._refused = lambda index: AxisCalibration._refused(model, index)
    return model


def test_lowest_above_highest_is_refused_saying_so() -> None:
    from gremlin.ui.device import AxisCalibration

    upside_down = _calibration(500, -500)
    reason = AxisCalibration.saveRefusedReason(upside_down, 0)
    assert "The lowest value is above the highest." in reason
    assert "the same" not in reason  # was "...values are the same"
    assert AxisCalibration.save(upside_down, 0) is False


def test_equal_lowest_and_highest_keep_their_own_message() -> None:
    from gremlin.ui.device import AxisCalibration

    flat = _calibration(120, 120)
    reason = AxisCalibration.saveRefusedReason(flat, 0)
    assert "lowest and highest values are the same" in reason
    assert "above the highest" not in reason


# 07 S12 ------------------------------------------------------------------------


def test_button_map_refusal_names_the_damaged_module_file(
    module_path: pathlib.Path,
) -> None:
    from gremlin.ui.hardware_profile import HardwareProfile

    guid = _pjoy_guid()
    module_path.write_text('{"device": "pJoy Pro", "nod', encoding="utf-8")
    before = module_path.read_bytes()
    shown: list[str] = []

    def record(message: str, _details: str) -> None:
        shown.append(message)

    signal.showError.connect(record)
    try:
        profile = HardwareProfile()
        profile.setDeviceGuid(guid)
        assert profile.save("pJoy Pro", json.dumps({"nodes": []})) is False
    finally:
        signal.showError.disconnect(record)
    assert module_path.read_bytes() == before
    # The error dialog the user sees names the damage and Start Fresh.
    assert len(shown) == 1
    assert "pjoy_pro.json is damaged" in shown[0]
    assert "Start Fresh" in shown[0]
