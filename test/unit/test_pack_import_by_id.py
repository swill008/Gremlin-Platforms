# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device Pack Import by the chosen row's id (08 S106a): with two identical
sticks, the window's selection carries "targetGuid" (the "Put this pack on"
row's id) and the pack goes onto that stick: its own module file, its wires
and its autosave (10 S21). Without an id the name decides, as before."""

from __future__ import annotations

import json
import uuid
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from gremlin import device_initialization, shared_state
from gremlin.modules import store
from gremlin.profile import DeviceInfo, Profile
from gremlin.ui import device_pack, hardware_profile
from test.unit import test_stage1_modules
from test.unit.test_id_not_name_lookups import FIRST, SECOND, TWIN
from test.unit.test_stage1_history_pack import _url
from test.unit.test_stage1_modules import map_button, mapped

_app = test_stage1_modules._app
folder = test_stage1_modules.folder


def _twins() -> list[SimpleNamespace]:
    return [
        # A real device summary's fields: a Home model still alive from an
        # earlier test reads them when the device list changes (seen on CI).
        SimpleNamespace(
            name=TWIN, device_guid=SimpleNamespace(uuid=uid), button_count=8,
            axis_count=0, hat_count=0, vendor_id=0x1234, product_id=0x5678,
            is_virtual=False,
        )
        for uid in (FIRST, SECOND)
    ]


@pytest.fixture
def twins(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two plugged-in sticks of one name, eight buttons each."""
    monkeypatch.setattr(device_initialization, "physical_devices", _twins)
    monkeypatch.setattr(store, "live_devices", _twins)


def _profile(monkeypatch: pytest.MonkeyPatch) -> Profile:
    profile = Profile()
    for uid in (FIRST, SECOND):
        profile.device_database.devices[uid] = DeviceInfo(uid, TWIN)
    monkeypatch.setattr(shared_state, "current_profile", profile)
    return profile


def _write_own_files() -> dict[str, Path]:
    """Each twin's own file (bound to its id), told apart by a marker."""
    paths = {}
    for guid, marker, stem in (
        (str(FIRST), "first", "twin_stick"),
        (str(SECOND), "second", "twin_stick_2"),
    ):
        doc = {
            "kind": "control.hardware",
            "device": TWIN,
            "direction": "source",
            "boundGuidLocal": guid,
            "claim": {"buttons": [1], "axes": [], "hats": [], "keys": []},
            "twinMarker": marker,
        }
        path = store.folder() / f"{stem}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc), encoding="utf-8")
        paths[marker] = path
    for guid, marker in ((str(FIRST), "first"), (str(SECOND), "second")):
        assert store.path_for_id(TWIN, guid) == paths[marker]
    return paths


def _pack(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """A pack of the first twin: button 1 wired in Default, rowHeight 44."""
    source = _profile(monkeypatch)
    map_button(source, FIRST, 1, 1)
    built = device_pack.assemble(TWIN, lambda stored: None, guid=str(FIRST))
    assert not isinstance(built, str), built
    pack = tmp_path / "twin pack.zip"
    pack.write_bytes(built[0])
    with zipfile.ZipFile(pack) as zf:
        doc = json.loads(zf.read("map.json"))
        rest = {n: zf.read(n) for n in zf.namelist() if n != "map.json"}
    doc["layout"] = {"groups": ["G44"]}
    with zipfile.ZipFile(pack, "w") as zf:
        zf.writestr("map.json", json.dumps(doc))
        for name, data in rest.items():
            zf.writestr(name, data)
    return pack


def _doc(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def autosaves(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    """The (name, guid) of each autosave the import keeps."""
    kept: list[tuple[str, str]] = []

    def record(name: str, guid: str, *_args: object) -> str:
        kept.append((name, guid))
        return ""

    monkeypatch.setattr(hardware_profile, "_autosave", record)
    return kept


def _same(a: str, b: uuid.UUID) -> bool:
    return store.stored_guid_key(a) == store.stored_guid_key(str(b))


def test_import_with_the_second_twins_id_changes_the_second(
    folder: Path,
    twins: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    autosaves: list,
) -> None:
    """Old code ignored "targetGuid": the name found the first twin."""
    paths = _write_own_files()
    pack = _pack(monkeypatch, tmp_path)
    first_before = paths["first"].read_bytes()
    target = _profile(monkeypatch)
    selection = {
        "items": ["in.groups", "wire:Default"],
        "targetGuid": str(SECOND),
    }
    hw = hardware_profile.HardwareProfile()
    done = json.loads(hw.importPack(_url(pack), TWIN, json.dumps(selection)))
    assert done["ok"], done
    second = _doc(paths["second"])
    assert second["twinMarker"] == "second"
    assert second.get("layout", {}).get("groups") == ["G44"]
    assert paths["first"].read_bytes() == first_before
    assert mapped(target, SECOND) == {("Default", 1)}
    assert mapped(target, FIRST) == set()
    assert len(autosaves) == 1
    assert _same(autosaves[0][1], SECOND), autosaves


def test_the_preview_counts_the_second_twins_wires(
    folder: Path, twins: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _write_own_files()
    pack = _pack(monkeypatch, tmp_path)
    target = _profile(monkeypatch)
    map_button(target, SECOND, 1, 1)
    map_button(target, SECOND, 2, 2)
    selection = {"items": ["wire:Default"], "targetGuid": str(SECOND)}
    hw = hardware_profile.HardwareProfile()
    shown = json.loads(hw.previewPackImport(_url(pack), TWIN, json.dumps(selection)))
    assert shown["ok"], shown
    assert shown["modes"] == [{"name": "Default", "here": 2, "pack": 1}]


def test_import_without_an_id_goes_by_the_name_as_before(
    folder: Path,
    twins: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    autosaves: list,
) -> None:
    """No "targetGuid" (or ""): the same as apply_zip by the name alone."""
    paths = _write_own_files()
    pack = _pack(monkeypatch, tmp_path)
    selection: dict = {"items": ["in.groups"]}

    def changed() -> dict[str, bool]:
        return {
            k: _doc(p).get("layout", {}).get("groups") == ["G44"]
            for k, p in paths.items()
        }

    by_name = device_pack.apply_zip(pack, TWIN, dict(selection))
    expected = changed()
    hw = hardware_profile.HardwareProfile()
    for chosen in (selection, {**selection, "targetGuid": ""}):
        _write_own_files()
        done = json.loads(hw.importPack(_url(pack), TWIN, json.dumps(chosen)))
        assert done["ok"] == by_name["ok"], done
        assert changed() == expected
