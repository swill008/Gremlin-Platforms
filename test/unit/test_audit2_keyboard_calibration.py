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
from typing import Any

import pytest
import shiboken6
from PySide6 import QtCore

import dill
from gremlin import shared_state
from gremlin.event_handler import Event
from gremlin.profile import Profile
from gremlin.signal import signal
from gremlin.types import InputType
from gremlin.ui.backend import UIState
from gremlin.ui.device import AxisCalibration, InputIdentifier

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


_A = (30, False)
_S = (31, False)


def _page() -> Any:  # noqa: ANN401
    """The Keyboard page's model (KeyboardLayoutModel, 05 S128)."""
    from gremlin.ui.keyboard_layout import KeyboardLayoutModel

    model = KeyboardLayoutModel()
    _KEPT.append(model)
    return model


_KEPT: list[Any] = []


def _add(model: Any, key: tuple, mode: str = "Default") -> str:  # noqa: ANN401
    event = Event(InputType.Keyboard, key, dill.UUID_Keyboard, mode)
    return model.addKey([event], mode)


def _parents(model: Any) -> list[str]:  # noqa: ANN401
    return [
        model.keyAt(i)
        for i in range(model.rowCount())
        if model.keyAt(i).startswith("parent:")
    ]


@pytest.fixture(autouse=True)
def _no_held_layout() -> Iterator[None]:
    from gremlin.modules import store
    from gremlin.ui.keyboard_layout import keyboard_store

    yield
    store.discard_pending("")
    keyboard_store().load()


# --- deleting the last key ----------------------------------------------------


def test_no_row_gives_no_key(profile: Profile) -> None:
    model = _page()
    assert model.keyAt(-1) == ""  # failed on an empty list
    first = _add(model, _A)
    second = _add(model, _S)
    assert model.keyAt(-1) == ""
    assert model.keyAt(model.rowCount()) == ""  # past the end
    assert _parents(model) == [first, second]


def test_deleting_the_last_key_lets_the_editor_go_of_it(profile: Profile) -> None:
    from gremlin.ui.keyboard_layout import key_row

    model = _page()
    key = _add(model, _A)
    assert key == key_row(_A)
    model.beginPane(key, -1)
    assert model.paneModel is not None
    # What the page does on Delete: the pane open on the key closes (S76).
    page = Path(__file__).resolve().parents[2] / "qml/KeyboardPage.qml"
    text = page.read_text(encoding="utf-8")
    delete = text[text.index("function _askDelete"):]
    delete = delete[: delete.index("_layout.deleteParents(keys)")]
    assert "if (actionOpen && keys.indexOf(paneKey) >= 0)" in delete
    assert "_pane.closeNow()" in delete
    model.endPane()
    model.deleteParents([key])
    assert _parents(model) == [] and model.paneModel is None
    # The editor asks for nothing more, and the key is not made again.
    assert not profile.inputs.get(dill.UUID_Keyboard)


def test_loading_another_profile_lets_go_of_the_key(
    profile: Profile, ui_state: UIState
) -> None:
    key = InputIdentifier(dill.UUID_Keyboard, InputType.Keyboard, _A)
    ui_state.setCurrentInput(key, 0)
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
    model = _page()
    key = _add(model, _A, "Combat")
    model.setMode("Default")
    assert not model.canDelete(key)  # Default shown: not in this mode
    model.deleteParents([key])
    assert [i.mode for i in profile.inputs[dill.UUID_Keyboard]] == ["Combat"]
    model.setMode("Combat")
    assert model.canDelete(key)


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
