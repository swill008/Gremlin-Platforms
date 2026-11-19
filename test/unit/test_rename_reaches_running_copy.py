# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A mode renamed or deleted while a Run is on reaches the Run's own copy of
the profile (code_runner.profile_snapshot), not only the open profile and the
mode stack (04 S44, S46)."""

from __future__ import annotations

import sys
import uuid
from collections.abc import Iterator
from typing import Any

sys.path.append(".")

import pytest
from PySide6 import QtCore

from gremlin import code_runner, mode_manager, plugin_manager, shared_state
from gremlin.profile import Profile
from gremlin.types import InputType
from gremlin.ui import profile as ui_profile

_STICK = uuid.UUID("12121212-3434-5656-7878-909090909090")
_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


@pytest.fixture
def mm(monkeypatch: pytest.MonkeyPatch) -> Iterator[mode_manager.ModeManager]:
    # No stored last mode or settings file in play.
    monkeypatch.setattr(mode_manager, "_profile_running", lambda: False)
    manager = mode_manager.ModeManager()
    monkeypatch.setattr(manager, "_rewrite_stored_name", lambda *a: None)
    stack = list(manager._mode_stack)
    yield manager
    manager._mode_stack = stack


def _cycle_profile(monkeypatch: pytest.MonkeyPatch) -> tuple[Profile, Any]:
    p = Profile()
    monkeypatch.setattr(shared_state, "current_profile", p)
    for name in ("Ground", "Orbit", "Space"):
        p.modes.add_mode(name)
    item = p.get_input_item(
        _STICK, InputType.JoystickButton, 1, "Default", create_if_missing=True
    )
    change = plugin_manager.PluginManager().create_instance(
        "Change Mode", InputType.JoystickButton
    )
    from action_plugins.change_mode import ChangeType

    change.change_type = ChangeType.Cycle
    change.target_modes = ["Ground", "Orbit", "Space"]
    item.add_item_binding().root_action.insert_action(change, "children")
    return p, change


def _run_copy_change(copy: Profile) -> Any:  # noqa: ANN401
    found = copy.library.actions_by_predicate(
        lambda a: getattr(a, "_target_modes", None) is not None
    )
    assert len(found) == 1
    return found[0]


def test_rename_while_running_moves_the_running_cycle(
    mm: mode_manager.ModeManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    open_profile, _ = _cycle_profile(monkeypatch)
    copy = code_runner.profile_snapshot(open_profile)
    monkeypatch.setattr(shared_state, "current_profile", open_profile)
    monkeypatch.setattr(shared_state, "running_profile", copy)
    held = _run_copy_change(copy)._target_modes  # the running Cycle's list
    mm._mode_stack = [mode_manager.Mode("Ground", None)]

    ui_profile.rename_mode("Orbit", "Low Orbit")

    assert held == ["Ground", "Low Orbit", "Space"]
    sequence = mode_manager.ModeSequence(held)
    assert sequence.next("Ground", {"Default", "Ground", "Low Orbit", "Space"}) == (
        "Low Orbit"
    )
    assert "Low Orbit" in copy.modes.mode_names()
    assert "Orbit" not in copy.modes.mode_names()


def test_rename_while_stopped_leaves_no_copy_to_change(
    mm: mode_manager.ModeManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    open_profile, change = _cycle_profile(monkeypatch)
    monkeypatch.setattr(shared_state, "current_profile", open_profile)
    monkeypatch.setattr(shared_state, "running_profile", None)
    ui_profile.rename_mode("Orbit", "Low Orbit")
    assert change._target_modes == ["Ground", "Low Orbit", "Space"]


def test_drop_while_running_falls_back_to_a_mode_that_still_exists(
    mm: mode_manager.ModeManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    # "Alpha" is the first top-level mode; the Run is only in it.
    open_profile = Profile()
    open_profile.modes.add_mode("Alpha")
    copy = code_runner.profile_snapshot(open_profile)
    monkeypatch.setattr(shared_state, "current_profile", open_profile)
    monkeypatch.setattr(shared_state, "running_profile", copy)
    mm._mode_stack = [mode_manager.Mode("Alpha", None)]

    ui_profile.delete_mode("Alpha")

    assert mm.current.name == "Default"
    assert [m.name for m in mm._mode_stack] == ["Default"]


def test_drop_fallback_takes_a_child_moved_up(monkeypatch: pytest.MonkeyPatch) -> None:
    p = Profile()
    p.modes.add_mode("Alpha")
    p.modes.add_mode("Zulu")
    p.modes.set_parent("Default", "Zulu")
    p.modes.add_mode("Beta")
    p.modes.set_parent("Beta", "Alpha")
    # Top level: Alpha, Zulu. Without Alpha, Beta moves up and comes first.
    assert mode_manager._first_mode_without(p, "Alpha") == "Beta"
