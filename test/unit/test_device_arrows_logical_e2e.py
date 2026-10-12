# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The title's device arrows step on and back through the Logical Device
page (to-do 132), end to end on the real program.

A journey (test/journeys/_harness.py): the app is built off-screen in its
own process with a temporary USERPROFILE and two fake sticks. The story
opens Device Bindings on the first stick and presses the title's next
arrow round the whole input cycle (_moduleModel.pileLeaders("source"):
sticks, Keyboard, OSC, Logical Device), then the previous arrow. Before
the fix the Logical Device page hid the arrows and cycleModules returned
at once for "logical": a dead end.

Spec: 01 S58b (new, to-do 132; the lead asks the user).
"""

from __future__ import annotations

import pathlib
import sys
from typing import Any

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "test" / "journeys"))
from _harness import (  # noqa: E402  # pyright: ignore[reportMissingImports]
    Journey,
    run_journey,
)

NEXT, PREVIOUS = "", ""


# +-------------------------------------------------------------------------
# | Script side (the child process)


def _arrow(j: Journey, glyph: str) -> Any:  # noqa: ANN401
    """The title's shown, enabled previous or next arrow, or None."""
    for item in j.walk(j.win.contentItem()):
        if (
            item.property("text") == glyph
            and item.isVisible()
            and item.property("enabled")
        ):
            return item
    return None


def _where(j: Journey) -> dict:
    return {
        "tab": str(j.ev("uiState.currentTab")),
        "direction": str(j.ev("configDirection")),
        "focus": str(j.ev("_moduleModel.focusedSlug")),
        "next": _arrow(j, NEXT) is not None,
        "previous": _arrow(j, PREVIOUS) is not None,
    }


def _press(j: Journey, glyph: str) -> dict:
    arrow = _arrow(j, glyph)
    if arrow is not None:
        j.click(arrow)
        j.settle()
    return _where(j)


def story(j: Journey) -> None:
    out = j.out
    j.open_device_bindings("pjoy_pro")
    j.settle()
    order = [str(s) for s in j.ev("_moduleModel.pileLeaders('source')")]
    out["order"] = order
    out["start"] = _where(j)
    # Round the cycle and one more, so the step after Logical Device shows.
    out["forward"] = [_press(j, NEXT) for _ in range(len(order) + 1)]
    out["back"] = [_press(j, PREVIOUS) for _ in range(len(order) + 1)]


def main() -> None:
    def before(j: Journey) -> None:
        bravo = j.add_stick("Stick Bravo", 21)
        j.input_module(buttons=[1])
        j.input_module("Stick Bravo", buttons=[1], guid=bravo)

    Journey(before).run(story)


# +-------------------------------------------------------------------------
# | Pytest side


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("device_arrows"))


def _focus_after_logical(out: dict, steps: list, step: int) -> str:
    order = out["order"]
    at = [s["direction"] for s in steps].index("logical")
    assert at + 1 < len(steps), steps
    want = order[(order.index("logical") + step) % len(order)]
    assert steps[at + 1]["focus"] == want, (want, steps)
    return want


def test_the_cycle_holds_the_logical_device(run: dict) -> None:
    assert "logical" in run["order"], run["order"]
    assert run["start"]["focus"] == "pjoy_pro", run["start"]


def test_the_arrows_show_on_the_logical_device_page(run: dict) -> None:
    logical = [s for s in run["forward"] if s["direction"] == "logical"]
    assert logical, run["forward"]
    assert all(s["next"] and s["previous"] for s in logical), logical


def test_next_moves_on_from_the_logical_device(run: dict) -> None:
    want = _focus_after_logical(run, run["forward"], 1)
    assert run["forward"][-1]["direction"] != "logical" or want == "logical"


def test_previous_moves_back_from_the_logical_device(run: dict) -> None:
    _focus_after_logical(run, run["back"], -1)


def test_a_full_round_comes_back_to_the_start(run: dict) -> None:
    order = run["order"]
    assert run["forward"][len(order) - 1]["focus"] == "pjoy_pro", run["forward"]
    assert run["back"][len(order) - 1]["focus"] == run["forward"][-1]["focus"]


if __name__ == "__main__":
    main()
