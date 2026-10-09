# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The names the user gives devices (the Home card name, 10 S7): kept in the
settings, read by every screen. Not UI: gremlin/modules (the Device Library)
reads and renames through it; gremlin.ui.device_names relays changes to QML."""

from __future__ import annotations

import uuid
from collections.abc import Callable

from gremlin.config import Configuration
from gremlin.types import PropertyType

SECTION = "devices"
GROUP = "display"
NAME = "aliases"

_CACHE: dict[str, str] | None = None
# The stored list _CACHE was read from: a value put back from outside
# (Tools > History Restore) is read again.
_CACHE_RAW: list | None = None


def _ensure() -> Configuration:
    cfg = Configuration()
    if not cfg.exists(SECTION, GROUP, NAME):
        cfg.register(
            SECTION,
            GROUP,
            NAME,
            PropertyType.List,
            [],
            "Friendly display names for devices and inputs.",
            {},
            False,
        )
    return cfg


def _load() -> dict[str, str]:
    global _CACHE, _CACHE_RAW
    raw = _ensure().value(SECTION, GROUP, NAME) or []
    if _CACHE is not None and raw == _CACHE_RAW:
        return _CACHE
    names: dict[str, str] = {}
    for entry in raw:
        if isinstance(entry, list) and len(entry) >= 2:
            key = str(entry[0]).strip()
            value = str(entry[1]).strip()
            if key:
                names[key] = value
    _CACHE = names
    _CACHE_RAW = [list(e) if isinstance(e, list) else e for e in raw]
    return names


def _save(names: dict[str, str]) -> None:
    global _CACHE, _CACHE_RAW
    _CACHE = dict(names)
    rows = [[key, value] for key, value in names.items() if value]
    _CACHE_RAW = [list(row) for row in rows]
    _ensure().set(SECTION, GROUP, NAME, rows)


def _same_key(key: object) -> str:
    """Device ids match without braces or case ({ABC-1} == abc-1); other
    keys ("keyboard", "xbox") as they are, trimmed."""
    text = str(key or "").strip()
    bare = text.strip("{}")
    try:
        return str(uuid.UUID(bare)).upper()
    except ValueError:
        return text


def _stored_key(names: dict[str, str], key: object) -> str | None:
    want = _same_key(key)
    for stored in names:
        if _same_key(stored) == want:
            return stored
    return None


def display_name(key: str, default: str) -> str:
    """The alias the user gave (Home device list, Button Map), else default."""
    names = _load()
    stored = _stored_key(names, key)
    alias = names.get(stored, "").strip() if stored is not None else ""
    return alias or default


# Called after every alias change (set_alias); the UI relays it to QML.
_LISTENERS: list[Callable[[], None]] = []


def on_change(listener: Callable[[], None]) -> None:
    if listener not in _LISTENERS:
        _LISTENERS.append(listener)


def set_alias(key: str, value: str) -> None:
    names = dict(_load())
    stored = _stored_key(names, key)
    if stored is not None:
        names.pop(stored)
    key = str(key).strip()
    text = str(value or "").strip()
    if text:
        names[key] = text
    _save(names)
    for listener in list(_LISTENERS):
        listener()


def forget(gone: Callable[[str], bool]) -> bool:
    """Drops the alias of every device gone(id) says is forgotten (no
    module file, not plugged in: D-02-GL243-FORGET); keys that aren't device
    ids ("keyboard", "xbox") stay. True when one was dropped."""
    names = _load()
    kept: dict[str, str] = {}
    for key, value in names.items():
        try:
            uid = str(uuid.UUID(str(key).strip().strip("{}"))).upper()
        except ValueError:
            kept[key] = value
            continue
        if not gone(uid):
            kept[key] = value
    if len(kept) == len(names):
        return False
    _save(kept)
    return True
