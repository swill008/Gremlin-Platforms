# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The device's background picture's store rules (07 S157, S127,
D-07-BG-COMPOSITE): which background nodes it shows, its key, the file and
its reserved name, the photo every page shows, and that it is a picture the
map names (kept by the clean-up, History and every .gmap)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6 import QtCore, QtGui

from gremlin import history_modules
from gremlin.modules import store
from test.unit.test_stage1_modules import (  # noqa: F401  # pyright: ignore[reportMissingImports]
    folder,
    stick_guid,
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


def _picture(dev: Path, name: str, width: int = 20, height: int = 10) -> str:
    (dev / store.PICTURES).mkdir(parents=True, exist_ok=True)
    image = QtGui.QImage(width, height, QtGui.QImage.Format.Format_RGB32)
    image.fill(0x336699)
    assert image.save(str(dev / store.PICTURES / name))
    return store.picture_ref(name)


def _png(key: str = "") -> bytes:
    image = QtGui.QImage(8, 4, QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtGui.QColor(0, 0, 0, 0))
    if key:
        image.setText(store.DEVICE_PHOTO_KEY, key)
    buffer = QtCore.QBuffer()
    buffer.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
    assert image.save(buffer, "PNG")  # pyright: ignore[reportCallIssue, reportArgumentType]
    return bytes(buffer.data().data())


def _bg(node_id: str, **extra: object) -> dict:
    node = {
        "id": node_id,
        "kind": "draw",
        "shape": "rect",
        "plane": "background",
        "fx": 0.2,
        "fy": 0.2,
        "fw": 0.3,
        "fh": 0.3,
    }
    node.update(extra)
    return node


def _pic(node_id: str, src: str, **extra: object) -> dict:
    return _bg(node_id, shape="image", src=src, **extra)


def _chip(n: int) -> dict:
    return {"id": f"c{n}", "kind": "btn", "hwId": n, "fx": 0.1, "fy": 0.1}


# --- the file and its constants ------------------------------------------------


def test_the_file_is_device_photo_png_in_pictures(tmp_path: Path) -> None:
    assert store.DEVICE_PHOTO == "device-photo.png"
    assert store.DEVICE_PHOTO_SIDE == 1024
    assert store.picture_ref(store.DEVICE_PHOTO) == "pictures/device-photo.png"
    assert store.device_photo_path(tmp_path) == (
        tmp_path / "pictures" / "device-photo.png"
    )


# --- what it shows -------------------------------------------------------------


def test_visible_background_is_the_shown_background_nodes_in_order() -> None:
    a, b = _bg("a"), _pic("b", "pictures/b.png")
    doc = {
        "nodes": [
            a,
            _chip(1),
            _bg("hid", hidden=True),
            {"id": "f", "kind": "draw", "shape": "image", "src": "pictures/f.png"},
            b,
        ]
    }
    assert store.visible_background(doc) == [a, b]
    assert store.visible_background({"nodes": [_chip(1)]}) == []
    assert store.visible_background({}) == []
    assert store.visible_background(None) == []


# --- its key ---------------------------------------------------------------------


def test_no_visible_background_has_no_key(tmp_path: Path) -> None:
    assert store.background_key({"nodes": [_chip(1)]}, tmp_path) == ""
    assert store.background_key({"nodes": [_bg("h", hidden=True)]}, tmp_path) == ""


def test_the_key_follows_the_background_only(tmp_path: Path) -> None:
    ref = _picture(tmp_path, "back.png")
    doc = {"nodes": [_pic("p", ref), _bg("s"), _chip(1)]}
    key = store.background_key(doc, tmp_path)
    assert key and len(key) == 20

    # Foreground, hidden layers and screen-only keys don't change it.
    moved_chip = {"nodes": [_pic("p", ref), _bg("s"), {**_chip(1), "fx": 0.9}]}
    assert store.background_key(moved_chip, tmp_path) == key
    hidden_added = {"nodes": [*doc["nodes"], _bg("h", hidden=True)]}
    assert store.background_key(hidden_added, tmp_path) == key
    screen = {
        "nodes": [
            _pic("p", ref, srcUrl="file:///x.png", lookUrl="u", selected=True, _tmp=1),
            _bg("s"),
        ]
    }
    assert store.background_key(screen, tmp_path) == key

    # A background change does: a move, a new layer, the picture's file.
    moved = {"nodes": [_pic("p", ref, fx=0.5), _bg("s")]}
    assert store.background_key(moved, tmp_path) != key
    assert store.background_key({"nodes": [_pic("p", ref)]}, tmp_path) != key
    _picture(tmp_path, "back.png", 200, 100)
    assert store.background_key(doc, tmp_path) != key


def test_the_render_version_is_in_the_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    doc = {"nodes": [_bg("s")]}
    key = store.background_key(doc, tmp_path)
    monkeypatch.setattr(store, "RENDER_VERSION", store.RENDER_VERSION + 1)
    assert store.background_key(doc, tmp_path) != key


def test_a_copied_picture_keeps_the_key(tmp_path: Path) -> None:
    """Size, not time: a picture copied by Export / Import keeps its key."""
    one, two = tmp_path / "one", tmp_path / "two"
    ref = _picture(one, "back.png")
    (two / store.PICTURES).mkdir(parents=True)
    (two / store.PICTURES / "back.png").write_bytes(
        (one / store.PICTURES / "back.png").read_bytes()
    )
    doc = {"nodes": [_pic("p", ref)]}
    assert store.background_key(doc, one) == store.background_key(doc, two)


# --- the file: written, read, current, removed --------------------------------


def test_written_without_a_history_step_and_read_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[object] = []
    monkeypatch.setattr(history_modules, "before_change", calls.append)
    store.write_device_photo(tmp_path, _png("abc123"))
    assert store.device_photo_path(tmp_path).is_file()
    assert store.device_photo_key(tmp_path) == "abc123"
    assert calls == []


def test_current_when_the_key_matches(tmp_path: Path) -> None:
    doc = {"nodes": [_bg("s")]}
    assert not store.device_photo_current(tmp_path, doc)  # no file
    store.write_device_photo(tmp_path, _png(store.background_key(doc, tmp_path)))
    assert store.device_photo_current(tmp_path, doc)
    assert not store.device_photo_current(tmp_path, {"nodes": [_bg("s", fx=0.6)]})
    # No visible background: never current, the file should go.
    assert not store.device_photo_current(tmp_path, {"nodes": [_chip(1)]})


def test_current_reads_the_folders_module_file(tmp_path: Path) -> None:
    import json

    doc = {"nodes": [_bg("s")]}
    (tmp_path / store.MODULE_FILE).write_text(json.dumps(doc), encoding="utf-8")
    store.write_device_photo(tmp_path, _png(store.background_key(doc, tmp_path)))
    assert store.device_photo_current(tmp_path)


def test_a_file_without_a_key_is_stale(tmp_path: Path) -> None:
    store.write_device_photo(tmp_path, _png())
    assert store.device_photo_key(tmp_path) == ""
    assert not store.device_photo_current(tmp_path, {"nodes": [_bg("s")]})


def test_remove_device_photo(tmp_path: Path) -> None:
    store.remove_device_photo(tmp_path)  # nothing there: no error
    store.write_device_photo(tmp_path, _png("k"))
    store.remove_device_photo(tmp_path)
    assert not store.device_photo_path(tmp_path).exists()
    assert store.device_photo_key(tmp_path) == ""


# --- the photo every page shows (07 S127) -----------------------------------------


def test_shown_photo_is_the_background_picture_when_it_is_there() -> None:
    doc = {"nodes": [_bg("s"), _pic("p", "pictures/bottom.png")]}
    there = {"pictures/device-photo.png", "pictures/bottom.png"}
    assert store.shown_photo_ref(doc, there.__contains__) == (
        "pictures/device-photo.png"
    )


def test_shown_photo_falls_back_to_the_bottom_background_picture() -> None:
    doc = {"nodes": [_bg("s"), _pic("p", "pictures/bottom.png")]}
    assert store.shown_photo_ref(doc, lambda ref: False) == "pictures/bottom.png"
    # A file left behind with no visible background left is not shown.
    hidden = {"nodes": [_pic("p", "pictures/bottom.png", hidden=True)]}
    assert store.shown_photo_ref(hidden, lambda ref: True) == "pictures/bottom.png"
    assert store.shown_photo_ref({"nodes": [_chip(1)]}, lambda ref: True) == ""


# --- a picture the map names (07 S106, 08 S8, S113) ------------------------------


def test_named_refs_holds_it_with_a_visible_background() -> None:
    doc = {"nodes": [_pic("p", "pictures/back.png"), _chip(1)]}
    assert store.named_refs(doc) == {"pictures/back.png", "pictures/device-photo.png"}
    assert store.named_refs({"nodes": [_bg("s")]}) == {"pictures/device-photo.png"}
    assert store.named_refs({"nodes": [_bg("h", hidden=True)]}) == set()
    front = {"nodes": [{"id": "f", "shape": "image", "src": "pictures/f.png"}]}
    assert store.named_refs(front) == {"pictures/f.png"}


def test_the_clean_up_keeps_it(modules: Path) -> None:
    name, guid = "pJoy Pro", stick_guid()
    dev = store.ensure_device_dir(name, guid)
    ref = _picture(dev, "back.png")
    _picture(dev, "stray.png")
    store.write_device_photo(dev, _png("k"))
    removed = store.remove_unused_pictures(
        name, guid, store.named_refs({"nodes": [_pic("p", ref)]})
    )
    assert [p.name for p in removed] == ["stray.png"]
    assert store.device_photo_path(dev).is_file()


# --- the reserved name --------------------------------------------------------------


def test_put_picture_never_writes_a_user_picture_under_its_name(
    modules: Path,
) -> None:
    name, guid = "pJoy Pro", stick_guid()
    dev = store.ensure_device_dir(name, guid)
    store.write_device_photo(dev, _png("k"))
    ref = store.put_picture(name, guid, _png(), "device-photo.png")
    assert ref == "pictures/device-photo_1.png"
    assert store.device_photo_key(dev) == "k"  # the made file untouched
    again = store.put_picture(name, guid, _png(), "Device-Photo.png")
    assert Path(again).name.casefold() != store.DEVICE_PHOTO
    assert store.device_photo_key(dev) == "k"


def test_a_staged_picture_never_takes_its_name(tmp_path: Path) -> None:
    name, same = store._free_picture_name("device-photo.png", b"x", [tmp_path])
    assert (name, same) == ("device-photo_1.png", False)


def test_copying_a_map_leaves_it_to_be_made_at_the_destination(
    tmp_path: Path,
) -> None:
    src, dest = tmp_path / "src", tmp_path / "dest"
    ref = _picture(src, "back.png")
    store.write_device_photo(src, _png("k"))
    refs = store.named_refs({"nodes": [_pic("p", ref)]})
    moved = store.copy_pictures(src, refs, dest)
    assert moved == {ref: ref}
    assert not store.device_photo_path(dest).exists()
