# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""A Device Bindings or Keyboard layout held unsaved while another writer
changes the device's module file (03 gap #28): the newer file wins, the held
change is dropped and the page is told (decision AD2). A held name for a
control no longer claimed is not written (03 S42). Deleting the device's
file drops its held change; a file gone at Save is said, not silent.

Spec: 05 S122a (AD2); 03 S42.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest

from gremlin import history_modules
from gremlin import signal as gremlin_signal
from gremlin.modules import store
from test.unit._device_folders import put_module

GUID = "{11111111-2222-3333-4444-555555555555}"
NAME = "Test Stick"
HELD = {"groups": ["A"], "order": ["button:1"], "group_of": {"button:1": "A"}}
NEWER = {"groups": ["B"], "order": ["button:2"], "group_of": {"button:2": "B"}}


@pytest.fixture
def device(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setattr(store, "folder", lambda: folder)
    path = put_module(
        folder,
        NAME,
        {
            "kind": "control.hardware",
            "device": NAME,
            "direction": "source",
            "claim": {"buttons": [1, 2], "friendly": {"button:1": "Fire"}},
            "nodes": [],
        },
        GUID,
    )
    assert store.module_file(NAME, GUID) == path
    monkeypatch.setattr(history_modules, "note_write", lambda *a, **k: None)
    store.discard_pending()
    yield path
    store.discard_pending()


@pytest.fixture
def told(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[tuple[str, str]]]:
    got: list[tuple[str, str]] = []

    def listen(what: str, guid: str) -> None:
        got.append((what, guid))

    store.add_pending_listener(listen)
    yield got
    store.remove_pending_listener(listen)


@pytest.fixture
def notes(
    qapp: object, monkeypatch: pytest.MonkeyPatch
) -> Iterator[list[tuple[str, str]]]:
    got: list[tuple[str, str]] = []

    def shown(title: str, text: str) -> None:
        got.append((title, text))

    monkeypatch.setattr(
        gremlin_signal,
        "display_error",
        lambda msg, details="": got.append(("error", msg)),
    )
    gremlin_signal.signal.showNotification.connect(shown)
    yield got
    gremlin_signal.signal.showNotification.disconnect(shown)


def _doc(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _newer_doc(path: Path) -> dict:
    doc = _doc(path)
    doc["layout"] = NEWER
    doc["claim"] = {"buttons": [2, 3], "friendly": {"button:2": "Trigger"}}
    return doc


def _history_restore(path: Path) -> None:
    store.write_text(path, json.dumps(_newer_doc(path), indent=2) + "\n", "History")


def _pack_import(path: Path) -> None:
    data = (json.dumps(_newer_doc(path), indent=2) + "\n").encode("utf-8")
    store.replace(path, data, "Device Pack")


def _library_copy(path: Path) -> None:
    store.write_json(path, _newer_doc(path), "Device Library")


def _module_setup_save(path: Path) -> None:
    def change(doc: dict) -> None:
        doc.update(_newer_doc(path))

    store.update_path(path, change, "Module Setup")


@pytest.mark.parametrize(
    "writer",
    [_history_restore, _pack_import, _library_copy, _module_setup_save],
    ids=["history_restore", "pack_import", "library_copy", "module_setup_save"],
)
def test_newer_file_wins_over_held_layout(
    device: Path, told: list, notes: list, writer: object
) -> None:
    store.set_pending_layout(GUID, HELD, {"button:1": "Shoot"}, NAME)
    assert store.has_pending()
    told.clear()

    writer(device)  # type: ignore[operator]

    assert not store.has_pending()
    assert ("replaced", GUID) in told
    assert any(
        "The layout changed elsewhere; your unsaved changes for" in text
        and NAME in text
        for _title, text in notes
    )
    assert store.save_pending() == 0
    doc = _doc(device)
    assert doc["layout"]["groups"] == ["B"]
    assert doc["claim"]["friendly"] == {"button:2": "Trigger"}


def test_own_save_keeps_nothing_and_is_not_replaced(
    device: Path, told: list, notes: list
) -> None:
    store.set_pending_layout(GUID, HELD, {"button:2": "Pinkie"}, NAME)
    told.clear()
    assert store.save_pending() == 1
    assert ("replaced", GUID) not in told
    assert not notes
    doc = _doc(device)
    assert doc["layout"]["groups"] == ["A"]
    assert doc["claim"]["friendly"]["button:2"] == "Pinkie"


def test_write_not_touching_layout_or_claim_keeps_held(
    device: Path, told: list
) -> None:
    """A device map picture or view change leaves the held layout valid."""
    store.set_pending_layout(GUID, HELD, None, NAME)

    def change(doc: dict) -> None:
        doc["view"] = {"zoom": 2}

    store.update_path(device, change, "Device Mapping Editor")
    assert store.has_pending()
    store.save_pending()
    assert _doc(device)["layout"]["groups"] == ["A"]


def test_unclaimed_name_not_written(device: Path) -> None:
    """03 S42: a held name for a control no longer claimed is skipped."""
    store.set_pending_layout(GUID, None, {"button:2": "Pinkie"}, NAME)
    # The claim alone changes underneath, outside the store's writers.
    doc = _doc(device)
    doc["claim"]["buttons"] = [1]
    device.write_text(json.dumps(doc), encoding="utf-8")
    store.save_pending()
    assert "button:2" not in _doc(device)["claim"]["friendly"]


def test_device_delete_drops_held(device: Path, told: list) -> None:
    store.set_pending_layout(GUID, HELD, {"button:1": "Shoot"}, NAME)
    told.clear()
    store.delete_path(device, "Delete Device")
    assert not store.has_pending()
    assert ("replaced", GUID) in told


def test_missing_file_at_save_is_said(device: Path, notes: list) -> None:
    store.set_pending_layout(GUID, HELD, None, NAME)
    device.unlink()  # gone outside the store's writers
    assert store.save_pending() == 0
    assert not store.has_pending()
    assert any(title == "error" and NAME in text for title, text in notes)


def test_hardware_page_drops_steps_on_replaced() -> None:
    from gremlin.ui.hardware_layout import HardwareLayoutModel

    class FakeStore:
        writing = False
        guid = GUID
        loads = 0

        def load(self) -> None:
            self.loads += 1

    class Page:
        _store = FakeStore()
        reloaded = 0
        rebuilt = 0

        def _on_reloaded(self) -> None:
            self.reloaded += 1

        def _rebuild(self) -> None:
            self.rebuilt += 1

    page = Page()
    HardwareLayoutModel._on_pending(page, "replaced", GUID)  # type: ignore[arg-type]
    assert page._store.loads == 1
    assert page.reloaded == 1


def test_logical_device_reload_says_unreadable_rows(
    device: Path, notes: list, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AD1: a Restore/Import/Undo of the Logical Device's file says the rows
    it couldn't read, as opening does."""
    from gremlin import logical_device_file

    monkeypatch.setattr(logical_device_file, "path", lambda: device)
    monkeypatch.setattr(logical_device_file, "load", lambda: ["Row 3 skipped"])
    store.replace(device, device.read_bytes(), "History")
    assert ("Logical Device", "Row 3 skipped") in notes
