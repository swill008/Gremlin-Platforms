# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import re
from typing import Any, cast

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin.config import Configuration
from gremlin.error import GremlinError
from gremlin.osc import OSC_DEVICE_UUID, OscDevice, OscRuntime, guess_input_type
from gremlin.profile import InputItem
from gremlin.signal import signal
from gremlin.types import InputType
from gremlin import shared_state
from gremlin.ui.device import (
    InputIdentifier,
    QML_IMPORT_NAME,
    QML_IMPORT_MAJOR_VERSION,
    _description_from_item,
    _generate_action_sequence_descriptor,
)

assert QML_IMPORT_NAME == "Gremlin.Device"
assert QML_IMPORT_MAJOR_VERSION == 1

_IMPORT_LINE = re.compile(
    r"^(?P<addr>/\S+?)(?:\s*,\s*|\s+)(?P<suffix>[A-Za-z]+)?$"
)


def _parse_import_line(line: str) -> tuple[str, str] | None:
    text = line.strip()
    if not text:
        return None
    match = _IMPORT_LINE.match(text)
    if match:
        address = match.group("addr")
        suffix = (match.group("suffix") or "").upper()
    elif text.startswith("/"):
        address = text.split()[0].rstrip(",")
        suffix = ""
    else:
        return None
    if suffix in ("A", "C", "E"):
        return address, "Axis"
    return address, "Button"


class OscInputIdentifier(InputIdentifier):
    @QtCore.Property(str, notify=InputIdentifier.changed)
    def label(self) -> str:
        if not self.isValid:
            return "No input"
        item = OscDevice().find_by_id(self.input_type, int(self.input_id))
        if item is not None:
            return f"OSC - {item.label}"
        return (
            f"OSC - {InputType.to_string(self.input_type).capitalize()} "
            f"{self.input_id}"
        )

    @property
    def linear_index(self) -> int:
        if not self.isValid:
            raise GremlinError("Cannot compute linear index of invalid input")
        return max(int(self.input_id) - 1, 0)


@ta.QmlElement
class OscDeviceManagementModel(QtCore.QAbstractListModel):
    listenChanged = QtCore.Signal()
    listenBound = QtCore.Signal(int)
    commandCaptured = QtCore.Signal(str, str)

    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"name"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"label"),
        QtCore.Qt.ItemDataRole.UserRole + 3: QtCore.QByteArray(b"actionSequenceCount"),
        QtCore.Qt.ItemDataRole.UserRole + 4: QtCore.QByteArray(
            b"actionSequenceDescriptor"
        ),
        QtCore.Qt.ItemDataRole.UserRole + 5: QtCore.QByteArray(
            b"actionSequenceDisplayMode"
        ),
        QtCore.Qt.ItemDataRole.UserRole + 6: QtCore.QByteArray(b"description"),
    }

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._osc = OscDevice()
        self._mode: str = "Default"
        self._capture_only = False
        self._sort_alpha = False
        runtime = OscRuntime()
        runtime.learned.connect(self._on_learned)
        runtime.listenChanged.connect(self.listenChanged)
        signal.profileChanged.connect(self._profile_changed_cb)
        signal.inputItemChanged.connect(self.refreshInput)
        signal.oscDeviceModified.connect(self._full_refresh)

    def _labels(self) -> list[str]:
        labels = self._osc.labels_of_type()
        if self._sort_alpha:
            return sorted(labels)
        return labels

    @QtCore.Slot(str)
    def createInput(self, type_str: str) -> None:
        self.createMappedInput(type_str, "")

    @QtCore.Slot(str, str)
    def createMappedInput(self, type_str: str, label: str) -> None:
        address = (label or "").strip()
        if address:
            existing = self._osc.find_address(address)
            if existing is not None:
                try:
                    index = self._label_to_index(address)
                except ValueError:
                    index = self.rowCount() - 1
                self.listenBound.emit(index)
                return
        self.beginInsertRows(QtCore.QModelIndex(), self.rowCount(), self.rowCount())
        kwargs = {}
        if address:
            kwargs["label"] = address
        self._osc.create(InputType.to_enum(type_str), **kwargs)
        self.endInsertRows()
        self.dataChanged.emit(
            self.createIndex(0, 0), self.createIndex(self.rowCount(), 0)
        )
        signal.oscDeviceModified.emit()
        self.listenBound.emit(self.rowCount() - 1)

    @QtCore.Slot()
    def clearAllInputs(self) -> None:
        labels = list(self._osc.labels_of_type())
        self.beginResetModel()
        for label in labels:
            doomed = self._osc[label]
            self._drop_profile_mappings(doomed.type, doomed.id)
            self._osc.delete(label)
        self.endResetModel()
        signal.oscDeviceModified.emit()

    @QtCore.Slot()
    def sortInputs(self) -> None:
        self._sort_alpha = True
        self.beginResetModel()
        self.endResetModel()

    @QtCore.Slot(str)
    def importInputs(self, text: str) -> None:
        created = []
        for raw in (text or "").splitlines():
            parsed = _parse_import_line(raw)
            if parsed is None:
                continue
            address, type_str = parsed
            if self._osc.find_address(address) is not None:
                continue
            try:
                self._osc.create(InputType.to_enum(type_str), label=address)
                created.append(address)
            except GremlinError:
                continue
        if not created:
            return
        self.beginResetModel()
        self.endResetModel()
        signal.oscDeviceModified.emit()
        try:
            index = self._label_to_index(created[-1])
        except ValueError:
            index = self.rowCount() - 1
        self.listenBound.emit(index)

    @QtCore.Slot()
    def listenForInput(self) -> None:
        self._capture_only = False
        OscRuntime().listen_once()

    @QtCore.Slot()
    def listenForCommand(self) -> None:
        self._capture_only = True
        OscRuntime().listen_once()

    @QtCore.Slot()
    def cancelListen(self) -> None:
        self._capture_only = False
        OscRuntime().cancel_listen()

    def _on_learned(self, address: str, args: object) -> None:
        payload = args if isinstance(args, tuple) else ()
        if self._capture_only:
            self._capture_only = False
            shown = ", ".join(str(item) for item in payload)
            self.commandCaptured.emit(address, shown)
            return
        existing = self._osc.find_address(address)
        if existing is None:
            self.beginInsertRows(QtCore.QModelIndex(), self.rowCount(), self.rowCount())
            self._osc.create(guess_input_type(payload), label=address)
            self.endInsertRows()
            signal.oscDeviceModified.emit()
        try:
            index = self._label_to_index(address)
        except ValueError:
            index = self.rowCount() - 1
        self.listenBound.emit(index)
        signal.showNotification.emit(
            f"Bound OSC input {address}",
            "Map it to vJoy on the right, then run the profile.",
        )

    def _get_listening(self) -> bool:
        return OscRuntime().is_listening()

    @QtCore.Slot(str, str)
    def changeName(self, old_label: str, new_label: str) -> None:
        try:
            self._osc.set_label(old_label, new_label)
            self.dataChanged.emit(
                self.createIndex(0, 0), self.createIndex(self.rowCount(), 0)
            )
            signal.oscDeviceModified.emit()
        except GremlinError:
            pass

    def _drop_profile_mappings(self, input_type: InputType, input_id: int) -> None:
        profile = shared_state.current_profile
        if profile is None:
            return
        items = profile.inputs.get(OSC_DEVICE_UUID, [])
        profile.drop_inputs(
            OSC_DEVICE_UUID,
            [
                item
                for item in items
                if item.input_type == input_type and item.input_id == input_id
            ],
        )

    @QtCore.Slot(str)
    def deleteInput(self, label: str) -> None:
        item_index = self._label_to_index(label)
        doomed = self._osc[label]
        self._drop_profile_mappings(doomed.type, doomed.id)
        self.beginRemoveRows(QtCore.QModelIndex(), item_index, item_index)
        self._osc.delete(label)
        self.endRemoveRows()
        self.dataChanged.emit(
            self.createIndex(0, 0), self.createIndex(self.rowCount(), 0)
        )
        signal.oscDeviceModified.emit()

    @QtCore.Slot(str)
    def setMode(self, mode: str) -> None:
        self._mode = mode
        self.dataChanged.emit(
            self.createIndex(0, 0), self.createIndex(self.rowCount() - 1, 0)
        )

    @QtCore.Slot(int)
    def refreshInput(self, index: int) -> None:
        self.dataChanged.emit(self.createIndex(index, 0), self.createIndex(index, 0))

    def _full_refresh(self) -> None:
        self.beginResetModel()
        self.endResetModel()

    def _get_guid(self) -> str:
        return str(self._osc.device_guid)

    def _profile_changed_cb(self) -> None:
        self.beginResetModel()
        self.endResetModel()

    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._labels())

    def data(
        self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> str | int:
        if role not in self.roles:
            return "Unknown"
        input_info = self._index_to_input(index.row())
        input_item: InputItem | None = None
        if shared_state.current_profile is not None:
            input_item = shared_state.current_profile.get_input_item(
                self._osc.device_guid, input_info.type, input_info.id, self._mode
            )
        match cast(str, self.roles[role]):
            case "name":
                return (
                    f"{InputType.to_string(input_info.type).capitalize()} "
                    f"{input_info.id} - {input_info.label}"
                )
            case "label":
                return input_info.label
            case "actionSequenceCount":
                return len(input_item.action_sequences) if input_item else 0
            case "actionSequenceDescriptor":
                return (
                    _generate_action_sequence_descriptor(input_item)
                    if input_item
                    else ""
                )
            case "actionSequenceDisplayMode":
                return Configuration().value(
                    "global", "general", "action-sequence-information"
                )
            case "description":
                return _description_from_item(input_item) if input_item else ""
            case _:
                return ""

    @QtCore.Slot(int, result=InputIdentifier)
    def inputIdentifier(self, index: int) -> InputIdentifier:
        if index < 0:
            return OscInputIdentifier(parent=self)
        item = self._index_to_input(index)
        identifier = OscInputIdentifier(parent=self)
        identifier.device_guid = self._osc.device_guid
        identifier.input_type = item.type
        identifier.input_id = item.id
        return identifier

    def _index_to_input(self, index: int):
        return self._osc[self._labels()[index]]

    def _label_to_index(self, label: str) -> int:
        return self._labels().index(label.casefold())

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles

    guid = QtCore.Property(str, fget=_get_guid)
    listening = QtCore.Property(bool, fget=_get_listening, notify=listenChanged)
