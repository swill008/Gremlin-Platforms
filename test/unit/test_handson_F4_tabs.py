# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Hands-on fix F4: the Configuration device tab bar lists every device
(Main.qml's DeviceListModel), so a pinned vJoy keeps its tab.

DeviceListModel.deviceType is honoured now (it has a getter); "physical"
there would drop the vJoy rows and with them the pinned vJoy tabs.
Driven through the real program off-screen (the journey harness).
"""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "journeys"))
from _harness import Journey, run_journey, step  # noqa: E402


def _tabs(j: Journey, bar: object) -> list:
    """The bar's shown tab captions (its tab buttons that are visible)."""
    return [
        str(item.property("text"))
        for item in j.walk(bar)
        if item.metaObject().className().startswith("JGTabButton")
        and item.property("visible")
    ]


def story(j: Journey) -> None:
    from gremlin.ui.vjoy_status import VJoyStatus

    out = j.out
    bar = j.ev("_deviceList")
    # The bar shows on the Configuration page with no device page open.
    j.backend.uiState.setCurrentRoom("configuration")
    j.wait_until(lambda: bar.property("visible"), "the device tab bar")
    pins = VJoyStatus()
    out["device-type"] = j.ev("_deviceListModel.deviceType")
    pins.setPinned(1, False)
    j.settle()
    out["unpinned"] = _tabs(j, bar)
    pins.setPinned(1, True)
    j.settle()
    out["pinned"] = _tabs(j, bar)
    pins.setPinned(1, False)


def main() -> None:
    Journey().run(story)


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("f4tabs"))


def test_the_bar_lists_every_device(run: dict) -> None:
    assert step(run, "device-type") == "all"


def test_a_pinned_vjoy_shows_a_tab(run: dict) -> None:
    unpinned = step(run, "unpinned")
    pinned = step(run, "pinned")
    assert not any(t.lower().startswith("vjoy") for t in unpinned)
    assert [t for t in pinned if t.lower().startswith("vjoy")], pinned
    assert [t for t in unpinned if t in pinned] == unpinned


if __name__ == "__main__":
    main()
