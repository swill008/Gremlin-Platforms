# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Journey 1: edit an action, save, reload, Run, press, Stop.

The user loads a profile whose stick button 1 sends vJoy button 1, opens
the stick's Configuration page, changes the action in the pane to send
vJoy button 5 and presses OK, saves the profile, opens it again: the
change is there. Run, press the stick button: vJoy button 5 follows the
button (down, then up). Press it again and Stop while it is held: Gremlin
holds no vJoy device any more, and the button sends nothing while
stopped.

Spec: 05 (the pane edits a draft until OK, section 1), 04 (save and
reload), 06 S1, S4, S29, S33, S47. No known gap.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _harness import Journey, run_journey, step  # noqa: E402


def story(j: Journey) -> None:
    from PySide6 import QtCore

    from gremlin import plugin_manager, util
    from gremlin.types import InputType

    out = j.out
    stick = j.stick()
    uid = stick.device_guid.uuid

    # A profile on disk: stick button 1 -> vJoy 1 button 1 (made in the
    # open profile, saved, then a new profile opened).
    action = plugin_manager.PluginManager().create_instance(
        "Map to vJoy", InputType.JoystickButton
    )
    action.vjoy_device_id = 1
    action.vjoy_input_id = 1
    action.vjoy_input_type = InputType.JoystickButton
    item = j.profile.get_input_item(uid, InputType.JoystickButton, 1, "Default", True)
    item.add_item_binding().root_action.insert_action(action, "children")
    path = util.profiles_dir() / "journey1.xml"
    url = QtCore.QUrl.fromLocalFile(str(path)).toString()
    out["first-save"] = j.backend.saveProfile(url)
    j.backend.newProfile()

    j.backend.loadProfile(url)
    out["loaded"] = pathlib.Path(j.backend.profilePath()) == path

    # Configuration page: open button 1 in the pane, change the target, OK.
    catalog = j.open_configuration("pjoy_pro")
    index = j.device_index(catalog, "button", 1)
    catalog.beginPane(index, -1)
    actions = j.pane_actions(catalog)
    out["pane-actions"] = [a.name for a in actions]
    vjoy_editor = actions[1]
    vjoy_editor.vjoyInputId = 5
    live = j.profile.get_input_item(uid, InputType.JoystickButton, 1, "Default", False)
    out["before-ok"] = (
        live.action_sequences[0].root_action.get_actions()[0][0].vjoy_input_id
    )
    out["dirty"] = catalog.paneDirty()
    catalog.commitPane()
    catalog.reload()
    catalog.endPane()
    live = j.profile.get_input_item(uid, InputType.JoystickButton, 1, "Default", False)
    out["after-ok"] = (
        live.action_sequences[0].root_action.get_actions()[0][0].vjoy_input_id
    )

    # Save, then open another profile and this one again.
    out["saved"] = j.backend.saveProfile(url)
    j.backend.newProfile()
    j.backend.loadProfile(url)
    again = j.profile.get_input_item(uid, InputType.JoystickButton, 1, "Default", False)
    targets = [
        (a.vjoy_device_id, a.vjoy_input_id)
        for seq in again.action_sequences
        for a in seq.root_action.get_actions()[0]
    ]
    out["reloaded"] = targets

    # Run, press and release the stick button.
    j.backend.toggleActiveState()
    out["running"] = j.backend.runner.is_running()
    j.press(stick, 1, True)
    j.wait_until(lambda: j.vjoy.held_buttons() == [5], "vJoy button 5 down")
    out["held-while-pressed"] = j.vjoy.held_buttons()
    j.press(stick, 1, False)
    j.wait_until(lambda: j.vjoy.held_buttons() == [], "vJoy button 5 up")
    out["held-after-release"] = j.vjoy.held_buttons()

    # Press again and Stop while it is held.
    j.press(stick, 1, True)
    j.wait_until(lambda: j.vjoy.held_buttons() == [5], "vJoy button 5 down again")
    j.backend.toggleActiveState()
    out["running-after-stop"] = j.backend.runner.is_running()
    out["devices-held-after-stop"] = sorted(j.vjoy.vjoy_devices)
    writes_at_stop = len(j.vjoy.all_writes())
    j.press(stick, 1, False)
    j.press(stick, 1, True)
    j.settle()
    out["writes-while-stopped"] = j.vjoy.all_writes()[writes_at_stop:]
    out["devices-held-while-stopped"] = sorted(j.vjoy.vjoy_devices)
    out["buttons-ever-written"] = sorted(
        {index for kind, index, _value in j.vjoy.all_writes() if kind == "button"}
    )


def main() -> None:
    def before(j: Journey) -> None:
        j.input_module()
        j.vjoy_module()

    Journey(before).run(story)


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("j01"))


def test_the_pane_edits_a_draft_until_ok(run: dict) -> None:
    assert step(run, "first-save") is True
    assert step(run, "loaded") is True
    assert step(run, "pane-actions") == ["Root", "Map to vJoy"]
    assert step(run, "dirty") is True
    assert step(run, "before-ok") == 1
    assert step(run, "after-ok") == 5


def test_the_edit_is_saved_and_read_back(run: dict) -> None:
    assert step(run, "saved") is True
    assert step(run, "reloaded") == [[1, 5]]


def test_run_sends_the_button_to_vjoy(run: dict) -> None:
    assert step(run, "running") is True
    assert step(run, "held-while-pressed") == [5]
    assert step(run, "held-after-release") == []
    # Only the edited target was ever sent.
    assert step(run, "buttons-ever-written") == [5]


def test_stop_holds_nothing_and_sends_nothing(run: dict) -> None:
    assert step(run, "running-after-stop") is False
    assert step(run, "devices-held-after-stop") == []
    assert step(run, "writes-while-stopped") == []
    assert step(run, "devices-held-while-stopped") == []


if __name__ == "__main__":
    main()
