# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""Claim gate for the runtime wire: HID only if an input module passed it."""

from __future__ import annotations

from gremlin.modules.claim import claim_allows, claim_allows_key, kind_of
from gremlin.modules.ids import guid_key


def should_forward(
    guid: object,
    event_type: object,
    hid: object,
    *,
    claims: dict[str, dict],
    dest_guids: set[str],
    passthrough: set[str],
) -> bool:
    """True if this HID event may enter the wire (Map to vJoy, etc.)."""
    key = guid_key(guid)
    if not key:
        return False
    if key in passthrough:
        return True
    if key in dest_guids:
        return False
    if kind_of(event_type) == "key":
        return claim_allows_key(claims.get(key), hid)
    try:
        ident = int(hid)
    except (TypeError, ValueError):
        return False
    return claim_allows(claims.get(key), kind_of(event_type), ident)


def status_last_from_hid(direction: str) -> bool:
    """Status last-line: input cards may use module events; dest never uses HID."""
    return str(direction or "source").strip().lower() not in (
        "dest",
        "target",
        "output",
    )


def dest_last_change(
    previous: dict, current: dict, axis_eps: float = 0.04
) -> tuple[str, int] | None:
    """First dest feeder change worth showing on a Status card last-line."""
    if not previous or not current:
        return None
    for key, val in current.items():
        kind, _hid = key
        if kind != "button":
            continue
        old = previous.get(key, 0.0)
        try:
            if float(val) > 0.5 and float(old) <= 0.5:
                return key
        except (TypeError, ValueError):
            continue
    for key, val in current.items():
        kind, _hid = key
        if kind not in ("axis", "hat"):
            continue
        old = previous.get(key)
        if old is None:
            continue
        try:
            if abs(float(val) - float(old)) > axis_eps:
                return key
        except (TypeError, ValueError):
            continue
    return None
