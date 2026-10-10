# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Device Library fix wave (agent FX), from the independent re-trace:

- a stick renamed on Home is found by its device id, never by the shown
  name (S7, S12, S22, S26);
- the autosave limit never removes what an action or Undo needs (S19, S20,
  S41);
- Undo after Copy is exact: what the stick didn't have goes again (S25, S41);
- Undo after Swap moves everything back, references too (S28, S41);
- Move… is refused into the library's own subfolder (S36);
- the last change's label describes the change (S41).

On the real Library store (library.json in a temp folder), the real Device
Pack import and the real profile Batch."""

# The fixtures lib and sticks come from LC's and LW's tests.
# ruff: noqa: F811

from __future__ import annotations

import json
import pathlib
import uuid
from pathlib import Path

import pytest

import gremlin.profile
from gremlin import (
    device_initialization,
    library_copy,
    library_swap,
    shared_state,
    swap_devices,
    util,
)
from gremlin import device_library as library
from gremlin.modules import registry, store
from gremlin.profile import Profile
from gremlin.ui import device_pack
from test.unit.test_device_library_LC_copy import (  # noqa: F401 - the fixture
    _ALL,
    _REAL,
    _map,
    _own_path,
    _targets,
    lib,
)
from test.unit.test_device_library_LW_swap import (  # noqa: F401 - the fixture
    ALL,
    LEFT,
    LEFT_ID,
    RIGHT,
    RIGHT_ID,
    _where,
    sticks,
)
from test.unit.test_twin_devices import (  # noqa: F401 - the fixtures
    _app,
    _first_guid,
    _twin_guid,
    twins,
)
from test.unit.test_twin_devices import _module as _twin_module


def _real_library(lib: dict, monkeypatch: pytest.MonkeyPatch) -> Path:
    for name, real in _REAL.items():
        monkeypatch.setattr(library, name, real)
    folder = lib["tmp"] / "device library"
    monkeypatch.setattr(library, "folder", lambda: folder)
    return folder


def _saved_open(lib: dict) -> Path:
    """The open profile saved to disk (as File > Open leaves it)."""
    profile = lib["profile"]
    path = lib["tmp"] / "mine.xml"
    profile.to_xml(path)
    profile.fpath = path
    return path


# --- Gap 1: the shown name is not the stick (S7, S12, S22, S26) ---


def test_autosave_of_a_renamed_stick_holds_its_module_file(
    lib: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The window passes the Home card's name; the guid finds the file."""
    _real_library(lib, monkeypatch)
    answer = library.autosave(
        "My Renamed Stick", lib["guid"], "copy", "Autosave: before Copy from X", []
    )
    assert answer["ok"], answer
    assert "setup" in answer["setup"]["holds"], answer["setup"]["holds"]
    saved = library.save_setup("My Renamed Stick", lib["guid"], [])
    assert saved["ok"] and "setup" in saved["setup"]["holds"], saved


def test_a_device_row_carries_its_own_name(
    lib: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The window shows the Home card's name and passes ownName + guid."""
    _real_library(lib, monkeypatch)
    monkeypatch.setattr(library, "_alias", lambda guid, default: "My Renamed Stick")
    row = library.find_device("My Renamed Stick", lib["guid"])
    assert row is not None
    assert row["name"] == "My Renamed Stick"
    assert row["ownName"] == lib["name"]


def test_copy_onto_a_renamed_stick(lib: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    _real_library(lib, monkeypatch)
    name = lib["name"]
    # Renamed on Home (its alias): the label names it so (S17, S41).
    want = lib["guid"].lower()
    monkeypatch.setattr(
        library,
        "_alias",
        lambda guid, default: "My Renamed Stick" if guid.lower() == want else default,
    )
    imported = library.import_pack(lib["pack"])
    assert imported["ok"], imported
    stray = _own_path("My Renamed Stick")
    result = library_copy.copy(
        imported["setup"]["key"],
        "My Renamed Stick",
        lib["guid"],
        _ALL,
        [Path("")],
        ["Default"],
    )
    assert result["ok"], result
    doc = json.loads(_own_path(name).read_text(encoding="utf-8"))
    assert doc["view"] == {"rowHeight": 40}
    assert not stray.exists()
    assert (
        library.last_change()["label"]
        == f"Copy {imported['setup']['name']} to My Renamed Stick"
    )


@pytest.fixture
def renamed(sticks: dict, monkeypatch: pytest.MonkeyPatch) -> dict:
    """LW's two sticks, set up and plugged in, with the store finding module
    files by name only (as store.path_for does for a name that isn't the
    stick's own)."""
    own = {"Left stick": "left", "Right stick": "right"}
    monkeypatch.setattr(
        store,
        "path_for",
        lambda name, guid="": store.path_of(own.get(name) or registry.plain_slug(name)),
    )
    monkeypatch.setattr(library, "_connected", lambda: [LEFT, RIGHT])
    monkeypatch.setattr(
        library,
        "_set_up",
        lambda: [("Left stick", LEFT_ID, "left"), ("Right stick", RIGHT_ID, "right")],
    )
    return sticks


def test_swap_of_renamed_sticks_changes_their_own_files(
    renamed: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Renamed on Home (their aliases): the label names them so (S17, S41).
    names = {LEFT_ID: "My Left", RIGHT_ID: "My Right"}
    monkeypatch.setattr(
        library, "_alias", lambda guid, default: names.get(guid, default)
    )
    result = library_swap.swap(
        ("My Left", LEFT_ID), ("My Right", RIGHT_ID), ["appearance"], []
    )
    assert result["ok"], result
    left = json.loads(store.path_of("left").read_text(encoding="utf-8"))
    # Appearance only: the Output View moves; the layout stays (setup).
    assert "view" not in left and "layout" not in left
    right = json.loads(store.path_of("right").read_text(encoding="utf-8"))
    assert right["view"] == {"layout": "left view"}
    assert not store.path_of("my-left").exists()
    assert not store.path_of("my-right").exists()
    assert result["label"] == "Swap My Left with My Right"


# --- Gap 2: the limit never removes what is needed (S19, S20, S41) ---


def _flight(lib: dict, name: str) -> Path:
    path = lib["tmp"] / f"{name}.xml"
    profile = Profile()
    profile.device_database.devices[lib["uid"]] = gremlin.profile.DeviceInfo(
        lib["uid"], lib["name"]
    )
    _map(profile, lib["uid"], 1, "Default", 1, 1)
    profile.to_xml(path)
    shared_state.current_profile = lib["profile"]
    return path


def test_an_action_with_more_profiles_than_the_limit_keeps_them_all(
    lib: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    _real_library(lib, monkeypatch)
    library.set_settings({"keep": 1})
    paths = [_flight(lib, "one"), _flight(lib, "two")]
    answer = library.autosave(lib["name"], lib["guid"], "copy", "Autosave: x", paths)
    assert answer["ok"], answer
    assert len(answer["keys"]) == 2
    for key in answer["keys"]:
        assert library.pack_path(key).is_file()


def test_the_limit_never_removes_the_last_changes_autosaves(
    lib: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    _real_library(lib, monkeypatch)
    library.set_settings({"keep": 1})
    first = library.autosave(lib["name"], lib["guid"], "copy", "Autosave: a", [])
    assert first["ok"], first
    library.set_last_change("copy", first["keys"], "Copy a")
    second = library.autosave(lib["name"], lib["guid"], "copy", "Autosave: b", [])
    assert second["ok"], second
    assert library.pack_path(first["keys"][0]).is_file()
    # A third: the second (not Undo's way back) goes, the first stays.
    third = library.autosave(lib["name"], lib["guid"], "copy", "Autosave: c", [])
    assert third["ok"], third
    with pytest.raises(KeyError):
        library.pack_path(second["keys"][0])
    assert library.pack_path(first["keys"][0]).is_file()


def test_undo_with_keep_one_puts_the_copy_back(
    lib: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Undo's own "before Undo" autosave never removes the one it restores."""
    _real_library(lib, monkeypatch)
    library.set_settings({"keep": 1})
    path = _saved_open(lib)
    imported = library.import_pack(lib["pack"])
    result = library_copy.copy(
        imported["setup"]["key"], lib["name"], lib["guid"], _ALL, [path], ["Default"]
    )
    assert result["ok"], result
    undone = library_copy.undo_last()
    assert undone["ok"], undone
    assert _targets(lib["profile"], lib["uid"], "Default") == {3: (1, 3)}


def test_undo_and_restore_never_raise_on_a_missing_pack(
    lib: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    _real_library(lib, monkeypatch)
    path = _saved_open(lib)
    imported = library.import_pack(lib["pack"])
    assert library_copy.copy(
        imported["setup"]["key"], lib["name"], lib["guid"], _ALL, [path], ["Default"]
    )["ok"]
    keys = library.last_change()["autosaves"]

    def gone(key: str) -> Path:
        raise KeyError(key)

    monkeypatch.setattr(library, "pack_path", gone)
    undone = library_copy.undo_last()
    assert not undone["ok"] and undone["error"]
    restored = library_copy.restore(keys[0])
    assert not restored["ok"] and restored["error"]
    # Nothing was changed by the refused Undo.
    assert _targets(lib["profile"], lib["uid"], "Default") == {1: (2, 1)}


# --- Gap 4: Undo after Copy is exact (S25, S41) ---


def test_undo_of_a_copy_onto_a_new_stick_leaves_it_new(
    lib: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No module file and no bindings before the copy: none after Undo."""
    _real_library(lib, monkeypatch)
    profile, uid = lib["profile"], lib["uid"]
    profile.drop_inputs(uid, list(profile.inputs.get(uid, [])))
    _own_path(lib["name"]).unlink()
    path = _saved_open(lib)
    imported = library.import_pack(lib["pack"])
    result = library_copy.copy(
        imported["setup"]["key"],
        lib["name"],
        lib["guid"],
        _ALL,
        [path],
        ["Default", "Combat"],
    )
    assert result["ok"], result
    assert _targets(profile, uid, "Default") == {1: (2, 1)}
    assert _own_path(lib["name"]).is_file()
    undone = library_copy.undo_last()
    assert undone["ok"], undone
    assert _targets(profile, uid, "Default") == {}
    assert _targets(profile, uid, "Combat") == {}
    assert not _own_path(lib["name"]).exists()


def test_undo_of_a_copy_puts_the_module_file_back_exactly(
    lib: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Parts the target lacked (Calibration, Button Map nodes...) go again."""
    _real_library(lib, monkeypatch)
    before = _own_path(lib["name"]).read_bytes()
    path = _saved_open(lib)
    imported = library.import_pack(lib["pack"])
    result = library_copy.copy(
        imported["setup"]["key"],
        lib["name"],
        lib["guid"],
        list(library.PARTS),
        [path],
        ["Default"],
    )
    assert result["ok"], result
    assert _own_path(lib["name"]).read_bytes() != before
    assert library_copy.undo_last()["ok"]
    assert _own_path(lib["name"]).read_bytes() == before


# --- Gap 5: Undo after Swap (S28, S41) ---


def _refs(profile: gremlin.profile.Profile) -> list:
    return sorted(
        (label, str(device), kind, number)
        for label, device, kind, number in swap_devices.device_references(profile)
    )


def test_undo_of_a_swap_puts_everything_back(
    renamed: dict,
    xml_dir: pathlib.Path,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in ("autosave", "set_last_change", "last_change", "pack_path", "devices"):
        monkeypatch.setattr(library, name, _REAL[name])
    monkeypatch.setattr(library, "folder", lambda: tmp_path / "device library")
    profile = gremlin.profile.Profile()
    profile.from_xml(xml_dir / "profile_auto_mapper.xml")
    monkeypatch.setattr(shared_state, "current_profile", profile)
    path = pathlib.Path(profile.fpath)
    files = (store.path_of("left").read_bytes(), store.path_of("right").read_bytes())
    where = (_where(profile, LEFT_ID), _where(profile, RIGHT_ID))
    refs = _refs(profile)
    assert where[1] == set()  # Right has no bindings in this profile
    result = library_swap.swap(LEFT, RIGHT, ALL, [path])
    assert result["ok"], result
    assert _where(profile, LEFT_ID) != where[0]
    undone = library_copy.undo_last()
    assert undone["ok"], undone
    assert (_where(profile, LEFT_ID), _where(profile, RIGHT_ID)) == where
    assert _refs(profile) == refs
    assert (
        store.path_of("left").read_bytes(),
        store.path_of("right").read_bytes(),
    ) == files
    # Undo is a change too: undoing it swaps again.
    again = library_copy.undo_last()
    assert again["ok"], again
    assert _where(profile, LEFT_ID) != where[0]


# --- Move… and the label (S36, S41) ---


def test_move_into_its_own_subfolder_is_refused(
    lib: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.config import Configuration

    folder = _real_library(lib, monkeypatch)
    monkeypatch.setattr(Configuration, "set", lambda *a, **k: None)
    assert library.autosave(lib["name"], lib["guid"], "copy", "Autosave: a", [])["ok"]
    with pytest.raises(ValueError):
        library.set_settings({"folder": str(folder / "inside")})
    assert not (folder / "inside").exists()


def test_undo_then_redo_keep_the_changes_label(
    lib: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The change record keeps its label across Undo and Redo (never "Undo
    Undo"); the Edit items' names are test_library_undo_redo.py's (S53,
    D-10-UNDO-REDO, which replaced D-10-REDO-LABEL)."""
    _real_library(lib, monkeypatch)
    profile, uid = lib["profile"], lib["uid"]
    path = _saved_open(lib)
    imported = library.import_pack(lib["pack"])
    assert library_copy.copy(
        imported["setup"]["key"], lib["name"], lib["guid"], _ALL, [path], ["Default"]
    )["ok"]
    copied = f"Copy {imported['setup']['name']} to {lib['name']}"
    last = library.last_change()
    assert last["label"] == copied and not last.get("undone")
    assert library_copy.undo_last()["ok"]
    last = library.last_change()
    assert last["label"] == copied and last["undone"] is True
    assert _targets(profile, uid, "Default") == {3: (1, 3)}
    # Redo: the copy again, and the item reads Undo again.
    assert library_copy.undo_last()["ok"]
    last = library.last_change()
    assert last["label"] == copied and not last["undone"]
    assert _targets(profile, uid, "Default") == {1: (2, 1)}


_ = uuid


# --- Twins: the guid decides the Copy target (S22) ---


def _twin_doc(slug: str) -> dict:
    return json.loads((util.modules_dir() / f"{slug}.json").read_text("utf-8"))


def _second_twin() -> str:
    """The first stick's file is bound to it, so it keeps the plain name and
    the twin is "pJoy Pro (2)" with its own file."""
    first = _own_path("pJoy Pro")
    doc = json.loads(first.read_text("utf-8"))
    doc["boundGuidLocal"] = _first_guid()
    first.write_text(json.dumps(doc), encoding="utf-8")
    device_initialization.joystick_devices_initialization()
    second = _twin_guid()
    _twin_module("pjoy_pro_2", "pJoy Pro (2)", second, [7])
    return second


def test_apply_zip_onto_the_second_twin_writes_its_own_file(
    lib: dict, twins: list
) -> None:
    second = _second_twin()
    first = _own_path(lib["name"]).read_bytes()
    match = store.match_known_device("pJoy Pro", second)
    assert match is not None and match["guid"].lower() == second.lower()
    result = device_pack.apply_zip(
        lib["pack"],
        "pJoy Pro",
        {"items": ["in.view"]},
        record_undo=False,
        target_guid=second,
    )
    assert result["ok"], result
    assert _twin_doc("pjoy_pro_2")["view"] == {"rowHeight": 40}
    assert _own_path(lib["name"]).read_bytes() == first


def test_copy_onto_the_second_twin_writes_its_own_file(lib: dict, twins: list) -> None:
    second = _second_twin()
    first = _own_path(lib["name"]).read_bytes()
    result = library_copy.copy(
        lib["setup"]["key"], "pJoy Pro", second, ["appearance"], [], []
    )
    assert result["ok"], result
    assert _twin_doc("pjoy_pro_2")["view"] == {"rowHeight": 40}
    assert _own_path(lib["name"]).read_bytes() == first
