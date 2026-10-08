# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Device Library store's context-menu side (10 S15, S44, S49, S50):
Remove from Library and its plan, Delete Saved Setups, Keep This Autosave,
deleting several at once and Export Current Setup…, on the real store in a
temporary library folder and modules folder (the LS fixture)."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from gremlin import device_library as library
from test.unit import test_device_library_LS_store as _ls
from test.unit.test_device_library_LS_store import (
    GUID,
    NAME,
    _by_key,
    _module,
    _row,
)

lib = _ls.lib  # the LS fixture


def _zips(lib: dict) -> list[Path]:
    return sorted(lib["folder"].rglob("*.zip"))


# --- Remove from Library (S15, D-10-REMOVE) ------------------------------------------


def test_removal_plan_says_what_remove_needs(lib: dict) -> None:
    _module(lib["modules"])
    library.save_setup(NAME, GUID, [])
    library.save_setup(NAME, GUID, [])
    key = _row()["key"]
    plan = library.removal_plan(key)
    assert plan["ok"], plan
    assert plan["name"] == NAME and plan["shown"] == NAME
    assert plan["setups"] == 2
    assert plan["module_file"] is True and plan["connected"] is False
    lib["plugged"].append((NAME, GUID))
    assert library.removal_plan(key)["connected"] is True
    assert not library.removal_plan("dev-nothere")["ok"]


def test_remove_refuses_a_connected_device(lib: dict) -> None:
    _module(lib["modules"])
    lib["plugged"].append((NAME, GUID))
    library.save_setup(NAME, GUID, [])
    key = _row()["key"]
    out = library.remove_device(key)
    assert not out["ok"]
    assert "plugged in" in out["error"] and "Clear Setup" in out["error"]
    assert len(_by_key(key)["setups"]) == 1
    assert len(_zips(lib)) == 1


def test_remove_after_delete_device_removes_the_device_and_every_setup(
    lib: dict,
) -> None:
    path = _module(lib["modules"])
    library.save_setup(NAME, GUID, [])
    key = _row()["key"]
    # The module file is still here: the caller runs Delete Device first.
    refused = library.remove_device(key)
    assert not refused["ok"] and refused.get("module_file") is True
    assert library.device(key) is not None
    # Delete Device: its "stick deleted" autosave, then the file goes.
    kept = library.autosave(NAME, GUID, "deleted", "Autosave: stick deleted", [])
    assert kept["ok"], kept
    path.unlink()
    assert library.removal_plan(key)["setups"] == 2
    out = library.remove_device(key)
    assert out["ok"], out
    assert library.device(key) is None
    assert library.devices() == []
    assert _zips(lib) == []


def test_remove_a_device_from_a_pack(lib: dict) -> None:
    pack = lib["tmp"] / "Ann stick.zip"
    with zipfile.ZipFile(pack, "w") as zf:
        zf.writestr("map.json", json.dumps({"device": "Ann stick"}))
    assert library.import_pack(pack)["ok"]
    key = _row("Ann stick")["key"]
    assert library.removal_plan(key)["module_file"] is False
    assert library.remove_device(key)["ok"]
    assert library.find_device("Ann stick") is None


# --- Delete Saved Setups (S15) ---------------------------------------------------


def test_delete_saved_setups_keeps_a_connected_device(lib: dict) -> None:
    path = _module(lib["modules"])
    lib["plugged"].append((NAME, GUID))
    library.save_setup(NAME, GUID, [])
    library.autosave(NAME, GUID, "copy", "Autosave: before Copy from X", [])
    key = _row()["key"]
    before = path.read_bytes()
    out = library.delete_saved_setups(key)
    assert out["ok"], out
    row = _by_key(key)
    assert row["setups"] == [] and row["state"] == "connected"
    assert path.read_bytes() == before
    assert _zips(lib) == []


def test_delete_saved_setups_refuses_a_saved_setup_key(lib: dict) -> None:
    _module(lib["modules"])
    lib["plugged"].append((NAME, GUID))
    made = library.save_setup(NAME, GUID, [])
    out = library.delete_saved_setups(made["keys"][0])
    assert not out["ok"]
    assert len(_row()["setups"]) == 1


# --- library.delete follows S15 ------------------------------------------------------


def test_delete_refuses_a_connected_device(lib: dict) -> None:
    _module(lib["modules"])
    lib["plugged"].append((NAME, GUID))
    library.save_setup(NAME, GUID, [])
    key = _row()["key"]
    out = library.delete(key)
    assert not out["ok"] and "plugged in" in out["error"]
    assert len(_by_key(key)["setups"]) == 1


# --- Keep This Autosave (S49) ------------------------------------------------------


def test_keep_makes_an_autosave_the_users_own(lib: dict) -> None:
    _module(lib["modules"])
    library.set_settings({"keep": 1})
    first = library.autosave(NAME, GUID, "copy", "Autosave: before Copy from X", [])
    key = first["keys"][0]
    out = library.keep(key)
    assert out["ok"], out
    setup = next(s for s in _row()["setups"] if s["key"] == key)
    assert setup["own"] is True
    assert any("Kept" in h["text"] for h in setup["history"])
    # The limit never removes it now (S13, S19).
    library.autosave(NAME, GUID, "copy", "Autosave: before Copy from Y", [])
    library.autosave(NAME, GUID, "copy", "Autosave: before Copy from Z", [])
    assert key in [s["key"] for s in _row()["setups"]]


def test_keep_refuses_what_is_not_an_autosave(lib: dict) -> None:
    _module(lib["modules"])
    made = library.save_setup(NAME, GUID, [])
    assert not library.keep(made["keys"][0])["ok"]
    assert not library.keep("set-nothere")["ok"]


# --- several at once (S50) -----------------------------------------------------------


def test_delete_many_removes_what_it_may_and_lists_the_rest(lib: dict) -> None:
    _module(lib["modules"])
    lib["plugged"].append((NAME, GUID))
    one = library.save_setup(NAME, GUID, [])["keys"][0]
    two = library.save_setup(NAME, GUID, [])["keys"][0]
    three = library.save_setup(NAME, GUID, [])["keys"][0]
    connected = _row()["key"]
    pack = lib["tmp"] / "Ann stick.zip"
    with zipfile.ZipFile(pack, "w") as zf:
        zf.writestr("map.json", json.dumps({"device": "Ann stick"}))
    assert library.import_pack(pack)["ok"]
    ann = _row("Ann stick")["key"]
    out = library.delete_many([one, two, ann, connected])
    assert out["ok"], out
    assert set(out["removed"]) == {one, two, ann}
    assert [r["key"] for r in out["refused"]] == [connected]
    assert "plugged in" in out["refused"][0]["error"]
    assert [s["key"] for s in _by_key(connected)["setups"]] == [three]
    assert library.find_device("Ann stick") is None
    assert out["warnings"]


def test_delete_many_with_nothing_removable_is_refused(lib: dict) -> None:
    _module(lib["modules"])
    lib["plugged"].append((NAME, GUID))
    out = library.delete_many([_row()["key"]])
    assert not out["ok"] and out["refused"]


# --- Export Current Setup… (S44) ---------------------------------------------------


def test_export_current_writes_a_pack_and_keeps_no_saved_setup(lib: dict) -> None:
    _module(lib["modules"])
    lib["plugged"].append((NAME, GUID))
    key = _row()["key"]
    dest = lib["tmp"] / "out" / "Mine"
    dest.parent.mkdir()
    out = library.export_current(key, dest)
    assert out["ok"], out
    written = dest.with_name("Mine.zip")
    assert written.is_file()
    with zipfile.ZipFile(written) as zf:
        doc = json.loads(zf.read("map.json"))
    assert doc.get("claim")
    assert _row()["setups"] == []
    assert _zips(lib) == []


def test_export_current_refuses_the_modules_folder(lib: dict) -> None:
    _module(lib["modules"])
    lib["plugged"].append((NAME, GUID))
    out = library.export_current(_row()["key"], lib["modules"] / "x.zip")
    assert not out["ok"]
    assert not (lib["modules"] / "x.zip").exists()
