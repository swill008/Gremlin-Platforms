# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Device Image's store rules (D-03-DEVICE-IMAGE, input modules only):
its own file pictures/device-image.<ext> named by the module file's
"deviceImage" key, set and removed outside any edit, carried as a picture
the module file names, and first in what every page shows as the device's
photo (Device Image, then the background picture, then the bottom
background picture)."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest

from gremlin.modules import module_file as module_file_io
from gremlin.modules import store

STICK = "1111AAAA2222BBBB3333CCCC4444DDDD"
NAME = "Device Image Test Stick"


@pytest.fixture
def modules(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    base = tmp_path / "modules"
    base.mkdir()
    monkeypatch.setattr(store, "folder", lambda: base)
    store._dirs_changed()
    yield base
    store._dirs_changed()


def _device(doc: dict | None = None) -> Path:
    made = store.ensure_device_dir(NAME, STICK)
    body = {"device": NAME, "nodes": []} if doc is None else doc
    (made / store.MODULE_FILE).write_text(json.dumps(body), encoding="utf-8")
    return made


def _doc(made: Path) -> dict:
    return json.loads((made / store.MODULE_FILE).read_text(encoding="utf-8"))


def _pictures(made: Path) -> list[str]:
    folder = made / store.PICTURES
    return sorted(p.name for p in folder.iterdir()) if folder.is_dir() else []


def _bottom(src: str) -> dict:
    return {
        "id": "b",
        "kind": "draw",
        "shape": "image",
        "src": src,
        "plane": "background",
    }


# --- the key and the file name -------------------------------------------------


def test_the_key_and_the_file_name() -> None:
    assert store.DEVICE_IMAGE_KEY == "deviceImage"
    assert store.device_image_name(Path("C:/x/My Stick.PNG")) == "device-image.png"
    assert store.device_image_name("shot.jpeg") == "device-image.jpeg"
    assert store.device_image_name("shot.gif") == "device-image.jpg"
    assert store.device_image_name("") == "device-image.jpg"


def test_device_image_ref_reads_the_key() -> None:
    assert store.device_image_ref({"deviceImage": "pictures/device-image.png"}) == (
        "pictures/device-image.png"
    )
    assert store.device_image_ref({"deviceImage": "device-image.png"}) == (
        "pictures/device-image.png"
    )
    assert store.device_image_ref({}) == ""
    assert store.device_image_ref({"deviceImage": 3}) == ""
    assert store.device_image_ref(None) == ""


# --- precedence: Device Image > background picture > bottom picture ------------


def test_the_image_comes_first() -> None:
    doc = {
        "device": NAME,
        "deviceImage": "pictures/device-image.png",
        "nodes": [_bottom("pictures/photo.png")],
    }
    assert store.shown_photo_ref(doc, lambda ref: True) == "pictures/device-image.png"


def test_without_the_image_file_the_background_picture_then_the_bottom() -> None:
    doc = {
        "device": NAME,
        "deviceImage": "pictures/device-image.png",
        "nodes": [_bottom("pictures/photo.png")],
    }
    made = {"pictures/device-photo.png", "pictures/photo.png"}
    assert store.shown_photo_ref(doc, made.__contains__) == (
        "pictures/device-photo.png"
    )
    assert store.shown_photo_ref(doc, lambda ref: False) == "pictures/photo.png"


def test_an_output_never_shows_an_image() -> None:
    doc = {
        "device": "vJoy 1",
        "direction": "dest",
        "deviceImage": "pictures/device-image.png",
        "nodes": [_bottom("pictures/photo.png")],
    }
    assert store.shown_photo_ref(doc, lambda ref: True) == "pictures/photo.png"


def test_the_image_is_a_named_picture() -> None:
    doc = {"deviceImage": "pictures/device-image.jpg", "nodes": []}
    assert store.named_refs(doc) == {"pictures/device-image.jpg"}
    assert store.named_refs({"nodes": []}) == set()


def test_a_moved_image_is_renamed() -> None:
    doc = {"deviceImage": "pictures/device-image.png", "nodes": []}
    moved = {"pictures/device-image.png": "pictures/device-image_1.png"}
    store._rename_refs(doc, moved)
    assert doc["deviceImage"] == "pictures/device-image_1.png"


# --- set and remove outside an edit -------------------------------------------


def test_set_writes_the_file_and_the_key(modules: Path, tmp_path: Path) -> None:
    made = _device()
    picked = tmp_path / "picked.png"
    picked.write_bytes(b"first image")
    ref = store.set_device_image(NAME, STICK, picked, "Home")
    assert ref == "pictures/device-image.png"
    assert _doc(made)["deviceImage"] == ref
    assert (made / ref).read_bytes() == b"first image"


def test_change_replaces_the_previous_file(modules: Path, tmp_path: Path) -> None:
    made = _device()
    first, second = tmp_path / "a.png", tmp_path / "b.jpg"
    first.write_bytes(b"first image")
    second.write_bytes(b"second image")
    store.set_device_image(NAME, STICK, first, "Home")
    ref = store.set_device_image(NAME, STICK, second, "Home")
    assert ref == "pictures/device-image.jpg"
    assert _doc(made)["deviceImage"] == ref
    assert _pictures(made) == ["device-image.jpg"]


def test_a_taken_name_gets_a_number(modules: Path) -> None:
    made = _device()
    store.set_device_image(NAME, STICK, b"one", "Home", as_name="x.png")
    ref = store.set_device_image(NAME, STICK, b"two", "Home", as_name="x.png")
    assert ref == "pictures/device-image_1.png"
    assert _pictures(made) == ["device-image_1.png"]
    assert (made / ref).read_bytes() == b"two"


def test_the_image_survives_the_unused_picture_clean_up(modules: Path) -> None:
    made = _device()
    ref = store.set_device_image(NAME, STICK, b"img", "Home", as_name="x.png")
    store.remove_unused_pictures(NAME, STICK)
    assert (made / ref).is_file()


def test_a_damaged_file_is_refused_before_any_picture(
    modules: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    told: list[object] = []
    monkeypatch.setattr(module_file_io, "report_refused", told.append)
    made = store.ensure_device_dir(NAME, STICK)
    (made / store.MODULE_FILE).write_text("{ not json", encoding="utf-8")
    assert store.set_device_image(NAME, STICK, b"img", "Home", as_name="x.png") == ""
    assert _pictures(made) == []
    assert (made / store.MODULE_FILE).read_text(encoding="utf-8") == "{ not json"
    assert len(told) == 1


def test_a_failed_write_removes_the_new_file(
    modules: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    made = _device()

    def fail(*args: object, **kwargs: object) -> bool:
        raise OSError("disk full")

    monkeypatch.setattr(store, "update", fail)
    assert store.set_device_image(NAME, STICK, b"img", "Home", as_name="x.png") == ""
    assert _pictures(made) == []


@pytest.mark.parametrize("name, guid", [("vJoy 1", ""), ("Logical Device", "")])
def test_outputs_and_the_logical_device_get_no_image(
    modules: Path, name: str, guid: str
) -> None:
    assert store.set_device_image(name, guid, b"img", "Home", as_name="x.png") == ""
    assert not any(modules.rglob("device-image*"))


def test_remove_drops_the_key_and_the_file(modules: Path) -> None:
    made = _device()
    ref = store.set_device_image(NAME, STICK, b"img", "Home", as_name="x.png")
    assert store.remove_device_image(NAME, STICK, "Home") is True
    assert "deviceImage" not in _doc(made)
    assert not (made / ref).exists()
    assert store.remove_device_image(NAME, STICK, "Home") is False


def test_remove_keeps_the_map_pictures(modules: Path) -> None:
    made = _device({"device": NAME, "nodes": [_bottom("pictures/photo.png")]})
    (made / store.PICTURES).mkdir(exist_ok=True)
    (made / store.PICTURES / "photo.png").write_bytes(b"bottom")
    store.set_device_image(NAME, STICK, b"img", "Home", as_name="x.png")
    store.remove_device_image(NAME, STICK, "Home")
    assert _pictures(made) == ["photo.png"]
    assert _doc(made)["nodes"] == [_bottom("pictures/photo.png")]
