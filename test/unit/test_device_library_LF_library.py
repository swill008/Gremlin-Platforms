# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Device Library store, the gaps filled by LF: what inputs a device has and
when it was last seen (10 S8), a saved setup's Button Map photo (S11), and a
device's current settings as a pack kept nowhere (S22). The real store in a
temporary library folder and modules folder."""

from __future__ import annotations

import json
import uuid
import zipfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from gremlin import device_library as library
from gremlin import plugin_manager, shared_state
from gremlin.modules import module_file, registry, store
from gremlin.profile import DeviceInfo, Profile
from gremlin.types import InputType

GUID = "{6C3D1E20-1111-2222-3333-444455556666}"
UID = uuid.UUID(GUID.strip("{}"))
NAME = "Stick A"
PNG = b"\x89PNG\r\n\x1a\n" + b"photo bytes" * 20


class _Clock:
    def __init__(self) -> None:
        self.at = 1_780_000_000.0

    def __call__(self) -> float:
        self.at += 1.0
        return self.at


@pytest.fixture
def lib(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[dict]:
    modules = tmp_path / "modules"
    modules.mkdir()
    folder = tmp_path / "device library"
    monkeypatch.setattr(store, "folder", lambda: modules)
    monkeypatch.setattr(library, "folder", lambda: folder)
    monkeypatch.setattr(library, "_photo_cache", lambda: tmp_path / "photo cache")
    plugged: list[tuple[str, str]] = []
    monkeypatch.setattr(library, "_connected", lambda: list(plugged))
    monkeypatch.setattr(library, "_alias", lambda guid, default: default)
    monkeypatch.setattr(library.clock, "now", _Clock())
    before = shared_state.current_profile
    shared_state.current_profile = None
    yield {"modules": modules, "folder": folder, "plugged": plugged, "tmp": tmp_path}
    shared_state.current_profile = before


def _module(modules: Path, photo: bool = False) -> Path:
    slug = registry.plain_slug(NAME)
    path = modules / f"{slug}.json"
    doc: dict = {
        "kind": "control.hardware",
        "device": NAME,
        "boundGuidLocal": GUID,
        "claim": {"buttons": [1, 2, 3], "axes": [1, 2], "hats": [1]},
        "nodes": [],
    }
    if photo:
        pictures = modules / slug
        pictures.mkdir(exist_ok=True)
        (pictures / "photo.png").write_bytes(PNG)
        doc["image"] = f"{slug}/photo.png"
    module_file.write_bytes(path, json.dumps(doc).encode("utf-8"))
    return path


def _profile() -> Profile:
    profile = Profile()
    profile.device_database.devices[UID] = DeviceInfo(UID, NAME)
    shared_state.current_profile = profile
    action = plugin_manager.PluginManager().create_instance(
        "Map to vJoy", InputType.JoystickButton
    )
    action.vjoy_device_id = 2
    action.vjoy_input_id = 7
    action.vjoy_input_type = InputType.JoystickButton
    item = profile.get_input_item(
        UID, InputType.JoystickButton, 1, "Default", create_if_missing=True
    )
    assert item is not None
    root = item.add_item_binding().root_action
    assert root is not None
    root.insert_action(action, "children")
    return profile


def _row() -> dict:
    row = library.find_device(NAME)
    assert row is not None
    return row


# --- S8 ----------------------------------------------------------------------


def test_s8_inputs_from_the_module_file_when_not_connected(lib: dict) -> None:
    _module(lib["modules"])
    got = library.inputs(_row()["key"])
    assert got == {"buttons": 3, "axes": 2, "hats": 1, "from": "module file"}


def test_s8_inputs_from_the_device_list_when_connected(
    lib: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    _module(lib["modules"])
    lib["plugged"].append((NAME, GUID))
    monkeypatch.setattr(
        store,
        "connected_input_ids",
        lambda guid: (
            ({1, 2, 3, 4, 5}, {1, 2, 3, 4}, {1, 2})
            if store.guid_text(guid).strip("{}").upper() == GUID.strip("{}")
            else None
        ),
    )
    got = library.inputs(_row()["key"])
    assert got == {"buttons": 5, "axes": 4, "hats": 2, "from": "device"}


def test_s8_last_seen_is_kept_after_the_stick_is_unplugged(lib: dict) -> None:
    _module(lib["modules"])
    lib["plugged"].append((NAME, GUID))
    assert _row()["seen"] == "now"
    library.note_seen([GUID])
    lib["plugged"].clear()
    seen = _row()["seen"]
    assert seen and seen != "now" and seen[:4].isdigit(), seen
    # Seeing a stick doesn't add it to the Library's list of devices.
    doc = json.loads((lib["folder"] / library.LIST_NAME).read_text("utf-8"))
    assert doc["devices"] == []


# --- S11 ---------------------------------------------------------------------


def test_s11_a_saved_setups_photo_comes_from_its_pack(lib: dict) -> None:
    _module(lib["modules"], photo=True)
    saved = library.save_setup(NAME, GUID, [])
    assert saved["ok"], saved
    path = library.photo(saved["setup"]["key"])
    assert path and Path(path).read_bytes() == PNG
    assert not Path(path).is_relative_to(lib["folder"])  # never in the Library
    # Asked again: the same file, not another copy.
    assert library.photo(saved["setup"]["key"]) == path


def test_s11_a_saved_setup_without_a_photo_has_none(lib: dict) -> None:
    _module(lib["modules"])
    saved = library.save_setup(NAME, GUID, [])
    assert library.photo(saved["setup"]["key"]) == ""
    assert library.photo("set-missing") == ""


# --- S22 ---------------------------------------------------------------------


def test_s22_current_settings_as_a_pack_kept_nowhere(lib: dict) -> None:
    _module(lib["modules"])
    profile = _profile()
    key = _row()["key"]
    got = library.current_pack(key, profile)
    assert got["ok"], got
    assert "setup" in got["holds"] and "bindings" in got["holds"]
    assert got["modes"] == ["Default"]
    with zipfile.ZipFile(__import__("io").BytesIO(got["data"])) as zf:
        assert "wires.json" in zf.namelist()
    # Nothing kept in the Library.
    assert _row()["setups"] == []
    assert not any(lib["folder"].rglob("*.zip"))
    module_only = library.current_pack(key, None)
    assert module_only["ok"] and "bindings" not in module_only["holds"]


def test_s22_a_device_with_nothing_here_has_no_current_settings(lib: dict) -> None:
    _module(lib["modules"])
    assert library.autosave(NAME, GUID, "deleted", "Autosave: stick deleted", [])["ok"]
    (lib["modules"] / f"{registry.plain_slug(NAME)}.json").unlink()
    got = library.current_pack(_row()["key"], None)
    assert not got["ok"] and "saved setup" in got["error"]
