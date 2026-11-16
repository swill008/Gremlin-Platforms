# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The messages between Gremlin and Gremlin Device Helper (S25).

Gremlin listens on PIPE_PREFIX + a random name (multiprocessing.connection,
family AF_PIPE, random authkey); the helper connects and answers each
request with {"ok": bool, "results": {id: "done" | "refused: ..." |
"error: ..."}}.

The helper only acts on ids the journal (S22) lists in the matching state,
so a request can never disable or enable any other device. Imports nothing
from the rest of the program: the helper ships with this module only.
"""

from __future__ import annotations

PIPE_PREFIX = r"\\.\pipe\gremlin-device-helper-"
STATES = (
    "to be disabled",
    "disabled",
    "disable failed",
    "to be enabled",
    "enabled",
    "enable failed",
)
OPS = ("ping", "disable", "enable", "quit")
MAX_ID_LENGTH = 260

# The journal state an id must be in for each action.
_NEEDED_STATE = {"disable": "to be disabled", "enable": "to be enabled"}


def valid_device_id(text: str) -> bool:
    """A Windows HID device instance id that is safe to hand to pnputil."""
    if not isinstance(text, str):
        return False
    if not text.startswith("HID\\") or len(text) <= len("HID\\"):
        return False
    if len(text) > MAX_ID_LENGTH or '"' in text:
        return False
    return not any(ord(c) < 0x20 or ord(c) == 0x7F for c in text)


def valid_enable_id(text: str) -> bool:
    """An id the helper may enable: a HID id, or a physical USB device id an
    older journal still lists (left by batch 7). Only "enable" takes USB ids,
    and only for an existing journal entry; nothing disables one (S21)."""
    if isinstance(text, str) and text.startswith("USB\\"):
        # The same safety checks as a HID id.
        return valid_device_id("HID\\" + text[len("USB\\") :])
    return valid_device_id(text)


def make_request(op: str, ids: list[str]) -> dict:
    """A request; ids are only used by "disable" and "enable"."""
    if op not in OPS:
        raise ValueError(f"unknown operation: {op!r}")
    return {"op": op, "ids": list(ids)}


def check_request(req: dict, journal: dict) -> tuple[list[str], dict[str, str]]:
    """(ids allowed, {id: "refused: <why>"}) for a disable or enable request.

    journal is the journal's entries, {id: {"name", "state", ...}}. Disable
    only ids the journal has as "to be disabled", enable only ids it has as
    "to be enabled". "ping" and "quit" allow nothing and refuse nothing.
    """
    allowed: list[str] = []
    refused: dict[str, str] = {}
    if not isinstance(req, dict):
        return allowed, refused
    op = req.get("op")
    ids = req.get("ids", [])
    if not isinstance(ids, list):
        ids = []
    if not isinstance(journal, dict):
        journal = {}
    for device_id in ids:
        key = device_id if isinstance(device_id, str) else repr(device_id)
        if key in refused or key in allowed:
            continue
        if op not in _NEEDED_STATE:
            if op in OPS:
                refused[key] = f"refused: {op} takes no devices"
            else:
                refused[key] = "refused: unknown operation"
            continue
        valid = valid_enable_id if op == "enable" else valid_device_id
        if not valid(device_id):
            refused[key] = "refused: not a game-input (HID) device id"
            continue
        entry = journal.get(device_id)
        if not isinstance(entry, dict):
            refused[key] = "refused: not in the journal"
            continue
        state = entry.get("state")
        if state != _NEEDED_STATE[op]:
            refused[key] = f"refused: the journal has it as {state!r}"
            continue
        allowed.append(device_id)
    return allowed, refused
