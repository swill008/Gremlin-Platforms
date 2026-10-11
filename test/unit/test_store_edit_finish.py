# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""07 S107, gap G32: a Save whose edit folder can't be removed (a picture
in added/ still open) is still a finished Save. The next edit starts fresh
(no old pictures in added/) and recover_edit never puts start/ back over
it."""

from __future__ import annotations

import contextlib
import json
import shutil
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from gremlin.modules import store

STICK = "1111AAAA2222BBBB3333CCCC4444DDDD"
NAME = "Edit Finish Stick"


@pytest.fixture
def modules(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    base = tmp_path / "modules"
    base.mkdir()
    monkeypatch.setattr(store, "folder", lambda: base)
    store._dirs_changed()
    yield base
    store._dirs_changed()


@contextlib.contextmanager
def _held_open(path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Keeps path open, so Windows refuses to remove its folder. Elsewhere
    removal of a folder holding path is refused the same way."""
    if sys.platform == "win32":
        with open(path, "rb"):
            yield
        return
    real = shutil.rmtree

    def refuse(target: object, *args: object, **kwargs: object) -> None:
        if path.exists() and Path(str(target)) in path.parents:
            raise PermissionError(f"{path} is open")
        real(target, *args, **kwargs)

    monkeypatch.setattr(shutil, "rmtree", refuse)
    yield
    monkeypatch.setattr(shutil, "rmtree", real)


def _saved_device() -> Path:
    made = store.ensure_device_dir(NAME, STICK)
    (made / store.MODULE_FILE).write_text(
        json.dumps({"device": NAME, "image": "", "nodes": []}), encoding="utf-8"
    )
    return made


def _save_with_held_picture(monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    made = _saved_device()
    temp = store.begin_edit(NAME, STICK)
    chip = store.stage_picture(NAME, STICK, b"first chip", "chip.png")

    def change(doc: dict) -> None:
        doc["nodes"] = [{"shape": "image", "src": chip}]

    with _held_open(temp / "added" / "chip.png", monkeypatch):
        assert store.commit_edit(NAME, STICK, change) == ""
        # The folder is left behind while the picture is open.
        assert (temp / "added" / "chip.png").is_file()
        recovered = store.recover_edit(NAME, STICK)
    assert recovered != "restored"
    return made, temp


def test_a_save_with_a_picture_open_is_saved(
    modules: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    made, _temp = _save_with_held_picture(monkeypatch)
    doc = json.loads((made / store.MODULE_FILE).read_text(encoding="utf-8"))
    assert doc["nodes"] == [{"shape": "image", "src": "pictures/chip.png"}]
    assert (made / store.PICTURES / "chip.png").read_bytes() == b"first chip"


def test_recover_never_rolls_back_a_finished_save(
    modules: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    made, temp = _save_with_held_picture(monkeypatch)
    saved = (made / store.MODULE_FILE).read_bytes()
    # Once the picture is closed, a later start finds nothing to put back.
    assert store.recover_edit(NAME, STICK) in ("", "dropped")
    assert (made / store.MODULE_FILE).read_bytes() == saved
    assert (made / store.PICTURES / "chip.png").is_file()
    assert not temp.exists()


def test_the_next_edit_starts_with_an_empty_added_folder(
    modules: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _made, temp = _save_with_held_picture(monkeypatch)
    ref = store.stage_picture(NAME, STICK, b"second chip", "other.png")
    assert ref == "pictures/other.png"
    assert sorted(p.name for p in (temp / "added").iterdir()) == ["other.png"]
    # start/ is the saved module, not the one from before the Save.
    start = json.loads((temp / "start" / store.MODULE_FILE).read_text("utf-8"))
    assert start["nodes"] == [{"shape": "image", "src": "pictures/chip.png"}]
    store.cancel_edit(NAME, STICK)
