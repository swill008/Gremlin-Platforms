# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The device's background picture travels and is made again on every path
that carries or changes the background (D-07-BG-COMPOSITE, 07 S157).

pictures/device-photo.png is a picture of the whole visible background.
Export puts it in the .gmap and a Device Library saved setup shows it (08
S113, 10 S11); Import as new / onto existing and Restore Import take or keep
it with the background tick (08 S75) and it stays current, so nothing is
made again; a History restore, a Device Library restore, Module Setup's
Save (03 S52; its Add Image… now names the Device Image and leaves the
background alone) and the Logical Device card's Add Image (03
S88) send the module-files notice, the maker's check_all runs and a stale
picture is made again. The real store, Device Pack, Device Library,
History and DevicePhotoMaker in an empty modules folder; a fake host draws
a small PNG for each job (the QML host's part, DevicePhotoHost.qml).
"""

from __future__ import annotations

import json
import struct
import time
import zipfile
import zlib
from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6 import QtCore, QtGui

from gremlin import device_initialization, history, library_copy, logical_device_file
from gremlin import device_library as library
from gremlin.logical_device import LogicalDevice
from gremlin.modules import ids, module_file, store
from gremlin.ui import device_pack, hardware_profile, history_model, module_model
from test.unit.test_stage1_modules import (  # noqa: F401  # pyright: ignore[reportMissingImports]
    folder,
)


def _png(width: int, height: int) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return (
            struct.pack(">I", len(data))
            + body
            + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
        )

    rows = b"".join(b"\x00" + b"\x80" * width for _ in range(height))
    header = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )


PNG = _png(4, 2)
OTHER_PNG = _png(6, 3)
NAME, GUID = "Stick A", "{6C3D1E20-1111-2222-3333-444455556666}"
NEW_NAME, NEW_GUID = "Stick B", "{6C3D1E20-9999-2222-3333-444455556666}"

_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


@pytest.fixture
def modules(request: pytest.FixtureRequest) -> Path:
    return request.getfixturevalue(folder.__name__)


def _settle() -> None:
    """Lets the module-files notice (a 0 ms timer) and its listeners run."""
    for _ in range(6):
        QtCore.QCoreApplication.processEvents()
        time.sleep(0.01)


# --- the maker, with a fake host -------------------------------------------------


class _Host(QtCore.QObject):
    """Stands in for DevicePhotoHost.qml: draws each job as a small PNG at
    its outPath at once and notes the device folder it was for."""

    def __init__(self, maker: QtCore.QObject) -> None:
        super().__init__()
        self.maker = maker
        self.drawn: list[Path] = []
        maker.renderWanted.connect(self.draw)  # type: ignore[attr-defined]

    @QtCore.Slot(str, str, str, int, str)
    def draw(
        self, token: str, _nodes: str, pictures_url: str, _side: int, out_path: str
    ) -> None:
        pictures = QtCore.QUrl(pictures_url).toLocalFile().rstrip("/\\")
        self.drawn.append(Path(pictures).parent.resolve())
        from gremlin.ui import device_photo

        # The host saves the drawing on black at out_path and on white beside
        # it; the maker mattes the two (an opaque picture on both is fine).
        image = QtGui.QImage(8, 4, QtGui.QImage.Format.Format_ARGB32)
        image.fill(QtGui.QColor(10, 20, 30, 255))
        white = str(device_photo.white_path(Path(out_path)))
        ok = image.save(out_path, "PNG") and image.save(white, "PNG")
        self.maker.rendered(token, ok)  # type: ignore[attr-defined]

    def drew(self, where: Path) -> bool:
        return Path(where).resolve() in self.drawn


@pytest.fixture
def host(modules: Path) -> Iterator[_Host]:
    """The real DevicePhotoMaker following the module-files notice, counting
    its check_all runs, with the fake host ready."""
    from gremlin.ui import device_photo

    class _Maker(device_photo.DevicePhotoMaker):
        checks = 0

        def check_all(self) -> None:
            type(self).checks += 1
            super().check_all()

    maker = _Maker()
    fake = _Host(maker)
    maker.hostReady = True  # type: ignore[attr-defined]
    fake.checks = lambda: _Maker.checks  # type: ignore[attr-defined]
    yield fake
    maker.close()
    maker.deleteLater()


def _made(fake: _Host, where: Path) -> bytes:
    """Makes the folder's background picture now (start-up check) and
    returns it; nothing is drawn after that until the background changes."""
    fake.maker.check_all()  # type: ignore[attr-defined]
    _settle()
    assert store.device_photo_current(where), "the background picture wasn't made"
    fake.drawn.clear()
    return store.device_photo_path(where).read_bytes()


# --- maps --------------------------------------------------------------------------


def _photo(ref: str = "pictures/photo.png", node_id: str = "bg_photo") -> dict:
    return {
        "kind": "draw", "shape": "image", "id": node_id, "src": ref,
        "plane": "background", "fx": 0.2, "fy": 0.1, "fw": 0.6, "fh": 0.3,
        "rot": 12, "opacity": 0.8,
    }  # fmt: skip


def _bg_shape(node_id: str = "bg_rect", fx: float = 0.0) -> dict:
    return {
        "kind": "draw", "shape": "rect", "id": node_id, "plane": "background",
        "fx": fx, "fy": 0, "fw": 0.5, "fh": 0.5,
    }  # fmt: skip


def _chip(hw: int = 1) -> dict:
    return {"kind": "btn", "id": f"b{hw}", "hwId": hw}


def _doc(name: str, guid: str, nodes: list[dict]) -> dict:
    return {
        "kind": "control.hardware",
        "device": name,
        "direction": "source",
        "boundGuidLocal": guid,
        "claim": {"buttons": [1, 2], "axes": [], "hats": [], "friendly": {}},
        "nodes": nodes,
    }


def _put(name: str, guid: str, doc: dict, pictures: dict[str, bytes]) -> Path:
    where = store.ensure_device_dir(name, guid)
    for file, data in pictures.items():
        dest = where / store.PICTURES / file
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    module_file.write_bytes(store.module_file_in(where), json.dumps(doc).encode())
    return where


def _read(where: Path) -> dict:
    return store.read_path(store.module_file_in(where))


def _plugged_stick() -> tuple[str, str]:
    for dev in device_initialization.physical_devices():
        if dev.name == "pJoy Pro":
            return dev.name, store.guid_text(dev.device_guid)
    pytest.skip("the fake stick is not there")


def _source(fake: _Host) -> tuple[Path, bytes]:
    where = _put(
        NAME, GUID, _doc(NAME, GUID, [_photo(), _bg_shape(), _chip()]),
        {"photo.png": PNG},
    )  # fmt: skip
    return where, _made(fake, where)


def _export(where: Path, path: Path) -> dict:
    plan = device_pack.plan_pack(
        NAME, lambda ref: store.find_picture(where, ref), guid=GUID
    )
    assert isinstance(plan, dict), plan
    path.write_bytes(device_pack.build_pack(plan)[0])
    return plan


def _items(path: Path) -> list[str]:
    items = device_pack.pack_item_ids(path)
    assert isinstance(items, dict), items
    return list(items["input"])


DEVICE_PHOTO_ARC = "pictures/device-photo.png"


# --- Export (08 S113) and the Device Library (10 S11) --------------------------------


def test_export_carries_the_background_picture(
    modules: Path, host: _Host, tmp_path: Path
) -> None:
    where, made = _source(host)
    path = tmp_path / "pack.gmap"
    plan = _export(where, path)
    # The preview shows it (07 S127 as changed).
    assert Path(plan["photoPath"]).read_bytes() == made
    with zipfile.ZipFile(path) as zf:
        assert DEVICE_PHOTO_ARC in zf.namelist(), zf.namelist()
        assert zf.read(DEVICE_PHOTO_ARC) == made
    # It is made, not a map picture: no row of its own in Import's list.
    described = device_pack.describe_zip(path)
    assert isinstance(described, dict), described
    rows = [i["id"] for s in described["sections"] for i in s["items"]]
    assert "pic:" + store.DEVICE_PHOTO not in rows
    assert described["photoUrl"]


def test_a_saved_setup_shows_the_background_picture(modules: Path, host: _Host) -> None:
    _where, made = _source(host)
    out = library.save_setup(NAME, GUID, [])
    assert out["ok"], out
    shown = library.photo(out["setup"]["key"])
    assert shown and Path(shown).read_bytes() == made


# --- Import (08 S75, S111-S113) and Restore Import -----------------------------------


def test_import_as_new_takes_the_picture_and_does_not_make_it_again(
    modules: Path, host: _Host, tmp_path: Path
) -> None:
    where, made = _source(host)
    path = tmp_path / "pack.gmap"
    _export(where, path)
    out = device_pack.import_as_new(
        path, NEW_NAME, {"items": _items(path), "targetGuid": NEW_GUID}
    )
    assert out.get("ok"), out
    _settle()
    there = store.device_dir(NEW_NAME, NEW_GUID)
    assert store.device_photo_path(there).read_bytes() == made
    assert store.device_photo_current(there)
    assert not host.drew(there)


def _own_map(target: str, target_guid: str, fake: _Host) -> tuple[Path, bytes]:
    there = _put(
        target, target_guid,
        _doc(target, target_guid,
             [_photo("pictures/own.png", "own_photo"), _bg_shape("own_rect", 0.3)]),
        {"own.png": OTHER_PNG},
    )  # fmt: skip
    return there, _made(fake, there)


def test_import_onto_a_device_with_the_background_tick_takes_the_packs_picture(
    modules: Path, host: _Host, tmp_path: Path
) -> None:
    target, target_guid = _plugged_stick()
    where, made = _source(host)
    there, own = _own_map(target, target_guid, host)
    assert own != made or store.device_photo_key(there) != store.device_photo_key(where)
    path = tmp_path / "pack.gmap"
    _export(where, path)
    out = device_pack.apply_zip(
        path, target, {"items": _items(path)}, target_guid=target_guid
    )
    assert out.get("ok"), out
    _settle()
    bg = [n["id"] for n in store.visible_background(_read(there))]
    assert bg == ["bg_photo", "bg_rect"], bg
    assert store.device_photo_path(there).read_bytes() == made
    assert store.device_photo_current(there)
    assert not host.drew(there)


def test_import_onto_a_device_without_the_background_tick_keeps_its_picture(
    modules: Path, host: _Host, tmp_path: Path
) -> None:
    target, target_guid = _plugged_stick()
    where, _made_here = _source(host)
    there, own = _own_map(target, target_guid, host)
    path = tmp_path / "pack.gmap"
    _export(where, path)
    chosen = [
        i for i in _items(path)
        if not i.startswith("pic:") and not i.endswith(("layout", "mapview", "print"))
    ]  # fmt: skip
    assert chosen, _items(path)
    out = device_pack.apply_zip(
        path, target, {"items": chosen}, target_guid=target_guid
    )
    assert out.get("ok"), out
    _settle()
    bg = [n["id"] for n in store.visible_background(_read(there))]
    assert bg == ["own_photo", "own_rect"], bg
    assert store.device_photo_path(there).read_bytes() == own
    assert store.device_photo_current(there)
    assert not host.drew(there)


def test_restore_import_puts_this_devices_picture_back_current(
    modules: Path, host: _Host, tmp_path: Path
) -> None:
    target, target_guid = _plugged_stick()
    where, made = _source(host)
    there, own = _own_map(target, target_guid, host)
    path = tmp_path / "pack.gmap"
    _export(where, path)
    out = device_pack.apply_zip(
        path, target, {"items": _items(path)}, target_guid=target_guid
    )
    assert out.get("ok"), out
    _settle()
    assert store.device_photo_path(there).read_bytes() == made
    back = device_pack.undo_import()
    assert back.get("ok"), back
    _settle()
    bg = [n["id"] for n in store.visible_background(_read(there))]
    assert bg == ["own_photo", "own_rect"], bg
    assert store.device_photo_path(there).read_bytes() == own
    assert store.device_photo_current(there)
    assert not host.drew(there)


# --- Paths that change the background: notice -> check_all -> made again -------------


def _history_entries() -> list[dict]:
    deadline = time.monotonic() + 5
    while history._writer is not None and time.monotonic() < deadline:
        time.sleep(0.02)
    return history.entries()


def test_a_history_restore_leaves_a_current_picture(
    modules: Path, host: _Host, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(history_model, "_changed_everywhere", lambda: None)
    where, first = _source(host)
    path = store.module_file_in(where)
    changed = _doc(NAME, GUID, [_photo(), _bg_shape(fx=0.4), _chip()])
    store.write_text(path, json.dumps(changed), "Test")
    _settle()
    assert host.drew(where), "a changed background wasn't made again"
    assert store.device_photo_current(where)
    host.drawn.clear()
    entry = next(
        e for e in _history_entries()
        if e.get("kind") == "save" and (e.get("before") or {}).get("text")
        and '"fx": 0.4' in str((e.get("after") or {}).get("text") or "")
    )  # fmt: skip
    checks = host.checks()  # type: ignore[attr-defined]
    ok, message = history_model._restore_module(entry, entry["before"])
    assert ok, message
    _settle()
    assert host.checks() > checks  # type: ignore[attr-defined]
    nodes = store.visible_background(_read(where))
    assert [n.get("fx") for n in nodes] == [0.2, 0.0]
    # Kept with the save as a named picture (put back current), or made again.
    assert store.device_photo_current(where)
    if not host.drew(where):
        assert store.device_photo_path(where).read_bytes() == first


def test_a_device_library_restore_leaves_a_current_picture(
    modules: Path, host: _Host
) -> None:
    target, target_guid = _plugged_stick()
    there, own = _own_map(target, target_guid, host)
    saved = library.save_setup(target, target_guid, [])
    assert saved["ok"], saved
    changed = _doc(
        target, target_guid,
        [_photo("pictures/own.png", "own_photo"), _bg_shape("own_rect", 0.7)],
    )  # fmt: skip
    store.write_text(store.module_file_in(there), json.dumps(changed), "Test")
    _settle()
    assert host.drew(there)
    host.drawn.clear()
    checks = host.checks()  # type: ignore[attr-defined]
    out = library_copy.restore_to_stick(saved["setup"]["key"])
    assert out.get("ok"), out
    _settle()
    assert host.checks() > checks  # type: ignore[attr-defined]
    nodes = store.visible_background(_read(there))
    assert [n.get("fx") for n in nodes] == [0.2, 0.3]
    assert store.device_photo_current(there)
    if not host.drew(there):
        assert store.device_photo_path(there).read_bytes() == own


def test_module_setup_save_with_import_image_makes_the_picture(
    modules: Path, host: _Host, tmp_path: Path
) -> None:
    target, target_guid = _plugged_stick()
    there = _put(target, target_guid, _doc(target, target_guid, [_chip()]), {})
    _settle()
    assert not store.device_photo_path(there).exists()
    src = tmp_path / "pick" / "shot.png"
    src.parent.mkdir()
    src.write_bytes(PNG)
    # Old: Import Image set the bottom background picture, so the background
    # picture was made again. An input module's Add Image… now names the
    # Device Image (03 S52, D-03-DEVICE-IMAGE): Save still sends the
    # module-files notice, but the background is not touched.
    hw = hardware_profile.HardwareProfile()
    hw.setDeviceGuid(target_guid)
    hw.beginEditFor(target, "setup")
    rel = hw.keepImage(target, src.as_uri())
    assert rel == "pictures/device-image.png"
    setup = module_model.DriverInputModel()
    try:
        setup.loadDevice(target_guid, target)
        setup.setClaimed(0, True)
        checks = host.checks()  # type: ignore[attr-defined]
        assert setup.saveClaim(target, "source", rel)
        assert hw.commitEditFor(target, "setup") == ""
        _settle()
    finally:
        setup.deleteLater()
    assert host.checks() > checks  # type: ignore[attr-defined]
    doc = _read(there)
    assert doc[store.DEVICE_IMAGE_KEY] == rel
    assert (there / rel).read_bytes() == PNG
    assert store.device_photo_ref(doc) == ""
    assert not host.drew(there)


@pytest.fixture
def ld(modules: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[LogicalDevice]:
    monkeypatch.setattr(library, "_connected", lambda: [])
    device = LogicalDevice()
    kept = device.to_dict()
    layout = {"controls": [], "groups": []}
    doc = {
        "kind": "control.hardware",
        "device": "Logical Device",
        "boundGuidLocal": "{" + str(ids.LOGICAL_DEVICE).upper() + "}",
        "nodes": [_chip()],
        "claim": {},
        logical_device_file.KEY: layout,
    }
    store.ensure_device_dir("Logical Device", str(ids.LOGICAL_DEVICE))
    module_file.write_bytes(logical_device_file.path(), json.dumps(doc).encode())
    device.load_dict(layout)
    yield device
    device.load_dict(kept)


def test_the_logical_device_cards_add_image_makes_no_background_picture(
    ld: LogicalDevice, host: _Host, tmp_path: Path
) -> None:
    # Input modules only (07 S157, changed 2026-10-11): the Logical Device
    # card keeps showing its own picture, the bottom background picture.
    there = logical_device_file.path().parent
    _settle()
    host.drawn.clear()
    source = tmp_path / "card.png"
    source.write_bytes(PNG)
    model = module_model.ModuleListModel()
    checks = host.checks()  # type: ignore[attr-defined]
    assert model.setCardImage("logical", source.as_uri())
    _settle()
    assert host.checks() > checks  # type: ignore[attr-defined]
    assert not host.drew(there)
    assert not store.device_photo_path(there).exists()
    doc = _read(there)
    assert store.shown_photo_ref(doc, lambda _r: True) == store.device_photo_ref(doc)
    assert store.device_photo_ref(doc)
    assert model.removeCardImage("logical")
    _settle()
    assert not store.device_photo_path(there).exists()
