# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A device's folder is found by its id first (device.json), then by its
shown name (03 S1 S4 S130, D-03-DEVICE-FOLDERS)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from unittest import mock

import pytest

from gremlin.modules import registry, store
from gremlin.modules.ids import guid_key
from test.unit._device_folders import put_module

_STICK = "87FDB100-A8F5-11F1-8003-444553540000"
_OTHER = "11111111-A8F5-11F1-8003-444553540000"


def _write(folder: Path, device: str, guid: str) -> Path:
    doc = {"device": device, "boundName": device, "boundGuidLocal": guid}
    return put_module(folder, device, doc, guid).parent


def _dirs_changed() -> None:
    registry._cache.clear()
    store._dirs_changed()


@pytest.fixture
def folder(tmp_path: Path) -> Iterator[Path]:
    _dirs_changed()
    with (
        mock.patch.object(store, "folder", return_value=tmp_path),
        mock.patch.object(registry, "_folder", return_value=tmp_path),
        mock.patch.object(registry, "connected_names", return_value={}),
        mock.patch.object(registry, "guid_for_name", return_value=""),
    ):
        yield tmp_path
    _dirs_changed()


def test_renamed_device_finds_its_folder_by_id(folder: Path) -> None:
    # Saved under the old name; Windows now reports a new name.
    old = _write(folder, "VKB EVO OT L", _STICK)
    assert store.device_dir("VKBsim Gladiator EVO OT L", _STICK) == old
    assert store.module_file("VKBsim Gladiator EVO OT L", _STICK) == old / "module.json"


def test_stale_id_does_not_pull_in_another_devices_folder(folder: Path) -> None:
    a = _write(folder, "Stick A", _STICK)
    b = _write(folder, "Stick B", _OTHER)
    connected = {"stick a": {guid_key(_STICK)}, "stick b": {guid_key(_OTHER)}}
    with mock.patch.object(registry, "connected_names", return_value=connected):
        # Stick B passed with Stick A's id: Stick B keeps its own folder.
        assert store.device_dir("Stick B", _STICK) == b
        assert store.device_dir("Stick A", _STICK) == a


def test_no_id_match_falls_back_to_the_shown_name(folder: Path) -> None:
    a = _write(folder, "Stick A", _STICK)
    assert store.device_dir("Stick A", "") == a
    # A device with no folder yet: its own name's folder, not made (S54).
    new = store.device_dir("New Stick", _OTHER)
    assert new == folder / "New Stick"
    assert not new.exists()
    assert not store.module_file("New Stick", _OTHER).is_file()


def test_a_folder_of_the_name_holding_another_id_is_not_taken(folder: Path) -> None:
    # S132: same shown name, different id -> "<name> (2)".
    _write(folder, "Stick A", _STICK)
    assert store.device_dir("Stick A", _OTHER) == folder / "Stick A (2)"
