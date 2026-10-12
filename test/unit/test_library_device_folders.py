# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Device Library on device folders (D-03-DEVICE-FOLDERS; 10 S11, S18,
S52, S57, S60, S61): a saved setup is the device folder zip (.gmap), an
autosave holds the whole folder, an older Device Pack setup still restores,
Copy and Swap copy pictures into the receiving stick's own folder, Remove
from Library removes the folder, and a refused rename says why. Everything
runs in temporary modules and library folders."""

from __future__ import annotations

import json
import uuid
import zipfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from gremlin import device_initialization, library_copy, library_swap, shared_state
from gremlin import device_library as library
from gremlin.modules import module_file, store

GUID = "{6C3D1E20-1111-2222-3333-444455556666}"
GUID_B = "{7D4E2F31-1111-2222-3333-444455556666}"
NAME = "Stick A"
NAME_B = "Stick B"
PHOTO_A = b"\x89PNG\r\n\x1a\nA-photo"
PHOTO_B = b"\x89PNG\r\n\x1a\nB-photo"


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
    monkeypatch.setattr(library.clock, "now", _Clock())
    before = shared_state.current_profile
    shared_state.current_profile = None
    yield {"modules": modules, "folder": folder, "tmp": tmp_path}
    shared_state.current_profile = before


def _doc(name: str, guid: str, image: str = "pictures/photo.png") -> dict:
    return {
        "kind": "control.hardware",
        "device": name,
        "boundGuidLocal": guid,
        "claim": {"buttons": [1, 2], "axes": [], "hats": [], "friendly": {}},
        # The device's photo: the bottom background picture (07 S127).
        "nodes": (
            [{"id": "bg", "kind": "draw", "shape": "image", "plane": "background",
              "src": image}] if image else []
        ) + [{"kind": "chip", "id": "b1"}],
    }


def _put(name: str, guid: str, doc: dict | None, pictures: dict[str, bytes]) -> Path:
    """A device folder as the program writes it: device.json, module.json
    (doc None: none) and its pictures."""
    where = store.ensure_device_dir(name, guid)
    for file, data in pictures.items():
        dest = where / store.PICTURES / file
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    if doc is not None:
        module_file.write_bytes(
            store.module_file_in(where), json.dumps(doc).encode("utf-8")
        )
    return where


def _names(path: Path) -> list[str]:
    with zipfile.ZipFile(path, "r") as zf:
        return zf.namelist()


# --- S60: a saved setup is the device folder zip ---------------------------------


def test_a_saved_setup_is_a_gmap_of_the_folder(lib: dict) -> None:
    _put(NAME, GUID, _doc(NAME, GUID), {"photo.png": PHOTO_A})
    out = library.save_setup(NAME, GUID, [])
    assert out["ok"], out
    setup = out["setup"]
    pack = Path(setup["pack"])
    assert pack.suffix == ".gmap"
    names = _names(pack)
    assert "gmap.json" in names and "module.json" in names
    assert "pictures/photo.png" in names
    assert "device.json" not in names
    assert {"setup", "device_map"} <= set(setup["holds"])
    shown = library.photo(setup["key"])
    assert shown and Path(shown).read_bytes() == PHOTO_A


def test_an_autosave_holds_the_whole_folder(lib: dict) -> None:
    where = _put(
        NAME, GUID, _doc(NAME, GUID), {"photo.png": PHOTO_A, "old.png": PHOTO_B}
    )
    (where / store.RECOVERY_FILE).write_text("{}", encoding="utf-8")
    out = library.autosave(NAME, GUID, "copy", "Autosave: before Copy", [])
    assert out["ok"], out
    setup = out["setups"][0]
    names = _names(Path(setup["pack"]))
    for rel in ("module.json", "device.json", "recovery.json", "pictures/old.png"):
        assert library.EXACT_ENTRY + rel in names, rel
    kept = library.folder_files(setup["key"])
    assert kept["pictures/old.png"] == PHOTO_B
    assert (
        library.module_bytes(setup["key"]) == store.module_file(NAME, GUID).read_bytes()
    )


# --- older saved setups are not read (D-FIXLIST-B2) ---------------------------------


def _old_pack(tmp: Path, exact: bytes) -> Path:
    """A saved setup kept before device folders: a Device Pack with the
    module file kept exactly under exact/<slug>.json."""
    path = tmp / "Old setup.zip"
    doc = _doc(NAME, "", image="pictures/photo.png")
    doc.pop("boundGuidLocal")
    doc["pack"] = {"format": 1, "exportedName": NAME, "exportedGuid": GUID}
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("map.json", json.dumps(doc))
        zf.writestr("pictures/photo.png", PHOTO_A)
        zf.writestr(library.EXACT_ENTRY + "stick_a.json", exact)
    return path


def test_an_old_pack_setup_is_not_read(lib: dict) -> None:
    """Unreleased: no reader for .zip Device Packs, under either name."""
    exact = json.dumps(_doc(NAME, GUID, image="")).encode("utf-8")
    old = _old_pack(lib["tmp"], exact)
    got = library.import_pack(old)
    assert not got["ok"] and ".gmap" in got["error"], got
    renamed = old.rename(old.with_suffix(".gmap"))
    got = library.import_pack(renamed)
    assert not got["ok"] and "gmap.json" in got["error"], got
    assert all(not row["setups"] for row in library.devices())


# --- S61: Copy puts the pictures in the receiving stick's folder ------------------


def _plugged_stick() -> tuple[str, str]:
    for dev in device_initialization.physical_devices():
        if dev.name == "pJoy Pro":
            return dev.name, store.guid_text(dev.device_guid)
    pytest.skip("the fake stick is not there")


def test_copy_puts_the_pictures_in_the_receiving_folder(lib: dict) -> None:
    target, target_guid = _plugged_stick()
    source = _put(NAME, GUID, _doc(NAME, GUID), {"photo.png": PHOTO_A})
    saved = library.save_setup(NAME, GUID, [])
    assert saved["ok"], saved
    out = library_copy.copy(
        saved["setup"]["key"], target, target_guid, ["setup", "device_map"], [], []
    )
    assert out["ok"], out
    there = store.device_dir(target, target_guid)
    assert there != source
    doc = store.read_path(store.module_file_in(there))
    ref = store.device_photo_ref(doc)
    assert ref.startswith("pictures/"), ref
    assert store.picture_path(there, ref).read_bytes() == PHOTO_A
    # Not shared: the source keeps its own copy.
    assert (source / "pictures" / "photo.png").read_bytes() == PHOTO_A


# --- S52: Remove from Library removes the folder ---------------------------------


def test_remove_from_library_removes_the_folder(lib: dict) -> None:
    where = _put(NAME, GUID, _doc(NAME, GUID), {"photo.png": PHOTO_A})
    assert library.autosave(NAME, GUID, "deleted", "Autosave: deleted", [])["ok"]
    # Delete Device (run first by the window) took the module file.
    store.module_file_in(where).unlink()
    row = library.find_device(NAME, GUID)
    assert row is not None
    out = library.remove_device(row["key"])
    assert out["ok"], out
    assert not where.exists()
    assert library.find_device(NAME, GUID) is None


def test_remove_from_library_waits_for_delete_device(lib: dict) -> None:
    where = _put(NAME, GUID, _doc(NAME, GUID), {"photo.png": PHOTO_A})
    row = library.find_device(NAME, GUID)
    assert row is not None
    out = library.remove_device(row["key"])
    assert not out["ok"] and out.get("module_file")
    assert store.module_file_in(where).is_file()


# --- a refused rename says why ---------------------------------------------------


def test_a_refused_rename_shows_the_reason(
    lib: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin import device_aliases

    reason = (
        "The folder Stick A could not be renamed to New: a file in it is open "
        "in another program (Access is denied)."
    )
    monkeypatch.setattr(device_aliases, "set_alias", lambda key, value: reason)
    _put(NAME, GUID, _doc(NAME, GUID), {})
    row = library.find_device(NAME, GUID)
    assert row is not None
    out = library.rename(row["key"], "New")
    assert not out["ok"]
    assert out["error"] == reason
    again = library.find_device(NAME, GUID)
    assert again is not None and again["name"] == row["name"]


# --- S61: Swap keeps each stick's pictures in its own folder ---------------------


def test_swap_keeps_each_sticks_pictures_in_its_own_folder(lib: dict) -> None:
    dir_a = _put(NAME, GUID, _doc(NAME, GUID), {"photo.png": PHOTO_A})
    dir_b = _put(NAME_B, GUID_B, _doc(NAME_B, GUID_B), {"photo.png": PHOTO_B})
    shared = {"button": {1, 2}, "axis": set(), "hat": set()}
    before: list = []
    failed = library_swap._write_module_parts(
        (NAME, GUID), (NAME_B, GUID_B), ["device_map"], shared, before
    )
    assert failed == ""
    for where, photo in ((dir_a, PHOTO_B), (dir_b, PHOTO_A)):
        doc = store.read_path(store.module_file_in(where))
        ref = store.device_photo_ref(doc)
        assert ref.startswith("pictures/"), ref
        assert store.picture_path(where, ref).read_bytes() == photo
    # Each stick's own photo is still where it was.
    assert (dir_a / "pictures" / "photo.png").read_bytes() == PHOTO_A
    assert (dir_b / "pictures" / "photo.png").read_bytes() == PHOTO_B


def _saved_profile(tmp: Path, buttons: int = 2) -> Path:
    """A saved profile with Map to vJoy bindings on Stick A's buttons."""
    from gremlin import plugin_manager
    from gremlin.profile import DeviceInfo, Profile
    from gremlin.types import InputType

    uid = uuid.UUID(GUID.strip("{}"))
    profile = Profile()
    profile.device_database.devices[uid] = DeviceInfo(uid, NAME)
    before = shared_state.current_profile
    shared_state.current_profile = profile
    for button in range(1, buttons + 1):
        action = plugin_manager.PluginManager().create_instance(
            "Map to vJoy", InputType.JoystickButton
        )
        action.vjoy_device_id = 1
        action.vjoy_input_id = button
        action.vjoy_input_type = InputType.JoystickButton
        item = profile.get_input_item(
            uid, InputType.JoystickButton, button, "Default", create_if_missing=True
        )
        assert item is not None and action is not None
        binding = item.add_item_binding()
        assert binding.root_action is not None
        binding.root_action.insert_action(action, "children")
    path = tmp / "Flight.xml"
    profile.to_xml(path)
    shared_state.current_profile = before
    return path


def _bound(path: Path) -> int:
    from gremlin.profile import Profile

    profile = Profile()
    profile.from_xml(path)
    uid = uuid.UUID(GUID.strip("{}"))
    return sum(1 for item in profile.inputs.get(uid, []) if item.action_sequences)


def test_a_stick_with_no_module_file_is_saved_as_a_bindings_only_gmap(
    lib: dict,
) -> None:
    profile = _saved_profile(lib["tmp"])
    assert _bound(profile) == 2
    out = library.autosave(NAME, GUID, "copy", "Autosave: before Copy", [profile])
    assert out["ok"], out
    setup = out["setups"][0]
    pack = Path(setup["pack"])
    assert pack.suffix == ".gmap"
    with zipfile.ZipFile(pack, "r") as zf:
        head = json.loads(zf.read("gmap.json"))
        names = zf.namelist()
    assert head["parts"] == ["bindings"]
    assert "module.json" not in names and "bindings/wires.json" in names
    assert setup["holds"] == ["bindings"]
    assert setup["moduleFile"] == ""
    # The bindings go, then the autosave puts them back (and no folder).
    _empty_profile(profile)
    assert _bound(profile) == 0
    back = library_copy.restore(setup["key"])
    assert back["ok"], back
    assert _bound(profile) == 2
    assert not store.module_file(NAME, GUID).is_file()


def _empty_profile(path: Path) -> None:
    from gremlin.profile import DeviceInfo, Profile

    uid = uuid.UUID(GUID.strip("{}"))
    profile = Profile()
    profile.device_database.devices[uid] = DeviceInfo(uid, NAME)
    profile.to_xml(path)


def test_a_damaged_module_file_is_saved_as_a_gmap(lib: dict) -> None:
    where = _put(NAME, GUID, None, {"photo.png": PHOTO_A})
    store.module_file_in(where).write_bytes(b"{ not json")
    profile = _saved_profile(lib["tmp"])
    out = library.autosave(NAME, GUID, "deleted", "Autosave: deleted", [profile])
    assert out["ok"], out
    setup = out["setups"][0]
    pack = Path(setup["pack"])
    assert pack.suffix == ".gmap"
    assert library.DAMAGED_PART in setup["holds"] and "bindings" in setup["holds"]
    assert setup["moduleFile"] == "damaged"
    with zipfile.ZipFile(pack, "r") as zf:
        assert json.loads(zf.read("gmap.json"))["damaged"]
        assert zf.read(store.MODULE_FILE) == b"{ not json"
    assert library.module_bytes(setup["key"]) is None


def test_a_damaged_gmap_setup_restores_its_bindings(lib: dict) -> None:
    where = _put(NAME, GUID, None, {"photo.png": PHOTO_A})
    store.module_file_in(where).write_bytes(b"{ not json")
    profile = _saved_profile(lib["tmp"])
    out = library.autosave(NAME, GUID, "deleted", "Autosave: deleted", [profile])
    assert out["ok"], out
    setup = out["setups"][0]
    # Restore puts the bindings back; the damaged file is never written.
    _empty_profile(profile)
    back = library_copy.restore(setup["key"])
    assert back["ok"], back
    assert _bound(profile) == 2
    assert store.module_file_in(where).read_bytes() == b"{ not json"


def test_undo_puts_the_folder_back_from_the_autosave(lib: dict) -> None:
    where = _put(NAME, GUID, _doc(NAME, GUID), {"photo.png": PHOTO_A})
    before = store.module_file_in(where).read_bytes()
    out = library.autosave(NAME, GUID, "copy", "Autosave: before Copy", [])
    assert out["ok"], out
    setup = out["setups"][0]
    store.module_file_in(where).write_bytes(b'{"kind": "control.hardware"}')
    (where / "pictures" / "photo.png").unlink()
    note: dict = {"notes": [], "warnings": []}
    failed = library_copy._put_module_back(
        setup, NAME, GUID, Path(setup["pack"]), [], note
    )
    assert failed == ""
    assert store.module_file_in(where).read_bytes() == before
    assert (where / "pictures" / "photo.png").read_bytes() == PHOTO_A
