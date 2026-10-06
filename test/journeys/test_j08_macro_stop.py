# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Journey 8: Stop in the middle of a macro releases the key it holds.

In the Configuration pane the user gives stick button 1 a Macro: press A,
pause 3 seconds, release A. OK, save, open again, Run. A press of the
button starts the macro: A goes down. Stop during the pause: A comes up at
once (not when the pause would have ended), and the release the macro
still had queued is never sent after Stop.

No key reaches the PC: key output stays in the test process
(test/fake_input.py) and is read from there.

Spec: 06 S19, S20 (Stop ends every macro at its next step, a Pause at
once), S21 (Stop releases every key a macro holds), S65; 05 (Macro editor,
draft until OK). S26, S30 and S31 are open gaps elsewhere (vJoy relative
axis loop, timers, keys sent by scripts); this path doesn't reach them.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _harness import Journey, run_journey, step  # noqa: E402

_A = 0x1E  # scan code of A
_PAUSE = 3.0


def story(j: Journey) -> None:
    import time

    import dill
    from gremlin import event_handler
    from gremlin.types import InputType

    out = j.out
    stick = j.stick()
    sent = j.fake_input.sent

    def a_keys() -> list[bool]:
        return [entry[3] for entry in sent if entry[0] == "key" and entry[1] == _A]

    # The pane: a Macro on button 1 (press A, pause, release A), OK.
    catalog = j.open_configuration("pjoy_pro")
    catalog.beginPane(j.device_index(catalog, "button", 1), -1)
    root = j.pane_actions(catalog)[0]
    root.appendAction("Macro", "children")
    macro_editor = root.getActions("children")[0]
    a_key = event_handler.Event(
        InputType.Keyboard, (_A, False), dill.UUID_Keyboard, "Default", is_pressed=True
    )
    for kind in ("key", "pause", "key"):
        macro_editor.addAction(kind)
    steps = macro_editor.actions
    models = [steps.data(steps.index(row, 0), 0x0100 + 1) for row in range(3)]
    models[0].updateKey([a_key])
    models[0].isPressed = True
    models[1].duration = _PAUSE
    models[2].updateKey([a_key])
    models[2].isPressed = False
    catalog.commitPane()
    catalog.endPane()
    _path, _url = j.save_and_reopen("journey8")
    uid = stick.device_guid.uuid
    item = j.profile.get_input_item(uid, InputType.JoystickButton, 1, "Default", False)
    saved = item.action_sequences[0].root_action.get_actions()[0][0]
    out["saved-steps"] = [type(step).__name__ for step in saved.actions]

    j.backend.toggleActiveState()
    out["running"] = j.backend.runner.is_running()
    j.press(stick, 1, True)
    j.press(stick, 1, False)
    j.wait_until(lambda: a_keys() == [True], "A to go down")
    started = time.monotonic()
    j.backend.toggleActiveState()
    out["running-after-stop"] = j.backend.runner.is_running()
    out["after-stop"] = j.await_value(a_keys, [True, False])
    out["released-before-the-pause-ended"] = time.monotonic() - started < _PAUSE
    # The release the macro had queued never comes: wait past the pause.
    out["later"] = j.await_value(a_keys, [True, False, False], _PAUSE + 1.0)


def main() -> None:
    def before(j: Journey) -> None:
        j.input_module()

    Journey(before).run(story)


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("j08"))


def test_the_macro_is_made_in_the_pane_and_saved(run: dict) -> None:
    assert step(run, "saved-steps") == ["KeyAction", "PauseAction", "KeyAction"]


def test_stop_mid_macro_releases_the_held_key_at_once(run: dict) -> None:
    assert step(run, "running") is True
    assert step(run, "running-after-stop") is False
    assert step(run, "after-stop") == [True, False]
    assert step(run, "released-before-the-pause-ended") is True


def test_nothing_is_sent_after_stop(run: dict) -> None:
    assert step(run, "later") == [True, False]


if __name__ == "__main__":
    main()
