# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from unittest import mock

import pytest

from gremlin.ui import output_modules

# vjoy_3 claims 3 axes and 56 buttons, like the user's file.
_MODULES = [
    {
        "name": "vJoy 3",
        "vjoy_id": 3,
        "claim": {"axes": [1, 2, 3], "buttons": list(range(1, 57)), "hats": []},
    }
]


@pytest.fixture
def picker() -> output_modules.OutputModuleDevices:
    with (
        mock.patch.object(output_modules, "_dest_modules", return_value=_MODULES),
        mock.patch.object(output_modules.event_handler, "EventListener"),
    ):
        devices = output_modules.OutputModuleDevices()
        devices.validTypes = ["button"]
        yield devices


def _writes(devices: output_modules.OutputModuleDevices) -> list[tuple]:
    seen: list[tuple] = []
    devices.currentSelectionChanged.connect(lambda *args: seen.append(args))
    return seen


def test_saved_unclaimed_output_is_kept_and_flagged(
    picker: output_modules.OutputModuleDevices,
) -> None:
    writes = _writes(picker)
    picker.setInitialState(3, "button", 57)

    assert writes == []  # the wire is not re-pointed or written back
    assert picker.currentUnclaimed
    assert "Button 57 (not claimed)" in picker.inputChoices
    assert "vJoy 3" in picker.vjoyDevices


def test_claimed_output_still_selects_normally(
    picker: output_modules.OutputModuleDevices,
) -> None:
    writes = _writes(picker)
    picker.setInitialState(3, "button", 5)

    assert writes == [(3, "button", 5)]
    assert not picker.currentUnclaimed
    assert not any("(not claimed)" in label for label in picker.inputChoices)


def test_type_change_still_moves_to_a_claimed_output(
    picker: output_modules.OutputModuleDevices,
) -> None:
    picker.setInitialState(3, "button", 57)
    writes = _writes(picker)
    picker.validTypes = ["axis"]  # e.g. the action became an axis action

    assert writes and writes[-1][1] == "axis"
    assert not picker.currentUnclaimed
    assert not any("(not claimed)" in label for label in picker.inputChoices)


def test_vjoy_without_an_output_module_is_labelled(
    picker: output_modules.OutputModuleDevices,
) -> None:
    writes = _writes(picker)
    picker.setInitialState(4, "button", 2)

    assert writes == []
    assert "vJoy 4 (no output module)" in picker.vjoyDevices
    assert picker.currentUnclaimed
