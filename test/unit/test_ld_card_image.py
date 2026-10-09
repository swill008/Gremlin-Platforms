# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Logical Device card's Add/Change/Remove Image (03 S88,
D-03-LD-IMAGE): the picture is the card's photo, kept with its module file
(photo.<ext> plus "image") and written through the store, so History
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
from gremlin.ui import module_model

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
    monkeypatch.setattr(store, "into_library", lambda src: Path(src))
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
    path = ldf.path()
    assert path == modules / "logical_device.json"
    path.write_text(json.dumps(doc or {"name": "Logical Device"}), encoding="utf-8")
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

    photo = modules / "logical_device" / "photo.jpg"
    assert photo.read_bytes() == _JPEG
    doc = _doc(path)
    assert doc["image"] == "logical_device/photo.jpg"
    assert doc["layout"] == {"controls": []}
    card = model.cardMap("logical")
    assert card["photo"].startswith(photo.as_uri())
    assert card["hasPhoto"] is True
    assert any(p == path and '"image"' in text for p, text in writes)


def test_change_replaces_the_picture(
    modules: Path, writes: list, tmp_path: Path
) -> None:
    path = _ld_file(modules)
    model = module_model.ModuleListModel()
    model.reload()
    assert model.setCardImage("logical", _picture(tmp_path, "a.jpg", _JPEG))
    assert model.setCardImage("logical", _picture(tmp_path, "b.png", _PNG))

    pictures = modules / "logical_device"
    assert sorted(p.name for p in pictures.glob("photo*")) == ["photo.png"]
    assert (pictures / "photo.png").read_bytes() == _PNG
    assert _doc(path)["image"] == "logical_device/photo.png"
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

    assert not list((modules / "logical_device").glob("photo*"))
    assert _doc(path)["image"] == ""
    assert model.cardMap("logical")["photo"] == ""
    assert model.cardMap("logical")["hasPhoto"] is False
    assert any(p == path for p, _ in writes)


def test_other_cards_are_refused(modules: Path, tmp_path: Path) -> None:
    _ld_file(modules)
    model = module_model.ModuleListModel()
    model.reload()
    url = _picture(tmp_path, "a.jpg", _JPEG)
    assert model.setCardImage("pjoy_pro", url) is False
    assert model.setCardImage("keyboard", url) is False
    assert model.removeCardImage("keyboard") is False
    assert not (modules / "logical_device").exists()


def test_a_damaged_file_is_refused_and_left_alone(
    modules: Path, refused: list, tmp_path: Path
) -> None:
    path = ldf.path()
    path.write_bytes(b"{not json")
    model = module_model.ModuleListModel()
    model.reload()

    assert model.setCardImage("logical", _picture(tmp_path, "a.jpg", _JPEG)) is False
    assert model.removeCardImage("logical") is False

    assert path.read_bytes() == b"{not json"
    assert not list(modules.glob("logical_device/photo*"))
    assert refused and refused[0] == path
