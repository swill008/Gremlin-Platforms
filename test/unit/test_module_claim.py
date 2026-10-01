# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from gremlin.modules.claim import (
    claim_allows,
    claim_friendly,
    claim_ids,
    claim_is_empty,
    empty_claim,
    kind_of,
    read_claim,
    type_of,
)
from gremlin.types import InputType

_DOC = {
    "claim": {
        "buttons": [3, "1", 1, 0, -2, "x"],
        "axes": [2, 1],
        "hats": [],
        "keys": [65566, 30],
        "friendly": {"button:3": " Fire ", "axis:1": "Roll"},
    }
}


def test_read_claim_gives_clean_ids() -> None:
    claim = read_claim(_DOC)
    assert claim["buttons"] == [1, 3]  # numbers, sorted, no repeats, no 0 or less
    assert claim["axes"] == [1, 2]
    assert claim["keys"] == [65566, 30]  # keys keep their saved order
    assert claim["friendly"]["axis:1"] == "Roll"


def test_missing_claim_reads_as_empty() -> None:
    assert read_claim({}) == empty_claim()
    assert read_claim(None) == empty_claim()
    assert claim_is_empty(read_claim({}))


def test_allows_and_ids_by_kind() -> None:
    claim = read_claim(_DOC)
    assert claim_allows(claim, "button", 3)
    assert claim_allows(claim, "button", "3")
    assert not claim_allows(claim, "button", 2)
    assert claim_allows(claim, "key", 30)
    assert not claim_allows(claim, "nonsense", 1)
    assert claim_ids(claim, "hat") == []


def test_friendly_names_are_trimmed() -> None:
    claim = read_claim(_DOC)
    assert claim_friendly(claim, "button", 3) == "Fire"
    assert claim_friendly(claim, "button", 1) == ""


def test_kind_of_input_types_and_names() -> None:
    assert kind_of(InputType.JoystickAxis) == "axis"
    assert kind_of(InputType.JoystickButton) == "button"
    assert kind_of(InputType.JoystickHat) == "hat"
    assert kind_of(InputType.Keyboard) == "key"
    assert kind_of("axis") == "axis"
    assert kind_of(None) == ""
    assert type_of("hat") == InputType.JoystickHat
    assert type_of("unknown") == InputType.JoystickButton


def test_keys_alone_are_not_empty() -> None:
    assert not claim_is_empty({"keys": [30]})
