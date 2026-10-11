# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Logical Device's own module file (gremlin.logical_device_file,
decision D-04-LD-FILE): load / save through the module store (History
records it, other keys kept), save only when changed."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gremlin import history_modules
from gremlin import logical_device_file as ldf
from gremlin.logical_device import LogicalRows
from gremlin.modules import ids, store
from test.unit._device_folders import module_path, put_module

LD = "Logical Device"
LD_GUID = str(ids.LOGICAL_DEVICE)

_HAS_MODEL = all(
    hasattr(LogicalRows, name)
    for name in ("to_dict", "load_dict", "mark_saved", "by_uid")
)
needs_model = pytest.mark.skipif(
    not _HAS_MODEL, reason="LogicalRows dict/uid API not landed"
)


class FakeRows:
    """Stands in for LogicalRows' dict API (contract D-04-LD-FILE)."""

    def __init__(self, layout: dict | None = None) -> None:
        self.layout = layout or {"controls": [], "groups": []}
        self.dirty = False
        self.saved = 0

    def to_dict(self) -> dict:
        return json.loads(json.dumps(self.layout))

    def load_dict(self, d: dict) -> None:
        self.layout = json.loads(json.dumps(d))

    def mark_saved(self) -> None:
        self.dirty = False
        self.saved += 1


@pytest.fixture
def modules(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    monkeypatch.setattr(store, "folder", lambda: folder)
    monkeypatch.setattr(store, "_saved", lambda: None)
    return folder


@pytest.fixture
def writes(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Path, str]]:
    seen: list[tuple[Path, str]] = []
    monkeypatch.setattr(
        history_modules,
        "note_write",
        lambda path, text, old: seen.append((Path(path), text)),
    )
    return seen


def _control(uid: str, kind: str, number: int, label: str, **extra: object) -> dict:
    row = {"uid": uid, "type": kind, "id": number, "label": label}
    row.update(extra)
    return row


def test_the_file_is_the_logical_device_module_file(modules: Path) -> None:
    assert ldf.path() == modules / LD / "module.json"
    assert ldf.path() == module_path(modules, LD, LD_GUID)


def test_save_writes_the_layout_keeps_other_keys_and_history_records_it(
    modules: Path, writes: list
) -> None:
    put_module(modules, LD, {"name": "Logical Device", "notes": "kept"}, LD_GUID)
    rows = FakeRows(
        {"controls": [_control("a" * 32, "axis", 1, "Axis 1")], "groups": ["G"]}
    )
    rows.dirty = True
    assert ldf.save(rows) is True
    doc = json.loads(ldf.path().read_text(encoding="utf-8"))
    assert doc["name"] == "Logical Device" and doc["notes"] == "kept"
    assert doc["logical-device"]["controls"][0]["uid"] == "a" * 32
    assert doc["logical-device"]["groups"] == ["G"]
    assert rows.dirty is False
    assert [p for p, _ in writes] == [modules / LD / "module.json"]


def test_a_fresh_save_is_listed_as_the_logical_device_built_in(
    modules: Path, writes: list
) -> None:
    from gremlin import device_library
    from gremlin.modules import registry

    ldf.save(FakeRows())
    doc = json.loads(ldf.path().read_text(encoding="utf-8"))
    assert doc["kind"] == "control.hardware" and doc["direction"] == "source"
    assert doc["device"] == "Logical Device"
    found = [m for m in registry.inputs() if m.slug == LD]
    assert len(found) == 1
    assert registry.is_built_in_input(found[0])
    assert ids.guid_key(found[0].bound_guid) == ids.guid_key(ids.LOGICAL_DEVICE)
    assert device_library.is_built_in_guid(found[0].bound_guid)


def test_load_of_a_missing_file_is_empty_and_no_file_is_made(modules: Path) -> None:
    rows = FakeRows(
        {"controls": [_control("b" * 32, "button", 1, "Button 1")], "groups": []}
    )
    ldf.load(rows)
    assert rows.layout == {"controls": [], "groups": []}
    assert rows.saved == 1
    assert not ldf.path().exists()
    assert not (modules / LD).exists()


def test_load_reads_back_what_save_wrote(modules: Path, writes: list) -> None:
    layout = {
        "controls": [_control("c" * 32, "hat", 2, "Hat 2", group="G")],
        "groups": ["G"],
    }
    ldf.save(FakeRows(layout))
    rows = FakeRows()
    ldf.load(rows)
    assert rows.layout == layout


def test_a_damaged_file_is_not_written_over(
    modules: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.modules import module_file

    monkeypatch.setattr(module_file, "report_refused", lambda damaged: None)
    target = put_module(modules, LD, "{ not json", LD_GUID)
    rows = FakeRows(
        {"controls": [_control("d" * 32, "axis", 1, "Axis 1")], "groups": []}
    )
    rows.dirty = True
    assert ldf.save(rows) is False
    assert target.read_text(encoding="utf-8") == "{ not json"
    assert rows.dirty is True


def test_save_if_dirty_saves_only_a_changed_logical_device(
    modules: Path, writes: list, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows = FakeRows(
        {"controls": [_control("e" * 32, "axis", 1, "Axis 1")], "groups": []}
    )
    monkeypatch.setattr(ldf, "_rows", lambda r: r if r is not None else rows)
    assert ldf.save_if_dirty() is False
    assert writes == []
    rows.dirty = True
    assert ldf.save_if_dirty() is True
    assert len(writes) == 1 and rows.dirty is False


@needs_model
def test_real_rows_round_trip_through_the_file(modules: Path, writes: list) -> None:
    from gremlin.types import InputType

    rows = LogicalRows()
    made = rows.create(InputType.JoystickAxis, 1, "Throttle", group="Flight")
    assert rows.dirty
    ldf.save(rows)
    assert not rows.dirty
    again = LogicalRows()
    ldf.load(again)
    found = again.by_uid(made.uid)
    assert found is not None and found.label == "Throttle" and found.group == "Flight"
    assert not again.dirty
