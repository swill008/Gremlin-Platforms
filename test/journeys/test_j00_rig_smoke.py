# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Journey 0: the multi-device rig itself.

With Journey(**RIG) the program starts with four sticks ("pJoy Pro",
"Saitek X52" and two "Twin Stick"s) and vJoy 1 and 2. Unplugging the X52
through the driver's device change callback takes it off the device list;
plugging it back in brings it back under the same id.

Spec: none (test harness only).
"""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _harness import RIG, Journey, run_journey, step  # noqa: E402


def story(j: Journey) -> None:
    from gremlin import device_initialization

    out = j.out

    def names() -> list[str]:
        return [d.name for d in device_initialization.physical_devices()]

    out["sticks"] = names()
    out["vjoys"] = sorted(d.vjoy_id for d in device_initialization.vjoy_devices())
    guid = str(j.stick("Saitek X52").device_guid)

    j.unplug("Saitek X52")
    out["unplugged"] = names()

    j.replug("Saitek X52")
    out["replugged"] = names()
    out["same-id"] = str(j.stick("Saitek X52").device_guid) == guid


def main() -> None:
    Journey(None, **RIG).run(story)


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("j00"))


_ALL = ["pJoy Pro", "Saitek X52", "Twin Stick", "Twin Stick (2)"]


def test_rig_shows_four_sticks_and_two_vjoys(run: dict) -> None:
    assert sorted(step(run, "sticks")) == sorted(_ALL)
    assert step(run, "vjoys") == [1, 2]


def test_unplug_and_replug_keep_the_id(run: dict) -> None:
    assert "Saitek X52" not in step(run, "unplugged")
    assert sorted(step(run, "unplugged")) == sorted(
        ["pJoy Pro", "Twin Stick", "Twin Stick (2)"]
    )
    assert sorted(step(run, "replugged")) == sorted(_ALL)
    assert step(run, "same-id") is True


if __name__ == "__main__":
    main()
