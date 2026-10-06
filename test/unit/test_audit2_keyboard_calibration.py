# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Keyboard page and calibration fixes from the second audit.

- Deleting the last key: no row picked the last key (or failed on an empty
  list), and the editor kept the deleted key, which came back when edited.
  The same stale key was re-created in the next profile loaded.
- A key that exists only in another mode showed a Delete button that did
  nothing; the list now says whether the key is in the mode shown.
- Calibration Save accepted a center outside the range, which the next
  load threw away; it is now refused with the reason, and never written.
"""

from __future__ import annotations

import sys

sys.path.append(".")

import json
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest
import shiboken6
from PySide6 import QtCore

import dill
from gremlin import shared_state
from gremlin.event_handler import Event
from gremlin.profile import Profile
from gremlin.signal import signal
from gremlin.types import InputType
from gremlin.ui.backend import Backend, UIState
from gremlin.ui.device import AxisCalibration, InputIdentifier, KeyboardManagerModel

_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


@pytest.fixture
def profile() -> Iterator[Profile]:
    previous = shared_state.current_profile
    shared_state.current_profile = Profile()
    yield shared_state.current_profile
    shared_state.current_profile = previous


@pytest.fixture
def ui_state() -> Iterator[UIState]:
    state = UIState()
    state.setCurrentDevice(str(dill.UUID_Keyboard))
    yield state
    shiboken6.delete(state)


def _add(model: KeyboardManagerModel, key: tuple, mode: str = "Default") -> None:
    model.addKey([Event(InputType.Keyboard, key, dill.UUID_Keyboard, mode)], mode)


def _role(model: KeyboardManagerModel, name: bytes) -> int:
    return next(r for r, n in model.roles.items() if bytes(n) == name)


# --- deleting the last key ----------------------------------------------------


def test_no_row_gives_no_key(profile: Profile) -> None:
    model = KeyboardManagerModel()
    assert model.inputIdentifier(-1) is None  # failed on an empty list
    _add(model, (30, False))
    _add(model, (31, False))
    assert model.inputIdentifier(-1) is None  # was the last key
    assert model.inputIdentifier(2) is None  # past the end
    assert model.inputIdentifier(1).input_id == (31, False)


def test_deleting_the_last_key_lets_the_editor_go_of_it(
    profile: Profile, ui_state: UIState
) -> None:
    model = KeyboardManagerModel()
    _add(model, (30, False))
    ui_state.setCurrentInput(model.inputIdentifier(0), 0)
    assert ui_state.currentInput.isValid
    changes: list[None] = []
    ui_state.inputChanged.connect(lambda: changes.append(None))

    model.deleteInput(0)
    assert model.rowCount() == 0
    # What the page does once the list is empty.
    ui_state.clearKeyboardInput()
    assert not ui_state.currentInput.isValid
    assert changes  # the editor is told
    # The editor then asks for nothing, and the key is not made again.
    backend = SimpleNamespace(profile=profile, ui_state=ui_state)
    assert Backend.klass.getInputItem(backend, ui_state.currentInput, 0) is None
    assert not profile.inputs.get(dill.UUID_Keyboard)


def test_loading_another_profile_lets_go_of_the_key(
    profile: Profile, ui_state: UIState
) -> None:
    model = KeyboardManagerModel()
    _add(model, (30, False))
    ui_state.setCurrentInput(model.inputIdentifier(0), 0)
    stick = InputIdentifier(dill.UUID_LogicalDevice, InputType.JoystickButton, 1)
    ui_state.setCurrentInput(stick, 3)

    shared_state.current_profile = Profile()
    signal.profileChanged.emit()
    # The old key was kept and re-created in the new profile by the editor.
    assert not ui_state.currentInput.isValid
    # Other devices' inputs are left as they were.
    ui_state.setCurrentDevice(str(dill.UUID_LogicalDevice))
    assert ui_state.currentInput.input_id == 1 and ui_state.currentInputIndex == 3


# --- Delete only for a key in the mode shown ------------------------------------


def test_a_key_only_in_another_mode_is_not_in_this_one(profile: Profile) -> None:
    profile.modes.add_mode("Combat")
    model = KeyboardManagerModel()
    _add(model, (30, False), "Combat")
    in_mode = _role(model, b"inMode")
    assert model.data(model.index(0, 0), in_mode) is False  # Default shown
    model.setMode("Combat")
    assert model.data(model.index(0, 0), in_mode) is True


# --- calibration: a center outside the range ----------------------------------


def _axis(low: int, center_low: int, center_high: int, high: int) -> SimpleNamespace:
    model = SimpleNamespace(
        _device=SimpleNamespace(axis_map=[SimpleNamespace(axis_index=1)]),
        _device_uuid="x",
        _module_slug="stick",
        _state=[{
            "low": low, "centerLow": center_low, "centerHigh": center_high,
            "high": high, "withCenter": True, "unsavedChanges": True,
        }],
    )
    model._refused = lambda index: AxisCalibration._refused(model, index)
    return model


def test_a_center_outside_the_range_is_refused_with_the_reason() -> None:
    outside = _axis(-100, 150, 200, 100)
    reason = AxisCalibration._refused(outside, 0)
    assert "center is outside" in reason
    assert AxisCalibration.saveAllRefusedReason(outside) == reason
    assert AxisCalibration.save(outside, 0) is False
    assert AxisCalibration.saveAll(outside) is False
    assert AxisCalibration._refused(_axis(-100, -5, 5, 100), 0) == ""


def test_a_curve_loading_would_drop_is_not_written(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.modules import calibration

    path = tmp_path / "stick.json"
    path.write_text("{}", encoding="utf-8")
    row = {"slug": "stick", "path": path}
    monkeypatch.setattr(calibration, "module_for_slug", lambda slug: row)

    for bad in ((-100, 150, 200, 100, True), (50, 0, 0, 50, False)):
        assert calibration.write_axes("stick", {1: bad}) is False
        assert path.read_text(encoding="utf-8") == "{}"
    # One bad axis keeps the others from a half save.
    both = {1: (-100, 0, 0, 100, True), 2: (-100, 150, 200, 100, True)}
    assert calibration.write_axes("stick", both) is False
    # A curve that is written loads back as saved.
    good = (-100, -5, 5, 100, True)
    assert calibration.write_axes("stick", {1: good}) is True
    assert json.loads(path.read_text(encoding="utf-8"))["calibration"] == {
        "1": list(good)
    }
    assert calibration._stored_axis(row, 1) == good
