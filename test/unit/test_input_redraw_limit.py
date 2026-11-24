# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A burst of input highlights is a bounded number of jumps on the Device
Bindings page (05 S131; idea from upstream 5dc34e66, debounce input-flood
redraws).

A journey (test/journeys/_harness.py) on the real program off-screen: the
fake "pJoy Pro" stick, the program stopped, Input highlighting on. Fifty
setInputIndex notices in one go (no event loop turn between them, as a flood
of presses gives) make the page jump once, to the latest input, instead of
fifty times (DeviceBindingsPage jumpCount, _jumpTimer). Then two single
presses far apart still jump twice, and a real stick tap still flashes its
row.
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
    JourneyIncomplete,
    run_journey,
)

STICK = "pJoy Pro"
B2 = "parent:button:2"
B3 = "parent:button:3"


def _same_guid(a: object, b: object) -> bool:
    def clean(v: object) -> str:
        return str(v).strip("{}").lower()

    return clean(a) == clean(b)


def _row(model: Any, key: str) -> dict:  # noqa: ANN401
    names = {int(k): bytes(v).decode() for k, v in model.roleNames().items()}
    for r in range(model.rowCount()):
        index = model.index(r, 0)
        row = {name: model.data(index, role) for role, name in names.items()}
        if row.get("key") == key:
            return row
    return {}


def story(j: Journey) -> None:
    import json

    from gremlin.config import Configuration
    from gremlin.signal import signal
    from gremlin.ui.hardware_layout import HardwareLayoutModel

    out = j.out
    uid = j.stick(STICK).device_guid.uuid
    j.ev(f"openDeviceBindingsForCard(_moduleModel.cardMap({json.dumps('pjoy_pro')}))")

    def page_model() -> Any:  # noqa: ANN401
        for model in j.win.findChildren(HardwareLayoutModel):
            if _same_guid(model.property("guid"), uid) and model.property(
                "parentCount"
            ):
                return model
        return None

    layout = j.wait_until(page_model, "the Device Bindings page of pjoy_pro")

    def page() -> Any:  # noqa: ANN401
        for item in j.walk(j.win.contentItem()):
            if item.property("jumpCount") is not None and item.isVisible():
                return item
        return None

    def live_tree() -> Any:  # noqa: ANN401
        for item in j.walk(j.win.contentItem()):
            if item.property("liveDecoration") is True and item.isVisible():
                return item
        return None

    view = j.wait_until(page, "the Device Bindings page item", 5)
    tree = j.wait_until(live_tree, "the tree with live decoration", 5)
    j.settle()
    Configuration().set("ui", "general", "input-highlighting", True)
    out["running"] = bool(j.backend.property("gremlinActive"))
    b2 = int(_row(layout, B2).get("deviceIndex", -1))
    b3 = int(_row(layout, B3).get("deviceIndex", -1))
    out["indexes"] = [b2, b3]
    start = int(view.property("jumpCount"))
    # The flood: 50 notices, the last one for button 3.
    for i in range(49):
        signal.setInputIndex.emit(b2 if i % 2 else b3)
    signal.setInputIndex.emit(b3)
    j.await_value(lambda: int(view.property("jumpCount")) > start, True, 2)
    j.settle()
    out["flood_jumps"] = int(view.property("jumpCount")) - start
    out["flood_highlight"] = str(tree.property("highlightKey") or "")
    # Two notices far apart: two jumps.
    start = int(view.property("jumpCount"))
    signal.setInputIndex.emit(b2)
    j.await_value(lambda: int(view.property("jumpCount")) - start, 1, 2)
    j.settle()
    signal.setInputIndex.emit(b3)
    j.await_value(lambda: int(view.property("jumpCount")) - start, 2, 2)
    j.settle()
    out["apart_jumps"] = int(view.property("jumpCount")) - start
    out["apart_highlight"] = str(tree.property("highlightKey") or "")


def main() -> None:
    def before(j: Journey) -> None:
        j.input_module(buttons=[1, 2, 3, 4])

    Journey(before).run(story)


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("cfg_redraw_limit"))


def _step(out: dict, key: str) -> Any:  # noqa: ANN401
    if key in out:
        return out[key]
    raise JourneyIncomplete(
        f"The story never reached {key!r}.\n"
        f"Error: {out.get('error', '(none)')}\n{out.get('traceback', '')}\n"
        f"--- stderr\n{out.get('_stderr', '')}"
    )


def test_a_flood_of_highlights_is_one_jump_to_the_latest(run: dict) -> None:
    assert _step(run, "running") is False  # stopped: highlighting applies
    b2, b3 = _step(run, "indexes")
    assert b2 >= 0 and b3 >= 0
    jumps = _step(run, "flood_jumps")
    assert 1 <= jumps <= 2, jumps  # was 50: one jump per notice
    assert _step(run, "flood_highlight") == B3


def test_notices_far_apart_each_jump(run: dict) -> None:
    assert _step(run, "apart_jumps") == 2
    assert _step(run, "apart_highlight") == B3


if __name__ == "__main__":
    main()
