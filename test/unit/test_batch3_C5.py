# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Catch-up batch 3, Button Map, History, Device Pack, Auto Mapper (C5):
each fix driven through its real function or slot.

Spec: claude/program-map/07-button-map.md (S11, S20, S68, Q4, Q10, Q11,
Q12, Q14, RB10), 08-history-pack-automap.md (Q3, Q8, Q17, Q19, S45, S51,
section 10 gap 29), 03-modules.md (Q14). Decision D-07-RB10-NOEVOR.
GL-213, GL-221, GL-228, GL-229, GL-230, GL-268, GL-270, GL-271, GL-272,
GL-273, GL-276, GL-277. (GL-221's window part is in
test_stage1_button_map.py, GL-230's warning in test_j03_device_pack_undo.)
"""

from __future__ import annotations

import json
import os
import pathlib
import time
from collections.abc import Iterator

import pytest
from PySide6 import QtCore, QtQml

from gremlin.modules import store
from gremlin.ui import device_pack, hardware_profile

_ROOT = pathlib.Path(__file__).parents[2]
_GLADIATOR = "qml/images/vkb_gladiator_rig.jpg"


@pytest.fixture
def maps(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> pathlib.Path:
    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setattr(store, "folder", lambda: folder)
    monkeypatch.setattr(
        store, "slug_for", lambda name, guid="": name.lower().replace(" ", "_")
    )
    monkeypatch.setattr(device_pack, "_match_pack_device", lambda name: None)
    monkeypatch.setattr(hardware_profile, "_match_pack_device", lambda name: None)
    return folder


def _write(path: pathlib.Path, doc: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")


def _read(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# --- D-07-RB10-NOEVOR: no EVO R part names in chip hover text --------------


_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture
def chips_js() -> Iterator[QtQml.QJSEngine]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    engine = QtQml.QJSEngine()
    source = _ROOT / "qml" / "rig_chips.js"
    result = engine.evaluate(source.read_text(encoding="utf-8"), str(source))
    assert not result.isError(), result.toString()
    # As in the editor before the fix: an EVO R list, no device face.
    engine.evaluate(
        'var tick = 0; var face = null;'
        ' var physNames = {"btn:4": "White cap", "axis:1": "Stick X roll"}'
    )
    yield engine


def test_chip_full_names_have_no_evo_r_part_names(chips_js: QtQml.QJSEngine) -> None:
    def full(code: str) -> str:
        result = chips_js.evaluate(f"fullNameOf({code})")
        assert not result.isError(), result.toString()
        return result.toString()

    assert full('"btn", 4') == "Button 4"
    assert full('"axis", 1') == "Axis 1"
    assert full('"hat", 1') == "Hat 1"


def test_the_editor_has_no_evo_r_part_list() -> None:
    editor = (_ROOT / "qml" / "VkbRigEditor.qml").read_text(encoding="utf-8")
    chips = (_ROOT / "qml" / "rig_chips.js").read_text(encoding="utf-8")
    assert "physNames" not in editor and "physNames" not in chips
    assert "White cap" not in editor


# --- GL-213: Delete File says the pictures are kept (03 Q14) ----------------


def test_delete_file_confirm_says_the_pictures_are_kept() -> None:
    text = (_ROOT / "qml" / "DialogConfigureModule.qml").read_text(encoding="utf-8")
    start = text.index('_deleteGate.confirmThen("Delete Module File"')
    confirm = text[start:text.index('"Delete file"', start)]
    assert "The device's pictures are kept." in confirm


# --- GL-228: the Auto Mapper result in glossary words (08 Q8) ---------------


def test_auto_mapper_result_says_actions() -> None:
    from gremlin.auto_mapper import AutoMapper

    mapper = AutoMapper(None)  # type: ignore[arg-type]
    mapper._created_mappings = [object()] * 36  # type: ignore[list-item]
    mapper._num_retained_bindings = 0
    # The mode named too (08 S108).
    assert mapper._create_mappings_report("Default") == (
        "Made 36 actions in Default; 0 inputs kept their actions."
    )


# --- GL-229: export of a damaged module file (08 Q19) -----------------------


def test_export_of_a_damaged_module_file_says_so(maps: pathlib.Path) -> None:
    (maps / "test_stick.json").write_text("{not json", encoding="utf-8")
    built = device_pack.assemble("Test Stick", lambda ref: None)
    assert isinstance(built, str)
    assert "damaged" in built and "Start Fresh" in built
    assert "no module file yet" not in built
    peek = json.loads(hardware_profile.HardwareProfile().peekPackDevice("Test Stick"))
    assert peek["ok"] is False and peek["error"] == built


def test_export_without_a_module_file_still_says_none_yet(maps: pathlib.Path) -> None:
    assert device_pack.assemble("Test Stick", lambda ref: None) == (
        "This device has no module file yet."
    )
    peek = json.loads(hardware_profile.HardwareProfile().peekPackDevice("Test Stick"))
    assert peek["error"] == "This device has no module file yet."


# --- GL-230: checked controls are added, said apart (08 Q3) -----------------


def test_checked_controls_are_not_listed_as_replaced() -> None:
    assert device_pack._is_checks("in.checks")
    assert device_pack._is_checks("out:vjoy_1.checks")
    assert not device_pack._is_checks("in.names")
    assert not device_pack._is_checks("in.checksum")


# --- GL-221, GL-272: Clear Photo leaves no photo; no stock photos -----------


def test_saving_a_map_without_a_photo_names_no_photo(maps: pathlib.Path) -> None:
    hw = hardware_profile.HardwareProfile()
    assert hw.save("VKB Gladiator EVO R", json.dumps({"image": "", "nodes": []}))
    doc = _read(maps / "vkb_gladiator_evo_r.json")
    assert doc["image"] == ""


def test_a_stock_photo_reference_finds_nothing(maps: pathlib.Path) -> None:
    hw = hardware_profile.HardwareProfile()
    assert hw.imageUrl(_GLADIATOR) == ""
    _write(maps / "vkb_evo_r.json", {"kind": "control.hardware", "image": _GLADIATOR})
    assert hw.profilePhotoUrl("VKB EVO R") == ""
    assert not hasattr(hardware_profile, "_stock_photo")


# --- GL-271: asking a photo doesn't reload the object's document ------------


def test_asking_a_photo_leaves_the_document_alone(maps: pathlib.Path) -> None:
    hw = hardware_profile.HardwareProfile()
    _write(maps / "stick_a.json", {"kind": "control.hardware", "nodes": [1]})
    _write(maps / "stick_b.json", {"kind": "control.hardware", "nodes": [2]})
    hw.load("Stick A")
    before = (hw.path, hw.text)
    seen: list[str] = []
    hw.documentChanged.connect(lambda: seen.append("doc"))
    hw.pathChanged.connect(lambda: seen.append("path"))
    assert hw.profilePhotoUrl("Stick B") == ""
    assert (hw.path, hw.text) == before
    assert seen == []


def test_a_photo_named_by_the_file_is_still_found(maps: pathlib.Path) -> None:
    photo = maps / "stick_b" / "front.png"
    photo.parent.mkdir()
    photo.write_bytes(b"png")
    _write(maps / "stick_b.json", {"image": "stick_b/front.png"})
    url = hardware_profile.HardwareProfile().profilePhotoUrl("Stick B")
    assert "stick_b/front.png" in url


# --- GL-268, GL-270: Save refuses non-objects; one page size ----------------


def test_save_refuses_text_that_is_not_an_object(maps: pathlib.Path) -> None:
    hw = hardware_profile.HardwareProfile()
    assert hw.save("Test Stick", "[1, 2]") is False
    assert hw.save("Test Stick", "not json") is False
    assert not (maps / "test_stick.json").exists()


def test_save_stamps_the_one_page_size(maps: pathlib.Path) -> None:
    hw = hardware_profile.HardwareProfile()
    assert hw.save("Test Stick", json.dumps({"nodes": [], "page": 1, "pageW": 2}))
    doc = _read(maps / "test_stick.json")
    for key, value in hardware_profile.PAGE_SIZE.items():
        assert doc[key] == value
    window = (_ROOT / "qml" / "DialogJoystickButtonMap.qml").read_text(encoding="utf-8")
    assert "32000" not in window and "18000" not in window


# --- GL-273: pictures no map uses leave the device folder (07 Q11) ----------


def test_unused_pictures_go_when_an_edit_ends(maps: pathlib.Path) -> None:
    folder = maps / "test_stick"
    folder.mkdir()
    for name in ("photo.jpg", "on_map.png", "in_group.png", "in_template.png",
                 "in_recovery.png", "added.png", "pasted_1.png"):
        (folder / name).write_bytes(b"x")
    (folder / "notes.txt").write_text("not a picture", encoding="utf-8")
    _write(maps / "test_stick.json", {
        "image": "test_stick/photo.jpg",
        "nodes": [
            {"shape": "image", "src": "test_stick/on_map.png"},
            {"kind": "group", "members": [
                {"shape": "image", "src": "test_stick/in_group.png"}]},
        ],
    })
    _write(maps / "templates" / "t.json", {
        "nodes": [{"shape": "image", "src": "test_stick/in_template.png"}]})
    _write(store.recovery_path("other"), {
        "nodes": [{"shape": "image", "src": "test_stick/in_recovery.png"}]})
    hw = hardware_profile.HardwareProfile()
    assert hw.removeUnusedPictures("Test Stick") == 2
    left = sorted(p.name for p in folder.iterdir())
    assert left == ["in_group.png", "in_recovery.png", "in_template.png",
                    "notes.txt", "on_map.png", "photo.jpg"]
    assert hw.removeUnusedPictures("Test Stick") == 0


def test_the_window_drops_unused_pictures_when_an_edit_ends() -> None:
    window = (_ROOT / "qml" / "DialogJoystickButtonMap.qml").read_text(encoding="utf-8")
    start = window.index("function discardEdit()")
    body = window[start:window.index("function takeTheirs", start)]
    assert "dropUnusedPictures()" in body


# --- GL-276: the pack's preview folder is removed --------------------------


def test_the_preview_folder_goes_on_close_and_at_quit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registered: list[object] = []
    monkeypatch.setattr(device_pack, "_drop_at_exit", False)
    monkeypatch.setattr(device_pack.atexit, "register", registered.append)
    folder, urls = device_pack._stage_images({"a.png": b"png"})
    try:
        assert os.path.isdir(folder) and urls
        assert registered == [device_pack.drop_preview]
        hardware_profile.HardwareProfile().dropPackPreview()
        assert not os.path.exists(folder)
        assert device_pack._preview_dir == ""
    finally:
        device_pack.drop_preview()
    dialog = (_ROOT / "qml" / "DialogDevicePack.qml").read_text(encoding="utf-8")
    assert "_hw.dropPackPreview()" in dialog


# --- GL-277: a restored profile copy says it is the user's to delete ---------


def test_a_restored_profile_copy_says_where_it_stays(tmp_path: pathlib.Path) -> None:
    from gremlin import history_profile
    from gremlin.ui import history_model

    entry = {
        "at": time.time(),
        "subject": {"profile": str(tmp_path / "My.xml")},
        "before": {"packed": history_profile.pack_text("<profile/>")},
    }
    ok, message = history_model._restore_profile(entry, entry["before"], "before")
    assert ok
    assert "File > Load Profile" in message
    assert "until you delete it" in message


# --- GL-275: Auto Mapper vJoy sizes through the output module (08 R7) -------


def test_auto_mapper_reads_vjoy_sizes_through_the_output_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    from gremlin import auto_mapper, device_initialization
    from gremlin.modules import output

    vjoy = SimpleNamespace(vjoy_id=1, axis_map=[], button_count=0, hat_count=0)
    monkeypatch.setattr(device_initialization, "vjoy_devices", lambda: [vjoy])
    monkeypatch.setattr(device_initialization, "output_vjoy_devices", lambda: [vjoy])
    monkeypatch.setattr(output, "vjoy_layout", lambda vid: (3, 4, 1))
    monkeypatch.setattr(output, "vjoy_axis_ids", lambda vid: {1, 2, 6})
    limits = auto_mapper.AutoMapper(None)._vjoy_limits(1)  # type: ignore[arg-type]
    assert limits == {"axes": {1, 2, 6}, "buttons": {1, 2, 3, 4}, "hats": {1}}


# --- C2 request: History shows a setting's choice as Options does ----------


def test_history_shows_the_device_change_choice_as_options_does() -> None:
    from gremlin.ui import history_model

    text = history_model._settings_text(
        {"global/general/device-change-behavior": "Disable"}
    )
    assert text.endswith(": Stop")


def test_auto_mapper_falls_back_to_the_device_list_without_the_driver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    from gremlin import auto_mapper, device_initialization
    from gremlin.modules import output

    def no_driver(vid: int) -> tuple[int, int, int]:
        raise OSError("no vJoy driver")

    vjoy = SimpleNamespace(
        vjoy_id=1,
        axis_map=[SimpleNamespace(axis_index=1), SimpleNamespace(axis_index=3)],
        button_count=2,
        hat_count=1,
    )
    monkeypatch.setattr(device_initialization, "vjoy_devices", lambda: [vjoy])
    monkeypatch.setattr(device_initialization, "output_vjoy_devices", lambda: [vjoy])
    monkeypatch.setattr(output, "vjoy_layout", no_driver)
    monkeypatch.setattr(output, "vjoy_axis_ids", lambda vid: set())
    mapper = auto_mapper.AutoMapper(None)  # type: ignore[arg-type]
    expected = {"axes": {1, 3}, "buttons": {1, 2}, "hats": {1}}
    assert mapper._vjoy_limits(1) == expected
    # An empty layout (not read) falls back the same way.
    monkeypatch.setattr(output, "vjoy_layout", lambda vid: (0, 0, 0))
    assert mapper._vjoy_limits(1) == expected
