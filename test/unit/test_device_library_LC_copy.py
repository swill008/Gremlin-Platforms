# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device Library: Copy to Another Stick, Change vJoy Output and Undo
(10 S22-S25, S30-S33, S41), on the real Device Pack import and the real
profile Batch. The Library store is a small fake here: a saved setup is a
pack on disk, an autosave is the stick's pack made now."""

from __future__ import annotations

import shutil
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

from gremlin import (
    device_initialization,
    library_copy,
    plugin_manager,
    shared_state,
    util,
)
from gremlin import device_library as library
from gremlin.modules import module_file, registry
from gremlin.modules import store as module_store
from gremlin.profile import DeviceInfo, Profile
from gremlin.types import InputType
from gremlin.ui import device_pack

_OTHER = uuid.UUID("11111111-2222-3333-4444-555555555555")


def _stick() -> tuple[str, uuid.UUID]:
    for dev in device_initialization.physical_devices():
        if dev.name == "pJoy Pro":
            return dev.name, dev.device_guid.uuid
    pytest.skip("the fake stick is not there")


def _own_path(name: str) -> Path:
    return util.modules_dir() / f"{registry.plain_slug(name) or 'device'}.json"


def _map(
    profile: Profile,
    uid: uuid.UUID,
    button: int,
    mode: str,
    vjoy: int,
    out: int,
    nested: bool = False,
) -> None:
    action = profile.library.create("Map to vJoy", InputType.JoystickButton)
    assert action is not None
    action.vjoy_device_id = vjoy  # type: ignore[attr-defined]
    action.vjoy_input_id = out  # type: ignore[attr-defined]
    action.vjoy_input_type = InputType.JoystickButton  # type: ignore[attr-defined]
    item = profile.get_input_item(
        uid, InputType.JoystickButton, button, mode, create_if_missing=True
    )
    assert item is not None
    root = item.add_item_binding().root_action
    assert root is not None
    if nested:
        tempo = profile.library.create("Tempo", InputType.JoystickButton)
        assert tempo is not None
        tempo.insert_action(action, "short")
        root.insert_action(tempo, "children")
    else:
        root.insert_action(action, "children")


def _targets(profile: Profile, uid: uuid.UUID, mode: str) -> dict[int, tuple[int, int]]:
    from gremlin.profile import reachable

    out = {}
    for item in profile.inputs.get(uid, []):
        if item.mode != mode:
            continue
        for action in reachable(Profile.roots_of([item])):
            if getattr(action, "tag", "") == "map-to-vjoy":
                out[item.input_id] = (action.vjoy_device_id, action.vjoy_input_id)  # type: ignore[attr-defined]
    return out


def _new_profile(name: str, uid: uuid.UUID) -> Profile:
    profile = Profile()
    shared_state.current_profile = profile
    profile.device_database.devices[uid] = DeviceInfo(uid, name)
    profile.device_database.devices[_OTHER] = DeviceInfo(_OTHER, "Other Stick")
    return profile


class FakeLibrary:
    """The Library store's contract (devices, pack_path, autosave,
    add_history, set_last_change, last_change) on a temp folder."""

    def __init__(self, folder: Path) -> None:
        self.folder = folder
        self.devs: list[dict] = []
        self.history: list[tuple[str, str]] = []
        self.last: dict | None = None
        self.refuse = False
        self.autosaves: list[tuple[str, str, str, list[Path]]] = []

    def device_for(self, name: str, guid: str) -> dict:
        for dev in self.devs:
            if dev["name"] == name and dev["guid"] == guid:
                return dev
        dev = {"key": f"dev-{len(self.devs)}", "name": name, "guid": guid, "setups": []}
        self.devs.append(dev)
        return dev

    def add(
        self,
        name: str,
        guid: str,
        pack: bytes,
        holds: list[str],
        profiles: list[Path],
        origin: str = "user",
    ) -> dict:
        dev = self.device_for(name, guid)
        key = f"set-{sum(len(d['setups']) for d in self.devs)}"
        path = self.folder / f"{key}.zip"
        path.write_bytes(pack)
        setup = {
            "key": key,
            "device": dev["key"],
            "name": key,
            "origin": origin,
            "holds": holds,
            "pack": str(path),
            "profiles": [
                {"name": p.stem, "path": str(p), "modes": [], "actions": 0}
                for p in profiles
            ],
        }
        dev["setups"].insert(0, setup)
        return setup

    def autosave(
        self, name: str, guid: str, trigger: str, reason: str, profiles: list[Path]
    ) -> dict:
        self.autosaves.append((name, trigger, reason, list(profiles)))
        if self.refuse:
            return {"ok": False, "error": "disk full", "warnings": [], "notes": []}
        built = device_pack.assemble(name, lambda stored: None, None, None)
        assert not isinstance(built, str), built
        setup = self.add(
            name, guid, built[0], list(library.PARTS), profiles, "autosave"
        )
        return {"ok": True, "error": "", "warnings": [], "notes": [], "setups": [setup]}

    def pack_path(self, key: str) -> Path:
        for dev in self.devs:
            for setup in dev["setups"]:
                if setup["key"] == key:
                    return Path(setup["pack"])
        raise KeyError(key)

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(library, "devices", lambda: self.devs)
        monkeypatch.setattr(library, "pack_path", self.pack_path)
        monkeypatch.setattr(library, "autosave", self.autosave)
        monkeypatch.setattr(
            library, "add_history", lambda k, t: self.history.append((k, t))
        )
        monkeypatch.setattr(library, "set_last_change", self.set_last)
        monkeypatch.setattr(library, "last_change", lambda: self.last)

    def set_last(
        self,
        op: str,
        keys: list[str],
        label: str,
        detail: dict | None = None,
        *,
        undone: bool = False,
    ) -> None:
        self.last = {
            "op": op,
            "autosaves": list(keys),
            "label": label,
            "at": "",
            "undone": undone,
        }


@pytest.fixture
def lib(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[dict]:
    name, uid = _stick()
    modules = util.modules_dir()
    modules.mkdir(parents=True, exist_ok=True)
    aside = tmp_path / "aside"
    aside.mkdir()
    for old in modules.glob("*.json"):
        shutil.move(str(old), str(aside / old.name))
    before = {p.name for p in modules.iterdir()}
    bindings = module_store.bindings()
    module_store.set_bindings({})
    fake = FakeLibrary(tmp_path)
    fake.install(monkeypatch)
    try:
        yield _setup(tmp_path, name, uid, fake)
    finally:
        shared_state.current_profile = None
        for extra in modules.iterdir():
            if extra.name in before:
                continue
            if extra.is_dir():
                shutil.rmtree(extra, ignore_errors=True)
            else:
                extra.unlink(missing_ok=True)
        for old in aside.iterdir():
            shutil.move(str(old), str(modules / old.name))
        module_store.set_bindings(bindings)


def _module(name: str, buttons: list[int], row_height: int) -> dict:
    return {
        "kind": "control.hardware",
        "device": name,
        "direction": "source",
        "claim": {
            "buttons": buttons,
            "axes": [],
            "hats": [],
            "keys": [],
            "friendly": {},
        },
        "catalog": {"rowHeight": row_height},
        "nodes": [],
    }


def _setup(tmp_path: Path, name: str, uid: uuid.UUID, fake: FakeLibrary) -> dict:
    # The saved setup: an old stick's pack (made here as pJoy Pro, kept
    # under "Old Stick" in the Library).
    module_file.write_json(_own_path(name), _module(name, [1, 2], 40))
    source = _new_profile(name, uid)
    source.modes.add_mode("Combat")
    _map(source, uid, 1, "Default", 2, 1)
    _map(source, uid, 2, "Combat", 2, 2)
    _map(source, uid, 99, "Default", 2, 3)  # this stick has no button 99
    built = device_pack.assemble(name, lambda stored: None, None, None)
    assert not isinstance(built, str), built
    setup = fake.add("Old Stick", "", built[0], list(library.PARTS), [])
    # This PC: the stick's own module file and bindings.
    module_file.write_json(_own_path(name), _module(name, [3], 20))
    module_file.write_json(_own_path("Other Stick"), _module("Other Stick", [1], 30))
    target = _new_profile(name, uid)
    target.modes.add_mode("Landing")
    _map(target, uid, 3, "Default", 1, 3)
    _map(target, uid, 4, "Landing", 1, 4)
    _map(target, _OTHER, 1, "Default", 2, 5)
    target.mark_clean()
    return {
        "name": name,
        "uid": uid,
        "guid": str(uid),
        "setup": setup,
        "fake": fake,
        "profile": target,
        "pack": Path(setup["pack"]),
        "tmp": tmp_path,
    }


_ALL = ["setup", "button_map", "appearance", "bindings"]


def _doc(name: str) -> dict:
    import json

    return json.loads(_own_path(name).read_text(encoding="utf-8"))


def test_copy_puts_the_setup_on_the_stick_and_leaves_the_source(lib: dict) -> None:
    name, uid, profile = lib["name"], lib["uid"], lib["profile"]
    source_bytes = lib["pack"].read_bytes()
    result = library_copy.copy(
        lib["setup"]["key"], name, lib["guid"], _ALL, [Path("")], ["Default", "Combat"]
    )
    assert result["ok"], result
    # Ticked modes replaced (button 99 left out), others stay (S24).
    assert _targets(profile, uid, "Default") == {1: (2, 1)}
    assert _targets(profile, uid, "Combat") == {2: (2, 2)}
    assert _targets(profile, uid, "Landing") == {4: (1, 4)}
    assert _targets(profile, _OTHER, "Default") == {1: (2, 5)}
    # Module file: checks added, appearance replaced.
    doc = _doc(name)
    assert doc["catalog"] == {"rowHeight": 40}
    assert set(doc["claim"]["buttons"]) >= {1, 2, 3}
    # The source never changes; history and the last change are kept.
    assert lib["pack"].read_bytes() == source_bytes
    fake = lib["fake"]
    assert fake.autosaves[0][1:3] == ("copy", "Autosave: before Copy from Old Stick")
    assert fake.history == [(lib["setup"]["key"], f"Copied to {name}")]
    assert fake.last["op"] == "copy" and fake.last["autosaves"] == result["autosaves"]
    # The Device Pack window's Undo Import is not the way back.
    assert not device_pack.can_undo_import()


def test_copy_refuses_a_stick_that_is_not_plugged_in(lib: dict) -> None:
    before = _own_path(lib["name"]).read_bytes()
    result = library_copy.copy(
        lib["setup"]["key"],
        "Gone Stick",
        str(uuid.uuid4()),
        _ALL,
        [Path("")],
        ["Default"],
    )
    assert not result["ok"] and "plugged in" in result["error"]
    assert lib["fake"].autosaves == []
    assert _own_path(lib["name"]).read_bytes() == before


def test_copy_refuses_when_the_autosave_fails(lib: dict) -> None:
    lib["fake"].refuse = True
    before = _own_path(lib["name"]).read_bytes()
    result = library_copy.copy(
        lib["setup"]["key"], lib["name"], lib["guid"], _ALL, [Path("")], ["Default"]
    )
    assert not result["ok"] and "autosave" in result["error"]
    assert _own_path(lib["name"]).read_bytes() == before
    assert _targets(lib["profile"], lib["uid"], "Default") == {3: (1, 3)}
    assert lib["fake"].last is None


def test_plan_copy_lists_what_the_target_lacks(lib: dict) -> None:
    plan = library_copy.plan_copy(
        lib["setup"]["key"], lib["name"], lib["guid"], _ALL, [Path("")], ["Default"]
    )
    assert plan["ok"], plan
    assert any("Button 99" in w for w in plan["warnings"]), plan["warnings"]
    assert "wire:Default" in plan["items"] and "wire:Combat" not in plan["items"]


def test_copy_into_a_saved_profile_that_is_not_open(lib: dict) -> None:
    name, uid = lib["name"], lib["uid"]
    saved_path = lib["tmp"] / "other.xml"
    saved = Profile()
    saved.device_database.devices[uid] = DeviceInfo(uid, name)
    _map(saved, uid, 3, "Default", 1, 9)
    saved.to_xml(saved_path)
    open_profile = lib["profile"]
    shared_state.current_profile = open_profile
    result = library_copy.copy(
        lib["setup"]["key"], name, lib["guid"], ["bindings"], [saved_path], ["Default"]
    )
    assert result["ok"], result
    again = Profile()
    again.from_xml(saved_path)
    assert _targets(again, uid, "Default") == {1: (2, 1)}
    # The open profile wasn't ticked: as it was.
    assert _targets(open_profile, uid, "Default") == {3: (1, 3)}
    assert shared_state.current_profile is open_profile


def test_undo_puts_the_copy_back(lib: dict) -> None:
    name, uid, profile = lib["name"], lib["uid"], lib["profile"]
    before = _doc(name)
    assert library_copy.copy(
        lib["setup"]["key"], name, lib["guid"], _ALL, [Path("")], ["Default", "Combat"]
    )["ok"]
    result = library_copy.undo_last()
    assert result["ok"], result
    assert _targets(profile, uid, "Default") == {3: (1, 3)}
    assert _targets(profile, uid, "Landing") == {4: (1, 4)}
    assert _targets(profile, uid, "Combat") == {}
    after = _doc(name)
    assert after["claim"]["buttons"] == before["claim"]["buttons"]
    assert after["catalog"] == before["catalog"]
    fake = lib["fake"]
    assert fake.autosaves[-1][2] == "Autosave: before Undo"
    assert fake.last["op"] == "copy" and fake.last["undone"] is True


def test_undo_with_nothing_to_undo(lib: dict) -> None:
    result = library_copy.undo_last()
    assert not result["ok"] and "nothing to undo" in result["error"]


def test_change_output_renumbers_nested_actions_and_swaps_the_other(lib: dict) -> None:
    name, uid, profile = lib["name"], lib["uid"], lib["profile"]
    _map(profile, uid, 5, "Default", 1, 7, nested=True)
    plan = library_copy.plan_output(name, lib["guid"], {1: 2}, True, [Path("")])
    assert plan["ok"], plan
    assert {r["vjoy"]: (r["inputs"], r["text"]) for r in plan["rows"]} == {
        1: (3, "changes")
    }
    assert [(o["name"], o["vjoy"], o["to"]) for o in plan["others"]] == [
        ("Other Stick", 2, 1)
    ]
    result = library_copy.change_output(name, lib["guid"], {1: 2}, True, [Path("")])
    assert result["ok"], result
    assert _targets(profile, uid, "Default") == {3: (2, 3), 5: (2, 7)}
    assert _targets(profile, uid, "Landing") == {4: (2, 4)}
    assert _targets(profile, _OTHER, "Default") == {1: (1, 5)}
    fake = lib["fake"]
    assert [a[0] for a in fake.autosaves] == [name, "Other Stick"]
    assert fake.autosaves[0][2] == "Autosave: before Change vJoy Output (vJoy 1 → 2)"
    assert fake.last["op"] == "output" and len(fake.last["autosaves"]) == 2


def test_change_output_without_the_swap_leaves_the_other(lib: dict) -> None:
    name, uid, profile = lib["name"], lib["uid"], lib["profile"]
    result = library_copy.change_output(name, lib["guid"], {1: 3}, False, [Path("")])
    assert result["ok"], result
    assert _targets(profile, uid, "Default") == {3: (3, 3)}
    assert _targets(profile, _OTHER, "Default") == {1: (2, 5)}
    assert [a[0] for a in lib["fake"].autosaves] == [name]


def test_change_output_warns_about_unclaimed_outputs_and_scripts(
    lib: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.modules import output

    monkeypatch.setattr(output, "vjoy_allows", lambda vid, kind, number: number != 4)
    script = lib["tmp"] / "mine.py"
    script.write_text("x = vjoy[1].button(2)\n", encoding="utf-8")
    profile = lib["profile"]
    profile.scripts.add_script(script)
    plan = library_copy.plan_output(lib["name"], lib["guid"], {1: 2}, False, [Path("")])
    text = "\n".join(plan["warnings"])
    assert "Button 4" in text and "doesn't claim" in text
    assert "mine" in text and "vJoy 1" in text and "check it yourself" in text


def test_change_output_refuses_when_an_autosave_fails(lib: dict) -> None:
    lib["fake"].refuse = True
    result = library_copy.change_output(
        lib["name"], lib["guid"], {1: 2}, False, [Path("")]
    )
    assert not result["ok"]
    assert _targets(lib["profile"], lib["uid"], "Default") == {3: (1, 3)}


def test_undo_puts_a_change_output_back(lib: dict) -> None:
    name, uid, profile = lib["name"], lib["uid"], lib["profile"]
    assert library_copy.change_output(name, lib["guid"], {1: 2}, True, [Path("")])["ok"]
    result = library_copy.undo_last()
    assert result["ok"], result
    assert _targets(profile, uid, "Default") == {3: (1, 3)}
    assert _targets(profile, uid, "Landing") == {4: (1, 4)}
    assert _targets(profile, _OTHER, "Default") == {1: (2, 5)}


def test_pack_import_goes_into_a_given_profile_without_undo_import(lib: dict) -> None:
    """device_pack.apply_zip(profile=..., record_undo=False): the Device
    Library imports into a profile that isn't the open one and leaves the
    window's Undo Import alone."""
    name, uid = lib["name"], lib["uid"]
    other = Profile()
    other.device_database.devices[uid] = DeviceInfo(uid, name)
    open_profile = lib["profile"]
    result = device_pack.apply_zip(
        lib["pack"], name, {"items": ["wire:Default"]}, other, record_undo=False
    )
    assert result["ok"], result
    assert _targets(other, uid, "Default") == {1: (2, 1)}
    assert _targets(open_profile, uid, "Default") == {3: (1, 3)}
    assert not device_pack.can_undo_import()


def test_pack_item_ids_match_the_window(lib: dict) -> None:
    ids = device_pack.pack_item_ids(lib["pack"])
    assert not isinstance(ids, str)
    assert "in.checks" in ids["input"] and "in.catalog" in ids["input"]
    assert ids["modes"] == ["Combat", "Default"] or set(ids["modes"]) == {
        "Combat",
        "Default",
    }


_ = plugin_manager  # the plugins are loaded by conftest


_REAL = {
    name: getattr(library, name)
    for name in (
        "devices",
        "pack_path",
        "autosave",
        "add_history",
        "set_last_change",
        "last_change",
    )
}


def test_copy_and_undo_with_the_real_library(
    lib: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The same path on the real Library store (library.json in a temp folder)."""
    for name, real in _REAL.items():
        monkeypatch.setattr(library, name, real)
    monkeypatch.setattr(library, "folder", lambda: lib["tmp"] / "device library")
    name, uid, profile = lib["name"], lib["uid"], lib["profile"]
    profile_path = lib["tmp"] / "mine.xml"
    profile.to_xml(profile_path)
    profile.fpath = profile_path  # open, as File > Open leaves it
    imported = library.import_pack(lib["pack"])
    assert imported["ok"], imported
    setup_key = imported["setup"]["key"]
    before = _doc(name)
    result = library_copy.copy(
        setup_key, name, lib["guid"], _ALL, [profile_path], ["Default", "Combat"]
    )
    assert result["ok"], result
    assert _targets(profile, uid, "Default") == {1: (2, 1)}
    last = library.last_change()
    assert last and last["op"] == "copy" and last["autosaves"] == result["autosaves"]
    undone = library_copy.undo_last()
    assert undone["ok"], undone
    assert _targets(profile, uid, "Default") == {3: (1, 3)}
    assert _targets(profile, uid, "Combat") == {}
    assert _doc(name)["catalog"] == before["catalog"]
    assert library.last_change()["undone"] is True


def test_a_damaged_module_file_is_never_copied_to_another_stick(lib: dict) -> None:
    """10 S20a: from a setup holding a damaged module file, only bindings copy."""
    name, uid, profile = lib["name"], lib["uid"], lib["profile"]
    lib["setup"]["holds"] = ["setup_damaged", "bindings"]
    before = _own_path(name).read_bytes()
    refused = library_copy.copy(
        lib["setup"]["key"], name, lib["guid"], ["setup", "appearance"], [Path("")], []
    )
    assert not refused["ok"] and "damaged" in refused["error"]
    plan = library_copy.plan_copy(
        lib["setup"]["key"], name, lib["guid"], _ALL, [Path("")], ["Default"]
    )
    assert any("damaged" in w for w in plan["warnings"])
    result = library_copy.copy(
        lib["setup"]["key"], name, lib["guid"], _ALL, [Path("")], ["Default"]
    )
    assert result["ok"], result
    assert _own_path(name).read_bytes() == before
    assert _targets(profile, uid, "Default") == {1: (2, 1)}


def test_a_pack_is_built_from_a_profile_that_is_not_open(lib: dict) -> None:
    """device_pack.assemble(profile=..., guid=...): the Library's autosave
    of a profile that isn't open, without swapping the open one."""
    name, uid = lib["name"], lib["uid"]
    other = Profile()
    other.device_database.devices[uid] = DeviceInfo(uid, name)
    _map(other, uid, 7, "Default", 3, 8)
    built = device_pack.assemble(
        name, lambda stored: None, None, None, profile=other, guid=str(uid)
    )
    assert not isinstance(built, str), built
    path = lib["tmp"] / "other.zip"
    path.write_bytes(built[0])
    fresh = Profile()
    result = device_pack.apply_zip(
        path, name, {"items": ["wire:Default"]}, fresh, record_undo=False
    )
    assert result["ok"], result
    assert _targets(fresh, uid, "Default") == {7: (3, 8)}
    assert shared_state.current_profile is lib["profile"]
