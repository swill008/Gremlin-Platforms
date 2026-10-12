# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Where "the device's photo" is shown (07 S127, S157, D-07-BG-COMPOSITE):
the device's background picture (pictures/device-photo.png) once made,
else the bottom background picture. HardwareProfile.profilePhotoUrl (Home
cards, Module Setup, HidHide, the Xbox page) asks for it to be made when
it is missing or stale; the Device Library's photo, the Export and Import
Device previews show it; an import takes the pack's only with the pack's
background (08 S75); pictureSize reads a picture's own size (07 S83)."""

from __future__ import annotations

import json
import zipfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6 import QtCore, QtGui

from gremlin import device_library as library
from gremlin.modules import store
from gremlin.ui import device_pack, device_photo, hardware_profile
from test.unit._gmap_files import write_gmap  # pyright: ignore[reportMissingImports]
from test.unit.test_stage1_modules import (  # noqa: F401  # pyright: ignore[reportMissingImports]
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


@pytest.fixture
def wanted(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(device_photo, "want", lambda n, g: calls.append((n, g)))
    return calls


def _png(width: int, height: int, color: int, key: str = "") -> bytes:
    image = QtGui.QImage(width, height, QtGui.QImage.Format.Format_ARGB32)
    image.fill(color)
    if key:
        image.setText(store.DEVICE_PHOTO_KEY, key)
    data = QtCore.QByteArray()
    buffer = QtCore.QBuffer(data)
    buffer.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
    assert image.save(buffer, "PNG")  # pyright: ignore[reportCallIssue, reportArgumentType]
    return bytes(data.data())


def _put(folder: Path, name: str, data: bytes) -> Path:
    path = folder / store.PICTURES / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _bg(src: str) -> dict:
    return {
        "id": "b-" + Path(src).stem,
        "kind": "draw",
        "shape": "image",
        "src": src,
        "plane": "background",
        "fx": 0.2,
        "fy": 0.2,
        "fw": 0.3,
        "fh": 0.3,
    }


def _chip(n: int) -> dict:
    return {"id": f"c{n}", "kind": "btn", "hwId": n, "fx": 0.1, "fy": 0.1}


def _device(modules: Path, photo_key: str | None) -> Path:
    """pJoy Pro with one background picture; with photo_key, its
    device-photo.png holding that key ("current": the right one)."""
    doc = stick_doc(nodes=[_bg("pictures/back.png"), _chip(1)])
    current = write_module(modules, "pjoy_pro", doc)
    base = current.parent
    _put(base, "back.png", _png(40, 20, 0xFF336699))
    if photo_key is not None:
        key = store.background_key(doc, base) if photo_key == "current" else photo_key
        _put(base, store.DEVICE_PHOTO, _png(30, 30, 0xFFAA0000, key))
    return base


def _profile() -> hardware_profile.HardwareProfile:
    hw = hardware_profile.HardwareProfile()
    hw.setDeviceGuid(stick_guid())
    return hw


def _shown(url: str) -> str:
    return url.split("?")[0].rsplit("/", 1)[-1]


# --- Home cards, Module Setup, HidHide, Xbox page: profilePhotoUrl ---------


def test_cards_show_the_background_picture_once_made(
    modules: Path, wanted: list
) -> None:
    _device(modules, "current")
    assert _shown(_profile().profilePhotoUrl("pJoy Pro")) == store.DEVICE_PHOTO
    assert wanted == []


def test_cards_show_the_bottom_picture_and_ask_for_the_background_picture(
    modules: Path, wanted: list
) -> None:
    _device(modules, None)
    assert _shown(_profile().profilePhotoUrl("pJoy Pro")) == "back.png"
    assert wanted == [("pJoy Pro", stick_guid())]


def test_a_stale_background_picture_shows_until_it_is_made_again(
    modules: Path, wanted: list
) -> None:
    _device(modules, "0" * 20)
    assert _shown(_profile().profilePhotoUrl("pJoy Pro")) == store.DEVICE_PHOTO
    assert wanted == [("pJoy Pro", stick_guid())]


def test_no_background_asks_for_nothing(modules: Path, wanted: list) -> None:
    write_module(modules, "pjoy_pro", stick_doc(nodes=[_chip(1)]))
    assert _profile().profilePhotoUrl("pJoy Pro") == ""
    assert wanted == []


def test_picture_size_reads_the_pictures_own_size(tmp_path: Path) -> None:
    path = _put(tmp_path, "p.png", _png(48, 27, 0xFF000000))
    hw = _profile()
    url = QtCore.QUrl.fromLocalFile(str(path)).toString()
    assert hw.pictureSize(url) == {"w": 48, "h": 27}
    assert hw.pictureSize(str(path)) == {"w": 48, "h": 27}
    assert hw.pictureSize("") == {"w": 0, "h": 0}
    assert hw.pictureSize(url + "-missing") == {"w": 0, "h": 0}
    # A picture replaced by another of a new size is read again.
    path.write_bytes(_png(10, 5, 0xFF000000))
    import os

    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 10_000_000))
    assert hw.pictureSize(url) == {"w": 10, "h": 5}


# --- Device Library: Device map photo (10 S11) -----------------------------


def _setup_zip(tmp_path: Path, with_photo: bool) -> Path:
    doc = stick_doc(nodes=[_bg("pictures/back.png"), _chip(1)])
    path = tmp_path / "setup.zip"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(library.GMAP_MODULE, json.dumps(doc))
        zf.writestr("pictures/back.png", _png(40, 20, 0xFF336699))
        if with_photo:
            zf.writestr("pictures/" + store.DEVICE_PHOTO, _png(30, 30, 0xFFAA0000))
    return path


@pytest.mark.parametrize("with_photo", [True, False])
def test_a_saved_setup_shows_its_background_picture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, with_photo: bool
) -> None:
    pack = _setup_zip(tmp_path, with_photo)
    monkeypatch.setattr(library, "pack_path", lambda _key: pack)
    monkeypatch.setattr(library, "_photo_cache", lambda: tmp_path / "cache")
    shown = library.photo("set-1")
    assert shown
    size = QtGui.QImageReader(shown).size()
    assert (size.width(), size.height()) == ((30, 30) if with_photo else (40, 20))


# --- Export / Import Device previews (08) ----------------------------------


def test_the_export_preview_shows_the_background_picture(
    modules: Path, wanted: list
) -> None:
    base = _device(modules, "current")
    plan = device_pack.plan_pack(
        "pJoy Pro", lambda r: store.find_picture(base, r), guid=stick_guid()
    )
    assert isinstance(plan, dict), plan
    assert Path(plan["photoPath"]).name == store.DEVICE_PHOTO


def _pack(tmp_path: Path, photo_key: str) -> tuple[Path, dict]:
    """A .gmap of a stick whose background is theirs.png, with a
    device-photo.png holding photo_key ("current": the key the device has
    after taking that background)."""
    node = _bg("theirs.png")
    doc = {
        **stick_doc(nodes=[node, _chip(2)]),
        "pack": {"exportedName": "pJoy Pro", "format": 1},
    }
    theirs = _png(64, 32, 0xFF00AA00)
    if photo_key == "current":
        # The same background in a folder with the same picture: the key
        # the import leaves.
        scratch = tmp_path / "scratch"
        _put(scratch, "theirs.png", theirs)
        after = {"nodes": [{**node, "src": store.picture_ref("theirs.png")}]}
        photo_key = store.background_key(after, scratch)
    photo = _png(16, 16, 0xFF0000AA, photo_key)
    path = write_gmap(
        tmp_path / "pack.gmap",
        {"map.json": doc, "theirs.png": theirs, store.DEVICE_PHOTO: photo},
    )
    return path, {"theirs": theirs, "photo": photo}


def test_the_import_preview_shows_the_packs_background_picture(
    modules: Path, tmp_path: Path
) -> None:
    path, data = _pack(tmp_path, "current")
    described = device_pack.describe_zip(path)
    assert isinstance(described, dict), described
    shown = QtCore.QUrl(described["photoUrl"]).toLocalFile()
    assert Path(shown).read_bytes() == data["photo"]
    # It is made, never a picture row of its own.
    ids = [
        item["id"] for section in described["sections"] for item in section["items"]
    ]
    assert "pic:" + store.DEVICE_PHOTO not in ids


def test_taking_the_packs_background_takes_its_picture(
    modules: Path, tmp_path: Path
) -> None:
    base = _device(modules, "current")
    before = store.device_photo_path(base).read_bytes()
    path, data = _pack(tmp_path, "current")
    # Old: the Device photo tick alone ("pic:theirs.png"); that row is gone,
    # the pack's background comes with the Map tick (D-03-DEVICE-IMAGE).
    result = device_pack.apply_zip(
        path,
        "pJoy Pro",
        {"items": ["in.layout", "pic:theirs.png"]},
        target_guid=stick_guid(),
    )
    assert result.get("ok"), result
    assert store.device_photo_path(base).read_bytes() == data["photo"]
    assert store.device_photo_current(base)
    # Restore Import puts this device's back.
    assert device_pack.undo_import(force=True).get("ok")
    assert store.device_photo_path(base).read_bytes() == before


def test_keeping_this_devices_background_keeps_its_picture(
    modules: Path, tmp_path: Path
) -> None:
    base = _device(modules, "current")
    before = store.device_photo_path(base).read_bytes()
    path, _data = _pack(tmp_path, "current")
    result = device_pack.apply_zip(
        path, "pJoy Pro", {"items": ["in.checks"]}, target_guid=stick_guid()
    )
    assert result.get("ok"), result
    assert store.device_photo_path(base).read_bytes() == before


def test_a_pack_picture_that_does_not_match_is_left_out(
    modules: Path, tmp_path: Path
) -> None:
    base = _device(modules, None)
    path, _data = _pack(tmp_path, "f" * 20)
    result = device_pack.apply_zip(
        path, "pJoy Pro", {"items": ["pic:theirs.png"]}, target_guid=stick_guid()
    )
    assert result.get("ok"), result
    assert not store.device_photo_path(base).exists()
