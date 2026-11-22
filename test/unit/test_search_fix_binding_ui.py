# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Fix a binding from Search (01 S195), the Search window's side: what the
row menu and side panel offer (Remove binding… for an action of the open
profile, Change target… only for Map to vJoy), Remove's question, Change
target's start, Undo until the profile is saved or closed, and Open's
message for an unplugged device. The edits are gremlin.binding_edit's; a
stand-in records the calls (the real path is the end-to-end test's)."""

from __future__ import annotations

import pathlib
import sys
import types
from collections.abc import Iterator

import pytest

import gremlin
from gremlin import shared_state
from gremlin.ui import search_model
from gremlin.ui.search_model import SearchModel

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from test_search_model import ROWS, _Index, _row  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]

OPEN_VJOY = _row(
    source="open",
    source_name="Elite",
    source_path="C:/p/Elite.xml",
    target_keys=(("vjoy", 1, 3, 3),),
)
OPEN_KEY = _row(
    source="open",
    source_name="Elite",
    source_path="C:/p/Elite.xml",
    input_id=8,
    input_label="Button 8",
    action_tag="map-to-keyboard",
    action_name="Map to Keyboard",
    target_keys=(),
    targets=(),
)
UNPLUGGED = _row(
    source="open",
    source_name="Elite",
    source_path="C:/p/Elite.xml",
    device_name="HID Remapper 2DGG",
    input_id=9,
    input_label="Z Axis",
)


class _Profile:
    def __init__(self) -> None:
        self.unsaved = True
        # Read by other listeners (the can't-be-sent checks): no bindings.
        self.inputs: dict = {}

    def has_unsaved_changes(self) -> bool:
        return self.unsaved


class _EditError(Exception):
    pass


class _Record:
    def __init__(self, name: str) -> None:
        self.name = name
        self.done = False


class _Edits(types.ModuleType):
    """Stand-in gremlin.binding_edit."""

    EditError = _EditError

    def __init__(self) -> None:
        super().__init__("gremlin.binding_edit")
        self.calls: list[tuple] = []
        # The message every edit and undo is refused with ("": allowed).
        self.refuse = ""

    def _check(self) -> None:
        if self.refuse:
            raise _EditError(self.refuse)

    def describe(self, ref: object) -> str:
        return "the Map to vJoy binding from Z Axis of HID Remapper 2DGG (Default mode)"

    def remove_binding(self, ref: object) -> tuple:
        self._check()
        self.calls.append(("remove", ref))
        return ("undo-remove", ref)

    def change_vjoy_target(self, ref: object, vjoy: int, kind: str, ctl: int) -> tuple:
        self._check()
        self.calls.append(("change", ref, vjoy, kind, ctl))
        return ("undo-change", ref)

    def undo(self, record: object) -> None:
        self._check()
        self.calls.append(("undo", record))

    def device_name(self, guid: str) -> str:
        return "HID Remapper 2DGG"


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
def model(
    qapp: object, monkeypatch: pytest.MonkeyPatch, edits: _Edits, profile: _Profile
) -> Iterator[SearchModel]:
    monkeypatch.setattr(search_model, "_settings_load", dict)
    # The device list: only the HID Remapper is unplugged.
    monkeypatch.setattr(
        search_model, "_plugged", lambda row: row.device_name != UNPLUGGED.device_name
    )
    monkeypatch.setattr(search_model, "_settings_save", lambda _s: None)
    made = SearchModel(index=_Index([*ROWS, OPEN_VJOY, OPEN_KEY, UNPLUGGED]))
    made.searchFor("button")
    yield made
    made.close()
    made.deleteLater()


def _at(model: SearchModel, found: object) -> int:
    for i, item in enumerate(model._rows):
        if item.get("_row") is found:
            return i
    raise AssertionError("row not shown")


def test_a_map_to_vjoy_row_of_the_open_profile_offers_both(model: SearchModel) -> None:
    assert model.fixes(_at(model, OPEN_VJOY)) == {"remove": True, "changeTarget": True}


def test_change_target_is_only_for_map_to_vjoy(model: SearchModel) -> None:
    assert model.fixes(_at(model, OPEN_KEY)) == {"remove": True, "changeTarget": False}


def test_other_profiles_and_the_library_offer_neither(model: SearchModel) -> None:
    profile_row = _at(model, ROWS[0])
    assert model.fixes(profile_row) == {"remove": False, "changeTarget": False}
    assert model.removeQuestion(profile_row) == ""
    assert model.removeBinding(profile_row) is False


def test_remove_asks_the_spec_question_then_removes(
    model: SearchModel, edits: _Edits
) -> None:
    row = _at(model, UNPLUGGED)
    assert model.removeQuestion(row) == (
        "Remove the Map to vJoy binding from Z Axis of HID Remapper 2DGG "
        "(Default mode)?"
    )
    assert edits.calls == []  # asking changes nothing
    assert model.removeBinding(row) is True
    assert edits.calls == [("remove", UNPLUGGED)]
    assert model.canUndo is True


def test_an_edit_indexes_the_open_profile_again(
    model: SearchModel, profile: _Profile
) -> None:
    index = model.search_index()
    before = len(index.rebuilt)
    model.removeBinding(_at(model, OPEN_VJOY))
    assert index.rebuilt[before:] == [profile]


def test_change_target_starts_on_the_rows_vjoy_target_and_changes_it(
    model: SearchModel, edits: _Edits
) -> None:
    row = _at(model, OPEN_VJOY)
    assert model.changeTargetOf(row) == {
        "vjoyId": 1,
        "inputType": "button",
        "inputId": 3,
    }
    assert model.changeTargetOf(_at(model, OPEN_KEY)) == {}
    assert model.changeTarget(row, 2, "button", 5) is True
    assert edits.calls == [("change", OPEN_VJOY, 2, "button", 5)]
    assert model.changeTarget(_at(model, OPEN_KEY), 2, "button", 5) is False


def test_undo_puts_back_the_last_edit_first(model: SearchModel, edits: _Edits) -> None:
    model.removeBinding(_at(model, OPEN_VJOY))
    model.changeTarget(_at(model, OPEN_VJOY), 2, "button", 5)
    assert model.undo() is True
    assert model.undo() is True
    assert [c for c in edits.calls if c[0] == "undo"] == [
        ("undo", ("undo-change", OPEN_VJOY)),
        ("undo", ("undo-remove", OPEN_VJOY)),
    ]
    assert model.canUndo is False
    assert model.undo() is False


def test_undo_ends_when_the_profile_is_saved(
    model: SearchModel, edits: _Edits, profile: _Profile
) -> None:
    model.removeBinding(_at(model, OPEN_VJOY))
    profile.unsaved = False
    assert model.canUndo is False
    assert model.undo() is False
    assert not [c for c in edits.calls if c[0] == "undo"]


def test_undo_ends_when_another_profile_opens(
    model: SearchModel, edits: _Edits, monkeypatch: pytest.MonkeyPatch
) -> None:
    model.removeBinding(_at(model, OPEN_VJOY))
    monkeypatch.setattr(shared_state, "current_profile", _Profile())
    assert model.canUndo is False
    assert model.undo() is False


def test_open_on_an_unplugged_device_says_why(model: SearchModel) -> None:
    assert model.openMessage(_at(model, UNPLUGGED)) == (
        "HID Remapper 2DGG isn't plugged in, so its page can't open. Use "
        "Remove binding… or Change target… here, or plug it in."
    )
    assert model.openMessage(_at(model, OPEN_VJOY)) == ""


def test_the_window_asks_before_removing_and_shows_the_open_message() -> None:
    """The window's menu and side panel use the model's answers (no rules
    of their own): Remove asks through the one question box (Remove /
    Cancel), Open shows openMessage, Ctrl+Z undoes."""
    text = (ROOT / "qml" / "DialogSearch.qml").read_text(encoding="utf-8")
    for needle in (
        'text: "Remove binding…"',
        "visible: !!_rowMenu.fixes.remove",
        'text: "Change target…"',
        "visible: !!_rowMenu.fixes.changeTarget",
        "Confirm.ask(_root",
        'action: "Remove"',
        "onAccept: function() { _model.removeBinding(index) }",
        "_model.openMessage(index)",
        "sequences: [StandardKey.Undo]",
        "VJoySelector {",
    ):
        assert needle in text, needle
    detail = (ROOT / "qml" / "search" / "SearchDetail.qml").read_text(encoding="utf-8")
    for needle in (
        '"searchDetailRemove"',
        '"searchDetailChangeTarget"',
        '"searchDetailUndo"',
    ):
        assert needle in detail, needle


_RUNNING = "The profile is running: stop it to change its bindings."


def _told(model: SearchModel) -> list[tuple[str, str]]:
    got: list[tuple[str, str]] = []
    model.editRefused.connect(lambda title, why: got.append((title, why)))
    return got


def test_a_refused_remove_or_change_says_why(model: SearchModel, edits: _Edits) -> None:
    told = _told(model)
    edits.refuse = _RUNNING
    assert model.removeBinding(_at(model, OPEN_VJOY)) is False
    assert model.changeTarget(_at(model, OPEN_VJOY), 2, "button", 5) is False
    assert told == [("Can't change the binding", _RUNNING)] * 2
    assert model.canUndo is False  # nothing was changed


def test_a_refused_undo_says_why_and_can_be_tried_again(
    model: SearchModel, edits: _Edits
) -> None:
    model.removeBinding(_at(model, OPEN_VJOY))
    told = _told(model)
    edits.refuse = "The profile is running: stop it to undo."
    assert model.undo() is False
    assert told == [
        ("Can't change the binding", "The profile is running: stop it to undo.")
    ]
    assert model.canUndo is True
    edits.refuse = ""
    assert model.undo() is True


def test_an_unexpected_failure_still_says_so(
    model: SearchModel, edits: _Edits, monkeypatch: pytest.MonkeyPatch
) -> None:
    told = _told(model)

    def broken(_ref: object) -> None:
        raise ValueError("boom")

    monkeypatch.setattr(edits, "remove_binding", broken)
    assert model.removeBinding(_at(model, OPEN_VJOY)) is False
    assert told == [
        (
            "Can't change the binding",
            "The binding could not be changed. The log has the details.",
        )
    ]
