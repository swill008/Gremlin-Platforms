# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Logical Device card's Add/Change/Remove Image (03 S88,
D-03-LD-IMAGE): the picture is the card's photo, kept with its module file
(photo.<ext>, the bottom background picture, 07 S127) and written through
the store, so History
records it. Other cards and a damaged file are refused."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6 import QtCore

from gremlin import history_modules
from gremlin import logical_device_file as ldf
from gremlin.modules import module_file, store
from gremlin.modules.ids import LOGICAL_DEVICE
from gremlin.ui import module_model
from test.unit._device_folders import put_module

LD = "Logical Device"

_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32 + b"\xff\xd9"
_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    yield app


@pytest.fixture
def modules(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setattr(store, "folder", lambda: folder)
    monkeypatch.setattr(store, "_saved", lambda: None)
    monkeypatch.setattr(module_model, "_hidden_slugs", lambda: set())
    return folder


@pytest.fixture
def writes(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Path, str]]:
    seen: list[tuple[Path, str]] = []
    monkeypatch.setattr(
        history_modules,
        "note_write",
        lambda path, text, old: seen.append((Path(path), text)),
    )
    return seen


@pytest.fixture
def refused(monkeypatch: pytest.MonkeyPatch) -> list[Path]:
    seen: list[Path] = []
    monkeypatch.setattr(
        module_file, "report_refused", lambda error: seen.append(Path(error.path))
    )
    return seen


def _picture(tmp_path: Path, name: str, data: bytes) -> str:
    src = tmp_path / "pick" / name
    src.parent.mkdir(exist_ok=True)
    src.write_bytes(data)
    return src.as_uri()


def _ld_file(modules: Path, doc: dict | None = None) -> Path:
    path = put_module(modules, LD, doc or {"name": LD}, str(LOGICAL_DEVICE))
    assert path == ldf.path() == modules / LD / "module.json"
    return path


def _doc(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_add_sets_the_card_photo_and_the_file_image_with_history(
    modules: Path, writes: list, tmp_path: Path
) -> None:
    path = _ld_file(modules, {"name": "Logical Device", "layout": {"controls": []}})
    model = module_model.ModuleListModel()
    model.reload()
    assert model.cardMap("logical")["photo"] == ""
    assert model.cardMap("logical")["hasPhoto"] is False

    assert model.setCardImage("logical", _picture(tmp_path, "pic.jpg", _JPEG))

    photo = modules / LD / "pictures" / "photo.jpg"
    assert photo.read_bytes() == _JPEG
    doc = _doc(path)
    assert store.device_photo_ref(doc) == "pictures/photo.jpg"
    assert "image" not in doc
    assert doc["layout"] == {"controls": []}
    card = model.cardMap("logical")
    assert card["photo"].startswith(photo.as_uri())
    assert card["hasPhoto"] is True
    assert any(p == path and '"background"' in text for p, text in writes)


def test_change_replaces_the_picture(
    modules: Path, writes: list, tmp_path: Path
) -> None:
    path = _ld_file(modules)
    model = module_model.ModuleListModel()
    model.reload()
    assert model.setCardImage("logical", _picture(tmp_path, "a.jpg", _JPEG))
    assert model.setCardImage("logical", _picture(tmp_path, "b.png", _PNG))

    pictures = modules / LD / "pictures"
    assert sorted(p.name for p in pictures.glob("photo*")) == ["photo.png"]
    assert (pictures / "photo.png").read_bytes() == _PNG
    assert store.device_photo_ref(_doc(path)) == "pictures/photo.png"
    assert model.cardMap("logical")["photo"].startswith(
        (pictures / "photo.png").as_uri()
    )


def test_remove_drops_the_photo_and_clears_image(
    modules: Path, writes: list, tmp_path: Path
) -> None:
    path = _ld_file(modules)
    model = module_model.ModuleListModel()
    model.reload()
    assert model.setCardImage("logical", _picture(tmp_path, "a.jpg", _JPEG))
    writes.clear()

    assert model.removeCardImage("logical")

    assert not list((modules / LD / "pictures").glob("photo*"))
    assert store.device_photo_ref(_doc(path)) == ""
    assert model.cardMap("logical")["photo"] == ""
    assert model.cardMap("logical")["hasPhoto"] is False
    assert any(p == path for p, _ in writes)


def test_other_cards_are_refused(modules: Path, tmp_path: Path) -> None:
    """Output cards are refused. Input module cards (sticks, Keyboard) now
    take a Device Image of their own (D-03-DEVICE-IMAGE); it never lands in
    the Logical Device's folder."""
    _ld_file(modules)
    model = module_model.ModuleListModel()
    model.reload()
    url = _picture(tmp_path, "a.jpg", _JPEG)
    # Old: every card but the Logical Device was refused.
    assert model.setCardImage("xbox", url) is False
    assert model.removeCardImage("xbox") is False
    model.setCardImage("pjoy_pro", url)
    model.setCardImage("keyboard", url)
    assert not (modules / LD / "pictures").exists()


def test_a_damaged_file_is_refused_and_left_alone(
    modules: Path, refused: list, tmp_path: Path
) -> None:
    path = put_module(modules, LD, b"{not json", str(LOGICAL_DEVICE))
    model = module_model.ModuleListModel()
    model.reload()

    assert model.setCardImage("logical", _picture(tmp_path, "a.jpg", _JPEG)) is False
    assert model.removeCardImage("logical") is False

    assert path.read_bytes() == b"{not json"
    assert not list(modules.glob(f"{LD}/pictures/photo*"))
    assert refused and refused[0] == path
