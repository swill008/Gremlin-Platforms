# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Map text stays sharp at every zoom (07 S158, D-07-SHARP-TEXT).

Zoom is a scale on the editor's world and the chip font follows the window,
so a small window draws ~4 px text that the zoom then enlarges. Native
(Windows) text is rasterized at that tiny size and goes blocky with colour
fringes; Qt rendering draws glyph outlines and stays sharp when scaled. The
hidden text-measuring item must draw the same way so text-box layout
matches what is shown.
"""

from __future__ import annotations

import pathlib
import re

import pytest

_QML = pathlib.Path(__file__).resolve().parents[2] / "qml"

# File -> how many Text items it draws on the map.
_MAP_TEXT = {
    "RigChipLabel.qml": 2,
    "RigGroupItem.qml": 1,
    "RigDrawItem.qml": 3,
}


def render_types(source: str) -> list[str]:
    return re.findall(r"renderType:\s*Text\.(\w+)", source)


@pytest.mark.parametrize("name", sorted(_MAP_TEXT))
def test_map_text_uses_qt_rendering(name: str) -> None:
    found = render_types((_QML / name).read_text(encoding="utf-8"))
    assert len(found) == _MAP_TEXT[name], found
    assert set(found) == {"QtRendering"}, f"{name}: {found}"


def test_text_measuring_item_matches_text_boxes() -> None:
    source = (_QML / "VkbRigEditor.qml").read_text(encoding="utf-8")
    block = re.search(r"Text\s*\{[^{}]*id:\s*_textFit[^{}]*\}", source)
    assert block, "hidden _textFit measuring item not found"
    assert render_types(block.group(0)) == ["QtRendering"], block.group(0)
