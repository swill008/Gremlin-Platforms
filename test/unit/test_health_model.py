# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Health window's model (01 S197): Look in (default This profile only),
the four checks with counts from gremlin.health, lines grouped profile →
device with the ⚠ / Not plugged in facts, the Why panel, picking lines
(Ctrl/Shift), Remove binding… / Change target… on the picked lines and one
Undo for a change to several lines. The findings are the real
gremlin.health over a stand-in index; the edits a stand-in
gremlin.binding_edit that records the calls."""

from __future__ import annotations

import dataclasses
import sys
import types
import uuid
from collections.abc import Iterator

import pytest

import gremlin
from gremlin import health, shared_state
from gremlin import references as refs
from gremlin.search_index import SearchRow
from gremlin.types import InputType
from gremlin.ui import health_model
from gremlin.ui.health_model import HealthModel

_STICK = str(uuid.UUID("{61111111-2222-3333-4444-555555555555}"))
_GONE = str(uuid.UUID("{71111111-2222-3333-4444-555555555555}"))


def _row(input_id: int, **fields: object) -> SearchRow:
    target = ("vjoy", 1, int(InputType.JoystickButton.value), input_id)
    base: dict = {
        "source": "open",
        "source_name": "Elite",
        "source_path": "C:/p/Elite.xml",
        "device_guid": _STICK,
        "device_name": "T.16000M",
        "mode": "Default",
        "input_type": int(InputType.JoystickButton.value),
        "input_id": input_id,
        "input_label": f"Button {input_id}",
        "custom_name": "",
        "action_tag": "map-to-vjoy",
        "action_name": "Map to vJoy",
        "text": f"vJoy 1 Button {input_id}",
        "targets": (f"vJoy 1 Button {input_id}",),
        "target_keys": (target,),
        "role": "reads-input",
        "binding_index": 0,
        "path": (),
        "kinds": frozenset({"action", "vjoy"}),
        "references": (refs.Reference("sends-output", target),),
    }
    base.update(fields)
    known = {f.name for f in dataclasses.fields(SearchRow)}
    return SearchRow(**{k: v for k, v in base.items() if k in known})


def _missing(input_id: int, **fields: object) -> SearchRow:
    target = ("vjoy", 3, int(InputType.JoystickButton.value), input_id)
    return _row(
        input_id,
        target_keys=(target,),
        references=(refs.Reference("sends-output", target, why="vJoy 3 isn't there."),),
        **fields,
    )


BROKEN = _missing(1)
BROKEN_2 = _missing(2)
FINE = _row(3)
EMPTY = _row(
    4, action_tag="", action_name="", text="", targets=(), target_keys=(), references=()
)
UNPLUGGED = _row(5, device_guid=_GONE, device_name="HID Remapper 2DGG")
OTHER = _missing(6, source="profile", source_name="DCS", source_path="C:/p/DCS.xml")
LIBRARY = _row(
    7,
    source="library",
    source_name="Warthog setup",
    source_path="pack.zip",
    device_guid=_GONE,
)
ROWS = [BROKEN, BROKEN_2, FINE, EMPTY, UNPLUGGED, OTHER, LIBRARY]


class _Index:
    def __init__(self, rows: list[SearchRow]) -> None:
        self._rows = tuple(rows)
        self.listeners: list = []
        self.rebuilt: list = []

    def rows(self) -> tuple[SearchRow, ...]:
        return self._rows

    def set_rows(self, rows: list[SearchRow]) -> None:
        self._rows = tuple(rows)
        for callback in list(self.listeners):
            callback()

    def add_listener(self, callback: object) -> None:
        self.listeners.append(callback)

    def remove_listener(self, callback: object) -> None:
        if callback in self.listeners:
            self.listeners.remove(callback)

    def rebuild_open(self, profile: object) -> None:
        self.rebuilt.append(profile)


class _EditError(Exception):
    pass


class _Record:
    def __init__(self, name: str) -> None:
        self.name = name
        self.done = False


class _Edits(types.ModuleType):
    EditError = _EditError

    def __init__(self) -> None:
        super().__init__("gremlin.binding_edit")
        self.calls: list[tuple] = []
        self.refuse_on = -1  # refuse the n-th edit (0-based), -1 never
        self.refuse_undo = ""

    def describe(self, ref: SearchRow) -> str:
        return f"the Map to vJoy binding from {ref.input_label}"

    def remove_binding(self, ref: SearchRow) -> _Record:
        if len([c for c in self.calls if c[0] != "undo"]) == self.refuse_on:
            raise _EditError(f"{ref.input_label} is no longer in the profile.")
        self.calls.append(("remove", ref.input_id, ref.binding_index))
        return _Record(f"remove {ref.input_id}")

    def change_vjoy_target(
        self, ref: SearchRow, vjoy: int, kind: str, ctl: int
    ) -> _Record:
        self.calls.append(("change", ref.input_id, vjoy, kind, ctl))
        return _Record(f"change {ref.input_id}")

    def undo(self, record: _Record) -> None:
        if self.refuse_undo:
            raise _EditError(self.refuse_undo)
        record.done = True
        self.calls.append(("undo", record.name))

    def device_name(self, guid: str) -> str:
        return "HID Remapper 2DGG"


class _Profile:
    def __init__(self) -> None:
        self.unsaved = True
        self.inputs: dict = {}

    def has_unsaved_changes(self) -> bool:
        return self.unsaved


@pytest.fixture
def edits(monkeypatch: pytest.MonkeyPatch) -> _Edits:
    fake = _Edits()
    monkeypatch.setitem(sys.modules, "gremlin.binding_edit", fake)
    monkeypatch.setattr(gremlin, "binding_edit", fake, raising=False)
    return fake


@pytest.fixture
def profile(monkeypatch: pytest.MonkeyPatch) -> _Profile:
    made = _Profile()
    monkeypatch.setattr(shared_state, "current_profile", made, raising=False)
    return made


@pytest.fixture
def index(monkeypatch: pytest.MonkeyPatch) -> Iterator[_Index]:
    monkeypatch.setattr(health, "_plugged", lambda guid, name: guid != _GONE)
    monkeypatch.setattr(health_model, "_watching", True)
    made = _Index(ROWS)
    health.attach(made)  # type: ignore[arg-type]
    yield made
    health._reset_for_tests()


@pytest.fixture
def model(
    qapp: object, index: _Index, edits: _Edits, profile: _Profile
) -> Iterator[HealthModel]:
    made = HealthModel(index=index)
    yield made
    made.close()
    made.deleteLater()


def _lines(model: HealthModel) -> list[SearchRow]:
    return [item["_row"] for item in model._rows if "_row" in item]


def _at(model: HealthModel, row: SearchRow) -> int:
    for i, item in enumerate(model._rows):
        if item.get("_row") is row:
            return i
    raise AssertionError("line not shown")


def test_look_in_starts_on_this_profile_only(model: HealthModel) -> None:
    assert model.lookIn == "this"
    assert [s["label"] for s in model.scopes] == ["All profiles", "This profile only"]
    assert OTHER not in _lines(model)
    model.lookIn = "all"
    assert OTHER in _lines(model)
    # The Device Library is not a profile: never in Health.
    assert LIBRARY not in _lines(model)


def test_the_four_checks_with_counts_in_order(model: HealthModel) -> None:
    checks = model.checks
    assert [c["label"] for c in checks] == [
        "Binding output not found",
        "Used twice",
        "No bindings",
        "Not plugged in",
    ]
    counts = {c["name"]: c["count"] for c in checks}
    assert counts == {"notFound": 2, "usedTwice": 0, "noBindings": 1, "notPlugged": 1}
    assert all(c["on"] for c in checks)


def test_only_lines_with_a_ticked_problem_show(model: HealthModel) -> None:
    assert set(_lines(model)) == {BROKEN, BROKEN_2, EMPTY, UNPLUGGED}
    model.setCheck("notFound", False)
    assert set(_lines(model)) == {EMPTY, UNPLUGGED}
    model.setCheck("noBindings", False)
    model.setCheck("notPlugged", False)
    assert _lines(model) == []
    assert model.statusText == "0 problems in 0 profiles"


def test_grouped_profile_then_device_with_the_status_facts(model: HealthModel) -> None:
    kinds = [(item["rowKind"], item["title"]) for item in model._rows]
    assert kinds[0] == ("profile", "Elite (open)")
    assert ("device", "HID Remapper 2DGG") in kinds and ("device", "T.16000M") in kinds
    broken = model.get(_at(model, BROKEN))
    assert broken["notFound"] is True and broken["why"] == "vJoy 3 isn't there."
    assert broken["notPlugged"] is False
    unplugged = model.get(_at(model, UNPLUGGED))
    assert unplugged["notPlugged"] is True and unplugged["notFound"] is False
    assert model.statusText == "4 problems in 1 profile"
    model.lookIn = "all"
    assert model.statusText == "5 problems in 2 profiles"


def test_why_panel_has_the_reason_and_the_fix_with_links(model: HealthModel) -> None:
    why = model.why(_at(model, BROKEN))
    (found,) = why["findings"]
    assert found["label"] == "Binding output not found"
    assert found["why"] == "vJoy 3 isn't there."
    assert found["fix"] == health.FIXES["notFound"]
    assert '<a href="tools.drivers">Tools › Drivers</a>' in found["fixHtml"]
    assert model.why(0) == {}  # a heading


def test_click_ctrl_and_shift_pick_lines(model: HealthModel) -> None:
    a, b = _at(model, BROKEN), _at(model, BROKEN_2)
    c = _at(model, EMPTY)
    model.select(a, False, False)
    assert model.selectedRows == [a]
    model.select(c, True, False)
    assert model.selectedRows == sorted([a, c])
    model.select(c, True, False)
    assert model.selectedRows == [a]
    model.select(b, False, False)
    model.select(c, False, True)
    assert model.selectedRows == [
        i for i in sorted([b, c, a]) if min(b, c) <= i <= max(b, c)
    ]
    assert model.get(b)["selected"] is True
    model.clearSelection()
    assert model.selectedCount == 0


def test_fixes_for_the_picked_lines(model: HealthModel) -> None:
    model.select(_at(model, BROKEN), False, False)
    assert model.fixes() == {"remove": True, "changeTarget": True}
    model.select(_at(model, BROKEN_2), True, False)
    # Several lines: removed together; Change target… is for one line.
    assert model.fixes() == {"remove": True, "changeTarget": False}
    assert model.removeQuestion() == "Remove 2 bindings?"
    model.select(_at(model, EMPTY), True, False)
    # An input with no action has nothing to remove.
    assert model.fixes()["remove"] is False
    model.lookIn = "all"
    model.select(_at(model, OTHER), False, False)
    # Only the open profile can be changed.
    assert model.fixes() == {"remove": False, "changeTarget": False}


def test_removing_several_is_one_change_and_one_undo(
    model: HealthModel, edits: _Edits, index: _Index, profile: _Profile
) -> None:
    model.select(_at(model, BROKEN), False, False)
    model.select(_at(model, BROKEN_2), True, False)
    before = len(index.rebuilt)
    assert model.removeSelected() is True
    assert sorted(c[1] for c in edits.calls) == [1, 2]
    # The open profile is indexed again once for the whole change.
    assert index.rebuilt[before:] == [profile]
    assert model.canUndo is True
    assert model.undo() is True
    undone = [c for c in edits.calls if c[0] == "undo"]
    assert len(undone) == 2
    # Last done is undone first.
    assert undone[0][1] == f"remove {edits.calls[1][1]}"
    assert model.canUndo is False


def test_the_last_action_of_a_binding_goes_first(
    qapp: object, edits: _Edits, profile: _Profile, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = _missing(8, binding_index=0)
    second = _missing(8, binding_index=1, path=("1",))
    monkeypatch.setattr(health, "_plugged", lambda guid, name: True)
    monkeypatch.setattr(health_model, "_watching", True)
    idx = _Index([first, second])
    health.attach(idx)  # type: ignore[arg-type]
    made = HealthModel(index=idx)
    try:
        made.select(_at(made, first), False, False)
        made.select(_at(made, second), True, False)
        made.removeSelected()
        assert [c[2] for c in edits.calls] == [1, 0]
    finally:
        made.close()
        health._reset_for_tests()


def test_change_target_starts_on_the_lines_target(
    model: HealthModel, edits: _Edits
) -> None:
    model.select(_at(model, BROKEN), False, False)
    assert model.changeTargetStart() == {
        "vjoyId": 3,
        "inputType": "button",
        "inputId": 1,
    }
    assert model.changeTarget(1, "button", 9) is True
    assert edits.calls == [("change", 1, 1, "button", 9)]
    assert model.undo() is True


def test_a_refused_edit_says_why_and_keeps_what_was_done(
    model: HealthModel, edits: _Edits
) -> None:
    told: list = []
    model.editRefused.connect(lambda t, w: told.append((t, w)))
    edits.refuse_on = 1
    model.select(_at(model, BROKEN), False, False)
    model.select(_at(model, BROKEN_2), True, False)
    assert model.removeSelected() is False
    assert told and told[0][0] == "Can't change the binding"
    assert "no longer in the profile" in told[0][1]
    # The one that was removed can be undone.
    assert model.canUndo is True


def test_undo_ends_when_the_profile_is_saved(
    model: HealthModel, profile: _Profile
) -> None:
    model.select(_at(model, BROKEN), False, False)
    model.removeSelected()
    profile.unsaved = False
    assert model.canUndo is False
    assert model.undo() is False


def test_a_refused_undo_says_why_and_can_be_tried_again(
    model: HealthModel, edits: _Edits
) -> None:
    told: list = []
    model.editRefused.connect(lambda t, w: told.append((t, w)))
    model.select(_at(model, BROKEN), False, False)
    model.removeSelected()
    edits.refuse_undo = "The profile is running: stop it to undo."
    assert model.undo() is False
    assert told[-1][1] == "The profile is running: stop it to undo."
    edits.refuse_undo = ""
    assert model.undo() is True


def test_opening_reads_the_index_again(
    qapp: object, index: _Index, edits: _Edits, profile: _Profile
) -> None:
    refreshed: list = []
    index.refresh_sources = lambda: refreshed.append(1)  # type: ignore[attr-defined]
    made = HealthModel(index=index)
    try:
        assert index.rebuilt == [profile]
        assert refreshed == [1]
    finally:
        made.close()


def test_health_changes_show_again(
    qapp: object, model: HealthModel, index: _Index
) -> None:
    from PySide6 import QtCore

    index.set_rows([FINE])
    QtCore.QCoreApplication.processEvents()
    assert _lines(model) == []
    assert model.statusText == "0 problems in 0 profiles"


def test_copy_as_text_has_every_picked_line(
    model: HealthModel, monkeypatch: pytest.MonkeyPatch
) -> None:
    copied: list = []
    monkeypatch.setattr(health_model, "_set_clipboard", copied.append)
    model.select(_at(model, BROKEN), False, False)
    model.select(_at(model, UNPLUGGED), True, False)
    text = model.copyText()
    assert copied == [text]
    lines = text.split("\n")
    assert len(lines) == 2
    assert "Elite › T.16000M › Default › Button 1" in text
    assert "vJoy 3 isn't there." in text


def test_open_on_an_unplugged_device_says_why(model: HealthModel) -> None:
    assert "isn't plugged in" in model.openMessage(_at(model, UNPLUGGED))
    assert model.openMessage(_at(model, BROKEN)) == ""


def test_the_model_reads_no_health_rule_of_its_own() -> None:
    """One owner (01 S197): the model takes findings from gremlin.health."""
    import pathlib

    text = pathlib.Path(health_model.__file__).read_text(encoding="utf-8")
    for needle in ("references", ".missing", "plugged_in", "_RULES"):
        assert needle not in text, needle
