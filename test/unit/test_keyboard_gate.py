# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Keyboard events reach the profile only through the Keyboard input module."""

from __future__ import annotations

from pathlib import Path

import dill
from gremlin.modules.claim import claim_allows_key, key_id, key_id_of
from gremlin.modules.gate import should_forward
from gremlin.modules.ids import guid_key
from gremlin.types import InputType

_ROOT = Path(__file__).resolve().parents[2]
_KB = guid_key(dill.UUID_Keyboard)
_F1 = (59, False)
_RIGHT_CTRL = (29, True)


def _forward(identifier: object, claim: dict | None) -> bool:
    claims = {_KB: claim} if claim is not None else {}
    return should_forward(
        dill.UUID_Keyboard,
        InputType.Keyboard,
        identifier,
        claims=claims,
        dest_guids=set(),
        passthrough=set(),
    )


def test_key_id_packs_the_extended_flag() -> None:
    assert key_id(29, False) == 29
    assert key_id(29, True) == 29 | (1 << 16)
    assert key_id_of((29, True)) == 65565
    assert key_id_of(59) == 59
    assert key_id_of(("x", 1)) is None


def test_claimed_key_passes_and_unclaimed_key_does_not() -> None:
    claim = {"keys": [59, key_id(29, True)]}
    assert _forward(_F1, claim)
    assert _forward(_RIGHT_CTRL, claim)
    assert not _forward((60, False), claim)  # F2 not claimed
    assert not _forward((29, False), claim)  # left Ctrl is not right Ctrl


def test_no_saved_keyboard_claim_passes_every_key() -> None:
    # Matches the Configure dialog, which ticks every key until a choice is saved.
    assert _forward(_F1, {"keys": []})
    assert _forward(_F1, None)


def test_older_files_with_bare_scan_codes_still_work() -> None:
    assert claim_allows_key({"keys": [29]}, _RIGHT_CTRL)


def test_profile_takes_keyboard_events_from_the_input_runtime() -> None:
    text = (_ROOT / "gremlin" / "code_runner.py").read_text(encoding="utf-8")
    assert "keyboard_event.connect(self.event_handler.process_event)" not in text
    assert "key_event.connect(self.event_handler.process_event)" in text
