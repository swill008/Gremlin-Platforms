# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Device Library store (10 Device Library): library.json, saved setups
as Device Packs, the autosave rules (S12-S21), names (S7, S13), import of
someone else's pack (S35), search (S5), tidy (S38), size (S4) and the last
change kept for Undo (S41). Everything runs in a temporary library folder
and modules folder."""

from __future__ import annotations

import io
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


class _Clock:
    """Steps one second per reading, so every saved setup has its own time."""

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
    plugged: list[tuple[str, str]] = []
    monkeypatch.setattr(library, "_connected", lambda: list(plugged))
    aliases: dict[str, str] = {}
    monkeypatch.setattr(
        library, "_alias", lambda guid, default: aliases.get(guid, default)
    )
    monkeypatch.setattr(
        library, "_set_alias", lambda guid, name: aliases.__setitem__(guid, name)
    )
    monkeypatch.setattr(library.clock, "now", _Clock())
    before = shared_state.current_profile
    shared_state.current_profile = None
    yield {
        "modules": modules,
        "folder": folder,
        "plugged": plugged,
        "aliases": aliases,
        "tmp": tmp_path,
    }
    shared_state.current_profile = before


def _module(modules: Path, name: str = NAME, guid: str = GUID) -> Path:
    path = modules / f"{registry.plain_slug(name)}.json"
    doc = {
        "kind": "control.hardware",
        "device": name,
        "boundGuidLocal": guid,
        "claim": {"buttons": [1, 2], "friendly": {"btn:1": "Fire"}},
        "calibration": {"1": [0, 100, 200, 300]},
        "nodes": [{"kind": "chip", "id": "b1"}],
    }
    module_file.write_bytes(path, json.dumps(doc).encode("utf-8"))
    return path


def _saved_profile(tmp: Path, vjoy: int = 1, buttons: int = 3) -> Path:
    profile = Profile()
    profile.device_database.devices[UID] = DeviceInfo(UID, NAME)
    before = shared_state.current_profile
    shared_state.current_profile = profile  # actions are made in its library
    for button in range(1, buttons + 1):
        action = plugin_manager.PluginManager().create_instance(
            "Map to vJoy", InputType.JoystickButton
        )
        action.vjoy_device_id = vjoy
        action.vjoy_input_id = button
        action.vjoy_input_type = InputType.JoystickButton
        item = profile.get_input_item(
            UID, InputType.JoystickButton, button, "Default", create_if_missing=True
        )
        assert item is not None and action is not None
        binding = item.add_item_binding()
        assert binding.root_action is not None
        binding.root_action.insert_action(action, "children")
    path = tmp / "Flight.xml"
    profile.to_xml(path)
    shared_state.current_profile = before
    return path


def _by_key(key: str) -> dict:
    row = library.device(key)
    assert row is not None, key
    return row


def _row(name: str = NAME) -> dict:
    row = library.find_device(name)
    assert row is not None, name
    return row


# --- devices (S6, S9) ------------------------------------------------------------


def test_set_up_connected_and_deleted_devices_are_listed(lib: dict) -> None:
    _module(lib["modules"])
    assert _row()["state"] == "not_connected"
    lib["plugged"].append((NAME, GUID))
    lib["plugged"].append(("Throttle B", "{AAAAAAAA-1111-2222-3333-444455556666}"))
    assert _row()["state"] == "connected"
    assert _row()["module"]
    assert _row("Throttle B")["state"] == "connected"
    assert not _row("Throttle B")["module"]


def test_a_deleted_stick_shows_as_deleted(lib: dict) -> None:
    path = _module(lib["modules"])
    out = library.autosave(NAME, GUID, "deleted", "Autosave: stick deleted", [])
    assert out["ok"], out
    path.unlink()  # Delete Device removes the module file afterwards
    row = _row()
    assert row["state"] == "deleted"
    assert row["setups"][0]["name"] == "Autosave: stick deleted"
    assert row["setups"][0]["origin"] == "autosave"
    # Plugged in again, it is Connected with its autosave kept.
    lib["plugged"].append((NAME, GUID))
    assert _row()["state"] == "connected"
    assert len(_row()["setups"]) == 1


def test_nothing_is_read_from_the_old_deleted_devices_folder(lib: dict) -> None:
    old = lib["tmp"] / "deleted devices" / "Old Stick"
    old.mkdir(parents=True)
    (old / "Old Stick.2026.zip").write_bytes(b"PK")
    (lib["tmp"] / "deleted devices" / "old_stick 2026.json").write_text("{}")
    assert library.devices() == []


# --- saving (S12, S18) -------------------------------------------------------------


def test_save_setup_keeps_the_module_file_and_a_saved_profiles_bindings(
    lib: dict,
) -> None:
    _module(lib["modules"])
    profile_path = _saved_profile(lib["tmp"], vjoy=2, buttons=3)
    out = library.save_setup(NAME, GUID, [profile_path])
    assert out["ok"], out
    assert shared_state.current_profile is None  # put back after the build
    (setup,) = out["setups"]
    assert setup["own"] and setup["origin"] == "user"
    assert setup["name"] == "Flight"  # named after the profile (S12)
    assert setup["holds"] == ["setup", "button_map", "calibration", "bindings"]
    assert setup["profiles"][0]["modes"] == ["Default"]
    assert setup["profiles"][0]["actions"] == 3
    assert setup["vjoys"] == {"2": 3}
    with zipfile.ZipFile(setup["pack"]) as zf:
        assert "map.json" in zf.namelist() and "wires.json" in zf.namelist()
    assert library.pack_path(setup["key"]) == Path(setup["pack"])


def test_save_setup_with_no_profiles_keeps_the_module_file_only(lib: dict) -> None:
    _module(lib["modules"])
    out = library.save_setup(NAME, GUID, [])
    assert out["ok"], out
    assert "bindings" not in out["setups"][0]["holds"]
    assert out["setups"][0]["profiles"] == []


def test_a_profile_that_cant_be_read_refuses_the_save(lib: dict) -> None:
    _module(lib["modules"])
    out = library.save_setup(NAME, GUID, [lib["tmp"] / "missing.xml"])
    assert not out["ok"] and "missing.xml" in out["error"]
    assert library.devices()[0]["setups"] == []


# --- autosaves (S13, S16-S20) --------------------------------------------------------


def test_the_limit_keeps_the_newest_autosaves_and_never_the_users_own(
    lib: dict,
) -> None:
    _module(lib["modules"])
    own = library.save_setup(NAME, GUID, [])["setups"][0]
    keys = []
    for number in range(12):
        out = library.autosave(NAME, GUID, "copy", f"Autosave: {number}", [])
        assert out["ok"], out
        keys.append(out["keys"][0])
    setups = _row()["setups"]
    autos = [s for s in setups if s["origin"] == "autosave"]
    assert [s["key"] for s in autos] == list(reversed(keys))[:10]
    assert own["key"] in [s["key"] for s in setups]
    # The removed autosaves' packs are gone from the folder too.
    packs = list(lib["folder"].rglob("*.zip"))
    assert len(packs) == 11


def test_a_renamed_or_described_autosave_becomes_own_and_stays(lib: dict) -> None:
    _module(lib["modules"])
    library.set_settings({"keep": 2})
    first = library.autosave(NAME, GUID, "swap", "Autosave: before Swap", [])
    second = library.autosave(NAME, GUID, "swap", "Autosave: before Swap", [])
    assert library.rename(first["keys"][0], "Good bindings")["ok"]
    assert library.describe(second["keys"][0], "Before the trip")["ok"]
    for _ in range(3):
        library.autosave(NAME, GUID, "output", "Autosave: before Change", [])
    setups = {s["key"]: s for s in _row()["setups"]}
    assert setups[first["keys"][0]]["own"]
    assert setups[first["keys"][0]]["name"] == "Good bindings"
    assert setups[second["keys"][0]]["description"] == "Before the trip"
    assert len([s for s in setups.values() if not s["own"]]) == 2
    history = [line["text"] for line in setups[second["keys"][0]]["history"]]
    assert "Description edited" in history


def test_a_failed_write_refuses_the_autosave(
    lib: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    _module(lib["modules"])
    real = module_file.write_bytes

    def failing(path: Path, data: bytes) -> None:
        if Path(path).suffix == ".zip":
            raise OSError(28, "No space left on device")
        real(path, data)

    monkeypatch.setattr(library.module_file, "write_bytes", failing)
    out = library.autosave(NAME, GUID, "deleted", "Autosave: stick deleted", [])
    assert not out["ok"]
    assert out["error"].startswith("The autosave could not be kept")
    assert _row()["setups"] == []
    assert list(lib["folder"].rglob("*.zip")) == []


def test_a_pack_that_cant_be_read_back_refuses_the_autosave(
    lib: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    _module(lib["modules"])
    real = library._read_pack
    monkeypatch.setattr(
        library,
        "_read_pack",
        lambda data: "It is damaged." if isinstance(data, Path) else real(data),
    )
    out = library.autosave(NAME, GUID, "copy", "Autosave: before Copy from X", [])
    assert not out["ok"] and "read back" in out["error"]
    assert _row()["setups"] == []
    assert list(lib["folder"].rglob("*.zip")) == []


def test_a_damaged_module_file_is_autosaved_as_it_is(lib: dict) -> None:
    """S20a: the damaged file is kept byte for byte with the bindings, so
    Delete Device and Delete File always work for the stick."""
    path = _module(lib["modules"])
    raw = b"{ not json " + bytes([0xFF, 0x00]) + b" left as it was"
    path.write_bytes(raw)
    profile_path = _saved_profile(lib["tmp"], vjoy=1, buttons=2)
    out = library.autosave(
        NAME, GUID, "deleted", "Autosave: stick deleted", [profile_path]
    )
    assert out["ok"], out
    setup = out["setup"]
    assert setup["holds"] == ["setup_damaged", "bindings"]
    assert library.PART_LABELS["setup_damaged"] == "Setup (damaged file, kept as is)"
    assert setup["vjoys"] == {"1": 2}
    with zipfile.ZipFile(setup["pack"]) as zf:
        assert zf.read(library.DAMAGED_ENTRY + path.name) == raw
        doc = json.loads(zf.read("map.json"))
    # The pack's own map holds nothing from the damaged file: an import or
    # a Copy from it can only bring the bindings.
    assert "claim" not in doc and doc["damaged"]["file"] == path.name
    assert path.read_bytes() == raw  # the stick's file itself is untouched


def test_delete_file_autosave_of_a_damaged_file_keeps_it(lib: dict) -> None:
    path = _module(lib["modules"])
    path.write_text("{ not json", encoding="utf-8")
    out = library.autosave(
        NAME, GUID, "module_file", "Autosave: module file deleted", []
    )
    assert out["ok"], out
    assert out["setup"]["holds"] == ["setup_damaged"]


def test_a_damaged_file_that_doesnt_read_back_refuses_the_autosave(
    lib: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _module(lib["modules"])
    path.write_text("{ not json", encoding="utf-8")
    real = library.module_file.write_bytes

    def changed(dest: Path, data: bytes) -> None:
        if Path(dest).suffix == ".zip":
            blob = io.BytesIO()
            with (
                zipfile.ZipFile(io.BytesIO(data)) as src,
                zipfile.ZipFile(blob, "w") as out_zip,
            ):
                for name in src.namelist():
                    body = src.read(name)
                    if name.startswith(library.DAMAGED_ENTRY):
                        body = b"something else"
                    out_zip.writestr(name, body)
            data = blob.getvalue()
        real(dest, data)

    monkeypatch.setattr(library.module_file, "write_bytes", changed)
    out = library.autosave(NAME, GUID, "deleted", "Autosave: stick deleted", [])
    assert not out["ok"] and "read back" in out["error"]
    assert list(lib["folder"].rglob("*.zip")) == []


def test_saving_a_damaged_file_as_the_users_own_is_still_refused(lib: dict) -> None:
    path = _module(lib["modules"])
    path.write_text("{ not json", encoding="utf-8")
    out = library.save_setup(NAME, GUID, [])
    assert not out["ok"] and "damaged" in out["error"]


def test_delete_file_autosave_holds_setup_only(lib: dict) -> None:
    _module(lib["modules"])
    profile_path = _saved_profile(lib["tmp"])
    out = library.autosave(
        NAME, GUID, "module_file", "Autosave: module file deleted", [profile_path]
    )
    assert out["ok"], out
    (setup,) = out["setups"]
    assert setup["holds"] == ["setup"]
    assert setup["reason"] == "Autosave: module file deleted"


def test_an_unknown_trigger_is_refused(lib: dict) -> None:
    _module(lib["modules"])
    assert not library.autosave(NAME, GUID, "profile", "x", [])["ok"]


def test_autosave_keeps_one_setup_per_profile(lib: dict) -> None:
    _module(lib["modules"])
    first = _saved_profile(lib["tmp"], vjoy=1)
    second = first.with_name("Space.xml")
    second.write_bytes(first.read_bytes())
    out = library.autosave(
        NAME, GUID, "output", "Autosave: before Change", [first, second]
    )
    assert out["ok"], out
    assert [s["profiles"][0]["name"] for s in out["setups"]] == ["Flight", "Space"]


# --- names (S7) ----------------------------------------------------------------------


def test_renaming_a_set_up_device_renames_its_home_card(lib: dict) -> None:
    _module(lib["modules"])
    key = _row()["key"]
    assert library.rename(key, "Left Stick")["ok"]
    assert lib["aliases"][GUID] == "Left Stick"
    assert _by_key(key)["name"] == "Left Stick"
    assert library.describe(key, "The old one")["ok"]
    assert _by_key(key)["description"] == "The old one"


def test_an_empty_name_is_refused(lib: dict) -> None:
    _module(lib["modules"])
    assert not library.rename(_row()["key"], "  ")["ok"]


# --- delete (S15) ---------------------------------------------------------------------


def test_delete_keeps_a_set_up_device_and_removes_its_setups(lib: dict) -> None:
    _module(lib["modules"])
    library.save_setup(NAME, GUID, [])
    key = _row()["key"]
    out = library.delete(key)
    assert out["ok"] and out["notes"]
    assert library.device(key) is not None
    assert _by_key(key)["setups"] == []
    assert list(lib["folder"].rglob("*.zip")) == []


def test_delete_removes_a_deleted_device_and_a_single_setup(lib: dict) -> None:
    path = _module(lib["modules"])
    one = library.autosave(NAME, GUID, "deleted", "Autosave: stick deleted", [])
    two = library.autosave(NAME, GUID, "deleted", "Autosave: stick deleted", [])
    path.unlink()
    assert library.delete(one["keys"][0])["ok"]
    assert [s["key"] for s in _row()["setups"]] == two["keys"]
    assert library.delete(_row()["key"])["ok"]
    assert library.devices() == []


# --- packs from other people (S35, S14) -----------------------------------------------


def _foreign_pack(tmp: Path) -> Path:
    path = tmp / "Ann's Hornet stick.zip"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(
            "map.json",
            json.dumps(
                {
                    "device": "Hornet Grip",
                    "claim": {"buttons": [1]},
                    "pack": {
                        "exportedName": "Hornet Grip",
                        "exportedGuid": "{BBBBBBBB-1111-2222-3333-444455556666}",
                        "format": 2,
                        "author": "Ann",
                        "note": "My F/A-18 setup",
                    },
                }
            ),
        )
        zf.writestr(
            "wires.json",
            json.dumps(
                {
                    "modes": [
                        {"name": "Combat", "lines": ["Button 1 → vJoy 3 Button 1"]}
                    ],
                    "actions": [],
                    "tree": {"Combat": ""},
                }
            ),
        )
    return path


def test_someone_elses_pack_becomes_a_not_connected_device(lib: dict) -> None:
    out = library.import_pack(_foreign_pack(lib["tmp"]))
    assert out["ok"], out
    setup = out["setup"]
    assert setup["origin"] == "pack" and not setup["own"]
    assert setup["reason"] == "From Ann's pack"
    assert setup["description"] == "My F/A-18 setup"
    assert setup["holds"] == ["setup", "bindings"]
    assert setup["vjoys"] == {"3": 1}
    row = _row("Hornet Grip")
    assert row["state"] == "not_connected"
    assert row["setups"][0]["key"] == setup["key"]
    # Kept in the library folder, not where it was dropped from.
    assert lib["folder"] in Path(setup["pack"]).parents


def test_a_pack_goes_under_its_device_when_the_library_has_it(lib: dict) -> None:
    _module(lib["modules"], "Hornet Grip", "{BBBBBBBB-1111-2222-3333-444455556666}")
    library.import_pack(_foreign_pack(lib["tmp"]))
    assert len(library.devices()) == 1
    assert _row("Hornet Grip")["module"]


def test_a_file_that_isnt_a_pack_is_refused(lib: dict) -> None:
    bad = lib["tmp"] / "notes.zip"
    bad.write_bytes(b"not a zip")
    assert not library.import_pack(bad)["ok"]
    assert library.devices() == []


def test_export_writes_the_pack_and_refuses_the_modules_folder(lib: dict) -> None:
    _module(lib["modules"])
    key = library.save_setup(NAME, GUID, [])["keys"][0]
    out = library.export_setup(key, lib["tmp"] / "share" / "mine")
    assert out["ok"], out
    assert (lib["tmp"] / "share" / "mine.zip").is_file()
    assert not library.export_setup(key, lib["modules"] / "x.zip")["ok"]
    history = [line["text"] for line in _row()["setups"][0]["history"]]
    assert "Exported to mine.zip" in history


# --- search, tidy, size, settings, last change ----------------------------------------


def test_search_matches_names_contents_profiles_modes_vjoy_and_reasons(
    lib: dict,
) -> None:
    _module(lib["modules"])
    saved = library.save_setup(NAME, GUID, [_saved_profile(lib["tmp"], vjoy=2)])
    auto = library.autosave(NAME, GUID, "swap", "Autosave: before Swap with Bob", [])
    device_key = _row()["key"]
    setup_key = saved["keys"][0]
    assert library.search("stick a") == [device_key]
    assert library.search("flight") == [device_key, setup_key]
    assert library.search("vjoy 2") == [device_key, setup_key]
    assert library.search("default") == [device_key, setup_key]
    assert library.search("calibration") == [device_key, auto["keys"][0], setup_key]
    assert library.search("swap with bob") == [device_key, auto["keys"][0]]
    assert library.search("nothing like it") == []


def test_tidy_lists_old_autosaves_and_empty_deleted_devices(
    lib: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _module(lib["modules"])
    old = library.autosave(NAME, GUID, "copy", "Autosave: before Copy", [])
    own = library.save_setup(NAME, GUID, [])
    # Six months later.
    library.clock.now.at += 183 * 86400  # type: ignore[attr-defined]
    new = library.autosave(NAME, GUID, "copy", "Autosave: before Copy", [])
    assert [row["key"] for row in library.tidy_preview(3)] == old["keys"]
    assert library.tidy_preview(12) == []
    assert library.tidy(old["keys"] + own["keys"])["warnings"]
    keys = [s["key"] for s in _row()["setups"]]
    assert keys == new["keys"] + own["keys"]
    # A deleted device with no saved setups is listed too.
    path.unlink()
    library.delete(new["keys"][0])
    library.delete(own["keys"][0])
    library.set_settings({})  # no change
    with library._editing() as doc:
        doc["devices"][0]["kind"] = "deleted"
    preview = library.tidy_preview(3)
    assert [row["key"] for row in preview] == [_row()["key"]]
    assert library.tidy([preview[0]["key"]])["removed"] == 1
    assert library.devices() == []


def test_size_counts_the_library_folder(lib: dict) -> None:
    assert library.size_bytes() == 0
    _module(lib["modules"])
    library.save_setup(NAME, GUID, [])
    total = sum(p.stat().st_size for p in lib["folder"].rglob("*") if p.is_file())
    assert library.size_bytes() == total > 0


def test_settings_default_and_change(lib: dict) -> None:
    values = library.settings()
    assert values["keep"] == 10
    assert values["default_parts"] == ["setup", "button_map", "appearance", "bindings"]
    assert values["folder"] == str(lib["folder"])
    library.set_settings({"keep": 4, "default_parts": ["bindings", "calibration"]})
    values = library.settings()
    assert values["keep"] == 4
    assert values["default_parts"] == ["calibration", "bindings"]


def test_last_change_survives_a_reload(lib: dict) -> None:
    assert library.last_change() is None
    library.set_last_change("swap", ["set-1", "set-2"], "Swap Stick A and Stick B")
    # Read again from library.json, as after a restart.
    doc = json.loads((lib["folder"] / "library.json").read_text(encoding="utf-8"))
    assert doc["lastChange"]["autosaves"] == ["set-1", "set-2"]
    change = library.last_change()
    assert change is not None
    assert change["op"] == "swap" and change["label"] == "Swap Stick A and Stick B"
    assert change["at"]


def test_a_damaged_library_list_is_never_written_over(lib: dict) -> None:
    _module(lib["modules"])
    lib["folder"].mkdir(parents=True)
    (lib["folder"] / "library.json").write_text("{ broken", encoding="utf-8")
    out = library.autosave(NAME, GUID, "copy", "Autosave: before Copy", [])
    assert not out["ok"]
    assert (lib["folder"] / "library.json").read_text(encoding="utf-8") == "{ broken"


def test_the_open_profiles_bindings_are_read_in_memory(lib: dict) -> None:
    _module(lib["modules"])
    path = _saved_profile(lib["tmp"], vjoy=4, buttons=2)
    opened = Profile()
    opened.from_xml(path)
    shared_state.current_profile = opened
    path.unlink()  # only the open profile in memory has the bindings now
    out = library.save_setup(NAME, GUID, [path])
    assert out["ok"], out
    assert out["setups"][0]["vjoys"] == {"4": 2}
    assert shared_state.current_profile is opened
