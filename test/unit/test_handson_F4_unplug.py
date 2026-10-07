# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Hands-on fix F4: the open Configuration page follows the device under it
(05 S105 page part, 02 S33).

pJoy Pro's Configuration page is open and pJoy Pro is unplugged. The
program moves the page to the first physical device left (02 S33); the
page then belongs to that device: its title, the focused card, the
direction and the catalog's device name, not pJoy Pro's over the
Throttle's rows. With no stick left the page is the Logical Device.

Driven through the real program off-screen (the journey harness, fake
driver).
"""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "journeys"))
from _harness import Journey, run_journey, step  # noqa: E402


def _unplug(j: Journey, name: str) -> None:
    from gremlin import event_handler

    raw = next(d for d in j.dill_fake.devices if d.name == name.encode("utf-8"))
    j.dill_fake.devices.remove(raw)
    event_handler.EventListener()._run_device_list_update()


def _page(j: Journey) -> list:
    return [
        j.ev("configTitleName"),
        j.ev("configDirection"),
        j.ev("_moduleModel.focusedCardMap().slug"),
        j.ev("catalogPane() ? catalogPane().claimDeviceName : ''"),
    ]


def story(j: Journey) -> None:
    out = j.out
    state = j.backend.uiState
    j.open_configuration("pjoy_pro")
    out["before"] = _page(j)
    throttle = j.stick("Throttle").device_guid

    _unplug(j, "pJoy Pro")
    j.wait_until(
        lambda: str(state.currentDevice).upper().strip("{}")
        == str(throttle).upper().strip("{}"),
        "the page to move to the Throttle",
    )
    out["after"] = j.await_value(
        lambda: _page(j), ["Throttle", "source", "throttle", "Throttle"]
    )
    out["room"] = state.currentRoom

    _unplug(j, "Throttle")
    j.wait_until(lambda: state.currentTab == "logical", "the Logical tab")
    out["none-left"] = j.await_value(
        lambda: _page(j)[:2], ["Logical Device", "logical"]
    )


def main() -> None:
    def before(j: Journey) -> None:
        guid = j.add_stick("Throttle", 9)
        j.input_module("pJoy Pro")
        j.input_module("Throttle", guid=guid)

    Journey(before).run(story)


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("f4unplug"))


def test_page_starts_on_pjoy(run: dict) -> None:
    assert step(run, "before") == ["pJoy Pro", "source", "pjoy_pro", "pJoy Pro"]


def test_unplugged_page_follows_the_device_under_it(run: dict) -> None:
    assert step(run, "room") == "configuration"
    assert step(run, "after") == ["Throttle", "source", "throttle", "Throttle"]


def test_no_stick_left_is_the_logical_device(run: dict) -> None:
    assert step(run, "none-left") == ["Logical Device", "logical"]


if __name__ == "__main__":
    main()
