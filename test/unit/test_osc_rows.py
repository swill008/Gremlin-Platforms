# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""OSC's address list (D-09-OSC-FILE, D-09-OSC-INPUT): uids, numbers,
per-input settings, matching and the module-file dict format."""

from __future__ import annotations

import pytest

from gremlin.error import GremlinError
from gremlin.osc_rows import OscRow, OscRows
from gremlin.types import InputType

AXIS = InputType.JoystickAxis
BUTTON = InputType.JoystickButton


def test_new_rows_get_lowest_free_numbers_per_type_and_permanent_uids() -> None:
    rows = OscRows()
    a = rows.create(BUTTON, "/a")
    b = rows.create(BUTTON, "/b")
    x = rows.create(AXIS, "/x")
    assert (a.input_id, b.input_id, x.input_id) == (1, 2, 1)
    assert len({a.uid, b.uid, x.uid}) == 3 and len(a.uid) == 32
    rows.delete(a.uid)
    c = rows.create(BUTTON, "/c")
    assert c.input_id == 1 and c.uid != a.uid
    assert rows.uid_of(BUTTON, 1) == c.uid
    assert rows.identifier_of_uid(b.uid) == (BUTTON, 2)
    assert rows.by_number(AXIS, 1) is x
    assert rows.identifier_of_uid("missing") is None
    assert rows.uid_of(AXIS, 9) is None


def test_defaults_follow_the_table() -> None:
    row = OscRows().create(BUTTON, "/a")
    assert (row.mode, row.cmd_mode, row.data) == ("button", "message", [])
    assert row.source == 0
    assert (row.range_min, row.range_max) == (0.0, 1.0)
    assert (row.trigger, row.delay_ms) == (None, None)
    assert OscRows().create(AXIS, "/x").mode == "axis"


def test_addresses_are_checked_and_duplicates_refused() -> None:
    rows = OscRows()
    for bad in ("", "   ", "a/b"):
        with pytest.raises(GremlinError):
            rows.create(BUTTON, bad)
    first = rows.create(BUTTON, "/Same")
    with pytest.raises(GremlinError):
        rows.create(BUTTON, "/same")
    other = rows.create(BUTTON, "/other")
    with pytest.raises(GremlinError):
        rows.set_label(other.uid, "/SAME")
    with pytest.raises(GremlinError):
        rows.set_label(other.uid, "no-slash")
    rows.set_label(first.uid, "/renamed")
    assert first.label == "/renamed" and first.uid == rows.uid_of(BUTTON, 1)


def test_several_inputs_share_an_address_when_data_or_source_differ() -> None:
    rows = OscRows()
    on = rows.create(BUTTON, "/scene", cmd_mode="data", data=["1"])
    off = rows.create(BUTTON, "/scene", cmd_mode="data", data=["0"])
    left = rows.create(AXIS, "/xy", source=0)
    right = rows.create(AXIS, "/xy", source=1)
    with pytest.raises(GremlinError):
        rows.create(BUTTON, "/scene", cmd_mode="data", data=["1.0"])
    assert rows.matches("/SCENE", (1,)) == [on]
    assert rows.matches("/scene", ("0",)) == [off]
    assert rows.matches("/scene", (2,)) == []
    assert rows.matches("/scene", ()) == []
    assert rows.matches("/xy", (0.2, 0.4)) == [left, right]
    assert rows.matches("/nothing", ()) == []


def test_data_mode_compares_numbers_as_numbers_else_text() -> None:
    rows = OscRows()
    row = rows.create(BUTTON, "/a", cmd_mode="data", data=["1", "go"])
    assert rows.matches("/a", (1.0, "go")) == [row]
    assert rows.matches("/a", ("1.00", "go")) == [row]
    assert rows.matches("/a", (1, "Go")) == []
    assert rows.matches("/a", (1,)) == []
    message = rows.create(BUTTON, "/b")
    assert rows.matches("/b", ("anything", 5)) == [message]


def test_update_validates_settings_and_keeps_uid() -> None:
    rows = OscRows()
    row = rows.create(BUTTON, "/a")
    rows.mark_saved()
    for bad in (
        {"mode": "spin"},
        {"cmd_mode": "both"},
        {"data": "1"},
        {"source": -1},
        {"source": True},
        {"range_min": "x"},
        {"trigger": "yes"},
        {"delay_ms": -5},
        {"delay_ms": 1.5},
        {"colour": 1},
        {"range_max": 0.0},
    ):
        with pytest.raises(GremlinError):
            rows.update(row.uid, **bad)
    assert not rows.dirty
    rows.update(row.uid, trigger=True, delay_ms=100, mode="change", data=[1, 2])
    assert (row.trigger, row.delay_ms) == (True, 100)
    assert (row.mode, row.data) == ("change", ["1", "2"])
    assert rows.dirty


def test_mode_change_to_axis_moves_type_and_number_but_keeps_uid() -> None:
    rows = OscRows()
    rows.create(AXIS, "/x")
    row = rows.create(BUTTON, "/b")
    uid = row.uid
    rows.update(uid, mode="axis", range_min=-1.0, range_max=1.0)
    assert rows.identifier_of_uid(uid) == (AXIS, 2)
    assert rows.by_number(BUTTON, 1) is None
    with pytest.raises(GremlinError):
        rows.create(AXIS, "/y", mode="button")


def test_dict_round_trip_keeps_uids_numbers_and_settings() -> None:
    rows = OscRows()
    rows.create(BUTTON, "/a", trigger=False, delay_ms=40)
    rows.create(AXIS, "/x", range_min=-1.0, range_max=1.0, source=2)
    rows.create(BUTTON, "/s", cmd_mode="data", data=["3"], input_id=7)
    data = rows.to_dict()
    assert set(data) == {"inputs"}
    assert set(data["inputs"][0]) == {
        "uid",
        "type",
        "id",
        "label",
        "mode",
        "cmd_mode",
        "data",
        "source",
        "range_min",
        "range_max",
        "trigger",
        "delay_ms",
        "enc_format",
        "enc_step",
        "enc_output",
        "invert",
        "deadzone",
        "enc_accel",
    }
    assert data["inputs"][1]["type"] == "axis" and data["inputs"][2]["id"] == 7
    other = OscRows()
    other.load_dict(data)
    assert other.to_dict() == data
    assert not other.dirty and other.load_warnings == []
    assert all(isinstance(r, OscRow) for r in other.rows())


def test_load_dict_fills_defaults_and_skips_bad_entries() -> None:
    rows = OscRows()
    rows.load_dict(
        {
            "inputs": [
                {"uid": "u1", "type": "button", "id": 1, "label": "/a"},
                {"uid": "u2", "type": "button", "id": 2, "label": "no-slash"},
                {"uid": "u3", "type": "button", "id": 3, "label": "/a"},
                {"uid": "u1", "type": "button", "id": 4, "label": "/b"},
                {"uid": "u5", "type": "axis", "id": 1, "label": "/x", "mode": "spin"},
            ],
            "server": {"port": 9},
        }
    )
    assert [r.uid for r in rows.rows()] == ["u1"]
    assert rows.rows()[0].cmd_mode == "message"
    assert len(rows.load_warnings) == 4
    assert not rows.dirty


def test_dirty_tracks_edits_and_mark_saved_clears_it() -> None:
    rows = OscRows()
    assert not rows.dirty
    row = rows.create(BUTTON, "/a")
    assert rows.dirty
    rows.mark_saved()
    rows.set_label(row.uid, "/a")
    rows.update(row.uid, mode="button")
    assert not rows.dirty
    rows.delete(row.uid)
    assert rows.dirty


# -- address patterns (D-09-OSC-PATTERNS, S147-S148) ----------------------


def test_pattern_rows_answer_every_matching_address() -> None:
    rows = OscRows()
    fader = rows.create(AXIS, "/fader/*")
    assert fader.is_pattern and not rows.create(BUTTON, "/go").is_pattern
    assert rows.matches("/FADER/3", (0.5,)) == [fader]
    assert rows.matches("/fader/3/x", (0.5,)) == []


def test_exact_input_wins_over_patterns_and_overlapping_patterns_all_fire() -> None:
    rows = OscRows()
    star = rows.create(AXIS, "/fader/*")
    one = rows.create(AXIS, "/fader/?")
    exact = rows.create(AXIS, "/fader/1")
    assert rows.matches("/fader/1", (0.1,)) == [exact]
    assert rows.matches("/fader/2", (0.1,)) == [star, one]
    assert rows.matches("/fader/22", (0.1,)) == [star]


def test_exact_data_row_that_does_not_match_leaves_it_to_patterns() -> None:
    rows = OscRows()
    exact = rows.create(BUTTON, "/scene", cmd_mode="data", data=["1"])
    star = rows.create(BUTTON, "/sc*")
    assert rows.matches("/scene", (1,)) == [exact]
    assert rows.matches("/scene", (2,)) == [star]


def test_an_incoming_pattern_reaches_exact_inputs_only() -> None:
    rows = OscRows()
    a = rows.create(BUTTON, "/btn/a")
    b = rows.create(BUTTON, "/btn/b")
    rows.create(BUTTON, "/btn/*")
    rows.create(BUTTON, "/other")
    assert rows.matches("/btn/[ab]") == [a, b]
    assert rows.matches("/BTN/?") == [a, b]
    assert rows.matches("/nothing/*") == []
    assert rows.matches("/btn/[") == []


def test_answered_by_ignores_data_and_covers_patterns() -> None:
    rows = OscRows()
    data = rows.create(BUTTON, "/scene", cmd_mode="data", data=["1"])
    star = rows.create(AXIS, "/fader/*")
    assert rows.answered_by("/Scene") == [data]
    assert rows.answered_by("/fader/9") == [star]
    assert rows.answered_by("/new") == []


def test_index_follows_rename_delete_load_and_reset() -> None:
    rows = OscRows()
    row = rows.create(BUTTON, "/a")
    rows.set_label(row.uid, "/b/*")
    assert rows.matches("/a") == [] and rows.matches("/b/x") == [row]
    rows.set_label(row.uid, "/c")
    assert rows.matches("/b/x") == [] and rows.matches("/c") == [row]
    rows.delete(row.uid)
    assert rows.matches("/c") == []
    other = OscRows()
    other.create(BUTTON, "/p/*")
    rows.load_dict(other.to_dict())
    assert [r.label for r in rows.matches("/p/q")] == ["/p/*"]
    rows.reset()
    assert rows.matches("/p/q") == []


def test_patterns_compile_once_not_per_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin import osc_pattern

    rows = OscRows()
    rows.create(AXIS, "/fader/*")
    calls = []
    real = osc_pattern.compile
    monkeypatch.setattr(
        osc_pattern, "compile", lambda text: calls.append(text) or real(text)
    )
    for _ in range(5):
        rows.matches("/fader/1", (0.5,))
    assert calls == []


def test_bad_patterns_are_refused_with_the_reason() -> None:
    rows = OscRows()
    with pytest.raises(GremlinError, match="never closed"):
        rows.create(BUTTON, "/a[b")
    row = rows.create(BUTTON, "/ok")
    with pytest.raises(GremlinError, match="backwards"):
        rows.set_label(row.uid, "/x[z-a]")
    with pytest.raises(GremlinError, match="space"):
        rows.create(BUTTON, "/a b")


def test_duplicate_rule_stays_literal_for_patterns() -> None:
    rows = OscRows()
    rows.create(AXIS, "/fader/*")
    rows.create(AXIS, "/fader/1")
    rows.create(AXIS, "/fader/?")
    with pytest.raises(GremlinError):
        rows.create(AXIS, "/FADER/*")
