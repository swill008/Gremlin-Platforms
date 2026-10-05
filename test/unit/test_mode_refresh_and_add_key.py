# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Behaviour kept when two circular imports were taken apart.

- Add Key puts the key in the mode the user is viewing (the keyboard list
  now passes that mode in, instead of the model asking the Backend).
- The axes are refreshed on a mode change while a profile runs, when
  "refresh-axis-on-mode-change" is on (the runner does it now, not the
  mode manager), never twice, and not after Stop.
"""

from __future__ import annotations

import sys

sys.path.append(".")

from collections.abc import Iterator
from unittest import mock

import pytest
from PySide6 import QtCore

import dill
from gremlin import code_runner, mode_manager, shared_state
from gremlin.config import Configuration
from gremlin.event_handler import Event
from gremlin.profile import Profile
from gremlin.types import InputType
from gremlin.ui.device import KeyboardManagerModel

_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


def test_add_key_goes_into_the_given_mode() -> None:
    previous = shared_state.current_profile
    shared_state.current_profile = Profile()
    try:
        model = KeyboardManagerModel()
        key = (30, False)
        event = Event(InputType.Keyboard, key, dill.UUID_Keyboard, "Combat")
        model.addKey([event], "Combat")
        items = shared_state.current_profile.inputs[dill.UUID_Keyboard]
        assert [(i.input_id, i.mode) for i in items] == [(key, "Combat")]
        model.addKey([], "Combat")
        assert len(shared_state.current_profile.inputs[dill.UUID_Keyboard]) == 1
    finally:
        shared_state.current_profile = previous


def test_a_key_in_two_modes_is_listed_once_with_the_shown_modes_actions() -> None:
    previous = shared_state.current_profile
    profile = Profile()
    profile.modes.add_mode("Combat")
    shared_state.current_profile = profile
    try:
        model = KeyboardManagerModel()
        key = (30, False)
        for mode in ("Default", "Combat"):
            model.addKey([Event(InputType.Keyboard, key, dill.UUID_Keyboard, mode)], mode)
        profile.get_input_item(
            dill.UUID_Keyboard, InputType.Keyboard, key, "Combat"
        ).add_item_binding()
        assert model.rowCount() == 1
        role = next(r for r, n in model.roles.items() if bytes(n) == b"actionSequenceCount")
        count = model.data(model.index(0, 0), role)
        assert count == 0  # Default shown: no actions there
        model.setMode("Combat")
        assert model.data(model.index(0, 0), role) == 1
        # Delete takes the key out of the mode shown only.
        model.deleteInput(0)
        modes = [i.mode for i in profile.inputs[dill.UUID_Keyboard]]
        assert modes == ["Default"] and model.rowCount() == 1
    finally:
        shared_state.current_profile = previous


@pytest.fixture
def refresh() -> Iterator[mock.Mock]:
    cfg = Configuration()
    before = cfg.value("global", "general", "refresh-axis-on-mode-change")
    with mock.patch.object(code_runner.RefreshPhysicalInputs, "refresh_axes") as m:
        yield m
    cfg.set("global", "general", "refresh-axis-on-mode-change", before)


def test_runner_refreshes_axes_on_mode_change_only_while_listening(
    refresh: mock.Mock,
) -> None:
    Configuration().set("global", "general", "refresh-axis-on-mode-change", True)
    runner = code_runner.CodeRunner()
    mm = mode_manager.ModeManager()
    try:
        mm.mode_changed.emit("Combat")
        assert refresh.call_count == 0  # not running: nothing listens

        runner._listen_to_mode_changes(True)
        runner._listen_to_mode_changes(True)  # a second start never doubles it
        mm.mode_changed.emit("Combat")
        assert refresh.call_count == 1

        Configuration().set("global", "general", "refresh-axis-on-mode-change", False)
        mm.mode_changed.emit("Default")
        assert refresh.call_count == 1  # option off

        Configuration().set("global", "general", "refresh-axis-on-mode-change", True)
        runner._listen_to_mode_changes(False)  # Stop
        mm.mode_changed.emit("Default")
        assert refresh.call_count == 1
    finally:
        runner._listen_to_mode_changes(False)


def test_mode_manager_no_longer_refreshes_on_its_own(refresh: mock.Mock) -> None:
    Configuration().set("global", "general", "refresh-axis-on-mode-change", True)
    mode_manager.ModeManager()._update_mode()
    assert refresh.call_count == 0
