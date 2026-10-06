# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Journey 10: Stop during a Tempo long press: nothing fires after Stop.

In the Configuration pane the user gives stick button 1 a Tempo: a short
press sends vJoy button 5, a long press (over 0.6 s) sends vJoy button 6.
OK, save, open again, Run. A long press first works: held past the time,
vJoy button 6 goes down; released, it comes up. Then the user presses the
button again and presses Stop before the 0.6 s are up. After Stop nothing
reaches vJoy: no device is opened again and nothing is written, also
after the Tempo time has passed.

Spec: 06 S4 (nothing is sent while stopped), S29, S30 (no Tempo, Double
Tap or Smart Toggle timer fires after Stop); 05 S91; 01 S90, S91. Was
gap GL-047 / AU-116: the timer is now a run_scope timer, cancelled at Stop.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _harness import Journey, run_journey, step  # noqa: E402

_THRESHOLD = 0.6


def story(j: Journey) -> None:
    from gremlin.types import InputType

    out = j.out
    stick = j.stick()
    uid = stick.device_guid.uuid

    # The pane: a Tempo on button 1 (short: vJoy 5, long: vJoy 6), OK.
    catalog = j.open_configuration("pjoy_pro")
    catalog.beginPane(j.device_index(catalog, "button", 1), -1)
    root = j.pane_actions(catalog)[0]
    root.appendAction("Tempo", "children")
    tempo = root.getActions("children")[0]
    tempo.threshold = _THRESHOLD
    for container, target in (("short", 5), ("long", 6)):
        tempo.appendAction("Map to vJoy", container)
        editor = tempo.getActions(container)[0]
        editor.vjoyDeviceId = 1
        editor.vjoyInputId = target
    catalog.commitPane()
    catalog.endPane()
    j.save_and_reopen("journey10")
    item = j.profile.get_input_item(uid, InputType.JoystickButton, 1, "Default", False)
    saved = item.action_sequences[0].root_action.get_actions()[0][0]
    out["saved"] = [
        saved.threshold,
        [a.vjoy_input_id for a in saved.short_actions],
        [a.vjoy_input_id for a in saved.long_actions],
    ]

    j.backend.toggleActiveState()
    out["running"] = j.backend.runner.is_running()
    # A long press works while running.
    j.press(stick, 1, True)
    out["long-press"] = j.await_value(j.vjoy.held_buttons, [6], _THRESHOLD + 5)
    j.press(stick, 1, False)
    out["long-release"] = j.await_value(j.vjoy.held_buttons, [])

    # Press again, Stop before the Tempo time is up.
    j.press(stick, 1, True)
    j.backend.toggleActiveState()
    out["running-after-stop"] = j.backend.runner.is_running()
    writes_at_stop = len(j.vjoy.all_writes())
    opened_at_stop = sum(len(d) for d in j.vjoy.opened.values())
    # Past the Tempo time: anything still armed would have fired by now.
    j.await_value(
        lambda: len(j.vjoy.all_writes()) > writes_at_stop, True, _THRESHOLD + 1.5
    )
    out["writes-after-stop"] = j.vjoy.all_writes()[writes_at_stop:]
    out["opened-after-stop"] = (
        sum(len(d) for d in j.vjoy.opened.values()) - opened_at_stop
    )
    out["held-after-stop"] = sorted(j.vjoy.vjoy_devices)
    j.press(stick, 1, False)


def main() -> None:
    def before(j: Journey) -> None:
        j.input_module()
        j.vjoy_module()

    Journey(before).run(story)


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("j10"))


def test_the_tempo_is_made_in_the_pane_and_saved(run: dict) -> None:
    assert step(run, "saved") == [_THRESHOLD, [5], [6]]


def test_a_long_press_works_while_running(run: dict) -> None:
    assert step(run, "running") is True
    assert step(run, "long-press") == [6]
    assert step(run, "long-release") == []
    assert step(run, "running-after-stop") is False


def test_nothing_fires_after_stop(run: dict) -> None:
    assert step(run, "writes-after-stop") == []
    assert step(run, "opened-after-stop") == 0
    assert step(run, "held-after-stop") == []


if __name__ == "__main__":
    main()
