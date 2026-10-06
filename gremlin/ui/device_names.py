# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import uuid

from PySide6 import QtCore

import gremlin.action_label  # noqa: F401
import gremlin.osc_bulk  # noqa: F401
import gremlin.ui.osc_settings_info  # noqa: F401
import gremlin.ui.vjoy_status  # noqa: F401
import gremlin.ui.live_input  # noqa: F401
import gremlin.ui.highlight_option  # noqa: F401
import gremlin.ui.window_placement  # noqa: F401
import gremlin.ui.type_aliases as ta
from gremlin.config import Configuration
from gremlin.types import PropertyType
from gremlin.ui.device import QML_IMPORT_MAJOR_VERSION, QML_IMPORT_NAME

assert QML_IMPORT_NAME == "Gremlin.Device"
assert QML_IMPORT_MAJOR_VERSION == 1

SECTION = "devices"
GROUP = "display"
NAME = "aliases"

_CACHE: dict[str, str] | None = None


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
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    raw = _ensure().value(SECTION, GROUP, NAME) or []
    names: dict[str, str] = {}
    for entry in raw:
        if isinstance(entry, list) and len(entry) >= 2:
            key = str(entry[0]).strip()
            value = str(entry[1]).strip()
            if key:
                names[key] = value
    _CACHE = names
    return names


def _save(names: dict[str, str]) -> None:
    global _CACHE
    _CACHE = dict(names)
    rows = [[key, value] for key, value in names.items() if value]
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


def shown_name(device_guid: object) -> str:
    """The name every screen shows for a device: the user's alias, else the
    device's own name (device_initialization.shown_name: twin name, vJoy
    number)."""
    from gremlin import device_initialization

    uid = getattr(device_guid, "uuid", device_guid)
    return display_name(str(uid), device_initialization.shown_name(uid))


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


@ta.QmlElement
class DeviceNames(QtCore.QObject):
    changed = QtCore.Signal()

    @QtCore.Slot(str, str, result=str)
    def display(self, key: str, default: str) -> str:
        return display_name(key, default)

    @QtCore.Slot(str, str)
    def setAlias(self, key: str, value: str) -> None:
        set_alias(key, value)
        self.changed.emit()
