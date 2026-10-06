# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

import json
from pathlib import Path

import pytest
from PySide6 import QtCore

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


@pytest.fixture
def view_folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An empty modules folder of its own; History in the temporary folder."""
    from gremlin import history, history_modules
    from gremlin.modules import registry, store

    QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    modules = tmp_path / "modules"
    modules.mkdir()
    monkeypatch.setattr(store, "folder", lambda: modules)
    monkeypatch.setattr(registry, "_binding_store", lambda: {})
    monkeypatch.setattr(history, "folder", lambda: tmp_path / "history")
    monkeypatch.setattr(history, "_pruned", True)
    monkeypatch.setattr(history_modules, "_last_pictures", {})
    registry._cache.clear()
    return modules


def test_vjoy_view_save_uses_that_devices_module_file(view_folder: Path) -> None:
    from gremlin import device_initialization
    from gremlin.ui import module_model

    vjoy = str(next(iter(device_initialization.vjoy_devices())).device_guid)
    stick = next(iter(device_initialization.physical_devices()))
    stick_file = view_folder / "pjoy_pro.json"
    stick_file.write_text(json.dumps({
        "kind": "control.hardware", "device": stick.name, "direction": "source",
        "boundGuidLocal": str(stick.device_guid),
    }), encoding="utf-8")
    stick_before = stick_file.read_bytes()
    model = module_model.ModuleListModel()
    # The view is saved into that vJoy's own module file (by name and id)
    # and read back from it.
    assert model.saveViewConfig("vJoy 1", vjoy, json.dumps({"showPads": False}))
    saved = json.loads((view_folder / "vjoy_1.json").read_text(encoding="utf-8"))
    assert saved["view"]["showPads"] is False
    assert json.loads(model.viewConfigJson("vJoy 1", vjoy))["showPads"] is False
    # An id that is not this vJoy's (a stale one) never reaches another
    # device's file: the same file, the stick's untouched.
    stale = str(stick.device_guid)
    assert model.saveViewConfig("vJoy 1", stale, json.dumps({"buttonColumns": 3}))
    saved = json.loads((view_folder / "vjoy_1.json").read_text(encoding="utf-8"))
    assert saved["view"]["buttonColumns"] == 3
    assert json.loads(model.viewConfigJson("vJoy 1", stale))["buttonColumns"] == 3
    assert stick_file.read_bytes() == stick_before
