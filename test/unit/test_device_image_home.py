# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Device Image on Home's input module cards (D-03-DEVICE-IMAGE, 03
S52, S88, S136): Add Image… / Change Image… / Remove Image on a stick,
Keyboard or OSC card set the device's own image file, named by the module
file's "deviceImage" key (not a map layer), each as one Home Undo step;
the card model's hasImage role says whether there is one. Output cards
are refused; the Logical Device card keeps its own picture (the bottom
background picture). Module Setup's Save names the staged image, or drops
it on Remove Image.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6 import QtCore

from gremlin import device_initialization, history_modules
from gremlin.modules import store
from gremlin.modules.ids import KEYBOARD, LOGICAL_DEVICE, OSC
from gremlin.ui import module_model
from test.unit._device_folders import (
    put_module,  # pyright: ignore[reportMissingImports]
)
from test.unit.test_stage1_modules import (  # noqa: F401  # pyright: ignore[reportMissingImports]
    folder,
)

_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32 + b"\xff\xd9"
_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
KB = "Keyboard"
KB_GUID = str(KEYBOARD).upper()


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    yield app


@pytest.fixture
def modules(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    path = tmp_path / "modules"
    path.mkdir()
    monkeypatch.setattr(store, "folder", lambda: path)
    monkeypatch.setattr(store, "_saved", lambda: None)
    monkeypatch.setattr(module_model, "_hidden_slugs", lambda: set())
    monkeypatch.setattr(history_modules, "note_write", lambda *a, **k: None)
    return path


def _pick(tmp_path: Path, name: str, data: bytes) -> str:
    src = tmp_path / "pick" / name
    src.parent.mkdir(exist_ok=True)
    src.write_bytes(data)
    return src.as_uri()


def _doc(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _keyboard(modules: Path) -> Path:
    nodes = [{"id": "chip", "kind": "draw", "shape": "rect", "plane": "background"}]
    doc = {"kind": "control.hardware", "device": KB, "direction": "source"}
    return put_module(modules, KB, {**doc, "nodes": nodes}, KB_GUID)


def _pictures(path: Path) -> list[str]:
    folder_ = path.parent / "pictures"
    return sorted(p.name for p in folder_.iterdir()) if folder_.is_dir() else []


def test_the_card_model_has_a_hasImage_role(modules: Path) -> None:
    _keyboard(modules)
    model = module_model.ModuleListModel()
    model.reload()
    assert "hasImage" in [bytes(v.data()).decode() for v in model.roleNames().values()]
    assert model.cardMap("keyboard")["hasImage"] is False
    assert model.cardMap("logical")["hasImage"] is False


def test_add_change_remove_on_an_input_card_with_home_undo(
    modules: Path, tmp_path: Path
) -> None:
    path = _keyboard(modules)
    nodes = _doc(path)["nodes"]
    model = module_model.ModuleListModel()
    model.reload()

    # Add Image…: the device image, its own file; the map is untouched.
    assert model.setCardImage("keyboard", _pick(tmp_path, "a.jpg", _JPEG))
    doc = _doc(path)
    assert doc[store.DEVICE_IMAGE_KEY] == "pictures/device-image.jpg"
    assert doc["nodes"] == nodes
    assert _pictures(path) == ["device-image.jpg"]
    assert model.cardMap("keyboard")["hasImage"] is True
    assert model.undoTip == "Undo Add Image (Ctrl+Z)"

    # Change Image…: the new file replaces the old one.
    assert model.setCardImage("keyboard", _pick(tmp_path, "b.png", _PNG))
    ref = store.device_image_ref(_doc(path))
    assert ref.startswith("pictures/device-image") and ref.endswith(".png")
    assert _pictures(path) == [Path(ref).name]
    assert model.undoTip == "Undo Change Image (Ctrl+Z)"

    # Remove Image: key and file go.
    assert model.removeCardImage("keyboard")
    assert store.DEVICE_IMAGE_KEY not in _doc(path)
    assert _pictures(path) == []
    assert model.cardMap("keyboard")["hasImage"] is False
    assert model.undoTip == "Undo Remove Image (Ctrl+Z)"

    # Undo Remove brings the file and the key back.
    model.undo()
    assert store.device_image_ref(_doc(path)) == ref
    assert (path.parent / ref).read_bytes() == _PNG
    assert model.cardMap("keyboard")["hasImage"] is True

    # Undo Change puts the first image back and drops the second file.
    model.undo()
    assert _doc(path)[store.DEVICE_IMAGE_KEY] == "pictures/device-image.jpg"
    assert _pictures(path) == ["device-image.jpg"]
    assert (path.parent / "pictures" / "device-image.jpg").read_bytes() == _JPEG

    # Undo Add: no image; Redo Add: the image again.
    model.undo()
    assert store.DEVICE_IMAGE_KEY not in _doc(path)
    assert _pictures(path) == []
    assert model.cardMap("keyboard")["hasImage"] is False
    model.redo()
    assert _doc(path)[store.DEVICE_IMAGE_KEY] == "pictures/device-image.jpg"
    assert model.cardMap("keyboard")["hasImage"] is True
    assert _doc(path)["nodes"] == nodes


def test_osc_card_takes_an_image(modules: Path, tmp_path: Path) -> None:
    path = put_module(
        modules, "OSC", {"kind": "control.hardware", "device": "OSC"}, str(OSC).upper()
    )
    model = module_model.ModuleListModel()
    model.reload()
    assert model.setCardImage("osc", _pick(tmp_path, "o.jpg", _JPEG))
    assert store.device_image_ref(_doc(path)) == "pictures/device-image.jpg"
    assert model.cardMap("osc")["hasImage"] is True


def test_output_cards_are_refused(modules: Path, tmp_path: Path) -> None:
    model = module_model.ModuleListModel()
    model.reload()
    url = _pick(tmp_path, "a.jpg", _JPEG)
    assert model.setCardImage("xbox", url) is False
    assert model.removeCardImage("xbox") is False
    assert model.setCardImage("no_such_card", url) is False
    assert not model.canUndo
    assert not list(modules.rglob("device-image*"))


def test_logical_device_card_keeps_its_bottom_background_picture(
    modules: Path, tmp_path: Path
) -> None:
    path = put_module(
        modules, "Logical Device", {"name": "Logical Device"}, str(LOGICAL_DEVICE)
    )
    model = module_model.ModuleListModel()
    model.reload()
    assert model.setCardImage("logical", _pick(tmp_path, "l.jpg", _JPEG))
    doc = _doc(path)
    assert store.device_photo_ref(doc) == "pictures/photo.jpg"
    assert store.DEVICE_IMAGE_KEY not in doc
    assert model.cardMap("logical")["hasImage"] is False


def _plugged_stick() -> tuple[str, str]:
    for dev in device_initialization.physical_devices():
        if dev.name == "pJoy Pro":
            return dev.name, store.guid_text(dev.device_guid)
    pytest.skip("the fake stick is not there")


def test_module_setup_save_names_the_image_and_remove_drops_it(
    folder: Path,  # noqa: F811
) -> None:
    name, guid = _plugged_stick()
    there = store.ensure_device_dir(name, guid)
    (there / "pictures").mkdir(exist_ok=True)
    (there / "pictures" / "device-image.png").write_bytes(_PNG)
    module = store.module_file_in(there)
    setup = module_model.DriverInputModel()
    try:
        setup.loadDevice(guid, name)
        setup.setClaimed(0, True)
        assert setup.saveClaim(name, "source", "pictures/device-image.png", False)
        doc = _doc(module)
        assert doc[store.DEVICE_IMAGE_KEY] == "pictures/device-image.png"
        assert not store.device_photo_ref(doc)
        # A Save that leaves the image alone keeps it.
        assert setup.saveClaim(name, "source")
        assert _doc(module)[store.DEVICE_IMAGE_KEY] == "pictures/device-image.png"
        # Remove Image, then Save: the key and the file go.
        assert setup.saveClaim(name, "source", "", True)
    finally:
        setup.deleteLater()
    assert store.DEVICE_IMAGE_KEY not in _doc(module)
    assert not (there / "pictures" / "device-image.png").exists()
