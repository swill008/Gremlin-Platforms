# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Logical Device's card picture is kept like every device's photo
(03 S88, D-03-LD-IMAGE): photo.<ext> in its picture folder plus its module
file's "image", so Save to Device Library and Restore (10 S6, S6a), Export
(S14, S44) and History carry it. The photo is set through the store as Add
Image does; the real store, Library, Device Pack and History in an empty
modules folder."""

from __future__ import annotations

import base64
import io
import json
import zipfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6 import QtCore

from gremlin import device_library as library
from gremlin import history, library_copy, logical_device_file
from gremlin.logical_device import LogicalDevice
from gremlin.modules import ids, module_file, store
from gremlin.ui import history_model, module_model
from test.unit.test_stage1_modules import (  # noqa: F401  # pyright: ignore[reportMissingImports]
    folder,
    settle_history,
)

LD_GUID = "{" + str(ids.LOGICAL_DEVICE).upper() + "}"
SLUG = logical_device_file.SLUG
# A 1x1 PNG.
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGA"
    "hKmMIQAAAABJRU5ErkJggg=="
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
def ld(modules: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[LogicalDevice]:
    """The Logical Device with a module file of one control, put back as it
    was afterwards; no stick plugged in."""
    monkeypatch.setattr(library, "_connected", lambda: [])
    device = LogicalDevice()
    kept = device.to_dict()
    layout = {
        "controls": [
            {
                "uid": f"{1:032x}",
                "type": "button",
                "id": 1,
                "label": "Fire",
                "user-label": "",
                "group": "",
                "hide-system": False,
            }
        ],
        "groups": [],
    }
    doc = {
        "kind": "control.hardware",
        "device": "Logical Device",
        "boundGuidLocal": LD_GUID,
        "nodes": [],
        "claim": {},
        logical_device_file.KEY: layout,
    }
    module_file.write_bytes(logical_device_file.path(), json.dumps(doc).encode())
    device.load_dict(layout)
    yield device
    device.load_dict(kept)


def _photo_path() -> Path:
    return store.pictures_dir_of(SLUG) / "photo.png"


def _set_photo(data: bytes = PNG) -> None:
    """Add Image as the contract says: the picture as photo.<ext> through
    the store, and the module file's "image" through update_path."""
    store.put_picture_at(_photo_path(), data)
    ref = store.picture_ref(SLUG, "photo.png")

    def change(doc: dict) -> None:
        doc["image"] = ref

    assert store.update_path(logical_device_file.path(), change, "Home")


def _clear_photo() -> None:
    """Remove Image: the photo files go, "image" is ""."""
    store.remove_picture_files(store.photo_files(SLUG))

    def change(doc: dict) -> None:
        doc["image"] = ""

    assert store.update_path(logical_device_file.path(), change, "Home")
    assert not _photo_path().exists()


def _image_key() -> str:
    doc = json.loads(logical_device_file.path().read_text(encoding="utf-8-sig"))
    return str(doc.get("image") or "")


def _pack_has_photo(data: bytes | Path) -> bool:
    """The pack holds the picture and its module file names it."""
    source = io.BytesIO(data) if isinstance(data, bytes) else Path(data)
    with zipfile.ZipFile(source) as zf:
        pictures = [n for n in zf.namelist() if zf.read(n) == PNG]
        named = False
        for name in zf.namelist():
            if not name.endswith(".json"):
                continue
            try:
                doc = json.loads(zf.read(name).decode("utf-8-sig"))
            except ValueError:
                continue
            if isinstance(doc, dict) and str(doc.get("image") or ""):
                named = True
    return bool(pictures) and named


def _ld_row() -> dict:
    return next(r for r in library.devices() if r["name"] == "Logical Device")


def _save() -> dict:
    out = library.save_setup("Logical Device", LD_GUID, [])
    assert out["ok"], out
    setups = out.get("setups") or [out.get("setup")]
    return setups[0]


def _card_photo(model: module_model.ModuleListModel | None = None) -> str:
    return str((model or module_model.ModuleListModel()).cardMap("logical")["photo"])


# --- the photo as the card shows it -----------------------------------------


def test_the_photo_set_through_the_store_shows_on_the_card(ld: LogicalDevice) -> None:
    assert _card_photo() == ""
    _set_photo()
    assert _image_key() == f"{SLUG}/photo.png"
    assert "photo.png" in _card_photo()


# --- Save to Device Library and Restore (10 S6, S6a) ------------------------


def test_save_to_device_library_keeps_the_picture(ld: LogicalDevice) -> None:
    _set_photo()
    setup = _save()
    assert _pack_has_photo(library.pack_path(setup["key"]))
    # The Library's own photo of the saved setup (S11) is the picture.
    shown = library.photo(setup["key"])
    assert shown and Path(shown).read_bytes() == PNG


def test_restore_puts_the_picture_back(ld: LogicalDevice) -> None:
    _set_photo()
    setup = _save()
    _clear_photo()
    assert _card_photo() == ""
    # Restore (S6: offered for a built-in input, no plugged-in check, S6a).
    out = library_copy.restore_to_stick(setup["key"])
    assert out["ok"], out
    assert _image_key()
    assert store.photo_files(SLUG)
    assert store.photo_files(SLUG)[0].read_bytes() == PNG
    assert _card_photo()


def test_putting_a_saved_setup_back_restores_the_picture(ld: LogicalDevice) -> None:
    """The Library's own put-back (as Undo uses), without the plugged-in
    gate: the pack itself carries the picture back."""
    _set_photo()
    setup = _save()
    _clear_photo()
    out = library_copy.restore(setup["key"])
    assert out["ok"], out
    assert _image_key()
    found = store.photo_files(SLUG)
    assert found and found[0].read_bytes() == PNG
    assert _card_photo()


# --- Export (S14, S44) ------------------------------------------------------


def test_export_saved_setup_includes_the_picture(
    ld: LogicalDevice, tmp_path: Path
) -> None:
    _set_photo()
    setup = _save()
    out = library.export_setup(setup["key"], tmp_path / "out" / "ld.zip")
    assert out["ok"], out
    assert _pack_has_photo(tmp_path / "out" / "ld.zip")


def test_export_current_setup_includes_the_picture(
    ld: LogicalDevice, tmp_path: Path
) -> None:
    _set_photo()
    out = library.export_current(_ld_row()["key"], tmp_path / "out" / "now.zip")
    assert out["ok"], out
    assert _pack_has_photo(tmp_path / "out" / "now.zip")


# --- History (history_modules + store._reload_logical_device) ---------------


def _ld_entries() -> list[dict]:
    settle_history()
    return [
        e
        for e in history.entries("button-map") + history.entries("modules")
        if (e.get("subject") or {}).get("fileName") == f"{SLUG}.json"
    ]


def test_history_restore_brings_the_picture_back_on_the_card(
    ld: LogicalDevice,
) -> None:
    model = module_model.ModuleListModel()
    _set_photo()
    model._set_card_photo("logical")  # what Add Image does after its write
    assert _card_photo(model)
    _clear_photo()
    model._set_card_photo("logical")
    assert _card_photo(model) == ""
    # The Remove Image entry's "before" has the picture.
    removal = next(
        e
        for e in sorted(_ld_entries(), key=lambda e: str(e.get("when") or ""))[::-1]
        if json.loads((e.get("before") or {}).get("text") or "{}").get("image")
        and not json.loads((e.get("after") or {}).get("text") or "{}").get("image")
    )
    reloaded: list[bool] = []
    from gremlin.signal import signal

    signal.logicalDeviceReloaded.connect(lambda: reloaded.append(True))
    result = history_model.restore(removal["id"], "before")
    assert result["ok"], result
    assert _image_key() == f"{SLUG}/photo.png"
    assert _photo_path().read_bytes() == PNG
    # store._reload_logical_device ran (the file was replaced).
    assert reloaded
    # A new card shows it ...
    assert "photo.png" in _card_photo()
    # ... and so does the card already on Home.
    for _ in range(20):
        QtCore.QCoreApplication.processEvents()
    assert "photo.png" in _card_photo(model)
