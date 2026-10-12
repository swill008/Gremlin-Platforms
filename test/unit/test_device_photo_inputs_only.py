# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The device's background picture (pictures/device-photo.png, 07 S157) is
for input modules only (user, 2026-10-11, D-07-BG-COMPOSITE input modules
only). Outputs (vJoy, the Xbox pad: direction "dest") and the Logical
Device are never drawn; their cards, Module Setup, Device Library entries
and Export / Import previews show the bottom background picture, as before
(07 S127). A file left in such a folder by an earlier run is removed.

The real store and DevicePhotoMaker in an empty modules folder; a fake host
draws a small PNG for each job (DevicePhotoHost.qml's part).
"""

from __future__ import annotations

import json
import zipfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6 import QtCore, QtGui

from gremlin import device_library as library
from gremlin.modules import ids, store
from gremlin.ui import device_photo, hardware_profile

LD = "Logical Device"


@pytest.fixture
def modules(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    base = tmp_path / "modules"
    base.mkdir()
    monkeypatch.setattr(store, "folder", lambda: base)
    monkeypatch.setattr(store, "notify_module_files", lambda: None)
    store._dirs_changed()
    return base


class _Host:
    """Answers each job at once with a 40 x 20 picture on black and white."""

    def __init__(self, maker: device_photo.DevicePhotoMaker) -> None:
        self.maker = maker
        self.jobs: list[str] = []
        maker.renderWanted.connect(self._job)

    def _job(self, token: str, _nodes: str, _pics: str, _side: int, out: str) -> None:
        self.jobs.append(out)
        for path, ground in (
            (out, "black"),
            (device_photo.white_path(Path(out)), "white"),
        ):
            image = QtGui.QImage(40, 20, QtGui.QImage.Format.Format_RGB32)
            image.fill(QtGui.QColor(ground))
            assert image.save(str(path))
        self.maker.rendered(token, True)


@pytest.fixture
def host(modules: Path, qapp: QtCore.QCoreApplication) -> Iterator[_Host]:
    made = device_photo.DevicePhotoMaker()
    made.setProperty("hostReady", True)
    yield _Host(made)
    made.close()


def _png(width: int, height: int) -> bytes:
    image = QtGui.QImage(width, height, QtGui.QImage.Format.Format_ARGB32)
    image.fill(0xFF336699)
    data = QtCore.QByteArray()
    buffer = QtCore.QBuffer(data)
    buffer.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
    assert image.save(buffer, "PNG")  # pyright: ignore[reportCallIssue, reportArgumentType]
    return bytes(data.data())


_BG = {
    "id": "b1",
    "kind": "draw",
    "shape": "image",
    "src": "pictures/back.png",
    "plane": "background",
    "fx": 0.2,
    "fy": 0.2,
    "fw": 0.3,
    "fh": 0.3,
}


def _doc(name: str, guid: str = "", direction: str = "source") -> dict:
    doc: dict = {
        "kind": "control.hardware",
        "device": name,
        "direction": direction,
        "nodes": [dict(_BG)],
    }
    if guid:
        doc["boundName"] = name
        doc["boundGuidLocal"] = guid
    return doc


def _device(name: str, guid: str = "", direction: str = "source") -> Path:
    """A device folder with one background picture and an old
    device-photo.png (as an earlier run of this batch left)."""
    path = store.ensure_device_dir(name, guid)
    pics = path / store.PICTURES
    pics.mkdir(exist_ok=True)
    (pics / "back.png").write_bytes(_png(40, 20))
    (pics / store.DEVICE_PHOTO).write_bytes(_png(30, 30))
    (path / store.MODULE_FILE).write_text(
        json.dumps(_doc(name, guid, direction)), encoding="utf-8"
    )
    return path


_LD_GUID = "{" + str(ids.LOGICAL_DEVICE).upper() + "}"
_NOT_INPUTS = [
    pytest.param("vJoy 1", "", "dest", id="vjoy"),
    pytest.param(LD, _LD_GUID, "source", id="logical-device"),
]


@pytest.mark.parametrize(("name", "guid", "direction"), _NOT_INPUTS)
def test_outputs_and_the_logical_device_get_no_background_picture(
    host: _Host, name: str, guid: str, direction: str
) -> None:
    path = _device(name, guid, direction)
    doc = store.read_path(store.module_file_in(path))
    assert not store.makes_device_photo(doc, path)
    assert store.background_key(doc, path) == ""
    host.maker.check_all()
    assert host.jobs == [], "never drawn"
    assert not store.device_photo_path(path).exists(), "an old file is removed"
    assert store.picture_ref(store.DEVICE_PHOTO) not in store.named_refs(doc)


def test_an_input_module_still_gets_it(host: _Host) -> None:
    path = _device("Stick One")
    doc = store.read_path(store.module_file_in(path))
    assert store.makes_device_photo(doc, path)
    host.maker.check_all()
    assert len(host.jobs) == 1
    assert store.device_photo_current(path)
    assert store.picture_ref(store.DEVICE_PHOTO) in store.named_refs(doc)


@pytest.mark.parametrize(("name", "guid", "direction"), _NOT_INPUTS)
def test_their_photo_is_the_bottom_picture_as_before(
    modules: Path, monkeypatch: pytest.MonkeyPatch, name: str, guid: str, direction: str
) -> None:
    asked: list[str] = []
    monkeypatch.setattr(device_photo, "want", lambda n, _g: asked.append(n))
    path = _device(name, guid, direction)
    doc = store.read_path(store.module_file_in(path))
    assert store.shown_photo_ref(doc, lambda _r: True) == "pictures/back.png"
    hw = hardware_profile.HardwareProfile()
    if guid:
        hw.setDeviceGuid(guid)
    url = hw.profilePhotoUrl(name)
    assert url.split("?")[0].rsplit("/", 1)[-1] == "back.png"


def test_an_input_modules_photo_is_its_background_picture(modules: Path) -> None:
    doc = _doc("Stick One")
    assert store.shown_photo_ref(doc, lambda _r: True) == store.picture_ref(
        store.DEVICE_PHOTO
    )


@pytest.mark.parametrize(
    ("name", "guid", "direction", "size"),
    [
        pytest.param("vJoy 1", "", "dest", (40, 20), id="vjoy"),
        pytest.param("Xbox 360 Controller", "", "dest", (40, 20), id="xbox"),
        pytest.param(LD, _LD_GUID, "source", (40, 20), id="logical-device"),
        pytest.param("Stick One", "", "source", (30, 30), id="input"),
    ],
)
def test_a_saved_setup_shows_what_it_showed_before(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    guid: str,
    direction: str,
    size: tuple[int, int],
) -> None:
    pack = tmp_path / "setup.zip"
    with zipfile.ZipFile(pack, "w") as zf:
        zf.writestr(library.GMAP_MODULE, json.dumps(_doc(name, guid, direction)))
        zf.writestr("pictures/back.png", _png(40, 20))
        zf.writestr("pictures/" + store.DEVICE_PHOTO, _png(30, 30))
    monkeypatch.setattr(library, "pack_path", lambda _key: pack)
    monkeypatch.setattr(library, "_photo_cache", lambda: tmp_path / "cache")
    shown = library.photo("set-1")
    found = QtGui.QImageReader(shown).size()
    assert (found.width(), found.height()) == size
