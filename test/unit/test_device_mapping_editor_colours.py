# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The device map colour picker's recent colours and eyedropper."""

from __future__ import annotations

import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

sys.path.append(".")

import os
import pathlib

from gremlin.config import Configuration
from gremlin.ui import hardware_profile


def test_recent_colours_newest_first_once_at_most_ten() -> None:
    Configuration().set("global", "internal", "device-map-recent-colours", [])
    profile = hardware_profile.HardwareProfile()
    for i in range(12):
        profile.noteColour(f"#0000{i:02X}")
    profile.noteColour("#000003")
    recent = profile.recentColours
    assert len(recent) == 10
    assert recent[0] == "#000003"
    assert recent.count("#000003") == 1
    assert recent[1] == "#00000B"


def test_recent_colours_ignore_what_is_not_a_colour() -> None:
    Configuration().set("global", "internal", "device-map-recent-colours", [])
    profile = hardware_profile.HardwareProfile()
    for bad in ("", "red", "#12345", "#GGGGGG", None):
        profile.noteColour(bad)
    assert profile.recentColours == []


# Runs in its own process: it needs a window to grab.
_EYEDROPPER = r"""
import os, sys
sys.path.insert(0, ".")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6 import QtCore, QtGui, QtQml, QtTest

app = QtGui.QGuiApplication(sys.argv[:1])
# As in the app: the application exists before HardwareProfile is used.
from gremlin.ui.hardware_profile import HardwareProfile
engine = QtQml.QQmlApplicationEngine()
engine.loadData(b'''
import QtQuick
import QtQuick.Window
Window {
    width: 200; height: 100; visible: true; color: "#102030"
    Rectangle { x: 0; y: 0; width: 100; height: 100; color: "#FF0000" }
    Rectangle { x: 100; y: 0; width: 100; height: 100; color: "#00AA44" }
}
''')
window = engine.rootObjects()[0]
QtTest.QTest.qWait(300)
profile = HardwareProfile()
left = profile.colorAt(window, 50, 50)
right = profile.colorAt(window, 150, 50)
outside = profile.colorAt(window, 500, 50)
# os._exit skips the usual flush.
print(left, right, repr(outside), flush=True)
os._exit(0)
"""


def test_eyedropper_reads_the_window() -> None:
    root = pathlib.Path(__file__).parents[2]
    result = proc_tree.run(
        [sys.executable, "-c", _EYEDROPPER],
        text=True,
        cwd=root,
        timeout=60,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
    )
    assert result.stdout.split() == ["#FF0000", "#00AA44", "''"], (
        smoke_report.explain(result)
    )
