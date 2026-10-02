# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""One destination label for every wire, using output-module names."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

from gremlin.modules import output, wiring
from gremlin.types import InputType
from vigem.xbox import XboxTarget

_ROOT = Path(__file__).resolve().parents[2]
_VJOY3 = {
    "buttons": list(range(1, 57)),
    "axes": [1, 2, 3],
    "hats": [],
    "keys": [],
    "friendly": {"button:5": "Fire"},
}


@pytest.fixture
def modules() -> Iterator[None]:
    """vJoy 3 claims buttons 1-56 and axes 1-3; the Xbox pad claims A."""
    xbox = SimpleNamespace(name="Xbox 360 Controller")
    with (
        mock.patch.object(
            output, "vjoy_module_name", side_effect=lambda v: "vJoy 3" if v == 3 else ""
        ),
        mock.patch.object(output, "vjoy_claim", side_effect=lambda v: _VJOY3),
        mock.patch.object(
            output,
            "vjoy_allows",
            side_effect=lambda v, k, i: (
                v == 3
                and int(i)
                in _VJOY3.get({"button": "buttons", "axis": "axes"}.get(k, ""), [])
            ),
        ),
        mock.patch.object(
            output, "xbox_module", side_effect=lambda p: xbox if p == 1 else None
        ),
    ):
        yield


def test_vjoy_long_and_short(modules: None) -> None:
    assert wiring.vjoy_dest(3, InputType.JoystickButton, 6) == "vJoy 3 · Button 6"
    assert wiring.vjoy_dest(3, InputType.JoystickButton, 6, short=True) == "vJoy 3 B6"
    assert wiring.vjoy_dest(3, InputType.JoystickAxis, 2, short=True) == "vJoy 3 Y"


def test_named_output_shows_its_name_in_the_long_form(modules: None) -> None:
    assert (
        wiring.vjoy_dest(3, InputType.JoystickButton, 5) == "vJoy 3 · Button 5 (Fire)"
    )
    assert wiring.vjoy_dest(3, InputType.JoystickButton, 5, short=True) == "vJoy 3 B5"


def test_unclaimed_and_missing_outputs_are_flagged(modules: None) -> None:
    assert wiring.vjoy_dest(3, InputType.JoystickButton, 57) == (
        "vJoy 3 · Button 57 (not claimed)"
    )
    assert wiring.vjoy_dest(3, InputType.JoystickButton, 57, short=True) == (
        "vJoy 3 B57 (not claimed)"
    )
    assert wiring.vjoy_dest(4, InputType.JoystickButton, 1).endswith(
        "(no output module)"
    )


def test_xbox_labels_name_the_pad_and_carry_no_claim_mark(modules: None) -> None:
    assert wiring.xbox_dest(1, XboxTarget.A) == "Xbox 360 Controller · A"
    assert wiring.xbox_dest(1, "left_trigger") == "Xbox 360 Controller · Left Trigger"
    assert wiring.xbox_dest(1, XboxTarget.A, short=True) == "Xbox 1 A"
    assert wiring.xbox_dest(2, XboxTarget.A) == "Xbox pad 2 · A"


def test_dest_label_reads_actions(modules: None) -> None:
    vjoy = SimpleNamespace(
        tag="map-to-vjoy",
        vjoy_device_id=3,
        vjoy_input_type=InputType.JoystickButton,
        vjoy_input_id=6,
    )
    xbox = SimpleNamespace(
        tag="map-to-xbox", xbox_device_id=1, xbox_target=XboxTarget.A
    )
    assert wiring.dest_label(vjoy) == "vJoy 3 · Button 6"
    assert wiring.dest_label(xbox, short=True) == "Xbox 1 A"
    assert wiring.dest_label(SimpleNamespace(tag="macro")) == ""


def test_no_other_file_builds_its_own_destination_text() -> None:
    for rel in (
        "gremlin/ui/binding_catalog.py",
        "gremlin/ui/input_pairing.py",
        "gremlin/ui/xbox_viewer.py",
    ):
        text = (_ROOT / rel).read_text(encoding="utf-8")
        assert 'f"vJoy {vid}' not in text and 'f"vJoy {vjoy_id} {' not in text, rel
        assert 'f"Xbox {' not in text, rel
