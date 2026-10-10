# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Feedback rows on the OSC page (OSC batch 2, OX8).

OscLayoutModel shows the feedback rows of OSC's file as child rows of kind
"feedback" after an input's actions (S153, S156), the rest under the fixed
group "Feedback not tied to an input" at the bottom; each edit is a page
Undo step and works while a profile runs (S155); the pane's Feedback editor
refuses a pattern as an outgoing address (S149) and says when an action
isn't in the current profile (S158).

Spec: 09 S149, S153-S158.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from gremlin import osc_device_file, osc_pattern, shared_state
from gremlin.osc import OscDevice, OscRuntime
from gremlin.profile import Profile
from gremlin.types import InputType
from gremlin.ui import control_layout, osc_device_model, osc_feedback_model
from gremlin.ui.osc_layout import FEEDBACK_GROUP, FEEDBACK_GROUP_TITLE, OscLayoutModel


@pytest.fixture
def modules(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    from gremlin.modules import store

    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setattr(store, "folder", lambda: folder)
    return folder


@pytest.fixture
def page(qapp: object, modules: Path) -> Iterator[OscLayoutModel]:
    OscDevice().rows.reset()
    OscRuntime().reset_live()
    saved = shared_state.current_profile
    shared_state.current_profile = Profile()
    model = OscLayoutModel()
    yield model
    model.endPane()
    model.endFeedback()
    OscDevice().rows.reset()
    OscRuntime().reset_live()
    shared_state.current_profile = saved


def _add(address: str, **settings: Any) -> str:  # noqa: ANN401
    row, error = osc_device_model.add_input({"address": address, **settings})
    assert row is not None and not error, error
    osc_device_model._emit_modified()
    return row.uid


def _key(address: str) -> str:
    row = OscDevice().find_address(address)
    assert row is not None
    word = "axis" if row.input_type == InputType.JoystickAxis else "button"
    return f"parent:{word}:{row.input_id}"


def _rows(model: OscLayoutModel) -> list[dict]:
    names = {int(k): bytes(v.data()).decode() for k, v in model.roleNames().items()}
    out = []
    for r in range(model.rowCount()):
        index = model.index(r, 0)
        out.append({name: model.data(index, role) for role, name in names.items()})
    return out


def _write(*rows: dict) -> list[dict]:
    base = osc_feedback_model.new_row()
    full = []
    for given in rows:
        row = dict(base, **given)
        row["id"] = osc_device_file.new_id()
        full.append(row)
    osc_device_file.write_feedback(full)
    return osc_device_file.read_feedback()


def test_a_feedback_row_shows_under_its_input_after_the_actions(
    page: OscLayoutModel,
) -> None:
    uid = _add("/deck/1")
    [row] = _write(
        {
            "source": {"kind": "osc_input", "device": None, "input": uid},
            "address": "/deck/1",
        }
    )
    rows = _rows(page)
    keys = [r["key"] for r in rows]
    parent = rows[keys.index(_key("/deck/1"))]
    fb = rows[keys.index(f"feedback:{row['id']}")]
    assert keys.index(fb["key"]) == keys.index(parent["key"]) + 1
    assert fb["rowKind"] == "feedback"
    assert fb["parentKey"] == parent["key"]
    assert fb["title"] == "Sends this input's value to the sender · /deck/1"
    assert fb["enabled"] is True and fb["feedbackId"] == row["id"]
    # No actions, one feedback row: the input still gets a caret.
    assert parent["childCount"] == 1
    assert FEEDBACK_GROUP not in keys


def test_rows_tied_to_no_input_go_to_the_fixed_group_at_the_bottom(
    page: OscLayoutModel,
) -> None:
    uid = _add("/deck/1")
    loose, under = _write(
        {"address": "/gremlin/mode"},
        {"address": "/gremlin/mode2", "input": uid},
    )
    rows = _rows(page)
    keys = [r["key"] for r in rows]
    assert keys[-2:] == [FEEDBACK_GROUP, f"feedback:{loose['id']}"]
    group = rows[-2]
    assert group["title"] == FEEDBACK_GROUP_TITLE
    assert group["rowKind"] == "group" and group["fixedGroup"] is True
    assert group["groupName"] == "" and group["childCount"] == 1
    assert rows[-1]["title"] == "Sends the mode to the sender · /gremlin/mode"
    # "Show under this input" puts the other row under /deck/1 (S153).
    shown = rows[keys.index(f"feedback:{under['id']}")]
    assert shown["parentKey"] == _key("/deck/1")
    # A filter other than the search text hides the bottom group.
    page.setFilter("", "axis", False, False, False)
    assert FEEDBACK_GROUP not in [r["key"] for r in _rows(page)]


def test_add_duplicate_turn_off_and_delete_are_page_undo_steps(
    page: OscLayoutModel,
) -> None:
    uid = _add("/deck/1")
    key = page.addFeedback(_key("/deck/1"))
    [row] = osc_device_file.read_feedback()
    assert key == f"feedback:{row['id']}"
    assert row["source"] == {"kind": "osc_input", "device": None, "input": uid}
    assert row["target"] == osc_device_file.REPLY and row["address"] == "/deck/1"
    assert page.lastChange.endswith("Add Feedback to /deck/1")

    twin = page.duplicateFeedback(key)
    assert twin and [r["id"] for r in osc_device_file.read_feedback()][0] == row["id"]
    assert page.setFeedbackEnabled(twin, False)
    assert osc_device_file.read_feedback()[1]["enabled"] is False
    assert page.deleteFeedback(key)
    assert len(osc_device_file.read_feedback()) == 1

    page.undo()  # delete
    page.undo()  # turn off
    page.undo()  # duplicate
    assert [r["id"] for r in osc_device_file.read_feedback()] == [row["id"]]
    page.undo()  # add
    assert osc_device_file.read_feedback() == []
    page.redo()
    assert [r["id"] for r in osc_device_file.read_feedback()] == [row["id"]]


def test_feedback_edits_and_their_undo_work_while_a_profile_runs(
    page: OscLayoutModel, monkeypatch: pytest.MonkeyPatch
) -> None:
    _add("/deck/1")
    monkeypatch.setattr(control_layout, "editing_locked", lambda: True)
    steps = len(page._undo)
    page.addGroup("Nope")  # a layout edit: refused while running
    assert len(page._undo) == steps
    key = page.addFeedback(_key("/deck/1"))
    assert key and len(osc_device_file.read_feedback()) == 1
    page.undo()
    assert osc_device_file.read_feedback() == []
    page.redo()
    assert len(osc_device_file.read_feedback()) == 1


def test_the_editor_refuses_a_pattern_address_and_commits_one_step(
    page: OscLayoutModel,
) -> None:
    _add("/deck/1")
    key = page.addFeedback(_key("/deck/1"))
    editor = page.beginFeedback(key)
    assert editor["address"] == "/deck/1" and editor["kind"] == "osc_input"
    assert {c["value"] for c in editor["choices"]["kinds"]} >= {
        "action_state",
        "paused",
    }
    assert page.setFeedbackField("address", "/fader/*") == osc_pattern.NO_PATTERN
    assert page.feedbackEditor["error"] == osc_pattern.NO_PATTERN
    assert page.setFeedbackField("address", "/deck/1/led") == ""
    assert page.setFeedbackField("max", "127") == ""
    assert page.feedbackDirty()
    # Nothing written before OK.
    assert osc_device_file.read_feedback()[0]["address"] == "/deck/1"
    steps = len(page._undo)
    assert page.commitFeedback()
    stored = osc_device_file.read_feedback()[0]
    assert stored["address"] == "/deck/1/led" and stored["max"] == 127.0
    assert len(page._undo) == steps + 1 and not page.feedbackDirty()
    page.undo()
    assert osc_device_file.read_feedback()[0]["address"] == "/deck/1"
    # The open editor follows the Undo.
    assert page.feedbackEditor["address"] == "/deck/1"
    page.setFeedbackField("address", "/x")
    page.discardFeedback()
    assert page.feedbackEditor["address"] == "/deck/1"


def test_an_action_state_row_whose_action_is_missing_says_so(
    page: OscLayoutModel,
) -> None:
    [row] = _write(
        {
            "source": {"kind": "action_state", "action": "not-a-real-action"},
            "address": "/gear",
        }
    )
    [fb] = [r for r in _rows(page) if r["key"] == f"feedback:{row['id']}"]
    assert fb["subtitle"] == osc_feedback_model.ACTION_MISSING
    assert fb["parentKey"] == FEEDBACK_GROUP
    editor = page.beginFeedback(fb["key"])
    assert editor["note"] == osc_feedback_model.ACTION_MISSING
    assert page.setFeedbackField("kind", "paused") == ""
    assert page.feedbackEditor["note"] == ""
