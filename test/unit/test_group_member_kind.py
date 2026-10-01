# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from gremlin.ui import device_pack
from gremlin.ui.hardware_profile import _filter_nodes, member_kind

# Axis 5, Hat 1 and Axis 4 grouped together: used to read as Buttons 5, 1, 4.
_MIXED = {
    "id": "g1",
    "kind": "stack",
    "members": [
        {"hwId": 5, "kind": "axis"},
        {"hwId": 1, "kind": "hat"},
        {"hwId": 4, "kind": "axis"},
    ],
}


def test_members_keep_their_own_kind() -> None:
    kinds = [member_kind(_MIXED, m) for m in _MIXED["members"]]
    assert kinds == ["axis", "hat", "axis"]


def test_members_saved_without_a_kind_follow_the_group() -> None:
    assert member_kind({"kind": "axis_stack"}, {"hwId": 2}) == "axis"
    assert member_kind({"kind": "stack"}, {"hwId": 2}) == "btn"
    assert member_kind({"kind": "stack"}, {"hwId": 2, "kind": "button"}) == "btn"


def test_filter_keeps_members_by_their_own_kind() -> None:
    # Claim has axes 4 and 5 and hat 1, but no buttons.
    kept = _filter_nodes([_MIXED], buttons=set(), axes={4, 5}, hats={1}, keys=set())
    assert [m["hwId"] for m in kept[0]["members"]] == [5, 1, 4]


def test_device_pack_sees_the_real_controls() -> None:
    assert device_pack._node_controls(_MIXED) == {("axis", 5), ("hat", 1), ("axis", 4)}
