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
from typing import Any
from unittest import mock

import pytest
from PySide6 import QtCore

import dill
from gremlin import code_runner, mode_manager, shared_state
from gremlin.config import Configuration
from gremlin.event_handler import Event
from gremlin.profile import Profile
from gremlin.types import InputType

_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


def _keyboard_page() -> Any:  # noqa: ANN401
    """The Keyboard page's model (KeyboardLayoutModel, 05 S128)."""
    from gremlin.ui.keyboard_layout import KeyboardLayoutModel

    model = KeyboardLayoutModel()
    _KEPT.append(model)
    return model


_KEPT: list[Any] = []


def _done() -> None:
    from gremlin.modules import store
    from gremlin.ui.keyboard_layout import keyboard_store

    store.discard_pending("")
    keyboard_store().load()


def test_add_key_goes_into_the_given_mode() -> None:
    previous = shared_state.current_profile
    shared_state.current_profile = Profile()
    try:
        model = _keyboard_page()
        key = (30, False)
        event = Event(InputType.Keyboard, key, dill.UUID_Keyboard, "Combat")
        model.addKey([event], "Combat")
        items = shared_state.current_profile.inputs[dill.UUID_Keyboard]
        assert [(i.input_id, i.mode) for i in items] == [(key, "Combat")]
        model.addKey([], "Combat")
        assert len(shared_state.current_profile.inputs[dill.UUID_Keyboard]) == 1
    finally:
        shared_state.current_profile = previous
        _done()


def test_a_key_in_two_modes_is_listed_once_with_the_shown_modes_actions() -> None:
    previous = shared_state.current_profile
    profile = Profile()
    profile.modes.add_mode("Combat")
    shared_state.current_profile = profile
    try:
        model = _keyboard_page()
        key = (30, False)
        for mode in ("Default", "Combat"):
            event = Event(InputType.Keyboard, key, dill.UUID_Keyboard, mode)
            model.addKey([event], mode)
        profile.get_input_item(
            dill.UUID_Keyboard, InputType.Keyboard, key, "Combat"
        ).add_item_binding()
        model.setMode("Default")
        parents = [r for r in model._rows if r["rowKind"] == "parent"]
        assert len(parents) == 1
        assert parents[0]["childCount"] == 0  # Default shown: no actions there
        model.setMode("Combat")
        parents = [r for r in model._rows if r["rowKind"] == "parent"]
        assert parents[0]["childCount"] == 1
        # Delete takes the key out of the mode shown only.
        model.deleteParents([parents[0]["key"]])
        modes = [i.mode for i in profile.inputs[dill.UUID_Keyboard]]
        parents = [r for r in model._rows if r["rowKind"] == "parent"]
        assert modes == ["Default"] and len(parents) == 1
    finally:
        shared_state.current_profile = previous
        _done()


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
