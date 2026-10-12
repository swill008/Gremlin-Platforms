# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""D-TESTLIST-1 items 9, 14, 15: restoring an older Device Library entry
puts back only that entry's change (its saved setups and files), merged
into the list as it is now; later changes stay. Its title is "Restored:
<original title>" / "Reapplied: <original title>". An autosave's result
names each pack it wrote by its full path (for the log). Real Library
store, real History, in temporary folders."""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from gremlin import device_library as library
from gremlin import history, library_undo, shared_state
from gremlin.modules import module_file, registry, store
from gremlin.ui import history_model

GUID = "{6C3D1E20-1111-2222-3333-444455556666}"
NAME = "Stick A"


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
    monkeypatch.setattr(library, "_connected", lambda: [])
    monkeypatch.setattr(library, "_alias", lambda guid, default: default)
    monkeypatch.setattr(library, "_set_alias", lambda guid, name: None)
    monkeypatch.setattr(library.clock, "now", _Clock())
    hist = tmp_path / "history"
    monkeypatch.setattr(history, "folder", lambda: hist)
    monkeypatch.setattr(history, "_pruned", True)
    before = shared_state.current_profile
    shared_state.current_profile = None
    path = modules / f"{registry.plain_slug(NAME)}.json"
    doc = {
        "kind": "control.hardware",
        "device": NAME,
        "boundGuidLocal": GUID,
        "claim": {"buttons": [1, 2]},
        "nodes": [{"kind": "chip", "id": "b1"}],
    }
    module_file.write_bytes(path, json.dumps(doc).encode("utf-8"))
    yield {"folder": folder}
    _entries()
    shared_state.current_profile = before


def _entries() -> list[dict]:
    deadline = time.monotonic() + 5
    while history._writer is not None and time.monotonic() < deadline:
        time.sleep(0.02)
    return history.entries()


def _entry_titled(title: str) -> dict:
    found = [e for e in _entries() if e.get("title") == title]
    assert found, [e.get("title") for e in _entries()]
    return found[0]


def _save(name: str) -> tuple[str, str, Path]:
    out = library.save_setup(NAME, GUID, [], own=True)
    assert out["ok"], out
    key = out["setup"]["key"]
    assert library.rename(key, name)["ok"]
    doc = json.loads((library.folder() / library.LIST_NAME).read_text("utf-8"))
    file = next(
        s["file"] for r in doc["devices"] for s in r["setups"] if s["key"] == key
    )
    return out["device"], key, library.folder() / file


def _setup_keys(device_key: str) -> list[str]:
    row = library.device(device_key)
    return [] if row is None else [s["key"] for s in row["setups"]]


def _restore(entry: dict, which: str) -> None:
    out = history_model.restore(entry["id"], which)
    assert out["ok"], out


def test_restoring_an_older_delete_brings_back_only_that_setup(lib: dict) -> None:
    device, key1, pack1 = _save("test1")
    _device, key2, pack2 = _save("test2")
    data1 = pack1.read_bytes()
    assert library.delete(key1)["ok"]
    assert library.delete(key2)["ok"]

    _restore(_entry_titled("Deleted saved setup test1"), "before")

    assert _setup_keys(device) == [key1], "test2 stays deleted (a later change)"
    assert pack1.read_bytes() == data1
    assert not pack2.exists()


def test_a_later_save_stays_when_an_older_delete_is_restored(lib: dict) -> None:
    device, key1, _pack1 = _save("test1")
    assert library.delete(key1)["ok"]
    _device, key3, pack3 = _save("test3")

    _restore(_entry_titled("Deleted saved setup test1"), "before")

    assert sorted(_setup_keys(device)) == sorted([key1, key3])
    assert pack3.exists()


def test_reapply_deletes_only_that_setup_again(lib: dict) -> None:
    device, key1, pack1 = _save("test1")
    _device, key2, _pack2 = _save("test2")
    assert library.delete(key1)["ok"]
    entry = _entry_titled("Deleted saved setup test1")
    _restore(entry, "before")
    assert sorted(_setup_keys(device)) == sorted([key1, key2])

    _restore(entry, "after")

    assert _setup_keys(device) == [key2]
    assert not pack1.exists()


def test_a_removed_device_comes_back_with_only_the_restored_setup(
    lib: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    device, key1, _pack1 = _save("test1")
    _device, key2, _pack2 = _save("test2")
    assert library.delete(key1)["ok"]
    # Later the device's other saved setup goes too, with its record.
    doc = json.loads((library.folder() / library.LIST_NAME).read_text("utf-8"))
    doc["devices"] = []
    with library._editing("Removed by a later change") as now:
        now["devices"] = doc["devices"]

    _restore(_entry_titled("Deleted saved setup test1"), "before")

    assert _setup_keys(device) == [key1]


def test_restore_is_recorded_as_restored_original_title(lib: dict) -> None:
    _device, key1, _pack1 = _save("test1")
    assert library.delete(key1)["ok"]
    original = _entry_titled("Deleted saved setup test1")
    count = len(_entries())

    ok, _message = library.restore_history(original, original["before"])

    assert ok
    new = _entries()[: len(_entries()) - count]
    titles = [e.get("title") for e in new]
    assert "Restored: Deleted saved setup test1" in titles
    assert not any("Put back from History" in str(t) for t in titles)


def test_library_undo_names_its_group_restored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[tuple] = []
    monkeypatch.setattr(
        history,
        "begin_group",
        lambda title, area="modules", extra=None: seen.append((title, extra)) or "",
    )
    monkeypatch.setattr(history, "end_group", lambda token: None)
    monkeypatch.setattr(history_model, "restore", lambda i, w: {"ok": True})

    library_undo.put_back(["a", "b"], "before", "Copied EVO R")

    assert seen == [
        (
            "Restored: Copied EVO R",
            {"of": "a", "ofAll": ["a", "b"], "restore": "before"},
        )
    ]


def test_an_autosave_names_its_packs_by_full_path(lib: dict) -> None:
    out = library.autosave(NAME, GUID, "module_file", "Before a test", [])

    assert out["ok"], out
    assert out["paths"], out
    for text in out["paths"]:
        path = Path(text)
        assert path.is_absolute() and path.is_file()
        assert lib["folder"] in path.parents
