# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Catch-up batch 2, Button Map (B6): fixes in gremlin/ui/hardware_profile.py
and the Button Map's JavaScript, each driven through its real slot.

Spec: claude/program-map/07-button-map.md (Q2, Q3, Q8, Q10, Q13, Q19, S29,
S81, RB8) and 08-history-pack-automap.md (R4, S49).
GL-030, GL-174, GL-175, GL-177, GL-178, GL-180, GL-181, GL-183, GL-196.
(GL-043 and GL-138 are in test_stage1_modules.py; GL-173, GL-176, GL-179,
GL-182, GL-184 in test_stage1_button_map.py; GL-188 in
test_stage1_history_pack.py.)
"""

from __future__ import annotations

import json
import pathlib
import zipfile
from collections.abc import Iterator

import pytest
from PySide6 import QtCore, QtGui, QtQml

from gremlin.modules import store
from gremlin.signal import signal
from gremlin.ui import device_pack, hardware_profile

_ROOT = pathlib.Path(__file__).parents[2]


@pytest.fixture
def maps(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> pathlib.Path:
    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setattr(store, "folder", lambda: folder)
    monkeypatch.setattr(
        store, "slug_for", lambda name, guid="": name.lower().replace(" ", "_")
    )
    return folder


def _zip_bytes() -> bytes:
    import io

    blob = io.BytesIO()
    with zipfile.ZipFile(blob, "w") as zf:
        zf.writestr("map.json", json.dumps({"kind": "control.hardware"}))
    return blob.getvalue()


# --- GL-030: the exported pack through a temporary file, read back ------------


def _fake_pack(monkeypatch: pytest.MonkeyPatch, data: bytes) -> None:
    monkeypatch.setattr(
        device_pack,
        "assemble",
        lambda *a, **k: (data, {"device": "Test Stick", "sizeText": "1 KB"}),
    )


def test_a_failed_export_leaves_the_older_pack_whole(
    maps: pathlib.Path, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # 08 R4: a write that stops part way never leaves half a zip over the
    # older pack.
    dest = tmp_path / "out" / "pack.zip"
    dest.parent.mkdir()
    old = _zip_bytes()
    dest.write_bytes(old)
    _fake_pack(monkeypatch, _zip_bytes() + b"more")
    real = pathlib.Path.write_bytes

    def half_then_full_disk(self: pathlib.Path, data: bytes) -> int:
        real(self, bytes(data)[:10])
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(pathlib.Path, "write_bytes", half_then_full_disk)
    result = json.loads(hardware_profile.HardwareProfile().exportPack(
        "Test Stick", dest.as_uri(), ""))
    monkeypatch.setattr(pathlib.Path, "write_bytes", real)
    assert result["ok"] is False
    assert dest.read_bytes() == old


def test_an_export_that_does_not_read_back_says_so(
    maps: pathlib.Path, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # As Delete Device's pack: read back before it counts as written.
    _fake_pack(monkeypatch, b"not a zip")
    dest = tmp_path / "out" / "pack.zip"
    result = json.loads(hardware_profile.HardwareProfile().exportPack(
        "Test Stick", dest.as_uri(), ""))
    assert result["ok"] is False
    assert "read back" in result["error"]
    _fake_pack(monkeypatch, _zip_bytes())
    result = json.loads(hardware_profile.HardwareProfile().exportPack(
        "Test Stick", dest.as_uri(), ""))
    assert result["ok"] is True, result
    assert not dest.with_name(dest.name + ".tmp").exists()


# --- GL-174, GL-175: nothing in the module file until Save -------------------


def test_choose_photo_writes_no_image_into_the_module_file(
    maps: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    # 07 Q2: the new photo waits beside the old one until Save.
    path = maps / "test_stick.json"
    path.write_text(
        json.dumps({"kind": "control.hardware", "nodes": []}), encoding="utf-8")
    before = path.read_bytes()
    picture = tmp_path / "new.png"
    image = QtGui.QImage(4, 4, QtGui.QImage.Format.Format_RGB32)
    image.fill(QtGui.QColor("#336699"))
    image.save(str(picture))
    hw = hardware_profile.HardwareProfile()
    hw.stashPhoto("Test Stick")
    rel = hw.copyImage(picture.as_uri(), "Test Stick")
    assert rel == "test_stick/photo.png"
    assert (maps / "test_stick" / "photo.png").is_file()
    assert path.read_bytes() == before
    # Save names it (one write).
    assert hw.save("Test Stick", json.dumps({"image": rel, "nodes": []}))
    assert json.loads(path.read_text(encoding="utf-8"))["image"] == rel


def test_a_ui_change_makes_no_module_file(maps: pathlib.Path) -> None:
    # 07 S29, S96 (GL-175): the ui block waits in the window until Save.
    hw = hardware_profile.HardwareProfile()
    assert hw.saveUi("Test Stick", json.dumps({"ui": {"guidesX": [0.5]}})) is False
    assert not (maps / "test_stick.json").exists()
    (maps / "test_stick.json").write_text(
        json.dumps({"kind": "control.hardware", "nodes": []}), encoding="utf-8")
    assert hw.saveUi("Test Stick", json.dumps({"ui": {"guidesX": [0.5]}})) is True
    doc = json.loads((maps / "test_stick.json").read_text(encoding="utf-8"))
    assert doc["ui"] == {"guidesX": [0.5]}


# --- GL-177: a typed name is always the user's ------------------------------


_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture
def chips_js() -> Iterator[QtQml.QJSEngine]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    engine = QtQml.QJSEngine()
    source = _ROOT / "qml" / "rig_chips.js"
    result = engine.evaluate(source.read_text(encoding="utf-8"), str(source))
    assert not result.isError(), result.toString()
    # The EVO R list the editor has (VkbRigEditor.physNames).
    engine.evaluate('var physNames = {"btn:4": "White cap", "axis:1": "Stick X roll"}')
    yield engine


def test_a_name_equal_to_an_evo_r_part_is_kept(chips_js: QtQml.QJSEngine) -> None:
    # 07 Q10, RB10: "White cap" on Button 4 is the user's name on any device.
    def kept(code: str) -> bool:
        return chips_js.evaluate(f"isUserFriendly({code})").toBool()

    assert kept('"btn", 4, "White cap"') is True
    assert kept('"axis", 1, "Stick X roll"') is True
    # The control's own label and an empty name still mean "no name".
    assert kept('"btn", 4, "Button 4"') is False
    assert kept('"btn", 4, "  "') is False


# --- GL-178: the picture folder ----------------------------------------------


class _Settings:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str, str], object] = {}

    def value(self, *key: str) -> object:
        return self.values.get(key, "")

    def set(self, *args: object) -> None:
        self.values[tuple(args[:3])] = args[3]  # type: ignore[index]


def test_the_picture_dialogs_open_where_the_last_picture_came_from(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    # 07 Q13: Pictures, or the last folder used; nothing made anywhere.
    settings = _Settings()
    monkeypatch.setattr(hardware_profile, "_picture_folder_config", lambda: settings)
    install = tmp_path / "install"
    install.mkdir()
    monkeypatch.setattr(hardware_profile, "_install_root", lambda: install)
    hw = hardware_profile.HardwareProfile()
    first = QtCore.QUrl(hw.imagesFolderUrl()).toLocalFile()
    assert "install" not in first
    shots = tmp_path / "shots"
    shots.mkdir()
    hw.notePictureFolder((shots / "a.png").as_uri())
    assert pathlib.Path(QtCore.QUrl(hw.imagesFolderUrl()).toLocalFile()) == shots
    assert list(install.iterdir()) == []


# --- GL-180: pool rows read again only when something changed ----------------


def test_the_pool_rows_key_changes_only_with_what_they_depend_on(
    maps: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # 07 RB8: a live press asks for the key; the module file and the profile
    # are read again only when it changed.
    from gremlin.ui import input_pairing

    guid = "{11111111-2222-3333-4444-555555555555}"
    monkeypatch.setattr(input_pairing, "_device_name", lambda g: "Test Stick")
    hw = hardware_profile.HardwareProfile()
    first = hw.chipsKey(guid)
    assert first and hw.chipsKey(guid) == first
    (maps / "test_stick.json").write_text(
        json.dumps({"claim": {"buttons": [1]}}), encoding="utf-8")
    second = hw.chipsKey(guid)
    assert second != first
    signal.profileChanged.emit()
    assert hw.chipsKey(guid) != second
    assert hw.chipsKey("") == ""


def test_the_card_reads_rows_by_the_key() -> None:
    # The card asks for the rows only when the key changed, not at every
    # live stamp (JoystickButtonMapCard.qml).
    card = (_ROOT / "qml" / "JoystickButtonMapCard.qml").read_text(encoding="utf-8")
    assert "_inventory.chipsKey(deviceGuid)" in card
    binding = card[card.find("property var chipRows"):]
    # Not a binding: refreshChipRows() assigns it (no "Overwriting binding").
    assert binding.startswith("property var chipRows: null")


# --- GL-181: a template's missing pictures ------------------------------------


def test_a_template_says_which_pictures_are_missing(
    maps: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    # 07 S81: a template keeps where its pictures are; a moved or deleted
    # one is named when it is applied.
    (maps / "test_stick").mkdir()
    (maps / "test_stick" / "here.png").write_bytes(b"png")
    hw = hardware_profile.HardwareProfile()
    nodes = [
        {"id": "p1", "kind": "draw", "shape": "image", "src": "test_stick/here.png"},
        {"id": "p2", "kind": "draw", "shape": "image", "src": "test_stick/gone.png"},
        {"id": "b1", "kind": "btn", "hwId": 1},
    ]
    assert hw.saveTemplate("Mine", json.dumps(nodes), "Test Stick")
    assert hw.templateMissingPictures("Mine") == ["gone.png"]
    assert hw.templateMissingPictures("Not there") == []


# --- GL-182: the controls a device has ----------------------------------------


def test_device_controls_come_from_the_pool_when_not_connected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(store, "connected_input_ids", lambda g: None)
    monkeypatch.setattr(hardware_profile, "chips_for_guid", lambda g: [
        {"kind": "btn", "hwId": 2}, {"kind": "axis", "hwId": 1}])
    have = hardware_profile.HardwareProfile().deviceControls("some-guid")
    assert have == {"known": True, "btn": [2], "axis": [1], "hat": []}
    monkeypatch.setattr(store, "connected_input_ids", lambda g: ({1, 3}, set(), {1}))
    have = hardware_profile.HardwareProfile().deviceControls("some-guid")
    assert have == {"known": True, "btn": [1, 3], "axis": [], "hat": [1]}


# --- GL-183: which file and why ------------------------------------------------


def test_a_failed_export_names_the_file_and_why(tmp_path: pathlib.Path) -> None:
    # 07 Q19: as Template export does.
    target = tmp_path / "no folder" / "map.png"
    hw = hardware_profile.HardwareProfile()
    image = QtGui.QImage(20, 10, QtGui.QImage.Format.Format_RGB32)
    image.fill(QtGui.QColor("#202020"))
    assert hw.saveArea(image, 20, 10, target.as_uri(), "png", "{}") is False
    said = hw.exportError()
    assert said.startswith("Export failed.")
    assert "map.png" in said and "the folder does not exist" in said
    ok = tmp_path / "map.png"
    assert hw.saveArea(image, 20, 10, ok.as_uri(), "png", "{}") is True
    assert hw.exportError() == ""


# --- GL-196: the export preview builds no zip ----------------------------------


def test_the_pack_preview_estimates_without_building_the_zip(
    maps: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # 08 S49: at every device change, on the UI thread: no zip.
    (maps / "test_stick").mkdir()
    (maps / "test_stick" / "photo.jpg").write_bytes(b"x" * 5000)
    (maps / "test_stick.json").write_text(json.dumps({
        "kind": "control.hardware", "image": "test_stick/photo.jpg", "nodes": []}),
        encoding="utf-8")

    def no_zip(*args: object, **kwargs: object) -> object:
        raise AssertionError("the preview built the pack")

    monkeypatch.setattr(device_pack, "assemble", no_zip)
    info = json.loads(hardware_profile.HardwareProfile().peekPackDevice("Test Stick"))
    assert info["ok"] is True, info
    assert info["bytes"] > 5000
    assert info["sizeText"].startswith("about ")
    assert info["photoUrl"].endswith("photo.jpg")
    missing = json.loads(hardware_profile.HardwareProfile().peekPackDevice("Nobody"))
    assert missing["ok"] is False
