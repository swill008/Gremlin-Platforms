# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""History with device folders (D-03-DEVICE-FOLDERS; 08 S8, S14, S43).

A save of <modules>/<Device Folder>/module.json is an entry with its
pictures and the device's id; Restore finds the folder by that id (also
after a rename); an entry from before device folders (<modules>/<slug>.json,
refs "<slug>/<file>") goes back into the device's folder with its refs
rewritten; the filter matches the id, and the device name for old entries;
other files in the folders are never module-file entries.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

from gremlin import history, history_modules
from gremlin.modules import ids, module_file, store
from gremlin.ui import history_model

_STICK = uuid.UUID("44444444-5555-6666-7777-888888888888")
_KEY = ids.stored_guid_key(str(_STICK))


def _settle() -> list[dict]:
    deadline = time.monotonic() + 5
    while history._writer is not None and time.monotonic() < deadline:
        time.sleep(0.02)
    return history.entries()


@pytest.fixture
def modules(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setattr(history, "folder", lambda: tmp_path / "history")
    monkeypatch.setattr(history, "_pruned", True)
    monkeypatch.setattr(store, "folder", lambda: folder)
    monkeypatch.setattr(history_model, "_changed_everywhere", lambda: None)
    yield folder
    _settle()


def _device(modules: Path, name: str, key: str = _KEY) -> Path:
    folder = modules / name
    (folder / "pictures").mkdir(parents=True, exist_ok=True)
    (folder / "device.json").write_text(
        json.dumps({"format": 1, "id": key, "name": name}), encoding="utf-8"
    )
    return folder


def test_a_save_in_a_device_folder_is_kept_with_its_pictures(modules: Path) -> None:
    folder = _device(modules, "Test Stick")
    (folder / "pictures" / "photo.png").write_bytes(b"photo")
    (folder / "pictures" / "knob.png").write_bytes(b"knob")
    path = folder / "module.json"
    module_file.write_json(path, {"device": "Test Stick"})
    module_file.write_json(
        path,
        {
            "device": "Test Stick",
            "image": "pictures/photo.png",
            "nodes": [{"id": "a", "kind": "image", "src": "pictures/knob.png"}],
        },
    )
    entry = _settle()[0]
    assert entry["title"].startswith("Saved Test Stick")
    subject = entry["subject"]
    assert subject["deviceId"] == _KEY
    assert subject["folder"] == "Test Stick"
    assert subject["fileName"] == "Test Stick/module.json"
    kept = {p["ref"]: p["keptFile"] for p in entry["after"]["pictures"]}
    assert set(kept) == {"pictures/photo.png", "pictures/knob.png"}
    assert history.kept_file(kept["pictures/photo.png"]).read_bytes() == b"photo"
    assert history.kept_file(kept["pictures/knob.png"]).read_bytes() == b"knob"


def test_restore_after_a_rename_finds_the_folder_by_its_id(modules: Path) -> None:
    folder = _device(modules, "Test Stick")
    (folder / "pictures" / "photo.png").write_bytes(b"first photo")
    path = folder / "module.json"
    module_file.write_json(
        path, {"device": "Test Stick", "image": "pictures/photo.png"}
    )
    module_file.write_json(path, {"device": "Test Stick", "claim": {"buttons": [1]}})
    entry = _settle()[0]
    (folder / "pictures" / "photo.png").unlink()
    os.rename(folder, modules / "Renamed Stick")
    renamed = modules / "Renamed Stick"
    (renamed / "device.json").write_text(
        json.dumps({"format": 1, "id": _KEY, "name": "Renamed Stick"}),
        encoding="utf-8",
    )

    ok, message = history_model._restore_module(entry, entry["before"])

    assert ok, message
    assert not (modules / "Test Stick").exists()
    doc = json.loads((renamed / "module.json").read_text(encoding="utf-8-sig"))
    assert doc["image"] == "pictures/photo.png"
    assert (renamed / "pictures" / "photo.png").read_bytes() == b"first photo"


def _old_entry(tmp_path: Path, doc: dict) -> tuple[dict, dict]:
    """An entry written before device folders: <modules>/old_stick.json."""
    photo = tmp_path / "kept photo.png"
    photo.write_bytes(b"old photo")
    knob = tmp_path / "kept knob.png"
    knob.write_bytes(b"old knob")
    entry = {
        "area": "device-mapping-editor",
        "kind": "save",
        "subject": {
            "device": "Old Stick",
            "file": str(tmp_path / "old modules" / "old_stick.json"),
            "fileName": "old_stick.json",
            "parts": ["image"],
        },
    }
    side = {
        "text": json.dumps(doc),
        "pictures": [
            {"ref": "old_stick/photo.png", "keptFile": history.keep_file(photo)},
            {"ref": "old_stick/knob.png", "keptFile": history.keep_file(knob)},
        ],
    }
    return entry, side


_OLD_DOC = {
    "device": "Old Stick",
    "image": "old_stick/photo.png",
    "nodes": [{"id": "k", "kind": "image", "src": "old_stick/knob.png"}],
}


def test_an_old_entry_goes_back_into_the_devices_folder(
    modules: Path, tmp_path: Path
) -> None:
    entry, side = _old_entry(tmp_path, _OLD_DOC)

    ok, message = history_model._restore_module(entry, side)

    assert ok, message
    assert not (modules / "old_stick.json").exists()
    folder = modules / "Old Stick"
    doc = json.loads((folder / "module.json").read_text(encoding="utf-8-sig"))
    assert doc["image"] == "pictures/photo.png"
    assert doc["nodes"][0]["src"] == "pictures/knob.png"
    assert (folder / "pictures" / "photo.png").read_bytes() == b"old photo"
    assert (folder / "pictures" / "knob.png").read_bytes() == b"old knob"
    assert (folder / "device.json").is_file()


def test_an_old_entry_with_an_id_goes_back_by_that_id(
    modules: Path, tmp_path: Path
) -> None:
    folder = _device(modules, "Shown Name Today")
    entry, side = _old_entry(tmp_path, _OLD_DOC | {"boundGuidLocal": str(_STICK)})

    ok, message = history_model._restore_module(entry, side)

    assert ok, message
    assert not (modules / "Old Stick").exists()
    doc = json.loads((folder / "module.json").read_text(encoding="utf-8-sig"))
    assert doc["image"] == "pictures/photo.png"
    assert (folder / "pictures" / "photo.png").read_bytes() == b"old photo"


def test_the_filter_matches_the_id_and_the_name_of_old_entries() -> None:
    new = {
        "area": "modules",
        "subject": {
            "device": "Test Stick",
            "deviceId": _KEY,
            "folder": "Test Stick",
            "fileName": "Test Stick/module.json",
        },
    }
    twin = {
        "area": "modules",
        "subject": {
            "device": "Test Stick",
            "deviceId": "99999999",
            "folder": "Test Stick (2)",
            "fileName": "Test Stick (2)/module.json",
        },
    }
    old = {
        "area": "modules",
        "subject": {
            "device": "Test Stick",
            "fileName": "test_stick.json",
        },
    }
    other_old = {
        "area": "modules",
        "subject": {
            "device": "Other Stick",
            "fileName": "other_stick.json",
        },
    }
    profile_input = {"area": "profile", "subject": {"deviceId": str(_STICK)}}
    wanted = {"deviceId": "{" + str(_STICK).upper() + "}", "deviceName": "test stick"}
    assert history_model._matches(new, wanted)
    assert not history_model._matches(twin, wanted)
    assert history_model._matches(old, wanted)
    assert not history_model._matches(other_old, wanted)
    assert history_model._matches(profile_input, wanted)
    of_device = {
        "ofDevice": {"deviceId": _KEY, "guid": str(_STICK), "name": "Test Stick"}
    }
    assert history_model._matches(new, of_device)
    assert not history_model._matches(twin, of_device)
    assert history_model._matches(old, of_device)
    assert not history_model._matches(other_old, of_device)
    # ofDevice is about module files and the Library, not profile inputs.
    assert not history_model._matches(profile_input, of_device)


def test_other_files_in_the_folders_are_not_entries(modules: Path) -> None:
    folder = _device(modules, "Test Stick")
    others = [
        modules / "old_stick.json",
        folder / "recovery.json",
        folder / "imported" / "module 2026-10-11 0930.json",
        folder / "module.json.bad-2026-10-11",
        modules / "templates" / "My Template" / "template.json",
        modules / "templates" / "module.json",
        modules / "cache" / "edit" / _KEY / "start" / "module.json",
        modules / "cache" / "module.json",
    ]
    for path in others:
        assert not history_modules.is_module_file(path), path
        path.parent.mkdir(parents=True, exist_ok=True)
        module_file.write_json(path, {"device": "Test Stick", "a": 1})
        module_file.write_json(path, {"device": "Test Stick", "a": 2})
    assert _settle() == []
    assert history_modules.is_module_file(folder / "module.json")
