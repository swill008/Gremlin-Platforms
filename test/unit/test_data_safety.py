# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Nothing the user made is lost without being asked: saving names the
unfinished actions it would leave out, deleting a module file keeps a copy,
and cancelling a Button Map edit puts the photo back."""

from __future__ import annotations

import sys

sys.path.append(".")

import json
import pathlib
import types

import pytest

from gremlin import profile
from gremlin.ui import hardware_profile


def _action(name: str, feedback: list[tuple[str, str]]) -> types.SimpleNamespace:
    entries = [
        types.SimpleNamespace(
            feedback_type=types.SimpleNamespace(name=kind), message=text
        )
        for kind, text in feedback
    ]
    return types.SimpleNamespace(name=name, user_feedback=lambda: entries)


def test_unfinished_actions_are_named_with_their_first_error() -> None:
    library = profile.Library()
    library._actions = {
        1: _action(
            "Play Sound",
            [("Error", "The sound file is missing"), ("Error", "second")],
        ),
        2: _action("Map to vJoy", [("Warning", "Not claimed yet")]),
        3: _action("Map to Keyboard", [("Error", "No keys")]),
    }
    assert library.unfinished_actions() == [
        "Play Sound: The sound file is missing",
        "Map to Keyboard: No keys",
    ]


@pytest.fixture
def modules(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> pathlib.Path:
    maps = tmp_path / "modules"
    maps.mkdir()
    monkeypatch.setattr(hardware_profile, "_maps_dir", lambda: maps)
    deleted = tmp_path / "deleted devices"
    monkeypatch.setattr(hardware_profile, "_deleted_dir", lambda: deleted)
    monkeypatch.setattr(hardware_profile, "_users_of_slug", lambda slug: set())
    monkeypatch.setattr(hardware_profile, "_binding_store", lambda: {})
    monkeypatch.setattr(hardware_profile, "_guid_for_name", lambda name: "")
    return maps


def test_deleting_a_module_file_keeps_a_copy(modules: pathlib.Path) -> None:
    claim = {"claim": {"buttons": [1]}}
    (modules / "stick_r.json").write_text(json.dumps(claim), encoding="utf-8")
    assert hardware_profile.delete_module_file("Stick R", "") == ""
    assert not (modules / "stick_r.json").exists()
    kept = list((modules.parent / "deleted devices").glob("stick_r *.json"))
    assert len(kept) == 1
    assert json.loads(kept[0].read_text(encoding="utf-8")) == claim


def test_no_copy_means_no_delete(
    modules: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (modules / "stick_r.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(hardware_profile, "_keep_deleted_copy", lambda path: None)
    message = hardware_profile.delete_module_file("Stick R", "")
    assert "not deleted" in message
    assert (modules / "stick_r.json").exists()


def test_cancel_puts_the_starting_photo_back(modules: pathlib.Path) -> None:
    folder = modules / "stick_r"
    folder.mkdir()
    (folder / "photo.jpg").write_bytes(b"original")
    doc = modules / "stick_r.json"
    doc.write_text(json.dumps({"image": "stick_r/photo.jpg"}), encoding="utf-8")
    hw = hardware_profile.HardwareProfile()

    hw.stashPhoto("Stick R")
    # Choose background… with a .png, then a second change in the same edit.
    (folder / "photo.jpg").unlink()
    (folder / "photo.png").write_bytes(b"new")
    doc.write_text(json.dumps({"image": "stick_r/photo.png"}), encoding="utf-8")
    hw.stashPhoto("Stick R")  # Keeps the session's first photo, not this one.

    assert hw.restorePhoto("Stick R") is True
    assert (folder / "photo.jpg").read_bytes() == b"original"
    assert not (folder / "photo.png").exists()
    assert json.loads(doc.read_text(encoding="utf-8"))["image"] == "stick_r/photo.jpg"
    # Nothing left to restore.
    assert hw.restorePhoto("Stick R") is False


def test_clear_image_then_cancel_and_save_drops_the_copy(modules: pathlib.Path) -> None:
    folder = modules / "stick_r"
    folder.mkdir()
    (folder / "photo.jpg").write_bytes(b"original")
    hw = hardware_profile.HardwareProfile()

    hw.stashPhoto("Stick R")
    assert hw.clearImage("Stick R")
    assert not (folder / "photo.jpg").exists()
    assert hw.restorePhoto("Stick R") is True
    assert (folder / "photo.jpg").read_bytes() == b"original"

    hw.stashPhoto("Stick R")
    hw.dropPhotoStash("Stick R")
    assert hw.restorePhoto("Stick R") is False
