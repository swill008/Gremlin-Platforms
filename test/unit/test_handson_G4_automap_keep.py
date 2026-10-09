# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""08 S105 (D-08-AUTOMAP-KEEP): after Create 1:1 Actions the Auto Mapper
keeps the ticked modules ticked and selected, so Create again works on the
same modules (what is shown is what Create uses).

The old window emptied its selection after Create while the boxes stayed
ticked, so a second Create made nothing. Driven through the real window,
off-screen, in its own process (the journey harness): the boxes are ticked
as a click ticks them, Create is pressed twice (the second time with
Overwrite used inputs on, confirmed), and the result line is read.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "test" / "journeys"))
from _harness import Journey, run_journey, step  # noqa: E402


def story(j: Journey) -> None:
    out = j.out
    j.ev('Helpers.createComponent("DialogAutoMapper.qml", { initialSlug: "pjoy_pro" })')
    win = j.window("Auto Mapper")

    def boxes() -> dict[str, object]:
        return {
            str(it.property("text")): it
            for it in j.walk(win.contentItem())
            if it.metaObject().className().startswith("CheckBox")
        }

    j.wait_until(lambda: "vJoy 1" in boxes(), "the module lists")
    found = boxes()
    out["names"] = sorted(found)
    # The vJoy box ticked as a click ticks it (the stick starts ticked).
    j.ev("toggle(); true", found["vJoy 1"])

    def ticked() -> list[str]:
        return sorted(name for name, box in boxes().items() if box.property("checked"))

    def create() -> None:
        button = next(
            it
            for it in j.walk(win.contentItem())
            if it.property("text") == "Create 1:1 Actions"
        )
        j.click(button)

    out["ticked-before"] = ticked()
    create()
    out["first"] = j.wait_until(
        lambda: (t := j.ev("_statusMessage.text", win)).startswith("Made") and t,
        "the first result",
    )
    out["ticked-after"] = ticked()
    out["selected-after"] = [
        j.ev("JSON.stringify(selectedInputModules)", win),
        j.ev("JSON.stringify(selectedOutputModules)", win),
    ]

    # Create again, Overwrite on: the same modules, so the same actions.
    j.ev("_statusMessage.text = ''", win)
    j.ev("_overwriteNonEmpty.checked = true", win)
    create()
    j.wait_until(
        lambda: j.ev("_question !== null && _question.opened", win), "Overwrite asks"
    )
    j.press_in("_question", "Replace Actions", win)
    out["second"] = j.wait_until(
        lambda: j.ev("_statusMessage.text", win), "the second result"
    )


def main() -> None:
    def before(j: Journey) -> None:
        j.input_module(buttons=[1, 2])
        j.vjoy_module()

    Journey(before).run(story)


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("g4_automap"))


def test_the_ticks_stay_and_are_what_create_uses(run: dict) -> None:
    assert step(run, "ticked-before") == ["pJoy Pro", "vJoy 1"], run.get("names")
    assert step(run, "first").startswith("Made "), run["first"]
    assert not step(run, "first").startswith("Made 0 "), run["first"]
    assert step(run, "ticked-after") == ["pJoy Pro", "vJoy 1"]
    inputs, outputs = step(run, "selected-after")
    assert '"pjoy_pro":true' in inputs, inputs
    assert '"vjoy_1":true' in outputs, outputs


def test_create_again_works_on_the_same_modules(run: dict) -> None:
    made = step(run, "first").split(";")[0]  # "Made N actions"
    assert step(run, "second").startswith(made + ";"), run["second"]


if __name__ == "__main__":
    main()
