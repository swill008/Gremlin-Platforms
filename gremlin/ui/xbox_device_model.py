# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import logging
import os

from PySide6 import QtCore, QtGui

import gremlin.ui.type_aliases as ta
from gremlin import shared_state
from gremlin.modules import output
from gremlin.signal import signal
from gremlin.types import InputType
from gremlin.ui.device import QML_IMPORT_MAJOR_VERSION, QML_IMPORT_NAME
from gremlin.ui.input_pairing import device_label
from gremlin.ui.xbox_maps import xbox_maps_for_item
from vigem.ids import XBOX_TAB_GUID
from vigem.xbox import XboxTarget

assert QML_IMPORT_NAME == "Gremlin.Device"
assert QML_IMPORT_MAJOR_VERSION == 1


def _input_text(device_id: str, item: object) -> str:
    """Readable input name: "Button 1", or "Button 1 — Name" for a named
    Logical Device input."""
    input_type = getattr(item, "input_type", None)
    try:
        number = int(item.input_id)
    except (TypeError, ValueError):
        return str(getattr(item, "input_id", ""))
    if device_label(device_id) == "Logical Device":
        from gremlin.logical_device import LogicalDevice

        logical = LogicalDevice()
        ident = LogicalDevice.Input.Identifier(input_type, number)
        if logical.exists(ident):
            return logical[ident].choice_label
    try:
        kind = InputType.to_string(input_type).capitalize()
    except Exception:
        kind = "Input"
    return f"{kind} {number}"


def _incoming_for(pad_id: int, target: XboxTarget) -> str:
    profile = shared_state.current_profile
    if profile is None:
        return ""
    hits: list[str] = []
    for device_id, items in (profile.inputs or {}).items():
        for item in items or []:
            if not any(
                pid == pad_id and value == target.value
                for pid, value in xbox_maps_for_item(item)
            ):
                continue
            guid = str(device_id)
            hits.append(f"{device_label(guid)} · {_input_text(guid, item)}")
    return "  ·  ".join(hits)


_VIGEM_DOWNLOAD = "https://github.com/nefarius/ViGEmBus/releases"


@ta.QmlElement
class XboxDriverStatus(QtCore.QObject):
    """The ViGEmBus check at the top of the Xbox Viewer, like HidHide's:
    installed, running (the program can connect), and its version."""

    changed = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._installed = False
        self._ready = False
        self._version = ""
        self._problem = ("", "")
        self.reload()

    @QtCore.Slot()
    def reload(self) -> None:
        self._installed = output.xbox_driver_installed()
        self._version = output.xbox_driver_version() if self._installed else ""
        # The output module's wording, the same everywhere the driver is checked.
        self._problem = output.xbox_driver_problem()
        self._ready = not self._problem[0]
        self.changed.emit()

    def _get_installed(self) -> bool:
        return self._installed

    def _get_ready(self) -> bool:
        return self._ready

    def _get_version(self) -> str:
        return self._version

    def _get_status(self) -> str:
        return "ViGEmBus driver found" if self._ready else self._problem[0]

    def _get_hint(self) -> str:
        return self._problem[1]

    @QtCore.Slot()
    def openDownload(self) -> None:
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(_VIGEM_DOWNLOAD))

    @QtCore.Slot()
    def openGameControllers(self) -> None:
        if os.name != "nt":
            return
        import subprocess

        try:
            subprocess.Popen(
                ["rundll32.exe", "shell32.dll,Control_RunDLL", "joy.cpl"],
                close_fds=True,
            )
        except OSError as exc:
            logging.getLogger("system").warning(f"joy.cpl failed: {exc}")

    installed = QtCore.Property(bool, fget=_get_installed, notify=changed)
    ready = QtCore.Property(bool, fget=_get_ready, notify=changed)
    driverVersion = QtCore.Property(str, fget=_get_version, notify=changed)
    statusText = QtCore.Property(str, fget=_get_status, notify=changed)
    hint = QtCore.Property(str, fget=_get_hint, notify=changed)


@ta.QmlElement
class XboxDeviceModel(QtCore.QAbstractListModel):
    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"label"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"target"),
        QtCore.Qt.ItemDataRole.UserRole + 3: QtCore.QByteArray(b"kind"),
        QtCore.Qt.ItemDataRole.UserRole + 4: QtCore.QByteArray(b"incoming"),
    }

    padIdChanged = QtCore.Signal()
    statusChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._pad_id = 1
        self._rows = list(XboxTarget)
        signal.profileChanged.connect(self.reload)
        signal.inputItemChanged.connect(self.reload)

    @QtCore.Slot()
    @QtCore.Slot(int)
    def reload(self, _index: int = 0) -> None:
        self.beginResetModel()
        self.endResetModel()
        self.statusChanged.emit()

    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._rows)

    def data(self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None
        target = self._rows[index.row()]
        key = bytes(self.roles.get(role, b"")).decode()
        if key == "label":
            return target.label
        if key == "target":
            return target.value
        if key == "kind":
            return target.kind
        if key == "incoming":
            return _incoming_for(self._pad_id, target)
        return None

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles

    def _get_pad_id(self) -> int:
        return self._pad_id

    def _set_pad_id(self, pad_id: int) -> None:
        ident = max(1, min(4, int(pad_id)))
        if ident == self._pad_id:
            return
        self._pad_id = ident
        self.reload()
        self.padIdChanged.emit()

    def _get_guid(self) -> str:
        return XBOX_TAB_GUID

    def _get_module_name(self) -> str:
        module = output.xbox_module(self._pad_id)
        return module.name if module is not None else f"Xbox pad {self._pad_id}"

    guid = QtCore.Property(str, fget=_get_guid, constant=True)
    padId = QtCore.Property(int, fget=_get_pad_id, fset=_set_pad_id, notify=padIdChanged)
    moduleName = QtCore.Property(str, fget=_get_module_name, notify=statusChanged)

