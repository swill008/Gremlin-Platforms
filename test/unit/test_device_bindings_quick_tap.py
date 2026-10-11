# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A quick tap always finds its row on the Device Bindings page
(D-05-QUICK-TAP, 05 S131).

A journey (test/journeys/_harness.py) on the real program off-screen: the
fake "pJoy Pro" stick, the program stopped, Input highlighting on. A stick
button pressed and released back to back, with no event loop turn between
them (so no live-tint poll of the row can see it), still makes the backend
say setInputIndex (backend._highlight_input on joystick_event) and the page
jumps to the row and flashes it (DeviceBindingsPage.showIndex ->
ControlTree.showKey). The jump is event-driven, so the row update rate
can't make it miss.
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

    def page() -> Any:  # noqa: ANN401
        for model in j.win.findChildren(HardwareLayoutModel):
            if _same_guid(model.property("guid"), uid) and model.property(
                "parentCount"
            ):
                return model
        return None

    layout = j.wait_until(page, "the Device Bindings page of pjoy_pro")

    def live_tree() -> Any:  # noqa: ANN401
        for item in j.walk(j.win.contentItem()):
            if item.property("liveDecoration") is True and item.isVisible():
                return item
        return None

    tree = j.wait_until(live_tree, "the tree with live decoration", 5)
    j.settle()
    Configuration().set("ui", "general", "input-highlighting", True)
    out["running"] = bool(j.backend.property("gremlinActive"))
    out["index"] = int(_row(layout, B3).get("deviceIndex", -1))
    out["highlight-before"] = str(tree.property("highlightKey") or "")
    emitted: list[int] = []
    signal.setInputIndex.connect(emitted.append)
    stick = j.stick(STICK)
    # Pressed and released between two row updates: no event loop turn.
    j.press(stick, 3, True)
    j.press(stick, 3, False)
    # The flash lasts 600 ms (ControlTree _flashTimer): read it first.
    out["flashed"] = str(
        j.await_value(lambda: str(tree.property("_flashKey") or ""), B3, 3)
    )
    out["highlight"] = str(tree.property("highlightKey") or "")
    j.await_value(lambda: len(emitted) >= 2, True, 1)
    out["jumps"] = list(emitted)
    signal.setInputIndex.disconnect(emitted.append)


def main() -> None:
    def before(j: Journey) -> None:
        j.input_module(buttons=[1, 2, 3, 4])

    Journey(before).run(story)


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("cfg_quick_tap"))


def _step(out: dict, key: str) -> Any:  # noqa: ANN401
    if key in out:
        return out[key]
    raise JourneyIncomplete(
        f"The story never reached {key!r}.\n"
        f"Error: {out.get('error', '(none)')}\n{out.get('traceback', '')}\n"
        f"--- stderr\n{out.get('_stderr', '')}"
    )


def test_a_quick_tap_jumps_to_its_row_and_flashes_it(run: dict) -> None:
    assert _step(run, "running") is False  # stopped: highlighting applies
    index = _step(run, "index")
    assert index >= 0
    assert _step(run, "highlight-before") != B3
    jumps = _step(run, "jumps")
    assert jumps and all(i == index for i in jumps), jumps
    assert _step(run, "highlight") == B3
    assert _step(run, "flashed") == B3


if __name__ == "__main__":
    main()
