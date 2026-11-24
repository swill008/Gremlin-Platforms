# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""F13-F24 use the scan codes a real key press reports (0x64-0x6E, 0x76),
not their virtual key codes (upstream 30151b96)."""

from __future__ import annotations

import pytest

import dill
from gremlin import keyboard
from gremlin.modules.claim import key_id
from gremlin.modules.gate import should_forward
from gremlin.modules.ids import guid_key
from gremlin.types import InputType

_REAL_SCAN_CODES = {
    "F13": 0x64,
    "F14": 0x65,
    "F15": 0x66,
    "F16": 0x67,
    "F17": 0x68,
    "F18": 0x69,
    "F19": 0x6A,
    "F20": 0x6B,
    "F21": 0x6C,
    "F22": 0x6D,
    "F23": 0x6E,
    "F24": 0x76,
}


@pytest.mark.parametrize("name,scan_code", sorted(_REAL_SCAN_CODES.items()))
def test_real_scan_code_names_the_key(name: str, scan_code: int) -> None:
    assert keyboard.key_from_code(scan_code, False).name == name
    assert keyboard.key_from_name(name.lower()).scan_code == scan_code


def test_keyboard_claim_with_f13_ticked_lets_a_real_f13_press_through() -> None:
    # The Configure dialog stores the id of the listed key (module_model).
    f13 = keyboard.key_from_name("f13")
    claim = {"keys": [key_id(f13.scan_code, f13.is_extended)]}
    claims = {guid_key(dill.UUID_Keyboard): claim}

    def forward(identifier: tuple[int, bool]) -> bool:
        return should_forward(
            dill.UUID_Keyboard,
            InputType.Keyboard,
            identifier,
            claims=claims,
            dest_guids=set(),
            passthrough=set(),
        )

    assert forward((0x64, False))  # a real F13 press
    assert not forward((0x65, False))  # F14 not ticked
