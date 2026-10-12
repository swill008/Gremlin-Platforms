# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""05 S125: the Device Bindings Appearance is saved per device.

A device with no look of its own uses the shared page entry; saving on a
device writes only that device's entry; "Apply to all devices" writes the
shared entry and clears every device entry of that page. Scope "" is the
plain per-page store other pages use.
"""

from __future__ import annotations

import json
from collections.abc import Iterator

import pytest

from gremlin.ui import window_placement as wp

PAGE = "device-bindings"
DEV_A = "{AAAA-1111}"
DEV_B = "{BBBB-2222}"


@pytest.fixture
def clean() -> Iterator[None]:
    wp.set_list_appearance(PAGE, {})
    wp.set_list_appearance("logical", {})
    wp.apply_list_appearance_to_all(PAGE, {})
    yield
    wp.apply_list_appearance_to_all(PAGE, {})
    wp.set_list_appearance("logical", {})


def _saved() -> dict:
    return wp._all_list_appearances()


def test_a_device_without_its_own_uses_the_shared_entry(clean: None) -> None:
    assert wp.list_appearance_for(PAGE, DEV_A) == {}
    wp.set_list_appearance(PAGE, {"rowHeight": 30})
    assert wp.list_appearance_for(PAGE, DEV_A) == {"rowHeight": 30}
    assert not wp.has_own_list_appearance(PAGE, DEV_A)


def test_the_device_entry_wins(clean: None) -> None:
    wp.set_list_appearance(PAGE, {"rowHeight": 30})
    wp.set_list_appearance_for(PAGE, DEV_A, {"rowHeight": 40})
    assert wp.list_appearance_for(PAGE, DEV_A) == {"rowHeight": 40}
    assert wp.has_own_list_appearance(PAGE, DEV_A)
    assert wp.list_appearance_for(PAGE, DEV_B) == {"rowHeight": 30}


def test_saving_one_device_leaves_the_others_alone(clean: None) -> None:
    wp.set_list_appearance(PAGE, {"rowHeight": 30})
    wp.set_list_appearance("logical", {"rowHeight": 22})
    wp.set_list_appearance_for(PAGE, DEV_B, {"rowHeight": 50})
    wp.set_list_appearance_for(PAGE, DEV_A, {"rowHeight": 40})
    saved = _saved()
    assert saved[PAGE] == {"rowHeight": 30}
    assert saved["logical"] == {"rowHeight": 22}
    assert saved[f"{PAGE}/{DEV_B}"] == {"rowHeight": 50}
    assert saved[f"{PAGE}/{DEV_A}"] == {"rowHeight": 40}


def test_an_empty_save_removes_the_device_entry(clean: None) -> None:
    wp.set_list_appearance(PAGE, {"rowHeight": 30})
    wp.set_list_appearance_for(PAGE, DEV_A, {"rowHeight": 40})
    wp.set_list_appearance_for(PAGE, DEV_A, {})
    assert f"{PAGE}/{DEV_A}" not in _saved()
    assert not wp.has_own_list_appearance(PAGE, DEV_A)
    assert wp.list_appearance_for(PAGE, DEV_A) == {"rowHeight": 30}
    assert _saved()[PAGE] == {"rowHeight": 30}


def test_apply_to_all_writes_shared_and_clears_device_entries(
    clean: None,
) -> None:
    wp.set_list_appearance("logical", {"rowHeight": 22})
    wp.set_list_appearance_for("logical", DEV_A, {"rowHeight": 23})
    wp.set_list_appearance_for(PAGE, DEV_A, {"rowHeight": 40})
    wp.set_list_appearance_for(PAGE, DEV_B, {"rowHeight": 50})
    wp.apply_list_appearance_to_all(PAGE, {"rowHeight": 60})
    saved = _saved()
    assert saved[PAGE] == {"rowHeight": 60}
    assert not [k for k in saved if k.startswith(f"{PAGE}/")]
    assert saved["logical"] == {"rowHeight": 22}
    assert saved[f"logical/{DEV_A}"] == {"rowHeight": 23}
    assert wp.list_appearance_for(PAGE, DEV_A) == {"rowHeight": 60}
    wp.apply_list_appearance_to_all(PAGE, {})
    assert PAGE not in _saved()
    wp.set_list_appearance_for("logical", DEV_A, {})


def test_scope_empty_is_the_plain_page_store(clean: None) -> None:
    wp.set_list_appearance_for(PAGE, "", {"rowHeight": 33})
    assert wp.list_appearance(PAGE) == {"rowHeight": 33}
    assert wp.list_appearance_for(PAGE, "") == {"rowHeight": 33}
    assert not wp.has_own_list_appearance(PAGE, "")
    assert not [k for k in _saved() if k.startswith(f"{PAGE}/")]
    wp.set_list_appearance_for(PAGE, "", {})
    assert PAGE not in _saved()


def test_the_qml_slots(clean: None) -> None:
    placement = wp.WindowPlacement()
    placement.setListAppearance(PAGE, json.dumps({"rowHeight": 30}))
    assert json.loads(placement.listAppearanceFor(PAGE, DEV_A)) == {
        "rowHeight": 30
    }
    assert placement.hasOwnListAppearance(PAGE, DEV_A) is False
    placement.setListAppearanceFor(PAGE, DEV_A, json.dumps({"rowHeight": 40}))
    assert json.loads(placement.listAppearanceFor(PAGE, DEV_A)) == {
        "rowHeight": 40
    }
    assert placement.hasOwnListAppearance(PAGE, DEV_A) is True
    placement.setListAppearanceFor(PAGE, DEV_A, "[1]")  # ignored
    placement.setListAppearanceFor(PAGE, DEV_A, "not json")
    assert wp.list_appearance_for(PAGE, DEV_A) == {"rowHeight": 40}
    placement.applyListAppearanceToAll(PAGE, json.dumps({"rowHeight": 60}))
    assert placement.hasOwnListAppearance(PAGE, DEV_A) is False
    assert json.loads(placement.listAppearance(PAGE)) == {"rowHeight": 60}
    placement.applyListAppearanceToAll(PAGE, "nope")  # ignored
    assert json.loads(placement.listAppearanceFor(PAGE, DEV_B)) == {
        "rowHeight": 60
    }
