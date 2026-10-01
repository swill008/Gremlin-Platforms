# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from gremlin.modules.gate import dest_last_change, should_forward, status_last_from_hid
from gremlin.modules.claim import claim_allows
from gremlin.modules.ids import guid_key


class _T:
    def __init__(self, name: str) -> None:
        self.name = name


JoystickAxis = _T("JoystickAxis")
JoystickButton = _T("JoystickButton")

EVO = "11111111-1111-1111-1111-111111111111"
VJOY3 = "044a6af0-a897-11f1-800b-444553540000"
OSC = "a7c3e91b-4d2f-4e18-9b06-2f8c1d5a6e70"

CLAIM = {"axes": [1, 2, 3], "buttons": [1, 8], "hats": []}


def test_norm_guid_forms() -> None:
    assert guid_key(EVO) == guid_key("{" + EVO + "}")
    assert "-" not in guid_key(EVO)


def test_claimed_axis_passes() -> None:
    assert claim_allows(CLAIM, "axis", 1) is True
    assert claim_allows(CLAIM, "axis", 6) is False
    assert claim_allows(CLAIM, "button", 8) is True
    assert claim_allows(None, "axis", 1) is False


def test_source_claimed_enters_wire() -> None:
    assert should_forward(
        EVO,
        JoystickAxis,
        1,
        claims={guid_key(EVO): CLAIM},
        dest_guids={guid_key(VJOY3)},
        passthrough={guid_key(OSC)},
    )


def test_unclaimed_button_does_not_enter_wire() -> None:
    assert not should_forward(
        EVO,
        JoystickButton,
        99,
        claims={guid_key(EVO): CLAIM},
        dest_guids=set(),
        passthrough=set(),
    )


def test_dest_vjoy_hid_never_enters_wire() -> None:
    assert not should_forward(
        VJOY3,
        JoystickAxis,
        1,
        claims={guid_key(VJOY3): CLAIM},
        dest_guids={guid_key(VJOY3)},
        passthrough=set(),
    )


def test_osc_passthrough() -> None:
    assert should_forward(
        OSC,
        JoystickButton,
        1,
        claims={},
        dest_guids=set(),
        passthrough={guid_key(OSC)},
    )


def test_unknown_device_dropped() -> None:
    assert not should_forward(
        "00000000-0000-0000-0000-000000000000",
        JoystickButton,
        1,
        claims={guid_key(EVO): CLAIM},
        dest_guids=set(),
        passthrough=set(),
    )


def test_status_last_hid_only_on_input_cards() -> None:
    assert status_last_from_hid("source") is True
    assert status_last_from_hid("dest") is False
    assert status_last_from_hid("output") is False


def test_dest_last_prefers_button_press_then_axis() -> None:
    prev = {("axis", 1): 0.0, ("button", 2): 0.0}
    curr = {("axis", 1): 0.5, ("button", 2): 1.0}
    assert dest_last_change(prev, curr) == ("button", 2)
    curr2 = {("axis", 1): 0.5, ("button", 2): 0.0}
    assert dest_last_change(prev, curr2) == ("axis", 1)
    assert dest_last_change(prev, prev) is None
    assert dest_last_change({}, curr) is None
