# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Cleanup, first batch (3 Oct review: E1, E7, E8, UI10, UI11, UI12, B19,
BM16, N26).

- HidHide device photos were copies named with Python's per-run hash, piling
  up in the program folder (B19); now the picked picture is used where it
  is, nothing is copied, and a card whose picture is gone shows none.
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
from types import SimpleNamespace

import pytest

_ROOT = pathlib.Path(__file__).parents[2]


def _text(rel: str) -> str:
    return (_ROOT / rel).read_text(encoding="utf-8")


def test_a_picked_photo_is_used_where_it_is(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    # The picker keeps the picked file's path: nothing is copied or deleted.
    from gremlin.ui import hidhide

    stored: dict = {}
    monkeypatch.setattr(hidhide, "_load_photos", lambda: dict(stored))
    monkeypatch.setattr(hidhide, "_save_photos", lambda rows: stored.update(rows))
    pictures = tmp_path / "My Pictures"
    pictures.mkdir()
    (pictures / "old.png").write_bytes(b"older pick")
    picture = pictures / "stick.png"
    picture.write_bytes(b"png")
    model = SimpleNamespace(reload=lambda: None)
    url = "file:///" + picture.as_posix()
    assert hidhide.HidHideModel.setDevicePhoto(model, r"HID\VID_1234", url)
    assert stored == {r"HID\VID_1234": str(picture.resolve())}
    assert sorted(p.name for p in pictures.iterdir()) == ["old.png", "stick.png"]


def test_a_card_shows_the_pick_blank_when_gone_else_the_module(
    tmp_path: pathlib.Path,
) -> None:
    from gremlin.ui import hidhide

    picture = tmp_path / "stick.png"
    picture.write_bytes(b"png")
    assert hidhide._card_photo(str(picture)).startswith("file:")
    assert hidhide._card_photo(str(tmp_path / "moved.png")) == ""  # no picture
    assert hidhide._card_photo("") is None  # never picked: the module's photo


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
    start = qml.index("id: _colorPop")
    # The picker, to its closing brace (four spaces in).
    picker = qml[start:qml.index("\n    }\n", start)]
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
    assert "if (rows[j].canExport)" in _text("qml/DialogDevicePack.qml")
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


# Batch D: drifting copies (N25).


def test_one_user_colour_one_logical_id_one_window_memory() -> None:
    import re

    for page in ("BindingCatalog", "LogicalPage", "OutputModuleView"):
        qml = _text(f"qml/{page}.qml")
        assert "function userColour(" not in qml and "Helpers.userColour(" in qml
    assert "function userColour(" in _text("qml/helpers.js")
    guid = re.compile(r"f0af472f-8e17-493b-a1eb-7333ee8543f2", re.I)
    for page in ("Main", "DeviceList"):
        assert not guid.search(_text(f"qml/{page}.qml"))
    from gremlin.ui.backend import UIState

    assert guid.fullmatch(UIState.logicalDeviceGuid.fget(None))
    windows = ("DialogAutoMapper", "DialogConfigureModule", "DialogDeviceInformation",
               "DialogDevicePack", "DialogHardwareHide", "DialogManageModes")
    for window in windows:
        assert "ToolWindowMemory {" in _text(f"qml/{window}.qml"), window
    assert "saveWindowSize" not in _text("qml/DialogHardwareHide.qml")


def test_pane_dividers_live_with_the_window_layout() -> None:
    from types import SimpleNamespace

    from gremlin.config import Configuration
    from gremlin.ui import window_placement
    from gremlin.ui.hidhide import HidHideModel
    from gremlin.ui.module_model import ModuleListModel

    cfg = Configuration()
    wp = window_placement
    key = (wp.SECTION, wp.GROUP, wp.KEY_SPLITS)
    window_placement._ensure()
    before = cfg.value(*key)
    try:
        cfg.set(*key, "{}")
        # Nothing saved the new way yet: the old setting is the start.
        assert HidHideModel.splitRatio.fget(None) == 600
        HidHideModel.saveSplitRatio(None, 700)
        assert HidHideModel.splitRatio.fget(None) == 700
        changed = SimpleNamespace(emit=lambda: None)
        home = SimpleNamespace(splitRatio=0.5, panesChanged=changed)
        ModuleListModel.setSplitRatio(home, 0.3)
        assert ModuleListModel.splitRatio.fget(None) == 0.3
        assert window_placement._split_map(cfg) == {"hardwareHide": 0.7, "home": 0.3}
    finally:
        cfg.set(*key, before)


def test_layer_rule_no_direct_hardware_reads() -> None:
    # N24: the UI reads devices through the input side (gremlin.modules
    # .hardware); device start-up asks vJoy through the output module.
    ui = _ROOT / "gremlin" / "ui"
    direct = [
        p.name for p in ui.glob("*.py") if "dill.DILL." in p.read_text(encoding="utf-8")
    ]
    assert direct == []
    start = _text("gremlin/device_initialization.py")
    assert "from vjoy import vjoy" not in start and "output.vjoy_layout(" in start
