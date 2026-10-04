# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Cleanup, first batch (3 Oct review: E1, E7, E8, UI10, UI11, UI12, B19,
BM16, N26).

- HidHide device photos were named with Python's per-run hash, so each
  session wrote a new file and none were removed (B19).
- Unused pieces removed: VJoyStatusPopup, LogicalDevice.qml (it could never
  load), hints.py and its CSV, ColorSwatch, two Main.qml functions and
  private helpers nothing called (E7, N26).
- Words from the glossary, OK not Ok, a separate icon for Dual Axis
  Deadzone, and a leader end no longer attaching to a drawing (E1, E8,
  UI12, BM16). UI10 and UI11 are qmllint findings (gone from its output).
"""

from __future__ import annotations

import sys

sys.path.append(".")

import pathlib
import shutil
from types import SimpleNamespace

import pytest

_ROOT = pathlib.Path(__file__).parents[2]


def _text(rel: str) -> str:
    return (_ROOT / rel).read_text(encoding="utf-8")


def test_a_device_photo_keeps_one_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    from gremlin.ui import hardware_profile, hidhide

    folder = tmp_path / "photos"
    folder.mkdir()
    (folder / "0badc0de.png").write_bytes(b"left by an old session")
    stored: dict = {}
    monkeypatch.setattr(hidhide, "_photo_dir", lambda: folder)
    monkeypatch.setattr(hidhide, "_load_photos", lambda: dict(stored))
    monkeypatch.setattr(hidhide, "_save_photos", lambda rows: stored.update(rows))
    monkeypatch.setattr(
        hardware_profile, "limit_image_file", lambda src, dest: shutil.copy(src, dest)
    )
    picture = tmp_path / "stick.png"
    picture.write_bytes(b"png")
    model = SimpleNamespace(reload=lambda: None)
    for _session in range(3):  # each one used to add a file
        assert hidhide.HidHideModel.setDevicePhoto(model, "HID\\VID_1234", str(picture))
    files = [p.name for p in folder.iterdir()]
    assert len(files) == 1  # the old session's file is gone too
    assert stored["HID\\VID_1234"].endswith(files[0])


def test_unused_pieces_are_gone() -> None:
    for rel in ("qml/VJoyStatusPopup.qml", "qml/LogicalDevice.qml",
                "gremlin/hints.py", "doc/hints.csv"):
        assert not (_ROOT / rel).exists(), rel
    main = _text("qml/Main.qml")
    for name in ("VJoyStatusPopup", "LogicalDevice {", "function focusedCard",
                 "function moduleField"):
        assert name not in main
    assert "component ColorSwatch" not in _text("qml/DialogJoystickButtonMap.qml")


def test_wording_follows_the_glossary() -> None:
    assert 'text: "OK"' in _text("qml/TextInputDialog.qml")
    assert 'qsTr("OK")' in _text("qml/MainFailure.qml")
    main = _text("qml/Main.qml")
    assert '"Output Module View"' not in main and '"Input Configuration"' not in main
    assert '"No module"' in _text("qml/StatusCard.qml")
    assert '"Save Module"' in _text("qml/DialogConfigureModule.qml")
    assert "Edit → Button Map Options… → Library" in _text(
        "qml/DialogJoystickButtonMap.qml"
    )


def test_dual_axis_deadzone_has_its_own_icon() -> None:
    from action_plugins.dual_axis_deadzone import DualAxisDeadzoneData
    from action_plugins.response_curve import ResponseCurveData

    assert DualAxisDeadzoneData.icon != ResponseCurveData.icon


def test_a_leader_end_skips_drawings_hotspots() -> None:
    leaders = _text("qml/rig_leaders.js").replace("\r", "")
    loop = leaders[leaders.index("function attachNear("):][:600]
    assert "if (isDraw(list[i]))\n            continue" in loop


# Batch B: light theme, typed colors, fonts (E5, E6, BM17).


def test_colour_picker_follows_the_theme_and_takes_a_hex() -> None:
    qml = _text("qml/DialogJoystickButtonMap.qml")
    picker = qml[qml.index("id: _colorPop"):][:12000]
    assert '"#18181B"\n            border.color' not in picker.replace("\r", "")
    assert "color: Style.bgRaised" in picker
    assert "id: _hexField" in picker and "_colorPop.takeHex(t.toUpperCase())" in picker


def test_fonts_come_from_style() -> None:
    import re

    hard = []
    for folder in ("qml", "action_plugins", "theme"):
        for path in (_ROOT / folder).rglob("*.qml"):
            if path.name != "Style.qml" and re.search(
                r'font\.family: "', path.read_text(encoding="utf-8")
            ):
                hard.append(path.name)
    assert hard == []


# Batch C: first-time users and large UI scales (UI13, N23).


def test_first_time_wording_and_room() -> None:
    assert "No buttons, axes or hats yet." in _text("qml/LogicalPage.qml")
    assert "Scripts are Python files" in _text("qml/ScriptManager.qml")
    assert "Press a control on the device to claim it" in _text(
        "qml/DialogConfigureModule.qml"
    )
    assert "if (rows[j].hasFile)" in _text("qml/DialogDevicePack.qml")
    assert "Load a profile first" in _text("qml/DialogSwapDevices.qml")
    info = _text("qml/DialogDeviceInformation.qml")
    assert "Layout.minimumWidth: Style.dp(220)" in info


def test_editors_fit_large_ui_scales() -> None:
    sound = _text("action_plugins/play_sound/PlaySoundAction.qml").replace("\r", "")
    fixed = 'Layout.preferredWidth: Style.dp(50)\n\n            text: "Volume"'
    assert fixed not in sound
    curve = _text("action_plugins/response_curve/ResponseCurveAction.qml")
    assert "Math.min(\n" in curve.replace("\r", "") and "_root.width" in curve
    macro = _text("action_plugins/macro/MacroAction.qml").replace("\r", "")
    start = macro.index("// Macro repeat configuration")
    repeat_row = macro[start:macro.index('text: "Exclusive"')]
    assert repeat_row.count("RowLayout {") == 2  # the switches have their own row
