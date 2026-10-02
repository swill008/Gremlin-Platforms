# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A device's module file is found by the device first, then by its name."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from unittest import mock

import pytest

from gremlin.modules import registry

_STICK = "87FDB100-A8F5-11F1-8003-444553540000"
_OTHER = "11111111-A8F5-11F1-8003-444553540000"


def _write(folder: Path, slug: str, device: str, guid: str) -> None:
    doc = {"device": device, "boundName": device, "boundGuidLocal": guid}
    (folder / f"{slug}.json").write_text(json.dumps(doc), encoding="utf-8")


@pytest.fixture
def folder(tmp_path: Path) -> Iterator[Path]:
    registry._cache.clear()
    with (
        mock.patch.object(registry, "_folder", return_value=tmp_path),
        mock.patch.object(registry, "_binding_store", return_value={}),
        mock.patch.object(registry, "_guid_for_name", return_value=""),
    ):
        yield tmp_path
    registry._cache.clear()


def test_renamed_device_finds_its_file_by_device(folder: Path) -> None:
    # Saved under the old name; Windows now reports a new name.
    _write(folder, "vkb_evo_ot_l", "VKB EVO OT L", _STICK)
    assert registry.resolve_module_slug("VKBsim Gladiator EVO OT L", _STICK) == (
        "vkb_evo_ot_l"
    )


def test_stale_id_does_not_pull_in_another_devices_file(folder: Path) -> None:
    _write(folder, "stick_a", "Stick A", _STICK)
    _write(folder, "stick_b", "Stick B", _OTHER)
    # Stick B passed with Stick A's id: Stick B keeps its own file.
    assert registry.resolve_module_slug("Stick B", _STICK) == "stick_b"


def test_no_device_match_falls_back_to_the_name(folder: Path) -> None:
    _write(folder, "stick_a", "Stick A", _STICK)
    assert registry.resolve_module_slug("Stick A", "") == "stick_a"
    assert registry.resolve_module_slug("New Stick", _OTHER) == "new_stick"


def test_saved_binding_still_wins(folder: Path) -> None:
    _write(folder, "stick_a", "Stick A", _STICK)
    key = registry.stored_guid_key(_STICK)
    with mock.patch.object(registry, "_binding_store", return_value={key: "custom"}):
        assert registry.resolve_module_slug("Stick A", _STICK) == "custom"
