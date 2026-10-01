# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import pathlib
import re

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_LITERAL = re.compile(r"[\"']#[0-9A-Fa-f]{6,8}[\"']")

# Colour literals still left per file. Light mode works only where colours come
# from the Style tokens, so these counts may only go down; lower a count (or drop
# the file) after converting it.
_REMAINING = {
    "action_plugins/response_curve/HandleControl.qml": 2,
    "action_plugins/response_curve/ResponseCurveAction.qml": 1,
    "qml/AxesStateSeries.qml": 8,
    "qml/BindingCatalog.qml": 24,
    "qml/ButtonState.qml": 2,
    "qml/DeviceInputList.qml": 1,
    "qml/DialogCalibration.qml": 3,
    "qml/DialogConfigureModule.qml": 15,
    "qml/DialogDevicePack.qml": 20,
    "qml/DialogHardwareHide.qml": 40,
    "qml/DialogHelp.qml": 7,
    "qml/DialogHiddenDevices.qml": 1,
    "qml/DialogJoystickButtonMap.qml": 66,
    "qml/DialogLiveLog.qml": 12,
    "qml/DialogManageModes.qml": 1,
    "qml/DismissibleDialog.qml": 1,
    "qml/InputButton.qml": 3,
    "qml/InputConfiguration.qml": 3,
    "qml/InputItemBinding.qml": 1,
    "qml/InputViewerCard.qml": 15,
    "qml/LogicalPage.qml": 11,
    "qml/Main.qml": 5,
    "qml/OptionWindowsScale.qml": 1,
    "qml/OscAddDialog.qml": 3,
    "qml/OscImportDialog.qml": 3,
    "qml/OutputModuleView.qml": 71,
    "qml/UnmappedCard.qml": 1,
    "qml/VJoySelector.qml": 2,
    "qml/VkbRigEditor.qml": 114,
    "qml/VkbRigFace.qml": 8,
    "qml/Xbox360Face.qml": 44,
    "qml/XboxDevice.qml": 1,
    "qml/XboxViewerCard.qml": 14,
}


def _counts() -> dict[str, int]:
    found = {}
    for folder in ("qml", "theme", "action_plugins"):
        for path in (_ROOT / folder).rglob("*.qml"):
            name = path.relative_to(_ROOT).as_posix()
            if name == "qml/Style.qml":
                continue
            count = len(_LITERAL.findall(path.read_text(encoding="utf-8")))
            if count:
                found[name] = count
    return found


def test_no_new_colour_literals() -> None:
    grown = {
        name: (count, _REMAINING.get(name, 0))
        for name, count in _counts().items()
        if count > _REMAINING.get(name, 0)
    }
    assert not grown, (
        f"Use a Style colour token instead of a literal (now, allowed): {grown}"
    )


def test_remaining_counts_are_current() -> None:
    # Keeps the list honest: a converted file must have its count lowered here.
    counts = _counts()
    stale = {
        name: (counts.get(name, 0), allowed)
        for name, allowed in _REMAINING.items()
        if counts.get(name, 0) < allowed
    }
    assert not stale, f"Lower these counts in _REMAINING (now, listed): {stale}"
