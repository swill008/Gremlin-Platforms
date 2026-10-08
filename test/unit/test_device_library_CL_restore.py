# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Restore to This Stick… (10 S48): a saved setup back on its own stick as
Copy does, on the real Library store, the real Device Pack import and the
real profile Batch (the LC fixture's fake stick)."""

from __future__ import annotations

import json

import pytest

from gremlin import device_library as library
from gremlin import library_copy
from gremlin.modules import module_file
from test.unit import test_device_library_LC_copy as _lc
from test.unit.test_device_library_LC_copy import (
    _REAL,
    _map,
    _own_path,
    _targets,
)

lib = _lc.lib  # the LC fixture


def _module(name: str, buttons: list[int], row_height: int, cal: list) -> dict:
    return {
        "kind": "control.hardware",
        "device": name,
        "direction": "source",
        "claim": {
            "buttons": buttons,
            "axes": [1],
            "hats": [],
            "keys": [],
            "friendly": {},
        },
        "catalog": {"rowHeight": row_height},
        "calibration": {"1": cal},
        "nodes": [],
    }


def _doc(name: str) -> dict:
    return json.loads(_own_path(name).read_text(encoding="utf-8"))


@pytest.fixture
def real(lib: dict, monkeypatch: pytest.MonkeyPatch) -> dict:
    for name, fn in _REAL.items():
        monkeypatch.setattr(library, name, fn)
    monkeypatch.setattr(library, "folder", lambda: lib["tmp"] / "device library")
    name, profile = lib["name"], lib["profile"]
    module_file.write_json(
        _own_path(name), _module(name, [3], 20, [0, 100, 200, 300, True])
    )
    path = lib["tmp"] / "mine.xml"
    profile.to_xml(path)
    profile.fpath = path  # open, as File > Open leaves it
    profile.mark_clean()
    saved = library.save_setup(name, lib["guid"], [path])
    assert saved["ok"], saved
    lib["saved"] = saved["setup"]
    lib["path"] = path
    # The stick changes afterwards.
    module_file.write_json(
        _own_path(name), _module(name, [5], 77, [10, 110, 210, 310, True])
    )
    _map(profile, lib["uid"], 6, "Default", 3, 6)
    return lib


def test_restore_puts_the_saved_setup_back_on_its_own_stick(real: dict) -> None:
    name, uid, profile = real["name"], real["uid"], real["profile"]
    setup = real["saved"]
    assert "calibration" in setup["holds"]
    out = library_copy.restore_to_stick(setup["key"])
    assert out["ok"], out
    doc = _doc(name)
    assert doc["catalog"] == {"rowHeight": 20}
    assert doc["calibration"] == {"1": [0, 100, 200, 300, True]}  # same stick: included
    assert _targets(profile, uid, "Default") == {3: (1, 3)}
    # Autosave first, named for the Restore; Undo is the last change.
    rows = library.find_device(name, real["guid"])["setups"]
    auto = [s for s in rows if s["key"] in out["autosaves"]]
    assert auto and auto[0]["reason"] == f"Autosave: before Restore of {setup['name']}"
    last = library.last_change()
    assert last["op"] == "copy" and last["autosaves"] == out["autosaves"]
    assert last["label"].startswith("Restore ")
    kept = next(s for s in rows if s["key"] == setup["key"])
    assert any(h["text"].startswith("Restored to") for h in kept["history"])
    # Undo puts the stick back as it was before the Restore.
    undone = library_copy.undo_last()
    assert undone["ok"], undone
    assert _doc(name)["catalog"] == {"rowHeight": 77}


def test_restore_refuses_a_stick_that_is_not_plugged_in(
    real: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(library_copy, "_connected", lambda guid: False)
    before = _own_path(real["name"]).read_bytes()
    out = library_copy.restore_to_stick(real["saved"]["key"])
    assert not out["ok"] and "plugged in" in out["error"]
    assert _own_path(real["name"]).read_bytes() == before
    assert library.last_change() is None


def test_restore_leaves_out_profiles_that_are_gone(real: dict) -> None:
    gone = real["tmp"] / "gone.xml"
    with library._editing() as doc:
        _rec, setup = library._find_setup(doc, real["saved"]["key"])
        setup["profiles"].append({"name": "gone", "path": str(gone), "modes": []})
    out = library_copy.restore_to_stick(real["saved"]["key"])
    assert out["ok"], out
    assert any("gone" in w for w in out["warnings"])


def test_restore_of_an_unknown_setup(real: dict) -> None:
    assert not library_copy.restore_to_stick("set-nothere")["ok"]
