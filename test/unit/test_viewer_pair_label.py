# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from unittest import mock

from gremlin.types import InputType
from gremlin.ui import viewer_devices


def test_xbox_pads_are_not_called_vjoy_devices() -> None:
    # One input to vJoy 2 button 5, another to Xbox pad 1.
    maps = {
        "a": [(2, InputType.JoystickButton, 5)],
        "b": [(1, None, 0)],
    }
    with mock.patch.object(
        viewer_devices.pairing, "_maps_for_item", side_effect=lambda item: maps[item]
    ):
        label = viewer_devices._pair_label(["a", "b"])
    assert label == "vJoy Device 2, Xbox 360 1"
