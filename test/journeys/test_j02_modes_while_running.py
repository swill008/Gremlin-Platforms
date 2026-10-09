# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Journey 2: rename and delete modes while running; Cycle keeps working.

The profile has modes Default and, under it, Ground, Orbit and Space;
stick button 2 (set in Default, so every mode has it) cycles through all
four (Change Mode, Cycle). The user saves it, opens it again and presses
Run. One press goes to Ground. With the profile still
running the user opens Manage Modes and renames Orbit to "Low Orbit": the
next press goes to Low Orbit. Then the user deletes Space (the window
asks first and counts its bindings): the next press skips it and goes back
to Default, and the one after to Ground. Stop, save, open again: the
Cycle names the renamed mode.

Spec: 04 S44 (rename moves a running Cycle), S45, S46, S46a, S49 (mode edits
while running), S56, S57 (Cycle skips a deleted mode); 06 S34; 01 S140. No known
gap.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _harness import Journey, run_journey, step  # noqa: E402


def story(j: Journey) -> None:
    from PySide6 import QtCore

    from action_plugins.change_mode import ChangeType
    from gremlin import mode_manager, plugin_manager, util
    from gremlin.types import InputType
    from gremlin.ui.profile import ModeHierarchyModel

    out = j.out
    stick = j.stick()
    uid = stick.device_guid.uuid
    profile = j.profile
    # Each mode under Default, so button 2 cycles in every mode.
    for name in ("Ground", "Orbit", "Space"):
        profile.modes.add_mode(name)
        profile.modes.set_parent(name, "Default")
    cycle = plugin_manager.PluginManager().create_instance(
        "Change Mode", InputType.JoystickButton
    )
    cycle.change_type = ChangeType.Cycle
    cycle.target_modes = ["Default", "Ground", "Orbit", "Space"]
    item = profile.get_input_item(uid, InputType.JoystickButton, 2, "Default", True)
    item.add_item_binding().root_action.insert_action(cycle, "children")
    # Space has a binding of its own (Manage Modes counts it).
    space_item = profile.get_input_item(uid, InputType.JoystickButton, 3, "Space", True)
    space_item.add_item_binding().root_action.insert_action(
        plugin_manager.PluginManager().create_instance(
            "Change Mode", InputType.JoystickButton
        ),
        "children",
    )

    path = util.profiles_dir() / "journey2.xml"
    url = QtCore.QUrl.fromLocalFile(str(path)).toString()
    out["first-save"] = j.backend.saveProfile(url)
    j.backend.newProfile()
    j.backend.loadProfile(url)
    out["modes-loaded"] = sorted(j.profile.modes.mode_names())

    def current() -> str:
        return mode_manager.ModeManager().current.name

    def tap(expected: str) -> str:
        j.press(stick, 2, True)
        j.press(stick, 2, False)
        return j.await_value(current, expected)

    j.backend.uiState.setCurrentMode("Default")
    j.backend.toggleActiveState()
    out["running"] = j.backend.runner.is_running()
    out["start"] = current()
    out["after-press-1"] = tap("Ground")

    # Manage Modes, while the profile runs.
    j.ev('Helpers.createComponent("DialogManageModes.qml")')
    manage = j.window("Manage Modes")
    hierarchy = j.wait_until(
        lambda: manage.findChild(ModeHierarchyModel), "the Manage Modes model"
    )
    out["window-modes"] = sorted(hierarchy.modeStringList())
    j.ev('modeHierarchy.renameMode("Orbit", "Low Orbit")', manage)
    out["modes-after-rename"] = sorted(j.profile.modes.mode_names())
    out["after-press-2"] = tap("Low Orbit")

    # The shared question (01 S140) opens on the window's root item.
    j.ev('confirmDelete("Space")', manage)
    j.wait_until(lambda: j.item(manage, "confirmAction"), "the delete question")
    out["delete-asks"] = j.item(manage, "confirmTitle").property("text")
    out["delete-says"] = j.item(manage, "confirmText").property("text")
    go = j.item(manage, "confirmAction")
    out["delete-button"] = go.property("text")
    out["delete-button-red"] = j.ev(
        "String(color) === String(Style.danger)",
        j.item(manage, "dangerButtonFill"),
    )
    # A real click on the red button goes ahead.
    centre = go.mapToScene(QtCore.QPointF(go.width() / 2, go.height() / 2))
    j.QTest.mouseClick(
        manage, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, centre.toPoint()
    )
    j.wait_until(
        lambda: "Space" not in j.profile.modes.mode_names(), "Space to be deleted"
    )
    out["modes-after-delete"] = sorted(j.profile.modes.mode_names())
    out["undo-after-delete"] = j.item(manage, "undoBarUndo").property("enabled")
    out["still-running"] = j.backend.runner.is_running()
    out["after-press-3"] = tap("Default")
    out["after-press-4"] = tap("Ground")

    # Stop, save, open again: the Cycle names the new mode name.
    j.backend.toggleActiveState()
    out["saved"] = j.backend.saveProfile(url)
    j.backend.newProfile()
    j.backend.loadProfile(url)
    again = j.profile.get_input_item(uid, InputType.JoystickButton, 2, "Default", False)
    action = again.action_sequences[0].root_action.get_actions()[0][0]
    out["cycle-after-reload"] = list(action.target_modes)
    out["modes-after-reload"] = sorted(j.profile.modes.mode_names())


def main() -> None:
    def before(j: Journey) -> None:
        j.input_module()

    Journey(before).run(story)


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("j02"))


def test_cycle_runs_from_the_loaded_profile(run: dict) -> None:
    assert step(run, "first-save") is True
    assert step(run, "modes-loaded") == ["Default", "Ground", "Orbit", "Space"]
    assert step(run, "running") is True
    assert step(run, "start") == "Default"
    assert step(run, "after-press-1") == "Ground"


def test_a_rename_while_running_moves_the_cycle(run: dict) -> None:
    assert step(run, "window-modes") == ["Default", "Ground", "Orbit", "Space"]
    assert step(run, "modes-after-rename") == ["Default", "Ground", "Low Orbit"] + [
        "Space"
    ]
    assert step(run, "after-press-2") == "Low Orbit"


def test_a_mode_deleted_while_running_is_skipped(run: dict) -> None:
    assert step(run, "delete-asks") == "Delete mode Space?"
    assert step(run, "delete-says").startswith("1 binding goes with it.")
    assert step(run, "delete-button") == "Delete Mode"
    assert step(run, "delete-button-red") is True
    assert step(run, "modes-after-delete") == ["Default", "Ground", "Low Orbit"]
    assert step(run, "undo-after-delete") is True
    assert step(run, "still-running") is True
    assert step(run, "after-press-3") == "Default"
    assert step(run, "after-press-4") == "Ground"


def test_the_renamed_cycle_is_saved(run: dict) -> None:
    assert step(run, "saved") is True
    assert step(run, "modes-after-reload") == ["Default", "Ground", "Low Orbit"]
    assert "Low Orbit" in step(run, "cycle-after-reload")
    assert "Orbit" not in step(run, "cycle-after-reload")


if __name__ == "__main__":
    main()
