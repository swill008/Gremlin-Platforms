# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

from gremlin.modules import registry
from test.unit._device_folders import module_path, put_module

_VJOY1_GUID = "{11111111-2222-3333-4444-555555555555}"


@pytest.fixture
def folder(tmp_path: Path) -> Iterator[Path]:
    registry._cache.clear()
    devices = [
        SimpleNamespace(vjoy_id=1, device_guid=_VJOY1_GUID),
        SimpleNamespace(
            vjoy_id=2, device_guid="{99999999-2222-3333-4444-555555555555}"
        ),
    ]
    with (
        mock.patch("gremlin.modules.store.folder", return_value=tmp_path),
        mock.patch(
            "gremlin.device_initialization.output_vjoy_devices", return_value=devices
        ),
    ):
        yield tmp_path
    registry._cache.clear()


def _write(folder: Path, name: str, doc: dict) -> None:
    put_module(folder, name, doc)


def test_direction_rules() -> None:
    assert registry.module_direction({"direction": "target"}, "stick") == "dest"
    assert registry.module_direction({"direction": "output"}, "stick") == "dest"
    # a vJoy or Xbox module is an output whatever its file says
    assert registry.module_direction({"direction": "source"}, "vjoy_1") == "dest"
    assert registry.module_direction({"device": "Xbox 360 1"}, "pad") == "dest"
    assert registry.module_direction({}, "vkbsim_gladiator") == "source"
    source_doc = {"direction": "source"}
    assert registry.module_direction(source_doc, name="VKBsim EVO") == "source"


def test_vjoy_number_is_the_first_digits() -> None:
    assert registry.vjoy_id_from_name("vJoy 1 (2)") == 1
    assert registry.vjoy_id_from_name("vJoy 12") == 12
    assert registry.vjoy_id_from_name("Keyboard") == 0


def test_resolve_prefers_bound_device(folder: Path) -> None:
    # bound to vJoy 1 even though the name says 2
    assert registry.resolve_vjoy_id("vJoy 2", _VJOY1_GUID) == 1
    assert registry.resolve_vjoy_id("vJoy 2") == 2
    assert registry.resolve_vjoy_id("vJoy 1 (2)") == 1
    assert registry.resolve_vjoy_id("vJoy 7") == 0  # no such vJoy


def test_scan_classifies_and_finds(folder: Path) -> None:
    _write(folder, "vJoy 1", {"device": "vJoy 1", "claim": {"buttons": [2, 1]}})
    _write(
        folder,
        "Stick",
        {"device": "Stick", "boundGuidLocal": "{ABCDEF01-0000-0000-0000-000000000000}"},
    )
    put_module(folder, "Broken", "{nope")
    # A module is its device's folder (03 S128): slug is the folder name.
    assert [m.slug for m in registry.outputs()] == ["vJoy 1"]
    assert [m.slug for m in registry.inputs()] == ["Stick"]
    assert registry.inputs()[0].path == folder / "Stick" / "module.json"
    assert registry.inputs()[0].dir == folder / "Stick"
    assert registry.outputs()[0].claim["buttons"] == [1, 2]
    assert registry.output_for_vjoy(1).slug == "vJoy 1"
    assert registry.output_for_vjoy(2) is None


def test_files_outside_a_device_folder_are_not_modules(folder: Path) -> None:
    # The old layout's root <slug>.json and reserved folders are not scanned.
    (folder / "stick.json").write_text(json.dumps({"device": "Stick"}), "utf-8")
    for reserved in ("templates", "cache", "imported"):
        (folder / reserved).mkdir()
        (folder / reserved / "module.json").write_text(
            json.dumps({"device": "Stick"}), "utf-8"
        )
    assert registry.modules() == []


def test_changed_file_is_read_again(folder: Path) -> None:
    _write(folder, "Stick", {"device": "Stick", "claim": {"buttons": [1]}})
    assert registry.inputs()[0].claim["buttons"] == [1]
    path = module_path(folder, "Stick")
    _write(folder, "Stick", {"device": "Stick", "claim": {"buttons": [1, 5]}})
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))
    assert registry.inputs()[0].claim["buttons"] == [1, 5]
    path.unlink()
    assert registry.modules() == []
