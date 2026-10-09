# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""10 Device Library S53 (D-10-UNDO-REDO): Undo and Redo walk through this
session's Library actions, each a Tools › History entry: Undo puts back the
newest one's "before", Redo its "after", a new action clears Redo, and an
Undo or Redo is never a step itself. Copy, Swap, Change vJoy Output and
Restore undo through their autosaves and redo by running again (S33: the
open profile). Each Library entry names its devices (S56, Show in History).
The real model, the real Library store and the real History, in temporary
folders."""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot

from gremlin import device_library as library
from gremlin import history, shared_state
from gremlin.modules import module_file, registry, store
from gremlin.ui.device_library_model import DeviceLibraryModel

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
    monkeypatch.setattr(library, "_connected", lambda: [(NAME, GUID)])
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
        "nodes": [],
    }
    module_file.write_bytes(path, json.dumps(doc).encode("utf-8"))
    yield {"modules": modules, "folder": folder}
    _settle()
    shared_state.current_profile = before


def _settle() -> list[dict]:
    deadline = time.monotonic() + 5
    while history._writer is not None and time.monotonic() < deadline:
        time.sleep(0.02)
    return history.entries()


@pytest.fixture
def model(qtbot: QtBot, lib: dict) -> DeviceLibraryModel:
    m = DeviceLibraryModel(watch_devices=False)
    m.refresh()
    return m


def _run(qtbot: QtBot, model: DeviceLibraryModel, start: Callable[[], int]) -> dict:
    with qtbot.waitSignal(model.result, timeout=10000) as blocker:
        assert start()
    res = blocker.args[0]
    assert res["ok"], res
    return res


def _device_key(model: DeviceLibraryModel) -> str:
    return next(d["key"] for d in model._devices if d.get("guid") == GUID)


def _setups(model: DeviceLibraryModel) -> list[dict]:
    model.refresh()
    dev = next(d for d in model._devices if d.get("guid") == GUID)
    return list(dev.get("setups") or [])


def _save(qtbot: QtBot, model: DeviceLibraryModel) -> dict:
    count = len(_setups(model))
    _run(qtbot, model, lambda: model.saveToLibrary(_device_key(model), []))
    setups = _setups(model)
    assert len(setups) == count + 1
    return setups[0]


def test_several_steps_undo_redo_and_titles(
    qtbot: QtBot, model: DeviceLibraryModel
) -> None:
    assert model.undoText == "" and model.redoText == ""
    first = _save(qtbot, model)
    saved_title = model.undoText
    assert saved_title.startswith("Undo Saved ") and "Device Library" in saved_title
    second = _save(qtbot, model)
    pack = model.api.library.folder() / next(
        s["file"]
        for r in json.loads(
            (model.api.library.folder() / library.LIST_NAME).read_text("utf-8")
        )["devices"]
        for s in r.get("setups") or []
        if s["key"] == second["key"]
    )
    data = pack.read_bytes()
    _run(qtbot, model, lambda: model.deleteItem(second["key"]))
    assert not pack.exists()
    assert model.undoText == f"Undo Deleted saved setup {second['name']}"
    assert model.redoText == ""

    # Undo: the delete is put back; Redo names it.
    _run(qtbot, model, model.undo)
    assert pack.read_bytes() == data
    assert {s["key"] for s in _setups(model)} == {first["key"], second["key"]}
    assert model.redoText == f"Redo Deleted saved setup {second['name']}"
    # The Restore Undo made is not a step: Undo now names the save before.
    assert model.undoText == saved_title

    # Several steps: Undo walks back through the saves.
    _run(qtbot, model, model.undo)
    assert [s["key"] for s in _setups(model)] == [first["key"]]
    _run(qtbot, model, model.undo)
    assert _setups(model) == []
    assert model.undoText == ""
    assert model.undo() == 0

    # Redo walks forward again, oldest first.
    _run(qtbot, model, model.redo)
    assert [s["key"] for s in _setups(model)] == [first["key"]]
    _run(qtbot, model, model.redo)
    assert {s["key"] for s in _setups(model)} == {first["key"], second["key"]}
    assert model.redoText == f"Redo Deleted saved setup {second['name']}"


def test_a_new_action_clears_redo(qtbot: QtBot, model: DeviceLibraryModel) -> None:
    first = _save(qtbot, model)
    _run(qtbot, model, model.undo)
    assert model.redoText.startswith("Redo Saved ")
    _save(qtbot, model)
    assert model.redoText == ""
    assert model.undoText.startswith("Undo Saved ")
    assert first["key"] not in {s["key"] for s in _setups(model)}


def test_copy_steps_undo_through_autosaves_and_redo_runs_again(
    qtbot: QtBot, model: DeviceLibraryModel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S33: Copy changes the open profile in memory, which History doesn't
    hold: its Undo goes through the autosaves (undo_change, with the change
    it kept), its Redo runs the same Copy again."""
    from gremlin import library_copy

    calls: list[tuple] = []
    changes = iter(
        [
            {"op": "copy", "autosaves": ["a1"], "label": "Copy X to Stick A"},
            {"op": "copy", "autosaves": ["a2"], "label": "Copy X to Stick A"},
        ]
    )

    def fake_copy(*args: object) -> dict:
        calls.append(("copy", *args))
        monkeypatch.setattr(library, "last_change", lambda c=next(changes): c)
        return {"ok": True, "notes": [], "warnings": []}

    def fake_undo(change: dict) -> dict:
        calls.append(("undo_change", change["autosaves"]))
        return {"ok": True, "notes": [], "warnings": []}

    monkeypatch.setattr(library_copy, "copy", fake_copy)
    monkeypatch.setattr(library_copy, "undo_change", fake_undo)
    monkeypatch.setattr(
        library_copy,
        "undo_last",
        lambda: pytest.fail("Undo must use the step's own change"),
    )
    first = _save(qtbot, model)
    key = _device_key(model)
    _run(
        qtbot, model, lambda: model.copy(first["key"], key, ["setup"], [], ["Default"])
    )
    assert model.undoText.startswith("Undo Copied ")
    assert model.undoText.endswith(" to Stick A")

    _run(qtbot, model, model.undo)
    assert calls[-1] == ("undo_change", ["a1"])
    assert model.redoText.startswith("Redo Copied ")

    _run(qtbot, model, model.redo)
    assert calls[-1][0] == "copy" and calls[-1][1] == first["key"]
    # Undo after Redo uses the autosaves the second run kept.
    _run(qtbot, model, model.undo)
    assert calls[-1] == ("undo_change", ["a2"])


def test_library_entries_name_their_devices(
    qtbot: QtBot, model: DeviceLibraryModel
) -> None:
    _save(qtbot, model)
    entries = [e for e in _settle() if e.get("kind") == "library"]
    assert entries
    devices = entries[0]["subject"].get("devices")
    assert devices == [{"guid": GUID, "name": NAME}]


def test_a_group_names_the_devices_of_its_parts() -> None:
    one = {"subject": {"devices": [{"guid": "g1", "name": "A"}]}}
    two = {
        "subject": {
            "devices": [{"guid": "g1", "name": "A"}, {"guid": "", "name": "B"}]
        }
    }
    entry = history.group_entry("modules", "Removed A", [one, two, {"subject": {}}])
    assert entry["subject"]["devices"] == [
        {"guid": "g1", "name": "A"},
        {"guid": "", "name": "B"},
    ]


def test_steps_alone() -> None:
    from gremlin import library_undo

    steps = library_undo.Steps()
    assert steps.undo_text() == "" and not steps.undo()["ok"]
    assert not steps.redo()["ok"]


def test_library_entries_match_show_in_history_for_their_device_only(
    lib: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S56: Save, Delete and Remove each land in History naming the device,
    so its ofDevice filter finds them; a twin (same name, other id) not."""
    from gremlin.ui import history_model

    own_file = f"{registry.plain_slug(NAME)}.json"
    mine = {"ofDevice": {"fileName": own_file, "guid": GUID, "name": NAME}}
    other = "{00000000-AAAA-BBBB-CCCC-000000000001}"
    twin = {"ofDevice": {"fileName": "twin.json", "guid": other, "name": NAME}}

    def new_entry(action: Callable[[], dict]) -> dict:
        count = len(_settle())
        out = action()
        assert out["ok"], out
        found = _settle()[: len(_settle()) - count]
        assert len(found) == 1, [e["title"] for e in found]
        return found[0]

    saved = library.save_setup(NAME, GUID, [], own=True)
    assert saved["ok"], saved
    second = new_entry(lambda: library.save_setup(NAME, GUID, [], own=True))
    deleted = new_entry(lambda: library.delete(saved["setup"]["key"]))
    for path in lib["modules"].glob("*.json"):
        path.unlink()
    monkeypatch.setattr(library, "_connected", lambda: [])
    monkeypatch.setattr(library, "_set_up", lambda: [])
    # Keyboard and OSC (built-ins) may be loaded by an earlier test.
    monkeypatch.setattr(library, "_modules", lambda: [])
    removed = new_entry(lambda: library.remove_device(saved["device"]))
    for entry in (second, deleted, removed):
        assert history_model._matches(entry, mine), entry["title"]
        assert not history_model._matches(entry, twin), entry["title"]
