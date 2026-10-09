# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Logical Device's own module file (gremlin.logical_device_file,
decision D-04-LD-FILE): load / save through the module store (History
records it, other keys kept), save only when changed, the version 14
merge (decision 3) and the profile backup."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gremlin import history_modules
from gremlin import logical_device_file as ldf
from gremlin.logical_device import LogicalRows
from gremlin.modules import store

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
    assert ldf.path() == modules / "logical_device.json"


def test_save_writes_the_layout_keeps_other_keys_and_history_records_it(
    modules: Path, writes: list
) -> None:
    (modules / "logical_device.json").write_text(
        json.dumps({"name": "Logical Device", "notes": "kept"}), encoding="utf-8"
    )
    rows = FakeRows(
        {"controls": [_control("a" * 32, "axis", 1, "Axis 1")], "groups": ["G"]}
    )
    rows.dirty = True
    assert ldf.save(rows) is True
    doc = json.loads((modules / "logical_device.json").read_text(encoding="utf-8"))
    assert doc["name"] == "Logical Device" and doc["notes"] == "kept"
    assert doc["logical-device"]["controls"][0]["uid"] == "a" * 32
    assert doc["logical-device"]["groups"] == ["G"]
    assert rows.dirty is False
    assert [p.name for p, _ in writes] == ["logical_device.json"]


def test_a_fresh_save_is_listed_as_the_logical_device_built_in(
    modules: Path, writes: list
) -> None:
    from gremlin import device_library
    from gremlin.modules import ids, registry

    ldf.save(FakeRows())
    doc = json.loads((modules / "logical_device.json").read_text(encoding="utf-8"))
    assert doc["kind"] == "control.hardware" and doc["direction"] == "source"
    assert doc["device"] == "Logical Device"
    found = [m for m in registry.inputs() if m.slug == "logical_device"]
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
    assert not (modules / "logical_device.json").exists()


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
    target = modules / "logical_device.json"
    target.write_text("{ not json", encoding="utf-8")
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


def test_merge_reuses_a_matching_control_and_adds_the_rest() -> None:
    file_layout = {
        "controls": [
            _control("1" * 32, "axis", 1, "Throttle"),
            _control("2" * 32, "button", 1, "Fire"),
        ],
        "groups": ["Flight"],
    }
    profile = {
        "controls": [
            _control("", "axis", 1, "Throttle"),  # same type+number+label: reused
            _control("", "button", 1, "Gear", group="Taxi"),  # number taken: next free
            _control("", "button", 4, "Fire"),  # label taken: made unique
            _control("", "hat", 3, "View"),  # free number kept
        ],
        "groups": ["Taxi", "Flight"],
    }
    merged, result = ldf.merge_layout(file_layout, profile)
    by_label = {c["label"]: c for c in merged["controls"]}
    assert result.uid_map[("axis", 1)] == "1" * 32
    assert by_label["Fire"]["uid"] == "2" * 32  # nothing removed or changed
    gear = by_label["Gear"]
    assert gear["id"] == 2 and gear["group"] == "Taxi"
    assert result.uid_map[("button", 1)] == gear["uid"]
    fire2 = by_label["Fire (2)"]
    assert fire2["id"] == 4 and result.uid_map[("button", 4)] == fire2["uid"]
    assert by_label["View"]["id"] == 3
    assert result.added == ["Gear", "Fire (2)", "View"]
    assert merged["groups"] == ["Flight", "Taxi"]
    uids = [c["uid"] for c in merged["controls"]]
    assert len(set(uids)) == len(uids)
    assert all(len(u) == 32 and int(u, 16) >= 0 for u in uids)
    assert len(merged["controls"]) == 5


def test_merging_the_same_profile_twice_adds_nothing_the_second_time() -> None:
    profile = {"controls": [_control("", "axis", 1, "Throttle")], "groups": []}
    first, result = ldf.merge_layout({"controls": [], "groups": []}, profile)
    second, again = ldf.merge_layout(first, profile)
    assert again.added == []
    assert again.uid_map == result.uid_map
    assert second == first


def test_merge_profile_rows_writes_the_file_when_something_was_added(
    modules: Path, writes: list
) -> None:
    rows = FakeRows()
    result = ldf.merge_profile_rows(
        {"controls": [_control("", "button", 2, "Fire")], "groups": []}, rows=rows
    )
    assert result.added == ["Fire"]
    doc = json.loads((modules / "logical_device.json").read_text(encoding="utf-8"))
    assert doc["logical-device"]["controls"][0]["uid"] == result.uid_map[("button", 2)]
    assert len(writes) == 1
    ldf.merge_profile_rows(
        {"controls": [_control("", "button", 2, "Fire")], "groups": []}, rows=rows
    )
    assert len(writes) == 1


def test_a_matching_row_only_in_memory_still_reaches_the_file(
    modules: Path, writes: list
) -> None:
    rows = FakeRows(
        {"controls": [_control("1" * 32, "axis", 1, "Throttle")], "groups": []}
    )
    result = ldf.merge_profile_rows(
        {"controls": [_control("", "axis", 1, "Throttle")], "groups": []}, rows=rows
    )
    assert result.added == [] and result.uid_map == {("axis", 1): "1" * 32}
    assert ldf.read_layout()["controls"][0]["uid"] == "1" * 32
    assert len(writes) == 1
    ldf.merge_profile_rows(
        {"controls": [_control("", "axis", 1, "Throttle")], "groups": []}, rows=rows
    )
    assert len(writes) == 1  # the file already holds it: nothing written


def test_a_dry_run_changes_nothing_and_agrees_with_the_real_merge(
    modules: Path, writes: list
) -> None:
    rows = FakeRows(
        {"controls": [_control("1" * 32, "axis", 1, "Throttle")], "groups": []}
    )
    before = rows.to_dict()
    profile = {
        "controls": [
            _control("", "axis", 1, "Throttle"),
            _control("", "axis", 1, "Rudder"),
        ],
        "groups": ["G"],
    }
    dry = ldf.merge_profile_rows(profile, dry_run=True, rows=rows)
    assert dry.added == ["Rudder"]
    assert rows.layout == before
    assert writes == [] and not (modules / "logical_device.json").exists()
    real = ldf.merge_profile_rows(profile, rows=rows)
    assert real.uid_map == dry.uid_map and real.added == dry.added


def test_a_carried_uid_is_kept_and_one_the_file_has_is_that_control() -> None:
    file_layout = {"controls": [_control("1" * 32, "button", 3, "Gear")], "groups": []}
    profile = {
        "controls": [
            _control("1" * 32, "button", 1, "Gear"),  # renumbered: same control by uid
            _control("9" * 32, "button", 2, "Flaps"),  # carried uid used when added
        ],
        "groups": [],
    }
    merged, result = ldf.merge_layout(file_layout, profile)
    assert result.uid_map == {("button", 1): "1" * 32, ("button", 2): "9" * 32}
    assert result.added == ["Flaps"]
    assert len(merged["controls"]) == 2


def test_backup_v14_is_made_once_beside_the_profile(tmp_path: Path) -> None:
    profile = tmp_path / "flight.xml"
    profile.write_text("<profile version='14'/>", encoding="utf-8")
    backup = ldf.backup_v14(profile)
    assert backup == tmp_path / "flight.xml.v14.bak"
    assert backup.read_text(encoding="utf-8") == "<profile version='14'/>"
    profile.write_text("<profile version='15'/>", encoding="utf-8")
    assert ldf.backup_v14(profile) is None
    assert backup.read_text(encoding="utf-8") == "<profile version='14'/>"


def test_current_uid_map_starts_empty() -> None:
    assert ldf.current_uid_map is None


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


@needs_model
def test_real_rows_merge_keeps_uids_and_adds(modules: Path, writes: list) -> None:
    from gremlin.types import InputType

    rows = LogicalRows()
    kept = rows.create(InputType.JoystickButton, 1, "Fire")
    result = ldf.merge_profile_rows(
        {
            "controls": [
                _control("", "button", 1, "Fire"),
                _control("", "button", 3, "Gear"),
            ],
            "groups": [],
        },
        rows=rows,
    )
    assert result.uid_map[("button", 1)] == kept.uid
    assert result.added == ["Gear"]
    gear = rows.by_uid(result.uid_map[("button", 3)])
    assert gear is not None and gear.label == "Gear" and gear.id == 3
    assert not rows.dirty
