# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Device Library: Copy from a device's current settings (10 S22), on the
real Device Pack import, the real profile Batch and the real pack builder;
the Library's list is LC's small fake (test_device_library_LC_copy.py).
The current settings are built in memory for the copy: nothing is kept in
the Library but the target's autosave (S25)."""

# The fixture lib comes from LC's tests: it is an argument of each test here.
# ruff: noqa: F811

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from gremlin import library_copy, shared_state
from gremlin.profile import DeviceInfo, Profile
from test.unit.test_device_library_LC_copy import (  # noqa: F401 - the fixture
    _ALL,
    _OTHER,
    _doc,
    _map,
    _targets,
    lib,
)


def _source(lib: dict) -> dict:
    """Other Stick: set up here (its module file), not plugged in, with
    bindings in the open profile (Button 1 → vJoy 2 Button 5)."""
    dev = {
        "key": "dev-other",
        "name": "Other Stick",
        "description": "",
        "state": "not_connected",
        "guid": str(_OTHER),
        "module": "other-stick",
        "setups": [],
    }
    lib["fake"].devs.append(dev)
    return dev


@pytest.fixture
def scratch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    folder = tmp_path / "scratch"
    folder.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(folder))
    return folder


def _kept(lib: dict) -> list[str]:
    return [
        s["key"]
        for d in lib["fake"].devs
        for s in d["setups"]
        if s.get("origin") != "autosave"
    ]


def test_s22_copy_a_devices_current_settings(lib: dict, scratch: Path) -> None:
    name, uid, profile = lib["name"], lib["uid"], lib["profile"]
    _source(lib)
    kept = _kept(lib)
    result = library_copy.copy(
        "dev-other", name, lib["guid"], _ALL, [Path("")], ["Default"]
    )
    assert result["ok"], result
    # The source's bindings in the open profile are now the target's (S24).
    assert _targets(profile, uid, "Default") == {1: (2, 5)}
    assert _targets(profile, uid, "Landing") == {4: (1, 4)}
    # Its module file too; the source keeps everything (S22).
    assert _doc(name)["catalog"] == {"rowHeight": 30}
    assert _doc("Other Stick")["catalog"] == {"rowHeight": 30}
    assert _targets(profile, _OTHER, "Default") == {1: (2, 5)}
    # Only the target's autosave is kept; nothing else in the Library and no
    # files left behind.
    fake = lib["fake"]
    assert _kept(lib) == kept
    assert fake.autosaves[0][1:3] == ("copy", "Autosave: before Copy from Other Stick")
    assert fake.last["op"] == "copy" and fake.last["autosaves"] == result["autosaves"]
    assert fake.history == []
    assert list(scratch.iterdir()) == []
    # Undo puts the target back.
    assert library_copy.undo_last()["ok"]
    assert _targets(profile, uid, "Default") == {3: (1, 3)}


def test_s22_current_settings_into_a_saved_profile(lib: dict, scratch: Path) -> None:
    name, uid = lib["name"], lib["uid"]
    _source(lib)
    saved_path = lib["tmp"] / "saved.xml"
    saved = Profile()
    shared_state.current_profile = saved
    saved.device_database.devices[uid] = DeviceInfo(uid, name)
    saved.device_database.devices[_OTHER] = DeviceInfo(_OTHER, "Other Stick")
    _map(saved, _OTHER, 2, "Default", 3, 3)
    _map(saved, uid, 3, "Default", 1, 9)
    saved.to_xml(saved_path)
    shared_state.current_profile = lib["profile"]
    result = library_copy.copy(
        "dev-other", name, lib["guid"], ["bindings"], [saved_path], ["Default"]
    )
    assert result["ok"], result
    again = Profile()
    again.from_xml(saved_path)
    # The bindings came from that profile, not the open one.
    assert _targets(again, uid, "Default") == {2: (3, 3)}
    assert _targets(lib["profile"], uid, "Default") == {3: (1, 3)}
    assert list(scratch.iterdir()) == []


def test_s23_plan_a_devices_current_settings(lib: dict, scratch: Path) -> None:
    _source(lib)
    plan = library_copy.plan_copy(
        "dev-other", lib["name"], lib["guid"], _ALL, [Path("")], []
    )
    assert plan["ok"], plan
    # What it holds and its modes, for the dialog's ticks.
    assert "setup" in plan["holds"] and "bindings" in plan["holds"]
    assert plan["sourceModes"] == ["Default"]
    assert plan["source"] == "Other Stick"
    assert list(scratch.iterdir()) == []


def test_s22_a_stick_is_not_copied_onto_itself(lib: dict, scratch: Path) -> None:
    lib["fake"].devs.append(
        {
            "key": "dev-self",
            "name": lib["name"],
            "description": "",
            "state": "connected",
            "guid": lib["guid"],
            "module": "pjoy-pro",
            "setups": [],
        }
    )
    result = library_copy.copy(
        "dev-self", lib["name"], lib["guid"], _ALL, [Path("")], ["Default"]
    )
    assert not result["ok"] and "another stick" in result["error"]
    assert lib["fake"].autosaves == []
