# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Batch 3, L3: the input name lives in InputItem (GL-258, 05 Q15, RB5, S77)."""

from __future__ import annotations

import sys

sys.path.append(".")

import uuid
from xml.etree import ElementTree

from gremlin.profile import InputItem, Profile
from gremlin.types import InputType


def _item(profile: Profile) -> InputItem:
    item = InputItem(profile.library)
    item.device_id = uuid.UUID("12345678-1234-1234-1234-123456789abc")
    item.input_type = InputType.JoystickButton
    item.input_id = 3
    item.mode = "Default"
    return item


def test_the_input_name_is_part_of_input_item_not_patched_in() -> None:
    import gremlin.action_label  # noqa: F401  (used to patch InputItem)

    for name in ("__init__", "from_xml", "to_xml"):
        assert getattr(InputItem, name).__module__ == "gremlin.profile", name


def test_the_input_name_round_trips_through_the_saved_xml() -> None:
    profile = Profile()
    item = _item(profile)
    assert item.action_name == ""
    item.action_name = "Gear up"

    node = item.to_xml()
    names = node.findall("action-name")
    assert [n.text for n in names] == ["Gear up"]
    # Same place as before: after the input fields and actions.
    assert list(node)[-1].tag == "action-name"

    again = InputItem(profile.library)
    again.from_xml(ElementTree.fromstring(ElementTree.tostring(node)))
    assert again.action_name == "Gear up"
    assert again.input_id == 3


def test_an_input_without_a_name_writes_no_action_name() -> None:
    profile = Profile()
    node = _item(profile).to_xml()
    assert node.find("action-name") is None

    again = InputItem(profile.library)
    again.from_xml(node)
    assert again.action_name == ""
