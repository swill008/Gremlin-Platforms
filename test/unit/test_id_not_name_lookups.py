# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A device is found by its Windows id, never its name (03 S90a): with two
identical sticks plugged in, the Auto Mapper's source and the Device Pack
export never take the first stick for the second."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

from gremlin import auto_mapper, device_initialization, profile
from gremlin.modules import store
from gremlin.ui import device_pack
from test.unit import test_stage1_modules

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


# --- Auto Mapper ---------------------------------------------------------------


def test_auto_mapper_source_is_its_own_id(twins: None) -> None:
    mapper = auto_mapper.AutoMapper(profile.Profile())
    source = {"name": TWIN, "boundName": TWIN, "guid": str(SECOND)}
    assert mapper._source_uuid(source) == SECOND


def _slug() -> str:
    return store.slug_for(TWIN, str(SECOND))


def test_auto_mapper_source_without_an_id_is_no_device(
    folder: Path, twins: None
) -> None:
    """Both twins use the file: no one device. Old code took the first stick
    of that name."""
    mapper = auto_mapper.AutoMapper(profile.Profile())
    source = {"name": TWIN, "boundName": TWIN, "guid": "", "slug": _slug()}
    assert mapper._source_uuid(source) is None


# --- Device Pack export ---------------------------------------------------------


def _write_files() -> None:
    doc = {
        "kind": "control.hardware",
        "device": TWIN,
        "direction": "source",
        "claim": {"buttons": [1], "axes": [], "hats": [], "keys": []},
    }
    for guid in ("", str(FIRST), str(SECOND)):
        path = store.path_for(TWIN, guid)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc), encoding="utf-8")
        path = store.path_for_id(TWIN, guid) if guid else path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc), encoding="utf-8")


def test_pack_export_of_the_second_twin_has_its_id(
    folder: Path, twins: None
) -> None:
    _write_files()
    plan = device_pack.plan_pack(TWIN, lambda _p: None, guid=str(SECOND))
    assert isinstance(plan, dict), plan
    assert plan["map"]["pack"]["exportedGuid"] == str(SECOND)


def test_pack_export_by_a_shared_name_is_refused(
    folder: Path, twins: None
) -> None:
    """Old code exported the first twin's id for a name both share."""
    _write_files()
    plan = device_pack.plan_pack(TWIN, lambda _p: None)
    assert isinstance(plan, str), plan["map"]["pack"]
    assert "More than one device is called Twin Stick" in plan


def test_pack_export_by_a_name_only_one_device_has(
    folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    one = _twins()[1:]
    monkeypatch.setattr(device_initialization, "physical_devices", lambda: one)
    monkeypatch.setattr(store, "live_devices", lambda: one)
    _write_files()
    plan = device_pack.plan_pack(TWIN, lambda _p: None)
    assert isinstance(plan, dict), plan
    assert plan["map"]["pack"]["exportedGuid"] == str(SECOND)
