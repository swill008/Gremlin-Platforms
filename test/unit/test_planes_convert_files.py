# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""ONE-TIME (tracker OT-2b): the start-up conversion writes old-layout maps
(live maps and Device Library saved setups) in today's layout on disk,
once, with a backup; exports and imported backups are not touched."""

from __future__ import annotations

import json
import logging
import zipfile
from datetime import date
from pathlib import Path

import pytest
from PySide6 import QtGui

from gremlin.modules import planes_convert_files as convert
from gremlin.modules import planes_once, store

OLD_MAP = {
    "device": "Stick",
    "image": "pictures/photo.png",
    "photo": {"scale": 1.2, "offX": 0.05, "fade": 0.2},
    "imageWidth": 320,
    "imageHeight": 180,
    "nodes": [{"id": "c1", "kind": "chip"}],
}
NEW_MAP = {"device": "Other", "nodes": [{"id": "c2", "kind": "chip"}]}



def _zip_photo(doc: dict, files: dict) -> None:
    """The saved-setup conversion start-up passes in (the modules package
    never imports the UI itself)."""
    from gremlin.ui import device_pack

    device_pack._old_photo_in_zip(doc, files)

def _picture(folder: Path) -> None:
    (folder / store.PICTURES).mkdir(parents=True, exist_ok=True)
    image = QtGui.QImage(320, 180, QtGui.QImage.Format.Format_RGB32)
    image.fill(0)
    assert image.save(str(folder / store.PICTURES / "photo.png"))


def _setup(tmp_path: Path) -> tuple[Path, Path]:
    data = tmp_path / "Gremlin Platforms"
    modules = data / "modules"
    old = modules / "Stick"
    old.mkdir(parents=True)
    _picture(old)
    (old / "module.json").write_text(json.dumps(OLD_MAP, indent=2), encoding="utf-8")
    new = modules / "Other"
    new.mkdir()
    (new / "module.json").write_text(json.dumps(NEW_MAP, indent=2), encoding="utf-8")
    return modules, data


def _old(path: Path) -> bool:
    doc = json.loads(path.read_text(encoding="utf-8"))
    return any(k in doc for k in planes_once.OLD_PHOTO_KEYS)


def test_old_map_converted_on_disk_with_a_backup(tmp_path: Path) -> None:
    modules, data = _setup(tmp_path)
    path = modules / "Stick" / "module.json"
    before = path.read_bytes()
    assert convert.run_if_needed(modules, data, zip_photo=_zip_photo) == []
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert not _old(path)
    assert store.device_photo_ref(doc) == "pictures/photo.png"
    assert doc["nodes"][0]["plane"] == "background"
    backup = (
        data
        / "backup"
        / f"{date.today().isoformat()} map photo convert"
        / "modules"
        / "Stick"
        / "module.json"
    )
    assert backup.read_bytes() == before


def test_converted_file_opens_like_the_in_memory_conversion(tmp_path: Path) -> None:
    from gremlin.ui import hardware_profile

    modules, data = _setup(tmp_path)
    path = modules / "Stick" / "module.json"
    in_memory = json.loads(
        hardware_profile._planes_text(path.read_text(encoding="utf-8"), path.parent)
    )
    convert.run_if_needed(modules, data, zip_photo=_zip_photo)
    on_disk = path.read_text(encoding="utf-8")
    # The new layer's id is made fresh each time; everything else matches.
    in_memory["nodes"][0]["id"] = json.loads(on_disk)["nodes"][0]["id"]
    assert json.loads(on_disk) == in_memory
    # The normal open path finds nothing more to do.
    assert hardware_profile._planes_text(on_disk, path.parent) == on_disk


def test_new_map_untouched_and_marker_stops_later_runs(tmp_path: Path) -> None:
    modules, data = _setup(tmp_path)
    new = modules / "Other" / "module.json"
    before = new.read_bytes()
    stamp = new.stat().st_mtime_ns
    convert.run_if_needed(modules, data, zip_photo=_zip_photo)
    assert new.read_bytes() == before and new.stat().st_mtime_ns == stamp
    marker = json.loads((modules / convert.MARKER).read_text(encoding="utf-8"))
    assert marker["converted"] == 1 and marker["date"] == date.today().isoformat()
    # With the marker, an old map put back is not looked at.
    old = modules / "Stick" / "module.json"
    old.write_text(json.dumps(OLD_MAP), encoding="utf-8")
    assert convert.run_if_needed(modules, data, zip_photo=_zip_photo) == []
    assert _old(old)


def test_second_run_without_marker_is_idempotent(tmp_path: Path) -> None:
    modules, data = _setup(tmp_path)
    convert.run_if_needed(modules, data, zip_photo=_zip_photo)
    (modules / convert.MARKER).unlink()
    path = modules / "Stick" / "module.json"
    once = path.read_bytes()
    assert convert.run_if_needed(modules, data, zip_photo=_zip_photo) == []
    assert path.read_bytes() == once
    backups = list((data / "backup").rglob("module.json"))
    assert len(backups) == 1


def test_existing_backup_is_never_written_over(tmp_path: Path) -> None:
    modules, data = _setup(tmp_path)
    backup = (
        data
        / "backup"
        / f"{date.today().isoformat()} map photo convert"
        / "modules"
        / "Stick"
        / "module.json"
    )
    backup.parent.mkdir(parents=True)
    backup.write_text("earlier", encoding="utf-8")
    convert.run_if_needed(modules, data, zip_photo=_zip_photo)
    assert backup.read_text(encoding="utf-8") == "earlier"
    assert (backup.parent / "module (2).json").is_file()


def test_broken_json_left_untouched_with_a_problem(tmp_path: Path) -> None:
    modules, data = _setup(tmp_path)
    broken = modules / "Broken"
    broken.mkdir()
    text = '{"image": "pictures/x.png", '
    (broken / "module.json").write_text(text, encoding="utf-8")
    before = (broken / "module.json").read_bytes()
    problems = convert.run_if_needed(modules, data, zip_photo=_zip_photo)
    assert any("Broken" in p for p in problems)
    assert (broken / "module.json").read_bytes() == before
    assert not _old(modules / "Stick" / "module.json")


def test_failed_write_leaves_the_file_and_no_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    modules, data = _setup(tmp_path)
    path = modules / "Stick" / "module.json"
    before = path.read_bytes()

    def refuse(target: Path, payload: bytes) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(convert.module_file_io, "write_bytes", refuse)
    problems = convert.run_if_needed(modules, data, zip_photo=_zip_photo)
    assert problems and "disk full" in problems[0]
    assert path.read_bytes() == before
    assert not (modules / convert.MARKER).exists()


def _gmap(path: Path, module: dict, extra: dict[str, bytes] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as zf:
        label = {"format": "gremlin-device", "folder": True}
        zf.writestr("gmap.json", json.dumps(label))
        zf.writestr("module.json", json.dumps(module))
        zf.writestr("bindings/outputs/vJoy 2.json", json.dumps(OLD_MAP))
        zf.writestr("exact/module.json", json.dumps(module))
        for name, data in (extra or {}).items():
            zf.writestr(name, data)


def test_library_saved_setup_converted(tmp_path: Path) -> None:
    modules, data = _setup(tmp_path)
    picture = (modules / "Stick" / "pictures" / "photo.png").read_bytes()
    setup = data / "device library" / "stick" / "setup 1.gmap"
    _gmap(setup, OLD_MAP, {"pictures/photo.png": picture})
    assert convert.run_if_needed(modules, data, zip_photo=_zip_photo) == []
    with zipfile.ZipFile(setup) as zf:
        module = json.loads(zf.read("module.json"))
        output = json.loads(zf.read("bindings/outputs/vJoy 2.json"))
        exact = json.loads(zf.read("exact/module.json"))
        assert zf.read("pictures/photo.png") == picture
    for doc in (module, output):
        assert not any(k in doc for k in planes_once.OLD_PHOTO_KEYS)
        assert store.device_photo_ref(doc) == "pictures/photo.png"
    # The autosave's verbatim copy for Undo stays as it was.
    assert exact == OLD_MAP
    assert list((data / "backup").rglob("setup 1.gmap"))


def test_exports_and_imported_backups_untouched(tmp_path: Path) -> None:
    modules, data = _setup(tmp_path)
    export = data / "export" / "Stick.gmap"
    _gmap(export, OLD_MAP)
    imported = modules / "Stick" / "imported" / "module 2026-11-01.json"
    imported.parent.mkdir()
    imported.write_text(json.dumps(OLD_MAP), encoding="utf-8")
    export_bytes, imported_bytes = export.read_bytes(), imported.read_bytes()
    convert.run_if_needed(modules, data, zip_photo=_zip_photo)
    assert export.read_bytes() == export_bytes
    assert imported.read_bytes() == imported_bytes


def test_log_line(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    modules, data = _setup(tmp_path)
    with caplog.at_level(logging.INFO, logger="system"):
        convert.run_if_needed(modules, data, zip_photo=_zip_photo)
    assert "Map photo convert: 1 maps converted, 0 left" in caplog.text
