# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""10 Device Library S51, 08 History S12a (D-10-IN-HISTORY): every change to
the Library's own files (its list and its saved setups) is one Tools ›
History entry per action, named for what happened, and Restore (the History
window's own restore()) puts back the files and the list as they were.
Real Library store, real History, in temporary folders."""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from gremlin import device_library as library
from gremlin import history, shared_state
from gremlin.modules import module_file, registry, store
from gremlin.ui import history_model

GUID = "{6C3D1E20-1111-2222-3333-444455556666}"
NAME = "Stick A"


class _Clock:
    """One second per reading: every saved setup has its own time."""

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
    monkeypatch.setattr(library, "_alias", lambda guid, default: default)
    monkeypatch.setattr(library, "_set_alias", lambda guid, name: None)
    monkeypatch.setattr(library.clock, "now", _Clock())
    hist = tmp_path / "history"
    monkeypatch.setattr(history, "folder", lambda: hist)
    monkeypatch.setattr(history, "_pruned", True)
    before = shared_state.current_profile
    shared_state.current_profile = None
    yield {"modules": modules, "folder": folder, "plugged": plugged}
    _entries()
    shared_state.current_profile = before


def _entries() -> list[dict]:
    deadline = time.monotonic() + 5
    while history._writer is not None and time.monotonic() < deadline:
        time.sleep(0.02)
    return history.entries()


def _new_since(count: int) -> list[dict]:
    """The entries recorded since there were count (newest first)."""
    now = _entries()
    return now[: len(now) - count]


def _module(modules: Path) -> Path:
    path = modules / f"{registry.plain_slug(NAME)}.json"
    doc = {
        "kind": "control.hardware",
        "device": NAME,
        "boundGuidLocal": GUID,
        "claim": {"buttons": [1, 2], "friendly": {"btn:1": "Fire"}},
        "nodes": [{"kind": "chip", "id": "b1"}],
    }
    module_file.write_bytes(path, json.dumps(doc).encode("utf-8"))
    return path


def _saved(lib: dict) -> tuple[str, str, Path]:
    """A saved setup of the stick: (device key, setup key, its pack file)."""
    _module(lib["modules"])
    out = library.save_setup(NAME, GUID, [], own=True)
    assert out["ok"], out
    setup = out["setup"]
    return out["device"], setup["key"], lib["folder"] / _file_of(setup["key"])


def _file_of(setup_key: str) -> str:
    doc = json.loads((library.folder() / library.LIST_NAME).read_text("utf-8"))
    for rec in doc["devices"]:
        for setup in rec.get("setups") or []:
            if setup["key"] == setup_key:
                return setup["file"]
    raise AssertionError(setup_key)


def _not_set_up(monkeypatch: pytest.MonkeyPatch, lib: dict) -> None:
    """The stick is unplugged and its module file gone: Not connected."""
    for path in lib["modules"].glob("*.json"):
        path.unlink()
    monkeypatch.setattr(library, "_set_up", lambda: [])
    lib["plugged"].clear()


def _restore_before(entry: dict) -> None:
    result = history_model.restore(entry["id"], "before")
    assert result["ok"], result


def test_saving_a_setup_is_one_entry(lib: dict) -> None:
    count = len(_entries())
    _saved(lib)
    new = _new_since(count)
    library_entries = [e for e in new if "Device Library" in e["title"]]
    assert [e["title"] for e in library_entries] in (
        [f"Saved {library.shown(NAME, GUID)} to the Device Library"],
        [f"Saved {NAME} to the Device Library"],
    )


def test_remove_from_library_is_one_entry_and_restore_puts_it_back(
    lib: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    key, setup_key, pack = _saved(lib)
    data = pack.read_bytes()
    list_before = (lib["folder"] / library.LIST_NAME).read_bytes()
    _not_set_up(monkeypatch, lib)
    assert library.device(key)["state"] != "connected"
    shown = library.removal_plan(key)["shown"]
    count = len(_entries())

    out = library.remove_device(key)

    assert out["ok"], out
    assert library.device(key) is None and not pack.exists()
    new = _new_since(count)
    assert [e["title"] for e in new] == [f"Removed {shown} from the Device Library"]

    _restore_before(new[0])

    row = library.device(key)
    assert row is not None, "the device row is back"
    assert [s["key"] for s in row["setups"]] == [setup_key]
    assert pack.read_bytes() == data
    assert json.loads((lib["folder"] / library.LIST_NAME).read_bytes()) == json.loads(
        list_before
    )


def test_delete_a_saved_setup_is_one_entry_and_restore_puts_it_back(
    lib: dict,
) -> None:
    key, setup_key, pack = _saved(lib)
    data = pack.read_bytes()
    name = library.device(key)["setups"][0]["name"]
    count = len(_entries())

    out = library.delete(setup_key)

    assert out["ok"], out
    assert not pack.exists()
    new = _new_since(count)
    assert [e["title"] for e in new] == [f"Deleted saved setup {name}"]

    _restore_before(new[0])

    assert [s["key"] for s in library.device(key)["setups"]] == [setup_key]
    assert pack.read_bytes() == data


def test_delete_saved_setups_is_one_entry(lib: dict) -> None:
    key, setup_key, pack = _saved(lib)
    _saved(lib)
    lib["plugged"].append((NAME, GUID))
    row = library.device(key)
    assert row["state"] == "connected" and len(row["setups"]) == 2
    count = len(_entries())

    out = library.delete_saved_setups(key)

    assert out["ok"], out
    assert library.device(key)["setups"] == []
    new = _new_since(count)
    assert len(new) == 1, [e["title"] for e in new]
    assert new[0]["title"] in {
        f"Deleted the saved setups of {row['name']}",
        f"Deleted the saved setups of {library.shown(NAME, GUID)}",
    }

    _restore_before(new[0])

    assert len(library.device(key)["setups"]) == 2
    assert pack.is_file()


def test_an_autosave_pruned_past_the_limit_is_in_the_entry(lib: dict) -> None:
    _module(lib["modules"])
    first = library.autosave(NAME, GUID, "module_file", "Change 1", [])
    assert first["ok"], first
    oldest_key = first["setup"]["key"]
    oldest = lib["folder"] / _file_of(oldest_key)
    data = oldest.read_bytes()
    for number in range(2, library.DEFAULT_KEEP + 1):
        assert library.autosave(NAME, GUID, "module_file", f"Change {number}", [])["ok"]
    count = len(_entries())

    out = library.autosave(NAME, GUID, "module_file", "Change 11", [])

    assert out["ok"], out
    assert not oldest.exists(), "the oldest autosave went (limit 10)"
    new = _new_since(count)
    assert len(new) == 1, [e["title"] for e in new]
    assert new[0]["title"] == "Autosave: Change 11"
    assert new[0]["kind"] == "library"

    _restore_before(new[0])

    keys = [s["key"] for s in library.device(out["device"])["setups"]]
    assert oldest_key in keys
    assert oldest.read_bytes() == data
