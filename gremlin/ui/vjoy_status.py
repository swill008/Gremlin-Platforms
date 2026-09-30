# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin.config import Configuration
from gremlin.types import PropertyType
from gremlin.ui.device import QML_IMPORT_MAJOR_VERSION, QML_IMPORT_NAME
from vjoy import vjoy
import gremlin.ui.xbox_device_model  # noqa: F401

assert QML_IMPORT_NAME == "Gremlin.Device"
assert QML_IMPORT_MAJOR_VERSION == 1

SECTION = "devices"
GROUP = "display"
VJOY_NAME = "vjoy-tabs"
EXTRA_NAME = "extra-tabs"
EXTRA_ALLOWED = ["keyboard", "logical", "osc", "xbox"]
EXTRA_DEFAULT = ["keyboard", "logical", "osc"]


class _PinHub(QtCore.QObject):
    changed = QtCore.Signal()


HUB = _PinHub()


_VJOY_DESCRIPTION = "vJoy device tabs shown in the main bar."
_EXTRA_DESCRIPTION = "Keyboard, Logical, OSC, and Xbox tabs shown in the main bar."


def _ensure(name: str, default: list, description: str) -> Configuration:
    # Registering an existing entry keeps its saved value.
    cfg = Configuration()
    cfg.register(
        SECTION,
        GROUP,
        name,
        PropertyType.List,
        default,
        description,
        {},
        False,
    )
    return cfg


def register_options() -> None:
    _ensure(VJOY_NAME, [], _VJOY_DESCRIPTION)
    _ensure(EXTRA_NAME, list(EXTRA_DEFAULT), _EXTRA_DESCRIPTION)


def _load_pins() -> set[int]:
    pins: set[int] = set()
    raw = _ensure(VJOY_NAME, [], _VJOY_DESCRIPTION).value(
        SECTION, GROUP, VJOY_NAME
    ) or []
    for item in raw:
        try:
            index = int(item)
        except (TypeError, ValueError):
            continue
        if 1 <= index <= 16:
            pins.add(index)
    return pins


def _save_pins(pins: set[int]) -> None:
    _ensure(VJOY_NAME, [], _VJOY_DESCRIPTION).set(
        SECTION, GROUP, VJOY_NAME, sorted(pins)
    )


def _load_extra() -> set[str]:
    raw = _ensure(
        EXTRA_NAME,
        list(EXTRA_DEFAULT),
        _EXTRA_DESCRIPTION,
    ).value(SECTION, GROUP, EXTRA_NAME)
    if raw is None:
        return set(EXTRA_DEFAULT)
    extras: set[str] = set()
    for item in raw:
        key = str(item).strip().lower()
        if key in EXTRA_ALLOWED:
            extras.add(key)
    return extras


def _save_extra(extras: set[str]) -> None:
    _ensure(
        EXTRA_NAME,
        list(EXTRA_DEFAULT),
        _EXTRA_DESCRIPTION,
    ).set(SECTION, GROUP, EXTRA_NAME, sorted(extras))


@ta.QmlElement
class VJoyStatus(QtCore.QObject):
    changed = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._active = [False] * 16
        self._pins = _load_pins()
        self._extra = _load_extra()
        HUB.changed.connect(self._reload_pins)

    def _reload_pins(self) -> None:
        self._pins = _load_pins()
        self._extra = _load_extra()
        self.changed.emit()

    @QtCore.Slot()
    def refresh(self) -> None:
        active = []
        for index in range(1, 17):
            try:
                active.append(bool(vjoy.device_exists(index)))
            except Exception:
                active.append(False)
        self._active = active
        self._pins = _load_pins()
        self._extra = _load_extra()
        self.changed.emit()

    @QtCore.Slot(int, result=bool)
    def isActive(self, index: int) -> bool:
        if 1 <= index <= 16:
            return self._active[index - 1]
        return False

    @QtCore.Slot(int, result=bool)
    def isPinned(self, index: int) -> bool:
        return int(index) in self._pins

    @QtCore.Slot(int, bool)
    def setPinned(self, index: int, pinned: bool) -> None:
        index = int(index)
        if index < 1 or index > 16:
            return
        if pinned:
            self._pins.add(index)
        else:
            self._pins.discard(index)
        _save_pins(self._pins)
        HUB.changed.emit()

    @QtCore.Slot(str, result=bool)
    def isExtraPinned(self, name: str) -> bool:
        return str(name).strip().lower() in self._extra

    @QtCore.Slot(str, bool)
    def setExtraPinned(self, name: str, pinned: bool) -> None:
        key = str(name).strip().lower()
        if key not in EXTRA_ALLOWED:
            return
        if pinned:
            self._extra.add(key)
        else:
            self._extra.discard(key)
        _save_extra(self._extra)
        HUB.changed.emit()

    @QtCore.Slot(result=bool)
    def xboxAvailable(self) -> bool:
        try:
            from vigem.xbox import XboxProxy

            return XboxProxy().available()
        except Exception:
            return False

    def _count(self) -> int:
        return sum(1 for item in self._active if item)

    def _pin_stamp(self) -> int:
        total = 0
        for index in self._pins:
            total += 1 << index
        for offset, name in enumerate(EXTRA_ALLOWED, start=17):
            if name in self._extra:
                total += 1 << offset
        return total

    activeCount = QtCore.Property(int, fget=_count, notify=changed)
    pinStamp = QtCore.Property(int, fget=_pin_stamp, notify=changed)
