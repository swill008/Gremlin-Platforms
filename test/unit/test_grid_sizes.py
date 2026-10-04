# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Button Map grid sizes go down to 1 (View > Grid > Size), and a map saved
with a size of 1 or 2 keeps it when it loads (sizes under 4 were dropped)."""

from __future__ import annotations

import pathlib
import re

_QML = pathlib.Path(__file__).parents[2] / "qml" / "DialogJoystickButtonMap.qml"


def test_size_menu_starts_at_one() -> None:
    qml = _QML.read_text(encoding="utf-8")
    menu = qml[qml.index('title: "Size"'):]
    sizes = [int(v) for v in re.findall(r'setGridPref\("gridSize", (\d+)\)', menu)]
    assert sizes[:3] == [1, 2, 4]


def test_a_saved_size_of_one_loads() -> None:
    qml = _QML.read_text(encoding="utf-8")
    assert "if (ui.gridSize >= 1)" in qml
