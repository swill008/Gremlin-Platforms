# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The device's photo is the bottom background picture (07 S111, S127,
D-07-BACKGROUND-PLANES): store.device_photo_ref reads it and
store.set_device_photo sets it; the pictures a map names include its
background layers (07 S106)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PySide6 import QtGui

from gremlin.modules import store


def _picture(folder: Path, name: str, width: int, height: int) -> str:
    (folder / store.PICTURES).mkdir(parents=True, exist_ok=True)
    image = QtGui.QImage(width, height, QtGui.QImage.Format.Format_RGB32)
    image.fill(0x336699)
    assert image.save(str(folder / store.PICTURES / name))
    return store.picture_ref(name)


def _bg(src: str, **extra: object) -> dict:
    node = {
        "id": "b" + src,
        "kind": "draw",
        "shape": "image",
        "src": src,
        "plane": "background",
        "fx": 0.2,
        "fy": 0.2,
        "fw": 0.3,
        "fh": 0.3,
    }
    node.update(extra)
    return node


def test_the_photo_is_the_bottom_background_picture() -> None:
    doc = {
        "nodes": [
            {"id": "s", "kind": "draw", "shape": "rect", "plane": "background"},
            _bg("pictures/bottom.png"),
            _bg("pictures/upper.png"),
            {"id": "f", "kind": "draw", "shape": "image", "src": "pictures/front.png"},
        ]
    }
    assert store.device_photo_ref(doc) == "pictures/bottom.png"


def test_a_foreground_picture_is_not_the_photo() -> None:
    doc = {
        "nodes": [
            {"id": "f", "kind": "draw", "shape": "image", "src": "pictures/a.png"}
        ]
    }
    assert store.device_photo_ref(doc) == ""
    assert store.device_photo_ref({}) == ""
    assert store.device_photo_ref(None) == ""


def test_an_old_map_names_its_photo_until_saved() -> None:
    assert store.device_photo_ref({"image": "pictures/photo.jpg", "nodes": []}) == (
        "pictures/photo.jpg"
    )


def test_set_device_photo_adds_a_bottom_layer_fitted_to_the_frame(
    tmp_path: Path,
) -> None:
    ref = _picture(tmp_path, "photo.png", 400, 200)
    chip = {"id": "c1", "kind": "chip"}
    shape = {"id": "s", "kind": "draw", "shape": "rect", "plane": "background"}
    doc = {"nodes": [shape, chip]}
    store.set_device_photo(doc, ref, tmp_path)
    first = doc["nodes"][0]
    assert first["plane"] == "background" and first["shape"] == "image"
    assert first["src"] == ref
    assert store.device_photo_ref(doc) == ref
    assert doc["nodes"][1] is shape
    assert doc["nodes"][-1] is chip
    # 400x200 in the 24000x13500 frame: width-bound, centred.
    assert first["fw"] == pytest.approx(0.75)
    assert first["fh"] == pytest.approx(24000 * 0.5 / 18000)
    assert first["fx"] == pytest.approx(0.125)
    assert first["fy"] + first["fh"] / 2 == pytest.approx(0.5)


def test_set_device_photo_replaces_the_picture_in_its_place(tmp_path: Path) -> None:
    ref = _picture(tmp_path, "new.png", 300, 300)
    old = _bg("pictures/old.png", crop={"x": 0.1}, opacity=0.5, locked=True)
    doc = {"nodes": [old]}
    store.set_device_photo(doc, ref, tmp_path)
    assert len(doc["nodes"]) == 1
    node = doc["nodes"][0]
    assert node["src"] == ref and node["opacity"] == 0.5 and node["locked"] is True
    assert "crop" not in node
    # Square picture inside the old 0.3 x 0.3 box: same centre.
    assert node["fx"] + node["fw"] / 2 == pytest.approx(0.35)
    assert node["fy"] + node["fh"] / 2 == pytest.approx(0.35)
    assert node["fw"] * 32000 == pytest.approx(node["fh"] * 18000)


def test_set_device_photo_empty_removes_it() -> None:
    doc = {"nodes": [_bg("pictures/old.png"), _bg("pictures/upper.png")]}
    store.set_device_photo(doc, "")
    assert [n["src"] for n in doc["nodes"]] == ["pictures/upper.png"]


def test_set_device_photo_turns_an_old_map_into_layers() -> None:
    doc = {"image": "pictures/old.png", "photo": {"scale": 1}, "nodes": []}
    store.set_device_photo(doc, "pictures/new.png")
    assert "image" not in doc and "photo" not in doc
    assert store.device_photo_ref(doc) == "pictures/new.png"
    assert len(doc["nodes"]) == 1


def test_named_refs_counts_background_pictures() -> None:
    doc = {
        "nodes": [
            _bg("pictures/back.png"),
            {"id": "f", "shape": "image", "src": "pictures/front.png"},
        ]
    }
    assert store.named_refs(doc) == {"pictures/back.png", "pictures/front.png"}


def test_unused_pictures_keep_background_pictures(tmp_path: Path) -> None:
    """remove_unused_pictures keeps a picture only a background layer names."""
    _picture(tmp_path, "back.png", 10, 10)
    _picture(tmp_path, "stray.png", 10, 10)
    keep = store._names_of(store.named_refs({"nodes": [_bg("pictures/back.png")]}))
    assert keep == {"back.png"}


# --- the real paths: Import, the Device Mapping Editor's load and save,
# Module Setup ---

from collections.abc import Iterator  # noqa: E402

from PySide6 import QtCore  # noqa: E402

from gremlin.ui import hardware_profile, module_model  # noqa: E402
from test.unit.test_stage1_modules import (  # noqa: E402,F401  # pyright: ignore[reportMissingImports]
    folder,
    stick_doc,
    stick_guid,
    write_module,
)

_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


@pytest.fixture
def modules(request: pytest.FixtureRequest) -> Path:
    return request.getfixturevalue(folder.__name__)


def _chip(n: int) -> dict:
    return {"id": f"c{n}", "kind": "btn", "hwId": n, "fx": 0.1, "fy": 0.1}


def test_import_keeps_this_devices_background_and_takes_the_foreground(
    modules: Path, tmp_path: Path
) -> None:
    """03 S135 (P5a): the imported file's background is not copied."""
    own_bg = _bg("pictures/mine.png")
    current = write_module(modules, "pjoy_pro", stick_doc(nodes=[own_bg, _chip(1)]))
    _picture(current.parent, "mine.png", 20, 10)
    source = tmp_path / "other"
    theirs = _picture(source, "theirs.png", 30, 30)
    front = _picture(source, "front.png", 30, 30)
    chosen = source / "other.json"
    chosen.write_text(
        json.dumps(
            {
                "kind": "control.hardware",
                "device": "Other",
                "direction": "source",
                "claim": {"buttons": [1, 2], "axes": [], "hats": [], "keys": []},
                "nodes": [
                    _bg(theirs),
                    _chip(2),
                    {"id": "p", "kind": "draw", "shape": "image", "src": front},
                ],
            }
        ),
        encoding="utf-8",
    )
    message = module_model.ModuleListModel().importModuleFile(
        stick_guid(), "pJoy Pro", str(chosen), "source"
    )
    assert message.startswith("Imported into pJoy Pro."), message
    assert "This device's background was kept." in message
    doc = json.loads(current.read_text(encoding="utf-8"))
    assert doc["nodes"][0] == own_bg
    assert [n["id"] for n in doc["nodes"]] == [own_bg["id"], "c2", "p"]
    assert store.device_photo_ref(doc) == "pictures/mine.png"
    pictures = current.parent / store.PICTURES
    assert (pictures / "front.png").is_file()
    assert not (pictures / "theirs.png").exists()


def test_import_onto_an_old_map_keeps_its_photo_as_background(
    modules: Path, tmp_path: Path
) -> None:
    current = write_module(
        modules,
        "pjoy_pro",
        stick_doc(image="pictures/photo.png", photo={"scale": 1}, nodes=[]),
    )
    _picture(current.parent, "photo.png", 40, 20)
    chosen = tmp_path / "other.json"
    chosen.write_text(
        json.dumps(
            {
                "kind": "control.hardware",
                "device": "Other",
                "direction": "source",
                "image": "pictures/x.png",
                "claim": {"buttons": [1], "axes": [], "hats": [], "keys": []},
                "nodes": [_chip(1)],
            }
        ),
        encoding="utf-8",
    )
    message = module_model.ModuleListModel().importModuleFile(
        stick_guid(), "pJoy Pro", str(chosen), "source"
    )
    assert "This device's background was kept." in message
    doc = json.loads(current.read_text(encoding="utf-8"))
    assert "image" not in doc and "photo" not in doc
    assert store.device_photo_ref(doc) == "pictures/photo.png"
    assert doc["nodes"][1]["id"] == "c1"


def _profile() -> hardware_profile.HardwareProfile:
    hw = hardware_profile.HardwareProfile()
    hw.setDeviceGuid(stick_guid())
    return hw


def test_load_turns_an_old_map_in_memory_only(modules: Path) -> None:
    """07 S125 (P3a): opening never writes the file."""
    current = write_module(
        modules,
        "pjoy_pro",
        stick_doc(
            image="pictures/photo.png",
            photo={"scale": 2, "fade": 0.5},
            nodes=[_chip(1)],
        ),
    )
    _picture(current.parent, "photo.png", 40, 20)
    before = current.read_bytes()
    text = _profile().load("pJoy Pro")
    assert current.read_bytes() == before
    doc = json.loads(text)
    assert "image" not in doc and "photo" not in doc
    assert doc["nodes"][0]["plane"] == "background"
    assert doc["nodes"][0]["opacity"] == pytest.approx(0.5)
    assert doc["nodes"][1]["id"] == "c1"


def test_save_writes_no_old_photo_keys(modules: Path) -> None:
    current = write_module(
        modules,
        "pjoy_pro",
        stick_doc(image="pictures/photo.png", photo={"scale": 1}, nodes=[]),
    )
    _picture(current.parent, "photo.png", 40, 20)
    hw = _profile()
    text = hw.load("pJoy Pro")
    assert hw.save("pJoy Pro", text)
    doc = json.loads(current.read_text(encoding="utf-8"))
    assert "image" not in doc and "photo" not in doc
    assert store.device_photo_ref(doc) == "pictures/photo.png"
    # The photo is still named, so it stays (07 S106).
    assert (current.parent / store.PICTURES / "photo.png").is_file()
    assert hw.profilePhotoUrl("pJoy Pro").split("?")[0].endswith("pictures/photo.png")


def test_profile_photo_is_the_bottom_background_picture(modules: Path) -> None:
    current = write_module(
        modules, "pjoy_pro", stick_doc(nodes=[_bg("pictures/back.png"), _chip(1)])
    )
    _picture(current.parent, "back.png", 40, 20)
    url = _profile().profilePhotoUrl("pJoy Pro")
    assert url.split("?")[0].endswith("pictures/back.png")


def test_module_setup_import_image_sets_the_bottom_picture(
    modules: Path, tmp_path: Path
) -> None:
    """07 S127: Module Setup's Import Image sets the same layer."""
    current = write_module(
        modules, "pjoy_pro", stick_doc(nodes=[_bg("pictures/back.png"), _chip(1)])
    )
    _picture(current.parent, "back.png", 40, 20)
    chosen = tmp_path / "pick" / "new.png"
    _picture(tmp_path / "pick", "x.png", 50, 50)
    (tmp_path / "pick" / store.PICTURES / "x.png").replace(chosen)
    hw = _profile()
    hw.beginEditFor("pJoy Pro", "setup")
    rel = hw.copyImage(QtCore.QUrl.fromLocalFile(str(chosen)).toString(), "pJoy Pro")
    assert rel
    assert hw.commitEditFor("pJoy Pro", "setup") == ""
    doc = json.loads(current.read_text(encoding="utf-8"))
    assert "image" not in doc
    assert store.device_photo_ref(doc) == store.normal_ref(rel)
    assert [n["id"] for n in doc["nodes"]] == ["bpictures/back.png", "c1"]
    # The old picture is no longer named and goes (07 S106).
    assert not (current.parent / store.PICTURES / "back.png").exists()


def test_adjusted_url_takes_a_pictures_look(modules: Path, tmp_path: Path) -> None:
    ref = _picture(tmp_path, "p.png", 8, 8)
    url = QtCore.QUrl.fromLocalFile(str(tmp_path / ref)).toString()
    hw = _profile()
    assert hw.adjustedPhotoUrl(url, {}) == ""
    grey = hw.adjustedPhotoUrl(url, {"grey": 1})
    assert grey.startswith("file:")
    assert hw.adjustedPhotoUrl(url, {"grey": 1, "bright": 0.2}) != grey
    assert hw.adjustedPhotoUrl(url, {"grey": 0.5}) != grey


def test_save_drops_the_screen_only_urls(modules: Path) -> None:
    """A picture's "srcUrl" and "lookUrl" (its look's adjusted copy) are
    for the screen only, never written."""
    current = write_module(modules, "pjoy_pro", stick_doc(nodes=[]))
    _picture(current.parent, "back.png", 40, 20)
    node = _bg(
        "pictures/back.png",
        look={"grey": 0.5},
        srcUrl="file:///x/back.png",
        lookUrl="file:///x/look.png",
    )
    hw = _profile()
    hw.load("pJoy Pro")
    assert hw.save("pJoy Pro", json.dumps({"nodes": [node, _chip(1)]}))
    saved = json.loads(current.read_text(encoding="utf-8"))["nodes"][0]
    assert "lookUrl" not in saved and "srcUrl" not in saved
    assert saved["look"] == {"grey": 0.5}
