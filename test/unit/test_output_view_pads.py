# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from pathlib import Path

_QML = Path(__file__).resolve().parents[2] / "qml/OutputModuleView.qml"


def test_show_pads_checkbox_and_off_is_zero() -> None:
    text = _QML.read_text(encoding="utf-8")
    assert 'text: "Show pads"' in text
    assert "padAOn" in text
    assert "padBOn" in text
    assert "v.padAX || 1" not in text
    assert "showPads !== false" in text


def test_view_reloads_after_both_name_and_guid_change() -> None:
    text = _QML.read_text(encoding="utf-8")
    assert "onDeviceNameChanged: { loadView();" not in text
    assert "onGuidChanged: reloadView()" in text
    assert "onDeviceNameChanged: reloadView()" in text
    model = Path(__file__).resolve().parents[2].joinpath("gremlin/ui/module_model.py").read_text(encoding="utf-8")
    assert "guid_for_module(name, guid)" in model


def test_save_toast_click_off_or_two_seconds() -> None:
    text = _QML.read_text(encoding="utf-8")
    assert "id: _savedToast" in text
    assert "interval: 2000" in text
    assert "CloseOnPressOutside" in text
    assert "_savedToast.open()" in text


def test_button_columns_to_one_and_stacked_label() -> None:
    text = _QML.read_text(encoding="utf-8")
    assert "from: 1; to: 16" in text
    assert "Math.max(1, Math.min(_root.buttonColumns," in text
    assert 'text: "Button"' in text


def test_show_meters_checkbox() -> None:
    text = _QML.read_text(encoding="utf-8")
    assert 'text: "Show meters"' in text
    assert "metersOn" in text
    assert "readonly property bool showMeters" not in text


def test_meter_uncheck_seeds_then_hides() -> None:
    """Empty meters meant all-on, so uncheck used to no-op. Mirror QML toggleMeter."""

    def meter_on(meters, hw):
        if not meters:
            return True
        if len(meters) == 1 and int(meters[0]) == 0:
            return False
        return hw in meters

    def toggle(meters, hw, on, all_hw):
        lst = list(meters or [])
        if lst == [0]:
            lst = []
        elif not lst:
            lst = list(all_hw)
        if on and hw not in lst:
            lst.append(hw)
        if not on and hw in lst:
            lst.remove(hw)
        return [0] if not lst else lst

    all_hw = [1, 2, 3]
    assert meter_on([], 2) is True
    lst = toggle([], 2, False, all_hw)
    assert lst == [1, 3]
    assert meter_on(lst, 2) is False
    lst = toggle(lst, 1, False, all_hw)
    lst = toggle(lst, 3, False, all_hw)
    assert lst == [0]
    assert meter_on(lst, 1) is False


def test_reset_does_not_save_and_has_width() -> None:
    text = _QML.read_text(encoding="utf-8")
    chunk = text[text.find("function resetView") : text.find("function rebuild")]
    assert "saveViewConfig" not in chunk
    assert "Options have been reset" in chunk
    assert "buttonWidth" in text
    assert "Pads hidden" in text


def test_button_grid_uses_columns_and_width() -> None:
    text = _QML.read_text(encoding="utf-8")
    assert "GridView" not in text
    # Columns is a maximum; the grid wraps to the width instead of hiding columns.
    assert "columns: Math.max(1, Math.min(_root.buttonColumns," in text
    assert "flickableDirection: Flickable.VerticalFlick" in text
    assert "Layout.preferredWidth: Style.dp(Math.max(40, _root.buttonWidth))" in text


def test_vjoy_view_save_uses_that_devices_module_file() -> None:
    text = Path(__file__).resolve().parents[2].joinpath("gremlin/ui/module_model.py").read_text(encoding="utf-8")
    save = text[text.find("def saveViewConfig"): text.find("def catalogConfigJson")]
    load = text[text.find("def viewConfigJson"): text.find("def saveViewConfig")]
    assert "module_json_path(name, guid)" in save
    assert "module_json_path(device_name, guid)" in load
    rule = Path(__file__).resolve().parents[2].joinpath("gremlin/ui/hardware_profile.py").read_text(encoding="utf-8")
    body = rule[rule.find("def module_json_path"): rule.find("def module_file_choices")]
    # The one rule every page uses (a vJoy never opens another vJoy's file:
    # test_audit3_module_files.test_one_vjoy_never_opens_another_vjoys_file).
    assert "_active_module_path(" in body
