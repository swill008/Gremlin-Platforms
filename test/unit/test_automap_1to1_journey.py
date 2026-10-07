# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""08 S90-S94: Create 1:1 Actions, through the real Auto Mapper window.

Driven off-screen in its own process (the journey harness): two sticks with
input modules claiming axes, buttons 1-8 and hats; the vJoy 1 output module
claiming everything.

Part 1 (S90): ticking a stick and vJoy 1 gives each claimed control a Map to
vJoy action to the same number on vJoy 1 (X to X, button 1 to button 1...).
The older tests only counted the actions ("Made N actions").

Part 2 (S92/S94/S103/S109): a second stick ticked onto vJoy 1, whose outputs
the first stick already sends to. S94 keeps those outputs for the first stick,
so the second stick's controls get nothing; the result line then counted them
as inputs that kept their actions although they had none, and did not list
them as skipped. S109 (D-08-AUTOMAP-REASON): they are not counted as kept and
are listed by range with the reason.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "test" / "journeys"))
from _harness import Journey, run_journey, step  # noqa: E402


def _targets(j: Journey, uid: object) -> list[list]:
    """[[kind, input id, vJoy id, vJoy kind, vJoy id]] for one stick."""
    from gremlin.types import InputType

    rows = []
    for item in j.profile.inputs.get(uid, []):
        for binding in item.action_sequences:
            for action in binding.root_action.get_actions()[0]:
                rows.append(
                    [
                        InputType.to_string(item.input_type),
                        int(item.input_id),
                        getattr(action, "vjoy_device_id", None),
                        InputType.to_string(getattr(action, "vjoy_input_type", None))
                        if hasattr(action, "vjoy_input_type")
                        else action.name,
                        getattr(action, "vjoy_input_id", None),
                    ]
                )
    return sorted(rows)


def story(j: Journey) -> None:
    out = j.out
    j.ev('Helpers.createComponent("DialogAutoMapper.qml", {})')
    win = j.window("Auto Mapper")

    def boxes() -> dict[str, object]:
        return {
            str(it.property("text")): it
            for it in j.walk(win.contentItem())
            if it.metaObject().className().startswith("CheckBox")
        }

    def tick(*names: str) -> None:
        for name, box in boxes().items():
            if bool(box.property("checked")) != (name in names):
                j.ev("toggle(); true", box)

    def create() -> str:
        j.ev("_statusMessage.text = ''", win)
        button = next(
            it
            for it in j.walk(win.contentItem())
            if it.property("text") == "Create 1:1 Actions"
        )
        j.click(button)
        return j.wait_until(lambda: j.ev("_statusMessage.text", win), "the result")

    j.wait_until(
        lambda: {"pJoy Pro", "Stick B", "vJoy 1"} <= set(boxes()), "the module lists"
    )
    first = j.stick("pJoy Pro").device_guid.uuid
    second = j.stick("Stick B").device_guid.uuid

    tick("pJoy Pro", "vJoy 1")
    out["first"] = create()
    out["first-targets"] = _targets(j, first)

    tick("Stick B", "vJoy 1")
    out["second"] = create()
    out["second-targets"] = _targets(j, second)


def main() -> None:
    def before(j: Journey) -> None:
        j.input_module(buttons=list(range(1, 9)))
        guid = j.add_stick("Stick B", 3)
        j.input_module(
            name="Stick B", buttons=list(range(1, 9)), guid=guid, slug="stick_b"
        )
        j.vjoy_module()

    Journey(before).run(story)


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("automap_1to1"))


def test_each_control_goes_to_the_same_number(run: dict) -> None:
    targets = step(run, "first-targets")
    assert step(run, "first").startswith("Made "), run["first"]
    by_input = {
        (kind, hid): (vid, vkind, vnum) for kind, hid, vid, vkind, vnum in targets
    }
    for button in range(1, 9):
        assert by_input.get(("button", button)) == (1, "button", button), targets
    for axis in (1, 2, 3):  # X, Y, Z
        assert by_input.get(("axis", axis)) == (1, "axis", axis), targets
    for hat in (1, 2):
        assert by_input.get(("hat", hat)) == (1, "hat", hat), targets
    # Nothing to another number or another vJoy.
    assert all(hid == vnum and vid == 1 for _k, hid, vid, _vk, vnum in targets)


def test_outputs_used_by_another_stick_are_not_reported_as_kept(run: dict) -> None:
    text = step(run, "second")
    buttons = [row for row in step(run, "second-targets") if row[0] == "button"]
    # S94: vJoy 1 buttons 1-8 already belong to the first stick.
    assert buttons == [], buttons
    # The second stick's buttons had no actions: none were kept.
    assert "0 inputs kept their actions" in text, text
    # S92 style: what was not made is listed by range, with the reason.
    assert (
        "Skipped vJoy 1 buttons 1-8: already used by another input in this mode."
        in text
    ), text


if __name__ == "__main__":
    main()
