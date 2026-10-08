# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from PySide6 import QtCore

import gremlin.action_label  # noqa: F401
import gremlin.osc_bulk  # noqa: F401
import gremlin.ui.osc_settings_info  # noqa: F401
import gremlin.ui.vjoy_status  # noqa: F401
import gremlin.ui.live_input  # noqa: F401
import gremlin.ui.highlight_option  # noqa: F401
import gremlin.ui.window_placement  # noqa: F401
import gremlin.ui.type_aliases as ta
from gremlin import device_aliases
from gremlin.device_aliases import (  # noqa: F401 - the names live there now
    GROUP,
    NAME,
    SECTION,
    _ensure,
    _load,
    _same_key,
    _save,
    _stored_key,
    display_name,
    forget,
    set_alias,
)
from gremlin.ui.device import QML_IMPORT_MAJOR_VERSION, QML_IMPORT_NAME

assert QML_IMPORT_NAME == "Gremlin.Device"
assert QML_IMPORT_MAJOR_VERSION == 1


def shown_name(device_guid: object) -> str:
    """The name every screen shows for a device: the user's alias, else the
    device's own name (device_initialization.shown_name: twin name, vJoy
    number)."""
    from gremlin import device_initialization

    uid = getattr(device_guid, "uuid", device_guid)
    return display_name(str(uid), device_initialization.shown_name(uid))


class _Renamed(QtCore.QObject):
    """Fires after any alias change, from QML or Python (the Device Library
    renames through set_alias, 10 S7); every DeviceNames relays it."""

    fired = QtCore.Signal()


_RENAMED: _Renamed | None = None


def _renamed() -> _Renamed:
    global _RENAMED
    if _RENAMED is None:
        _RENAMED = _Renamed()
        device_aliases.on_change(_RENAMED.fired.emit)
    return _RENAMED


@ta.QmlElement
class DeviceNames(QtCore.QObject):
    changed = QtCore.Signal()

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        _renamed().fired.connect(self.changed)

    @QtCore.Slot(str, str, result=str)
    def display(self, key: str, default: str) -> str:
        return display_name(key, default)

    @QtCore.Slot(str, str)
    def setAlias(self, key: str, value: str) -> None:
        # set_alias tells every DeviceNames, this one included.
        set_alias(key, value)
