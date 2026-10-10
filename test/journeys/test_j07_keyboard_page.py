# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Journey 7: Keyboard page, Add Key, an action, Run, press the key, Stop.

The user opens the Keyboard card's Configuration page, presses Add Key and
then F: F is listed and selected, and the editor shows it. The user gives
F a Map to vJoy action (vJoy button 4), saves and opens the profile again,
presses Run and then F: vJoy button 4 is held while F is held. Stop while
F is held: Gremlin holds no vJoy device, and F sends nothing while
stopped.

The action is given in the page's own pane (KeyboardLayoutModel's draft
pane, which OK writes, 05 Q5): a new key shows one empty binding there (Q4).

Spec: 05 S72, S73, S74 with Q4, Q5, S78, S79, S128; 06 S1, S4, S29, S33.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _harness import Journey, run_journey, step  # noqa: E402

_F = 0x21  # scan code of F


def story(j: Journey) -> None:
    import dill
    from gremlin.types import InputType
    from gremlin.ui.keyboard_layout import KeyboardLayoutModel, key_row
    from gremlin.ui.util import InputListenerModel

    out = j.out
    state = j.backend.uiState

    # The Keyboard card's Configuration page.
    j.ev('openConfigurationForCard(_moduleModel.cardMap("keyboard"))')
    j.wait_until(lambda: state.currentTab == "keyboard", "the Keyboard page")
    page = j.wait_until(lambda: j.ev("keyboardPane()"), "the Keyboard page item")
    layout = j.wait_until(
        lambda: page.findChild(KeyboardLayoutModel), "the page's layout model"
    )
    add_key = j.wait_until(
        lambda: next(
            (i for i in j.walk(page) if i.objectName() == "keyboardAddKey"), None
        ),
        "the Add Key button",
    )
    listener = j.wait_until(
        lambda: page.findChild(InputListenerModel), "the Add Key listener"
    )
    # Add Key opens its popup, which turns the listener on; then F.
    j.click(add_key)
    j.wait_until(lambda: listener.property("enabled"), "the Add Key popup")
    j.key(_F, True)
    j.key(_F, False)
    keys = j.wait_until(
        lambda: j.profile.inputs.get(dill.UUID_Keyboard, []), "F to be added"
    )
    code = tuple(keys[0].input_id)
    row = key_row(code)
    j.wait_until(lambda: page.property("paneKey") == row, "the pane on F")
    j.settle()
    out["selected"] = [
        keys[0].input_type == InputType.Keyboard and layout._selected == [row],
        list(code),
    ]
    out["listed"] = [list(item.input_id) for item in keys]

    # The editor for F: the Keyboard page's pane, a draft that OK writes.
    editor = layout.paneModel
    out["bindings-shown"] = editor.rowCount()
    binding = editor.data(editor.index(0, 0), 0x0100 + 1)
    root = binding.rootAction
    out["offered"] = "Map to vJoy" in root.compatibleActions
    root.appendAction("Map to vJoy", "children")
    vjoy_editor = root.getActions("children")[0]
    vjoy_editor.vjoyDeviceId = 1
    vjoy_editor.vjoyInputId = 4
    out["ok"] = layout.commitPane() >= 0

    _path, _url = j.save_and_reopen("journey7")
    item = j.profile.get_input_item(
        dill.UUID_Keyboard, InputType.Keyboard, code, "Default", False
    )
    out["reloaded"] = [
        a.vjoy_input_id
        for seq in item.action_sequences
        for a in seq.root_action.get_actions()[0]
    ]

    j.backend.toggleActiveState()
    out["running"] = j.backend.runner.is_running()
    j.key(_F, True)
    out["held"] = j.await_value(j.vjoy.held_buttons, [4])
    j.key(_F, False)
    out["released"] = j.await_value(j.vjoy.held_buttons, [])
    j.key(_F, True)
    j.wait_until(lambda: j.vjoy.held_buttons() == [4], "vJoy button 4 down again")
    j.backend.toggleActiveState()
    out["devices-after-stop"] = sorted(j.vjoy.vjoy_devices)
    writes = len(j.vjoy.all_writes())
    j.key(_F, False)
    j.key(_F, True)
    j.key(_F, False)
    j.settle()
    out["writes-while-stopped"] = j.vjoy.all_writes()[writes:]


def main() -> None:
    def before(j: Journey) -> None:
        j.vjoy_module()

    Journey(before).run(story)


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("j07"))


def test_add_key_lists_and_selects_the_pressed_key(run: dict) -> None:
    kind_ok, key = step(run, "selected")
    assert kind_ok is True
    assert step(run, "listed") == [key]


def test_a_new_key_shows_one_empty_binding(run: dict) -> None:
    assert step(run, "bindings-shown") == 1


def test_the_key_gets_an_action_that_is_saved(run: dict) -> None:
    assert step(run, "offered") is True
    assert step(run, "ok") is True
    assert step(run, "reloaded") == [4]


def test_run_sends_the_key_to_vjoy_and_stop_holds_nothing(run: dict) -> None:
    assert step(run, "running") is True
    assert step(run, "held") == [4]
    assert step(run, "released") == []
    assert step(run, "devices-after-stop") == []
    assert step(run, "writes-while-stopped") == []


if __name__ == "__main__":
    main()
