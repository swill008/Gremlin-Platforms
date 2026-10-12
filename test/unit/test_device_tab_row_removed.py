# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""The old device tab row and its vJoy tab pins are gone (question 127).

The row showed only in the configuration room with no device title, which no
normal flow reaches, and nothing could pin a vJoy tab any more.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_the_tab_row_and_its_pins_are_removed() -> None:
    for rel in ("qml/DeviceList.qml", "qml/DeviceTabBar.qml",
                "qml/JGTabButton.qml", "gremlin/ui/vjoy_status.py"):
        assert not (ROOT / rel).exists(), rel
    main = (ROOT / "qml/Main.qml").read_text(encoding="utf-8")
    for name in ("DeviceList {", "_deviceList", "nextTab", "_scriptButton",
                 "_profileSettingsButton", "DeviceTabBar"):
        assert name not in main, name
    start = (ROOT / "joystick_gremlin.py").read_text(encoding="utf-8")
    assert "vjoy_status" not in start
