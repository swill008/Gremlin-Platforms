# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Module claims: which inputs (or outputs) a module passes on.

A claim is the plain dict stored under "claim" in a module file:
{"buttons": [...], "axes": [...], "hats": [...], "keys": [...],
"xbox": ["a", "left_trigger", ...],
"friendly": {"button:5": "Fire", ...}}.
"xbox" holds the Xbox controls an Xbox output module passes, by name.
Anything not claimed does not exist for the rest of the pipeline.
"""

from __future__ import annotations

from gremlin.types import InputType

KINDS = ("button", "axis", "hat", "key")

_BUCKET = {"button": "buttons", "axis": "axes", "hat": "hats", "key": "keys"}

_KIND_OF_TYPE = {
    InputType.JoystickButton: "button",
    InputType.JoystickAxis: "axis",
    InputType.JoystickHat: "hat",
    InputType.Keyboard: "key",
}

_TYPE_OF_KIND = {
    "button": InputType.JoystickButton,
    "axis": InputType.JoystickAxis,
    "hat": InputType.JoystickHat,
    "key": InputType.Keyboard,
}


def _ints(values: object) -> list[int]:
    out: list[int] = []
    for raw in values or []:
        try:
            number = int(raw)
        except (TypeError, ValueError):
            continue
        if number > 0:
            out.append(number)
    return out


def _names(values: object) -> list[str]:
    out: list[str] = []
    for raw in values if isinstance(values, (list, tuple)) else []:
        name = str(raw or "").strip().lower()
        if name and name not in out:
            out.append(name)
    return out


def empty_claim() -> dict:
    return {
        "buttons": [],
        "axes": [],
        "hats": [],
        "keys": [],
        "xbox": [],
        "friendly": {},
    }


def read_claim(doc: dict | None) -> dict:
    """The claim of a module file, every id a positive int.

    Buttons, axes and hats are sorted without repeats; keys keep their saved
    order (packed scan code and extended flag).
    """
    raw = (doc or {}).get("claim")
    raw = raw if isinstance(raw, dict) else {}
    return {
        "buttons": sorted(set(_ints(raw.get("buttons")))),
        "axes": sorted(set(_ints(raw.get("axes")))),
        "hats": sorted(set(_ints(raw.get("hats")))),
        "keys": _ints(raw.get("keys")),
        "xbox": _names(raw.get("xbox")),
        "friendly": dict(raw.get("friendly") or {}),
    }


def kind_of(input_type: object) -> str:
    """"button", "axis", "hat" or "key" for an InputType or its name; "" otherwise."""
    if input_type in _KIND_OF_TYPE:
        return _KIND_OF_TYPE[input_type]
    text = str(getattr(input_type, "name", input_type) or "").lower()
    if "axis" in text:
        return "axis"
    if "hat" in text:
        return "hat"
    if "button" in text:
        return "button"
    if text in ("key", "keyboard"):
        return "key"
    return ""


def type_of(kind: str) -> InputType:
    """InputType for a kind; buttons when unknown."""
    return _TYPE_OF_KIND.get(kind, InputType.JoystickButton)


def claim_ids(claim: dict | None, kind: str) -> list[int]:
    """Claimed ids of one kind, sorted; [] for an unknown kind."""
    bucket = _BUCKET.get(kind)
    if not claim or not bucket:
        return []
    return sorted(set(_ints(claim.get(bucket))))


def claim_allows(claim: dict | None, kind: str, hid: object) -> bool:
    """True when the claim has this input."""
    try:
        want = int(hid)
    except (TypeError, ValueError):
        return False
    return want in claim_ids(claim, kind)


def claim_friendly(claim: dict | None, kind: str, hid: object) -> str:
    """The user's name for a claimed input, or "" when none."""
    try:
        number = int(hid)
    except (TypeError, ValueError):
        return ""
    names = (claim or {}).get("friendly") or {}
    return str(names.get(f"{kind}:{number}") or "").strip()


def key_id(scan_code: int, extended: bool) -> int:
    """A key as stored in a Keyboard claim: scan code, extended flag in bit 16."""
    return (int(scan_code) & 0xFFFF) | ((1 if extended else 0) << 16)


def key_id_of(identifier: object) -> int | None:
    """Key id of a keyboard event identifier ((scan_code, extended) or an id)."""
    if isinstance(identifier, (tuple, list)) and len(identifier) >= 2:
        try:
            return key_id(int(identifier[0]), bool(identifier[1]))
        except (TypeError, ValueError):
            return None
    try:
        return int(identifier)
    except (TypeError, ValueError):
        return None


def claim_allows_key(claim: dict | None, identifier: object) -> bool:
    """True when a Keyboard claim passes this key.

    A Keyboard module with no saved keys passes every key: that is what its
    Configure dialog shows (all keys ticked) until the user saves a choice.
    Older files stored the bare scan code; that still counts.
    """
    keys = set(claim_ids(claim, "key"))
    if not keys:
        return True
    ident = key_id_of(identifier)
    if ident is None:
        return False
    return ident in keys or (ident & 0xFFFF) in keys


def claim_xbox(claim: dict | None) -> list[str]:
    """Xbox controls claimed by an Xbox output module ("a", "left_trigger", ...)."""
    return _names((claim or {}).get("xbox"))


def claim_is_empty(claim: dict | None) -> bool:
    """True when nothing at all is claimed."""
    return not any(claim_ids(claim, kind) for kind in KINDS) and not claim_xbox(claim)
