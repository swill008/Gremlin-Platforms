# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import pathlib
import re

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_LITERAL = re.compile(r"[\"']#[0-9A-Fa-f]{6,8}[\"']")

# Colour literals allowed per file; the counts may only go down. Everything
# else takes its colours from the Style tokens so Dark mode switches it.
_REMAINING = {
    # Old fixed dark defaults, kept so saved colours equal to them still
    # follow Dark mode; and "#00000000", the "no colour" value.
    "qml/BindingCatalog.qml": 24,
    "qml/LogicalPage.qml": 11,
    "qml/OutputModuleView.qml": 12,
    # Overlays on the device photo and the colour picker's fixed palette.
    "qml/DialogJoystickButtonMap.qml": 48,
    # Counted since .js files are scanned too; older than the scan.
    "qml/helpers.js": 4,
    # Drawn on the device photo, which looks the same in both modes. The
    # Rig*.qml parts were split out of VkbRigEditor.qml with their colours.
    "qml/RigChipItem.qml": 6,
    "qml/RigDrawItem.qml": 8,
    "qml/RigGrid.qml": 3,
    "qml/RigGroupItem.qml": 3,
    "qml/RigGuides.qml": 1,
    "qml/RigLeaderLayer.qml": 9,
    "qml/RigMiniChip.qml": 10,
    "qml/RigSelRing.qml": 1,
    "qml/VkbRigEditor.qml": 10,
    "qml/rig_draw.js": 15,
    "qml/rig_groups.js": 6,
    "qml/rig_style.js": 8,
    "qml/rig_tables.js": 11,
    "qml/rig_text.js": 11,
    "qml/VkbRigFace.qml": 8,
    "qml/Xbox360Face.qml": 44,
}


def _counts() -> dict[str, int]:
    found = {}
    for folder in ("qml", "theme", "action_plugins"):
        # .js too: QML code-behind files (the Button Map editor's rig_*.js).
        paths = [*(_ROOT / folder).rglob("*.qml"), *(_ROOT / folder).rglob("*.js")]
        for path in paths:
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
