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
        mock.patch.object(registry, "_folder", return_value=tmp_path),
        mock.patch(
            "gremlin.device_initialization.output_vjoy_devices", return_value=devices
        ),
    ):
        yield tmp_path
    registry._cache.clear()


def _write(folder: Path, slug: str, doc: dict) -> None:
    (folder / f"{slug}.json").write_text(json.dumps(doc), encoding="utf-8")


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
    _write(folder, "vjoy_1", {"device": "vJoy 1", "claim": {"buttons": [2, 1]}})
    _write(
        folder,
        "stick",
        {"device": "Stick", "boundGuidLocal": "{ABCDEF01-0000-0000-0000-000000000000}"},
    )
    (folder / "broken.json").write_text("{nope", encoding="utf-8")
    assert [m.slug for m in registry.outputs()] == ["vjoy_1"]
    assert [m.slug for m in registry.inputs()] == ["stick"]
    assert registry.outputs()[0].claim["buttons"] == [1, 2]
    assert registry.find("abcdef01000000000000000000000000").slug == "stick"
    assert registry.find(name="VJOY 1").slug == "vjoy_1"
    assert registry.find(name="nothing") is None
    assert registry.output_for_vjoy(1).slug == "vjoy_1"
    assert registry.output_for_vjoy(2) is None


def test_changed_file_is_read_again(folder: Path) -> None:
    _write(folder, "stick", {"device": "Stick", "claim": {"buttons": [1]}})
    assert registry.inputs()[0].claim["buttons"] == [1]
    path = folder / "stick.json"
    _write(folder, "stick", {"device": "Stick", "claim": {"buttons": [1, 5]}})
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))
    assert registry.inputs()[0].claim["buttons"] == [1, 5]
    path.unlink()
    assert registry.modules() == []
