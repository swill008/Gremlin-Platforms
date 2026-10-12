# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A device is found by its Windows id, never its name (03 S90a): with two
identical sticks plugged in, the Auto Mapping Tool's source and the Device Pack
export never take the first stick for the second."""

from __future__ import annotations

import io
import json
import uuid
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from gremlin import auto_mapping_tool, device_initialization, profile
from gremlin.modules import device_zip, store
from gremlin.ui import device_pack
from test.unit import test_stage1_modules
from test.unit._device_folders import put_module

_app = test_stage1_modules._app
folder = test_stage1_modules.folder

TWIN = "Twin Stick"
FIRST = uuid.UUID("11111111-1111-1111-1111-111111111111")
SECOND = uuid.UUID("22222222-2222-2222-2222-222222222222")


def _twins() -> list[SimpleNamespace]:
    return [
        SimpleNamespace(name=TWIN, device_guid=SimpleNamespace(uuid=FIRST)),
        SimpleNamespace(name=TWIN, device_guid=SimpleNamespace(uuid=SECOND)),
    ]


@pytest.fixture
def twins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(device_initialization, "physical_devices", _twins)
    monkeypatch.setattr(store, "live_devices", _twins)


# --- Auto Mapping Tool ---------------------------------------------------------------


def test_auto_mapping_tool_source_is_its_own_id(twins: None) -> None:
    mapper = auto_mapping_tool.AutoMappingTool(profile.Profile())
    source = {"name": TWIN, "boundName": TWIN, "guid": str(SECOND)}
    assert mapper._source_uuid(source) == SECOND


def test_auto_mapping_tool_source_without_an_id_is_no_device(
    folder: Path, twins: None
) -> None:
    """A folder named after both twins and holding no id: either could use
    it, so no one device. Old code took the first stick of that name."""
    shared = folder / TWIN
    shared.mkdir()
    (shared / "module.json").write_text(
        json.dumps({"kind": "control.hardware", "device": TWIN}), encoding="utf-8"
    )
    store._dirs_changed()
    assert store.device_dir(TWIN, str(FIRST)) == shared
    assert store.device_dir(TWIN, str(SECOND)) == shared
    mapper = auto_mapping_tool.AutoMappingTool(profile.Profile())
    source = {"name": TWIN, "boundName": TWIN, "guid": "", "dir": str(shared)}
    assert mapper._source_uuid(source) is None


# --- Device Pack export ---------------------------------------------------------


def _write_files(guids: tuple[uuid.UUID, ...] = (FIRST, SECOND)) -> None:
    """Each plugged-in twin's folder (its own, by its id, 03 S1 S132)."""
    doc = {
        "kind": "control.hardware",
        "device": TWIN,
        "direction": "source",
        "claim": {"buttons": [1], "axes": [], "hats": [], "keys": []},
    }
    for guid in guids:
        put_module(store.folder(), TWIN, doc, str(guid))


def _packed_id(plan: dict) -> str:
    """The device id in the .gmap a plan builds (gmap.json "id")."""
    data, _info = device_pack.build_pack(plan)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        label = json.loads(zf.read(device_zip.GMAP_JSON))
    return device_zip.braced_guid(label["id"])


def test_pack_export_of_the_second_twin_has_its_id(folder: Path, twins: None) -> None:
    _write_files()
    plan = device_pack.plan_pack(TWIN, lambda _p: None, guid=str(SECOND))
    assert isinstance(plan, dict), plan
    assert _packed_id(plan) == device_zip.braced_guid(str(SECOND))


def test_pack_export_by_a_shared_name_is_refused(folder: Path, twins: None) -> None:
    """Old code exported the first twin's id for a name both share."""
    _write_files()
    plan = device_pack.plan_pack(TWIN, lambda _p: None)
    assert isinstance(plan, str), plan
    assert "More than one device is called Twin Stick" in plan


def test_pack_export_by_a_name_only_one_device_has(
    folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    one = _twins()[1:]
    monkeypatch.setattr(device_initialization, "physical_devices", lambda: one)
    monkeypatch.setattr(store, "live_devices", lambda: one)
    _write_files((SECOND,))

    plan = device_pack.plan_pack(TWIN, lambda _p: None)
    assert isinstance(plan, dict), plan
    assert _packed_id(plan) == device_zip.braced_guid(str(SECOND))
