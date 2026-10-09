# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Logical Device rows: permanent ids, dict form and the changed flag
(decision D-04-LD-FILE; 06 S78)."""

from __future__ import annotations

import re
import sys

sys.path.append(".")

import pytest

from gremlin.common import InputType
from gremlin.logical_device import LogicalDevice, LogicalRows

_HEX32 = re.compile(r"^[0-9a-f]{32}$")
B = InputType.JoystickButton
A = InputType.JoystickAxis
H = InputType.JoystickHat


@pytest.fixture(autouse=True)
def reset_logical() -> None:
    LogicalDevice().reset()


def test_every_row_has_a_permanent_random_id() -> None:
    rows = LogicalRows()
    first = rows.create(B)
    second = rows.create(B)
    assert _HEX32.match(first.uid)
    assert first.uid != second.uid
    given = rows.create(A, uid="ab" * 16)
    assert given.uid == "ab" * 16


def test_id_kept_through_rename_regroup_move_and_sort() -> None:
    rows = LogicalRows()
    made = rows.create_many(B, 3, group="Left")
    uids = [item.uid for item in made]
    rows.set_label(made[0].label, "Fire")
    rows.set_user_label(made[1].identifier, "Trigger")
    rows.set_member_group(made[2].identifier, "Right")
    rows.rename_group("Left", "Port")
    rows.place(made[2].identifier, "Port", before=made[0].identifier)
    rows.sort_within("user")
    rows.sort_within("number")
    assert [rows.by_uid(uid) for uid in uids] == made
    assert sorted(item.uid for item in rows.ordered()) == sorted(uids)


def test_lookups_by_uid() -> None:
    rows = LogicalRows()
    rows.create(B)
    hat = rows.create(H)
    assert rows.by_uid(hat.uid) is hat
    assert rows.by_uid("0" * 32) is None
    assert rows.uid_of(H, 1) == hat.uid
    assert rows.uid_of(H, 2) is None
    assert rows.identifier_of_uid(hat.uid) == LogicalRows.Input.Identifier(H, 1)
    assert rows.identifier_of_uid("missing") is None
    rows.delete(hat.identifier)
    assert rows.by_uid(hat.uid) is None


def test_number_is_lowest_free_and_new_row_gets_new_uid() -> None:
    rows = LogicalRows()
    one, two, three = rows.create_many(B, 3)
    rows.delete(two.identifier)
    again = rows.create(B)
    assert again.id == 2
    assert again.uid not in (one.uid, two.uid, three.uid)


def test_to_dict_and_load_dict_round_trip() -> None:
    rows = LogicalRows()
    rows.set_groups(["Stick", "Empty"])
    axis = rows.create(A, group="Stick", user_label="Pitch")
    axis.hide_system = True
    button = rows.create(B)
    rows.set_label(button.label, "Fire")
    data = rows.to_dict()
    assert data["groups"] == ["Stick", "Empty"]
    assert data["controls"][0] == {
        "uid": axis.uid,
        "type": "axis",
        "id": 1,
        "label": "Axis 1",
        "user-label": "Pitch",
        "group": "Stick",
        "hide-system": True,
    }
    assert data["controls"][1]["type"] == "button"
    assert data["controls"][1]["label"] == "Fire"

    other = LogicalRows()
    other.create(H)
    other.load_dict(data)
    assert other.to_dict() == data
    assert other.uid_of(H, 1) is None
    assert other.by_uid(axis.uid).second_name == "Pitch"
    assert other.by_uid(axis.uid).hide_system is True


def test_load_dict_keeps_numbers_and_order() -> None:
    rows = LogicalRows()
    data = {
        "controls": [
            {"uid": "c" * 32, "type": "button", "id": 7, "label": "Button 7",
             "user-label": "", "group": "", "hide-system": False},
            {"uid": "d" * 32, "type": "button", "id": 2, "label": "Button 2",
             "user-label": "", "group": "", "hide-system": False},
        ],
        "groups": [],
    }
    rows.load_dict(data)
    found = [(item.id, item.uid) for item in rows.ordered()]
    assert found == [(7, "c" * 32), (2, "d" * 32)]
    assert rows.create(B).id == 1


def test_dirty_set_by_changes_cleared_by_mark_saved() -> None:
    rows = LogicalRows()
    rows.load_dict({"controls": [], "groups": []})
    assert rows.dirty is False
    item = rows.create(B)
    assert rows.dirty is True
    rows.mark_saved()
    assert rows.dirty is False

    changes = [
        lambda: rows.set_label(item.label, "Renamed"),
        lambda: rows.set_user_label(item.identifier, "Name"),
        lambda: setattr(item, "hide_system", True),
        lambda: rows.set_member_group(item.identifier, "G"),
        lambda: rows.rename_group("G", "H"),
        lambda: rows.place(item.identifier, ""),
        lambda: rows.move_group_before("H", None),
        lambda: rows.sort_within("number"),
        lambda: rows.sort_groups(),
        lambda: rows.delete_group("H"),
        lambda: rows.set_groups(["X"]),
        lambda: rows.ensure_group("Y"),
        lambda: rows.create_many(A, 2),
        lambda: rows.restore(rows.memento()),
        lambda: rows.delete(item.identifier),
        lambda: rows.reset(),
    ]
    for change in changes:
        rows.mark_saved()
        change()
        assert rows.dirty is True, change


def test_values_and_load_leave_it_clean() -> None:
    rows = LogicalRows()
    rows.create(A)
    rows.create(B)
    data = rows.to_dict()
    rows.load_dict(data)
    assert rows.dirty is False
    rows.by_uid(data["controls"][0]["uid"]).update(0.5)
    rows.by_uid(data["controls"][1]["uid"]).update(True)
    rows.reset_values()
    assert rows.dirty is False


def test_singleton_shares_flag_and_ids_with_bound_rows() -> None:
    rows = LogicalRows()
    item = rows.create(B)
    rows.mark_saved()
    shown = LogicalDevice()
    shown.bind(rows)
    assert shown.by_uid(item.uid) is item
    shown.create(B)
    assert rows.dirty is True


def test_undo_restore_brings_back_the_same_uid() -> None:
    rows = LogicalRows()
    item = rows.create(B)
    memo = rows.memento()
    rows.delete(item.identifier)
    rows.create(B)
    rows.restore(memo)
    assert rows.uid_of(B, 1) == item.uid
