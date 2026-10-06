# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Journey 7: Keyboard page, Add Key, an action, Run, press the key, Stop.

The user opens the Keyboard card's Configuration page, presses Add Key and
then F: F is listed and selected, and the editor shows it. The user gives
F a Map to vJoy action (vJoy button 4), saves and opens the profile again,
presses Run and then F: vJoy button 4 is held while F is held. Stop while
F is held: Gremlin holds no vJoy device, and F sends nothing while
stopped.

Spec: 05 S72, S73, S74 with Q4, S78, S79; 06 S1, S4, S29, S33. Known gap:
GL-164 (a key added with Add Key shows no binding to add an action to:
Q4 says it should show one empty binding), marked xfail; the journey
then adds the binding with the editor model's newActionSequence (the slot
the removed "New Action Sequence" footer used) to go on.
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
    from gremlin.ui.util import InputListenerModel

    out = j.out
    state = j.backend.uiState

    # The Keyboard card's Configuration page.
    j.ev('openConfigurationForCard(_moduleModel.cardMap("keyboard"))')
    j.wait_until(lambda: state.currentTab == "keyboard", "the Keyboard page")

    def add_key_listener() -> object:
        for listener in j.win.findChildren(InputListenerModel):
            holder = listener.parent()
            if holder is not None and holder.property("text") == "Add Key":
                return listener
        return None

    listener = j.wait_until(add_key_listener, "the Add Key button")
    # Add Key: its record button opens the popup, which turns the listener
    # on; then F. The button's state machine starts once the page is up
    # (a click before that opens the popup with the listener off).
    holder = listener.parent()
    record = next(
        item
        for item in j.walk(holder)
        if item.metaObject().indexOfSignal("clicked()") >= 0
    )
    machine = next(
        c for c in holder.children() if c.metaObject().className() == "StateMachine"
    )
    j.wait_until(lambda: machine.property("running"), "the Add Key button to start")
    j.click(record)
    j.wait_until(lambda: listener.property("enabled"), "the Add Key popup")
    j.key(_F, True)
    j.key(_F, False)
    j.wait_until(
        lambda: (
            state.currentInput is not None
            and state.currentInput.device_guid == dill.UUID_Keyboard
        ),
        "F to be selected",
    )
    ident = state.currentInput
    out["selected"] = [ident.input_type == InputType.Keyboard, ident.input_id]
    keys = j.profile.inputs.get(dill.UUID_Keyboard, [])
    out["listed"] = [item.input_id for item in keys]

    # The editor for F (what the page's InputConfiguration shows).
    editor = j.backend.getInputItem(ident, state.currentInputIndex)
    out["bindings-shown"] = editor.rowCount()
    if editor.rowCount() == 0:
        editor.newActionSequence()
    binding = editor.data(editor.index(0, 0), 0x0100 + 1)
    root = binding.rootAction
    out["offered"] = "Map to vJoy" in root.compatibleActions
    root.appendAction("Map to vJoy", "children")
    vjoy_editor = root.getActions("children")[0]
    vjoy_editor.vjoyDeviceId = 1
    vjoy_editor.vjoyInputId = 4

    _path, _url = j.save_and_reopen("journey7")
    item = j.profile.get_input_item(
        dill.UUID_Keyboard, InputType.Keyboard, ident.input_id, "Default", False
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


@pytest.mark.xfail(
    strict=True, raises=AssertionError, reason="GL-164: a new key shows no binding"
)
def test_a_new_key_shows_one_empty_binding(run: dict) -> None:
    assert step(run, "bindings-shown") == 1


def test_the_key_gets_an_action_that_is_saved(run: dict) -> None:
    assert step(run, "offered") is True
    assert step(run, "reloaded") == [4]


def test_run_sends_the_key_to_vjoy_and_stop_holds_nothing(run: dict) -> None:
    assert step(run, "running") is True
    assert step(run, "held") == [4]
    assert step(run, "released") == []
    assert step(run, "devices-after-stop") == []
    assert step(run, "writes-while-stopped") == []


if __name__ == "__main__":
    main()
