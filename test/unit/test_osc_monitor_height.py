"""The docked OSC Monitor's height is remembered (09 S137, G-OSC36)."""

from __future__ import annotations

from pathlib import Path

PAGE = Path(__file__).resolve().parents[2] / "qml" / "OscPage.qml"


def test_the_monitor_height_is_read_and_saved_through_window_placement() -> None:
    text = PAGE.read_text(encoding="utf-8")
    assert 'toolRowState("oscPage")' in text
    assert 'saveToolRowState("oscPage"' in text
    grip = text[text.index("id: _dockGrip") :]
    grip = grip[: grip.index("OscMonitorPanel {")]
    assert "onReleased" in grip and "_saveMonitorHeight()" in grip
