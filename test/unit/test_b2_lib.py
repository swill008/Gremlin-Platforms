# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""D-FIXLIST-B2 (2a), 10 S14, S35, S39, S44: the Device Library's saved
setups, Import and Export use the device file (.gmap) only; a .zip Device
Pack is neither written nor read, and the window's choosers and messages
say .gmap."""

from __future__ import annotations

import json
import pathlib
import zipfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from gremlin import device_library as library
from gremlin import shared_state
from gremlin.modules import store
from gremlin.ui import device_library_model
from test.unit._gmap_pack import write_gmap

_ROOT = pathlib.Path(__file__).resolve().parents[2]
GUID = "{BBBBBBBB-1111-2222-3333-444455556666}"
WIRES = {
    "modes": [{"name": "Combat", "lines": ["Button 1 → vJoy 3 Button 1"]}],
    "actions": [],
    "tree": {"Combat": ""},
}
DOC = {
    "kind": "control.hardware",
    "device": "Hornet Grip",
    "claim": {"buttons": [1]},
    "pack": {
        "exportedName": "Hornet Grip",
        "exportedGuid": GUID,
        "author": "Ann",
        "note": "My F/A-18 setup",
    },
}


@pytest.fixture
def lib(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    modules = tmp_path / "modules"
    modules.mkdir()
    monkeypatch.setattr(store, "folder", lambda: modules)
    monkeypatch.setattr(library, "folder", lambda: tmp_path / "device library")
    monkeypatch.setattr(library, "_connected", lambda: [])
    monkeypatch.setattr(library, "_alias", lambda guid, default: default)
    monkeypatch.setattr(library, "_set_alias", lambda guid, name: None)
    before = shared_state.current_profile
    shared_state.current_profile = None
    yield tmp_path
    shared_state.current_profile = before


def _old_pack(path: Path) -> Path:
    """A Device Pack as the old window wrote it: map.json + wires.json."""
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("map.json", json.dumps(DOC))
        zf.writestr("wires.json", json.dumps(WIRES))
    return path


def test_an_old_zip_device_pack_is_refused_and_the_message_says_gmap(
    lib: Path,
) -> None:
    out = library.import_pack(_old_pack(lib / "Ann's Hornet stick.zip"))
    assert not out["ok"]
    assert ".gmap" in out["error"] and "(.zip" not in out["error"]
    assert [r for r in library.devices() if not r["builtIn"]] == []


def test_a_device_file_named_zip_is_refused(lib: Path) -> None:
    gmap = write_gmap(lib / "Hornet", DOC, WIRES)
    renamed = gmap.rename(lib / "Hornet.zip")
    out = library.import_pack(renamed)
    assert not out["ok"] and ".gmap" in out["error"]
    assert [r for r in library.devices() if not r["builtIn"]] == []


def test_an_old_pack_inside_a_gmap_name_is_refused(lib: Path) -> None:
    """Only the .gmap layout (gmap.json) is read: a map.json zip named
    .gmap is not a device file."""
    out = library.import_pack(_old_pack(lib / "old.gmap"))
    assert not out["ok"] and ".gmap" in out["error"]
    assert [r for r in library.devices() if not r["builtIn"]] == []


def test_a_gmap_imports_with_its_made_by_and_note(lib: Path) -> None:
    """S35: the saved setup says who made it and takes the Note, now read
    from the device file's gmap.json (madeBy, note)."""
    out = library.import_pack(write_gmap(lib / "Ann's Hornet stick", DOC, WIRES))
    assert out["ok"], out
    setup = out["setup"]
    assert setup["reason"] == "From Ann's device file"
    assert setup["description"] == "My F/A-18 setup"
    assert setup["vjoys"] == {"3": 1}
    assert Path(setup["pack"]).suffix == ".gmap"


def test_export_of_a_saved_setup_is_always_gmap(lib: Path) -> None:
    out = library.import_pack(write_gmap(lib / "Hornet", DOC, WIRES))
    key = out["setup"]["key"]
    (lib / "out").mkdir()
    saved = library.export_setup(key, lib / "out" / "shared.zip")
    assert saved["ok"], saved
    assert Path(saved["path"]).name == "shared.zip.gmap"
    assert not (lib / "out" / "shared.zip").exists()


def test_the_model_refuses_a_zip_and_says_gmap(qtbot: object) -> None:
    model = device_library_model.DeviceLibraryModel(api=None, watch_devices=False)
    results: list[dict] = []
    model.result.connect(results.append)
    assert model.importPack(Path("C:/x/pack.zip").as_uri()) == 0
    assert ".gmap" in results[-1]["error"] and "(.zip" not in results[-1]["error"]


def test_the_model_export_gives_a_zip_name_gmap() -> None:
    dest = device_library_model._export_dest(Path("C:/x/old.zip").as_uri())
    assert dest.name == "old.zip.gmap"


def test_the_window_choosers_offer_only_gmap() -> None:
    qml = (_ROOT / "qml" / "WindowDeviceLibrary.qml").read_text(encoding="utf-8")
    assert "*.zip" not in qml and '".zip"' not in qml
    assert qml.count('nameFilters: ["Device files (*.gmap)"]') == 3
