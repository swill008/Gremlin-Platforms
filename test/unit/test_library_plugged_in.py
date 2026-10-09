# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Device Library decides Connected / Not connected by the device's
Windows id against the live device list, never by its name (03 S90a, 10 S6,
S15, S50). The real store in a temporary modules folder; the device list and
the driver's live list are stood in for."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest

from gremlin import device_initialization, shared_state
from gremlin import device_library as library
from gremlin.modules import hardware, module_file, store

TWIN_1 = "{6C3D1E20-1111-2222-3333-444455556666}"
TWIN_2 = "{6C3D1E20-1111-2222-3333-777788889999}"
SPACED = "{AAAA0000-1111-2222-3333-444455556666}"
FOREIGN = "{BBBB0000-1111-2222-3333-444455556666}"


class Sticks:
    """The device list (which may lag) and the driver's live list."""

    def __init__(self) -> None:
        self.listed: list[tuple[str, str]] = []
        self.live: set[str] = set()


@pytest.fixture
def sticks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Sticks]:
    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setattr(store, "folder", lambda: folder)
    monkeypatch.setattr(library, "folder", lambda: tmp_path / "device library")
    monkeypatch.setattr(library, "_photo_cache", lambda: tmp_path / "photo cache")
    monkeypatch.setattr(library, "_alias", lambda guid, default: default)
    state = Sticks()
    monkeypatch.setattr(
        device_initialization,
        "physical_devices",
        lambda: [
            SimpleNamespace(name=n, device_guid=g, is_virtual=False)
            for n, g in state.listed
        ],
    )
    monkeypatch.setattr(
        hardware,
        "device_connected",
        lambda guid: str(guid).strip("{}").lower() in state.live,
    )
    before = shared_state.current_profile
    shared_state.current_profile = None
    state.folder = folder  # type: ignore[attr-defined]
    yield state
    shared_state.current_profile = before


def _live(state: Sticks, *guids: str) -> None:
    state.live = {g.strip("{}").lower() for g in guids}


def _write(folder: Path, slug: str, name: str, guid: str) -> None:
    doc = {"kind": "control.hardware", "device": name, "nodes": [], "claim": {}}
    if guid:
        doc["boundGuidLocal"] = guid
    module_file.write_bytes(folder / f"{slug}.json", json.dumps(doc).encode("utf-8"))


def _by_guid(guid: str) -> dict:
    want = library.stored_guid_key(guid)
    rows = [r for r in library.devices() if library.stored_guid_key(r["guid"]) == want]
    assert len(rows) == 1, rows
    return rows[0]


def _add_records(*records: dict) -> None:
    with library._editing(quiet=True) as doc:
        doc.setdefault("devices", []).extend(records)


def test_twin_sticks_one_unplugged_only_the_plugged_one_is_connected(
    sticks: Sticks,
) -> None:
    # The device list still holds the unplugged twin; its id isn't live.
    sticks.listed = [("Twin Stick", TWIN_1), ("Twin Stick", TWIN_2)]
    _live(sticks, TWIN_1)
    _add_records(
        {
            "key": "dev-twin2",
            "name": "Twin Stick",
            "ownName": "Twin Stick",
            "guid": TWIN_2,
            "kind": "setup",
            "seen": "",
            "setups": [],
        },
    )
    assert _by_guid(TWIN_1)["state"] == "connected"
    gone = _by_guid(TWIN_2)
    assert gone["state"] == "not_connected"
    # S15/S50: Remove is refused only for the plugged-in twin.
    refused = library.remove_device(_by_guid(TWIN_1)["key"])
    assert not refused["ok"] and "plugged in" in refused["error"]
    assert library.removal_plan(gone["key"])["connected"] is False
    assert library.remove_device(gone["key"])["ok"]
    assert library.stored_guid_key(TWIN_2) not in {
        library.stored_guid_key(r["guid"]) for r in library.devices()
    }


def test_a_name_with_double_spaces_is_connected_by_its_id(sticks: Sticks) -> None:
    _write(sticks.folder, "saitek", "Saitek  X52  Pro", SPACED)  # type: ignore[attr-defined]
    sticks.listed = [("Saitek  X52  Pro", SPACED)]
    _live(sticks, SPACED)
    row = _by_guid(SPACED)
    assert row["state"] == "connected"
    assert row["module"] == "saitek"
    assert library.removal_plan(row["key"])["connected"] is True
    # Unplugged (the id leaves the live list): Not connected, same name.
    _live(sticks)
    assert _by_guid(SPACED)["state"] == "not_connected"


def test_a_pack_device_not_on_this_pc_stays_not_connected(sticks: Sticks) -> None:
    # A stick of the same name is plugged in here, with its own id.
    sticks.listed = [("Twin Stick", TWIN_1)]
    _live(sticks, TWIN_1)
    _add_records(
        # From another PC's pack: no id, and an id that isn't on this PC.
        {
            "key": "dev-pack",
            "name": "Twin Stick",
            "ownName": "Twin Stick",
            "guid": "",
            "kind": "pack",
            "seen": "",
            "setups": [],
        },
        {
            "key": "dev-foreign",
            "name": "Twin Stick",
            "ownName": "Twin Stick",
            "guid": FOREIGN,
            "kind": "pack",
            "seen": "",
            "setups": [],
        },
    )
    rows = {r["key"]: r for r in library.devices()}
    assert rows["dev-pack"]["state"] == "not_connected"
    assert rows["dev-foreign"]["state"] == "not_connected"
    assert _by_guid(TWIN_1)["state"] == "connected"
    assert _by_guid(TWIN_1)["key"] not in ("dev-pack", "dev-foreign")
    assert library.removal_plan("dev-pack")["connected"] is False


def test_copy_and_restore_go_by_the_live_id(
    sticks: Sticks, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin import library_copy

    vjoy = SimpleNamespace(name="vJoy Device", device_guid=FOREIGN, is_virtual=True)
    monkeypatch.setattr(
        store,
        "live_devices",
        lambda: (
            [
                SimpleNamespace(name=n, device_guid=g, is_virtual=False)
                for n, g in sticks.listed
            ]
            + [vjoy]
        ),
    )
    # Both twins still listed; only the first one's id is live.
    sticks.listed = [("Twin Stick", TWIN_1), ("Twin Stick", TWIN_2)]
    _live(sticks, TWIN_1, FOREIGN)
    assert library_copy._connected(TWIN_1)
    assert not library_copy._connected(TWIN_2)
    assert not library_copy._connected("")
    assert not library_copy._connected(FOREIGN)  # a vJoy device, never a stick
    # Restore to This Stick refuses the unplugged twin.
    _add_records(
        {
            "key": "dev-twin2",
            "name": "Twin Stick",
            "ownName": "Twin Stick",
            "guid": TWIN_2,
            "kind": "setup",
            "seen": "",
            "setups": [
                {
                    "key": "set-1",
                    "name": "Mine",
                    "file": "none.zip",
                    "holds": ["bindings"],
                }
            ],
        },
    )
    out = library_copy.restore_to_stick("set-1")
    assert not out["ok"] and "plugged in" in out["error"], out
