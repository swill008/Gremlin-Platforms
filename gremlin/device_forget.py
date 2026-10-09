# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Remove from Library forgets the device's settings (10 S52,
D-10-REMOVE-ALL): its friendly name, its Home card settings and the
calibration kept in the program settings. Its module file (with the
calibration saved in it) goes with Delete Device. Not UI."""

from __future__ import annotations

import uuid
from typing import Any

from gremlin import device_aliases, history
from gremlin.config import Configuration
from gremlin.modules import store

# The Home card settings (gremlin.ui.module_model keeps them by card key):
# section, group and the keys holding a card.
_CARD_SECTION = "display"
_CARD_GROUP = "status"
_HIDDEN = "hidden-slugs"
_ORDER = "card-order"
_SIZES = "card-sizes"
_STACKS = "card-stacks"
_KEPT_STUBS = "kept-stubs"

_CALIBRATION = "calibration"


def _device_id(guid: str) -> str:
    """The id as settings store it (upper case, dashes), or "" for none."""
    try:
        return str(uuid.UUID(str(guid or "").strip().strip("{}"))).upper()
    except ValueError:
        return ""


def _without(raw: str, slug: str) -> str:
    """A comma list (hidden, order, kept) without slug."""
    return ",".join(
        p.strip() for p in raw.split(",") if p.strip() and p.strip() != slug
    )


def _without_size(raw: str, slug: str) -> str:
    """Card sizes (slug=WxH,...) without slug's."""
    return ",".join(
        p.strip()
        for p in raw.split(",")
        if p.strip() and p.split("=", 1)[0].strip() != slug
    )


def _without_stacked(raw: str, slug: str) -> str:
    """Stacks (a+b|c+d) without slug; a stack left with one card ends."""
    groups = []
    for part in raw.split("|"):
        group = [
            s.strip() for s in part.split("+") if s.strip() and s.strip() != slug
        ]
        if len(group) > 1:
            groups.append("+".join(group))
    return "|".join(groups)


_CARD_EDITS = {
    _HIDDEN: _without,
    _ORDER: _without,
    _KEPT_STUBS: _without,
    _SIZES: _without_size,
    _STACKS: _without_stacked,
}


def _changes(
    cfg: Configuration, slug: str, device_id: str
) -> dict[tuple[str, str, str], Any]:
    """Every setting forgetting the device changes, with its new value."""
    out: dict[tuple[str, str, str], Any] = {}
    if slug:
        for name, edit in _CARD_EDITS.items():
            if not cfg.exists(_CARD_SECTION, _CARD_GROUP, name):
                continue
            raw = str(cfg.value(_CARD_SECTION, _CARD_GROUP, name) or "")
            new = edit(raw, slug)
            if new != raw:
                out[(_CARD_SECTION, _CARD_GROUP, name)] = new
    if device_id:
        default = [-32768, 0, 0, 32767, True]
        for axis in cfg.entries(_CALIBRATION, device_id, only_exposed=False):
            if list(cfg.value(_CALIBRATION, device_id, axis) or []) != default:
                out[(_CALIBRATION, device_id, axis)] = list(default)
    return out


def forget_device(name: str, guid: str) -> None:
    """Forgets name/guid's friendly name, Home card settings (size, place,
    hidden, stack, kept card) and stored calibration; other devices' stay.
    Recorded as one settings entry in Tools > History (inside Remove's
    group it joins that entry), whose Restore puts them back."""
    cfg = Configuration()
    slug = store.card_key(name) if str(name or "").strip() else ""
    device_id = _device_id(guid)
    alias_key = (device_aliases.SECTION, device_aliases.GROUP, device_aliases.NAME)

    def alias_rows() -> list:
        device_aliases._ensure()
        rows = cfg.value(*alias_key) or []
        return [list(r) if isinstance(r, list) else r for r in rows]

    before: dict[str, Any] = {}
    after: dict[str, Any] = {}
    old_aliases = alias_rows()
    if device_id and device_aliases.forget(lambda uid: uid == device_id):
        before["/".join(alias_key)] = old_aliases
        after["/".join(alias_key)] = alias_rows()
    for key, value in _changes(cfg, slug, device_id).items():
        old = cfg.value(*key)
        before["/".join(key)] = list(old) if isinstance(old, (list, tuple)) else old
        after["/".join(key)] = value
        cfg.set(*key, value)
    if not before:
        return
    keys = sorted(before)
    from gremlin.config import settings_history_title
    from gremlin.signal import signal

    # These settings aren't shown in Options, so a save leaves them out of
    # History (config._view_entry): recorded here.
    title = settings_history_title(keys)
    history.record("settings", title, {"keys": keys}, before, after)
    signal.configChanged.emit()
