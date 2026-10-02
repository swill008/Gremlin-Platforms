# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import logging
import math
import time
import uuid
from typing import cast

from PySide6 import (
    QtCharts,
    QtCore,
)

import dill
import gremlin.ui.type_aliases as ta
from gremlin import (
    common,
    device_initialization,
    event_handler,
    keyboard,
    shared_state,
    util,
)
from gremlin.base_classes import AbstractActionData
from gremlin.config import Configuration
from gremlin.error import GremlinError
from gremlin.input_cache import DeviceDatabase
from gremlin.logical_device import LogicalDevice
from gremlin.profile import InputItem
from gremlin.ui.hardware_profile import persist_log
from gremlin.modules.calibration import values_for_module, write_axis
from gremlin.signal import signal
from gremlin.types import (
    InputType,
    PropertyType,
    ScanCode,
)
from gremlin.ui import backend

QML_IMPORT_NAME = "Gremlin.Device"
QML_IMPORT_MAJOR_VERSION = 1


def _generate_action_sequence_descriptor(item: InputItem) -> str:
    icons = []
    if item is not None:
        for seq in item.action_sequences:
            [
                _collect_action_icons(action, icons)
                for action in seq.root_action.get_actions()[0]
            ]
    return ":".join(icons)


def _collect_action_icons(action: AbstractActionData, icons: list[str]) -> None:
    icons.append(action.icon)
    if action.tag == "map-to-vjoy":
        type_lookup = {
            InputType.JoystickAxis: "A",
            InputType.JoystickButton: "B",
            InputType.JoystickHat: "H",
            InputType.Invalid: "I",
        }
        icons[-1] += (
            f",{action.vjoy_device_id},"
            f"{type_lookup[action.vjoy_input_type]},"
            f"{action.vjoy_input_id}"
        )
    elif action.tag == "map-to-xbox":
        target = getattr(action, "xbox_target", None)
        target_value = target.value if hasattr(target, "value") else str(target or "a")
        pad_id = getattr(action, "xbox_device_id", 1)
        icons[-1] += f",{pad_id},{target_value}"
    for selector in action._valid_selectors():
        icons.append("(")
        [
            _collect_action_icons(child, icons)
            for child in action._get_container(selector)
        ]
        icons.append(")")


def _description_from_item(item: InputItem) -> str:
    if item and len(item.action_sequences) > 0:
        labels = filter(
            lambda x: x != "Root",
            [seq.root_action.action_label for seq in item.action_sequences],
        )
        return " / ".join(labels)
    else:
        return ""


@ta.QmlElement
class InputIdentifier(QtCore.QObject):
    """Stores the identifier of a single input item."""

    changed = QtCore.Signal()

    def __init__(
        self,
        device_guid: uuid.UUID | None = None,
        input_type: InputType | None = None,
        input_id: int | ScanCode | None = None,
        parent: ta.OQO = None,
    ) -> None:
        super().__init__(parent)

        self.device_guid = device_guid
        self.input_type = input_type
        self.input_id = input_id

    @QtCore.Property(str, notify=changed)
    def label(self) -> str:
        if self.isValid:
            if self.device_guid == dill.UUID_LogicalDevice:
                dev_name = "Logical Device"
            elif self.device_guid == dill.UUID_Keyboard:
                dev_name = "Keyboard"
            else:
                dev_name = dill.DILL.get_device_name(
                    dill.GUID.from_uuid(self.device_guid)
                )
            return (
                f"{dev_name} - "
                + f"{InputType.to_string(self.input_type).capitalize()} "
                + f"{self.input_id}"
            )
        else:
            return "No input"

    @QtCore.Property(bool, notify=changed)
    def isValid(self) -> bool:
        return (
            self.device_guid is not None
            and self.input_type is not None
            and self.input_id is not None
        )

    @property
    def linear_index(self) -> int:
        """Returns the linear index of the input item.

        The linear index is computed based on the device information and
        the input type and id.

        Returns:
            The linear index of the input item
        """
        if not self.isValid:
            raise GremlinError("Cannot compute linear index of invalid input")

        device_info = dill.DILL.get_device_information_by_guid(
            dill.GUID.from_uuid(self.device_guid)
        )
        match self.input_type:
            case InputType.JoystickAxis:
                for i, axis in enumerate(device_info.axis_map):
                    if axis.axis_index == self.input_id:
                        return i
                raise GremlinError("Invalid axis id for device")
            case InputType.JoystickButton:
                return device_info.axis_count + (self.input_id - 1)
            case InputType.JoystickHat:
                return (
                    device_info.axis_count
                    + device_info.button_count
                    + (self.input_id - 1)
                )
            case _:
                raise GremlinError("Invalid input type for device")

    def __eq__(self, other: InputIdentifier) -> bool:
        return (
            self.device_guid == other.device_guid
            and self.input_type == other.input_type
            and self.input_id == other.input_id
        )


@ta.QmlElement
class DeviceListModel(QtCore.QAbstractListModel):
    """Model containing basic information about all connected devices."""

    selectedIndexChanged = QtCore.Signal()

    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"name"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"axes"),
        QtCore.Qt.ItemDataRole.UserRole + 3: QtCore.QByteArray(b"buttons"),
        QtCore.Qt.ItemDataRole.UserRole + 4: QtCore.QByteArray(b"hats"),
        QtCore.Qt.ItemDataRole.UserRole + 5: QtCore.QByteArray(b"pid"),
        QtCore.Qt.ItemDataRole.UserRole + 6: QtCore.QByteArray(b"vid"),
        QtCore.Qt.ItemDataRole.UserRole + 7: QtCore.QByteArray(b"guid"),
        QtCore.Qt.ItemDataRole.UserRole + 8: QtCore.QByteArray(b"joy_id"),
        QtCore.Qt.ItemDataRole.UserRole + 9: QtCore.QByteArray(b"vjoy_id"),
    }

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)

        self._selected_index = -1
        self._devices = device_initialization.input_devices()
        self._device_types = "all"
        self._reload_devices()

        event_handler.EventListener().device_change_event.connect(self.update_model)
        signal.profileChanged.connect(self.update_model)

    def update_model(self) -> None:
        """Updates the model if the connected devices change."""
        self._reload_devices()

    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._devices)

    def data(
        self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> str | int:
        if role not in self.roles:
            return "Unknown"

        device = self._devices[index.row()]
        match cast(str, self.roles[role]):
            case "name":
                if device.is_virtual:
                    return f"{device.name} {device.vjoy_id}"
                return device.name
            case "axes":
                return device.axis_count
            case "buttons":
                return device.button_count
            case "hats":
                return device.hat_count
            case "pid":
                return f"{device.product_id:04X}"
            case "vid":
                return f"{device.vendor_id:04X}"
            case "guid":
                return str(device.device_guid)
            case "joy_id":
                return device.joystick_id
            case "vjoy_id":
                return device.vjoy_id
            case _:
                return "Unknown"

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles

    @QtCore.Slot(int, result=str)
    def uuidAtIndex(self, index: int) -> str:
        if len(self._devices) == 0:
            return str(dill.UUID_Invalid)
        if not (0 <= index < len(self._devices)):
            raise GremlinError("Provided index out of range")

        return str(self._devices[index].device_guid.uuid)

    def _reload_devices(self) -> None:
        self.beginResetModel()
        if self._device_types == "physical":
            self._devices = device_initialization.physical_devices()
        elif self._device_types == "virtual":
            self._devices = device_initialization.vjoy_devices()
        elif self._device_types == "input":
            self._devices = device_initialization.input_devices()
        elif self._device_types == "all":
            self._devices = device_initialization.joystick_devices()
        self.endResetModel()

    def _change_device_type(self, types: str) -> None:
        """Sets which device types are going to be used.

        Valid options are:
        - physical
        - virtual
        - input (physical + input vJoy devices)
        - all

        Args:
            types: the type of devices to list
        """
        self._device_types = types
        self._reload_devices()

    @QtCore.Property(int, notify=selectedIndexChanged)
    def selectedIndex(self) -> int:
        return self._selected_index

    @selectedIndex.setter
    def selectedIndex(self, index: int) -> None:
        if 0 <= index < len(self._devices) and index != self._selected_index:
            self._selected_index = index

    deviceType = QtCore.Property(str, fset=_change_device_type)


@ta.QmlElement
class Device(QtCore.QAbstractListModel):
    """Model providing access to information about a single device."""

    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"name"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"actionSequenceCount"),
        QtCore.Qt.ItemDataRole.UserRole + 3: QtCore.QByteArray(
            b"actionSequenceDescriptor"
        ),
        QtCore.Qt.ItemDataRole.UserRole + 4: QtCore.QByteArray(
            b"actionSequenceDisplayMode"
        ),
        QtCore.Qt.ItemDataRole.UserRole + 5: QtCore.QByteArray(b"description"),
    }

    deviceChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)

        self._device: dill.DeviceSummary | None = None
        self._device_mapping: dict[str, str] | None = None
        self._mode: str = "Default"

        signal.profileChanged.connect(self._profile_changed_cb)
        signal.inputItemChanged.connect(self.refreshInput)

    @QtCore.Slot(int)
    def refreshInput(self, index: int) -> None:
        """Refreshes the input at the given index.

        Args:
            index: linear index of the device's inputs to refresh
        """
        self.dataChanged.emit(self.createIndex(index, 0), self.createIndex(index, 0))

    @QtCore.Slot(str)
    def setMode(self, mode: str) -> None:
        self._mode = mode
        self.dataChanged.emit(
            self.createIndex(0, 0), self.createIndex(self.rowCount() - 1, 0)
        )

    def _get_guid(self) -> str:
        if self._device is None:
            return "Unknown"
        else:
            return str(self._device.device_guid)

    def _set_guid(self, guid: str) -> None:
        if self._device is not None and guid == str(self._device.device_guid):
            return

        self.beginResetModel()
        self._device = dill.DILL.get_device_information_by_guid(
            dill.GUID.from_str(guid)
        )
        self._device_mapping = DeviceDatabase().get_mapping(self._device)
        self.endResetModel()
        self.deviceChanged.emit()

    def _profile_changed_cb(self) -> None:
        self.beginResetModel()
        self.endResetModel()
        self.deviceChanged.emit()

    def rowCount(self, parent: ta.MI = QtCore.QModelIndex()) -> int:
        if self._device is None:
            return 0

        return (
            self._device.axis_count + self._device.button_count + self._device.hat_count
        )

    def data(
        self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> str | int:
        if role not in self.roles:
            return "Unknown"

        input_info = self._convert_index(index.row())
        match cast(str, self.roles[role]):
            case "name":
                return self._name(input_info)
            case "actionSequenceCount":
                input_item = self._get_input_item(input_info)
                return len(input_item.action_sequences) if input_item else 0
            case "actionSequenceDescriptor":
                input_item = self._get_input_item(input_info)
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
                input_item = self._get_input_item(input_info)
                return _description_from_item(input_item) if input_item else ""
            case _:
                return ""

    @QtCore.Slot(int, result=str)
    def kindAt(self, index: int) -> str:
        if self._device is None or index < 0:
            return ""
        kind = self._convert_index(index)[0]
        if kind == InputType.JoystickAxis:
            return "axis"
        if kind == InputType.JoystickHat:
            return "hat"
        return "button"

    @QtCore.Slot(int, result=int)
    def hwIdAt(self, index: int) -> int:
        if self._device is None or index < 0:
            return 0
        return int(self._convert_index(index)[1])

    @QtCore.Slot(int, result=InputIdentifier)
    def inputIdentifier(self, index: int) -> InputIdentifier:
        """Returns the InputIdentifier for input with the specified index.

        Args:
            index: the index of the input for which to generate the
                InpuIdentifier instance

        Returns:
            An InputIdentifier instance referring to the input item with
            the given index.
        """
        identifier = InputIdentifier(parent=self)
        identifier.device_guid = self._device.device_guid.uuid
        input_info = self._convert_index(index)
        identifier.input_type = input_info[0]
        identifier.input_id = input_info[1]

        return identifier

    def _name(self, identifier: tuple[InputType, int]) -> str:
        if self._device_mapping is not None:
            return self._device_mapping.input_name(identifier)
        else:
            return common.input_to_ui_string(*identifier)

    def _convert_index(self, index: int) -> tuple[InputType, int]:
        assert self._device is not None

        axis_count = self._device.axis_count
        button_count = self._device.button_count

        if index < axis_count:
            return (InputType.JoystickAxis, self._device.axis_map[index].axis_index)
        elif index < axis_count + button_count:
            return (InputType.JoystickButton, index + 1 - axis_count)
        else:
            return (InputType.JoystickHat, index + 1 - axis_count - button_count)

    def _get_input_item(self, input_info: tuple[InputType, int]) -> InputItem:
        return shared_state.current_profile.get_input_item(
            self._device.device_guid.uuid, input_info[0], input_info[1], self._mode
        )

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles

    guid = QtCore.Property(str, fget=_get_guid, fset=_set_guid, notify=deviceChanged)


@ta.QmlElement
class LogicalDeviceManagementModel(QtCore.QAbstractListModel):
    """Model providing information about the intermedia output device."""

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

        self._logical = LogicalDevice()
        self._mode: str = "Default"

        signal.profileChanged.connect(self._profile_changed_cb)
        signal.inputItemChanged.connect(self.refreshInput)
        signal.logicalDeviceModified.connect(self._full_refresh)

    @QtCore.Slot(str)
    def createInput(self, type_str: str) -> None:
        self.beginInsertRows(QtCore.QModelIndex(), self.rowCount(), self.rowCount())
        self._logical.create(InputType.to_enum(type_str))
        self.endInsertRows()
        self.dataChanged.emit(
            self.createIndex(0, 0), self.createIndex(self.rowCount(), 0)
        )
        signal.logicalDeviceModified.emit()

    @QtCore.Slot(str, str)
    def changeName(self, old_label: str, new_label: str) -> None:
        try:
            self._logical.set_label(old_label, new_label)
            self.dataChanged.emit(
                self.createIndex(0, 0), self.createIndex(self.rowCount(), 0)
            )
            signal.logicalDeviceModified.emit()
        except GremlinError:
            # FIXME: Somehow needs to reset the text field to the previous value
            pass

    @QtCore.Slot(str)
    def deleteInput(self, label: str) -> None:
        item_index = self._label_to_index(label)
        self.beginRemoveRows(QtCore.QModelIndex(), item_index, item_index)
        self._logical.delete(label)
        self.endRemoveRows()
        self.dataChanged.emit(
            self.createIndex(0, 0), self.createIndex(self.rowCount(), 0)
        )
        signal.logicalDeviceModified.emit()

    @QtCore.Slot(str)
    def setMode(self, mode: str) -> None:
        self._mode = mode
        self.dataChanged.emit(
            self.createIndex(0, 0), self.createIndex(self.rowCount() - 1, 0)
        )

    @QtCore.Slot(int)
    def refreshInput(self, index: int) -> None:
        """Refreshes the input at the given index.

        Args:
            index: linear index of the input to refresh
        """
        self.dataChanged.emit(self.createIndex(index, 0), self.createIndex(index, 0))

    def _full_refresh(self) -> None:
        self.beginResetModel()
        self.endResetModel()

    def _get_guid(self) -> str:
        return str(self._logical.device_guid)

    def _profile_changed_cb(self) -> None:
        self.beginResetModel()
        self.endResetModel()

    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._logical.labels_of_type())

    def data(
        self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> str | int:
        if role not in self.roles:
            return "Unknown"

        input_info = self._index_to_input(index.row())
        input_item = shared_state.current_profile.get_input_item(
            self._logical.device_guid, input_info.type, input_info.id, self._mode
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

    @QtCore.Slot(str, result=list[str])
    def validLabels(self, type_str: str) -> list[str]:
        """Returns a list of valid labels for a given input."""
        type = InputType.to_enum(type_str)
        if len(self._logical.labels_of_type([type])) == 0:
            self._logical.create(type)
        return self._logical.labels_of_type([type])

    @QtCore.Slot(int, result=InputIdentifier)
    def inputIdentifier(self, index: int) -> InputIdentifier:
        """Returns the InputIdentifier for input with the specified index.

        Args:
            index: the index of the input for which to generate the
                InpuIdentifier instance

        Returns:
            An InputIdentifier instance referring to the input item with
            the given index.
        """
        if index < 0:
            return InputIdentifier(parent=self)

        input = self._index_to_input(index)
        identifier = InputIdentifier(parent=self)
        identifier.device_guid = self._logical.device_guid
        identifier.input_type = input.type
        identifier.input_id = input.id

        return identifier

    def _name(self, identifier: tuple[InputType, int]) -> str:
        return f"{InputType.to_string(identifier[0]).capitalize()} {identifier[1]:d}"

    def _index_to_input(self, index: int) -> LogicalDevice.Input:
        """Returns the label corresponding to the provided linear index.

        Args:
            index: the linear index into the list of inputs

        Returns:
            The input corresponding to the given index
        """
        return self._logical[self._logical.labels_of_type()[index]]

    def _label_to_index(self, label: str) -> int:
        """Returns the index corresponding to the given label.

        Args:
            label: name of the input for which to determine the index

        Returns:
            Index of the given label in the backend data storage
        """
        all_labels = self._logical.labels_of_type()
        return all_labels.index(label)

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles

    guid = QtCore.Property(str, fget=_get_guid)


@ta.QmlElement
class LogicalDeviceSelectorModel(QtCore.QAbstractListModel):
    inputsChanged = QtCore.Signal()
    selectionChanged = QtCore.Signal()

    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"label"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"id"),
        QtCore.Qt.ItemDataRole.UserRole + 3: QtCore.QByteArray(b"type"),
    }

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)

        self._logical = LogicalDevice()
        self._valid_types = []
        self._current_index = -1
        self._current_identifier = InputIdentifier(parent=self)

        signal.logicalDeviceModified.connect(self._refresh_model)

    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._logical.labels_of_type(self._valid_types))

    def data(
        self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> str | int | None:
        if role not in self.roleNames():
            raise GremlinError(f"Invalid role {role} in LogicalDeviceSelectorModel")

        input = self._logical.inputs_of_type(self._valid_types)[index.row()]
        match cast(str, self.roles[role]):
            case "label":
                return input.choice_label
            case "id":
                return input.id
            case "type":
                return InputType.to_string(input.type)
            case _:
                return None

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles

    def _set_valid_types(self, valid_types: list[str]) -> None:
        type_list = sorted(
            [InputType.to_enum(entry) for entry in valid_types], key=lambda x: x.value
        )
        if type_list != self._valid_types:
            is_initialized = len(self._valid_types) > 0
            self._valid_types = type_list
            self.inputsChanged.emit()
            if is_initialized:
                self._set_current_index(0)

    def _get_current_identifier(self) -> InputIdentifier:
        return self._current_identifier

    def _set_current_identifier(self, identifier: InputIdentifier) -> None:
        if identifier != self._current_identifier:
            # Find the index that would correspond to the given identifier.
            for i, input in enumerate(self._logical.inputs_of_type(self._valid_types)):
                if (
                    input.type == identifier.input_type
                    and input.id == identifier.input_id
                ):
                    self._set_current_index(i)

    def _get_current_index(self) -> int:
        return self._current_index

    def _set_current_index(self, index: int) -> None:
        if index != self._current_index:
            input = self._logical.inputs_of_type(self._valid_types)[index]
            self._current_identifier = InputIdentifier(
                LogicalDevice().device_guid, input.type, input.id, parent=self
            )
            self._current_index = index
            self.selectionChanged.emit()

    def _refresh_model(self) -> None:
        # Reset the complete model as the number of entries can have changed.
        self.beginResetModel()
        self.endResetModel()

    validTypes = QtCore.Property(list, fset=_set_valid_types, notify=inputsChanged)

    currentIdentifier = QtCore.Property(
        InputIdentifier,
        fget=_get_current_identifier,
        fset=_set_current_identifier,
        notify=selectionChanged,
    )

    currentIndex = QtCore.Property(
        int, fget=_get_current_index, fset=_set_current_index, notify=selectionChanged
    )


@ta.QmlElement
class KeyboardManagerModel(QtCore.QAbstractListModel):
    """Model providing information about and managing keyboard inputs."""

    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"name"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"actionSequenceCount"),
        QtCore.Qt.ItemDataRole.UserRole + 3: QtCore.QByteArray(
            b"actionSequenceDescriptor"
        ),
        QtCore.Qt.ItemDataRole.UserRole + 4: QtCore.QByteArray(
            b"actionSequenceDisplayMode"
        ),
        QtCore.Qt.ItemDataRole.UserRole + 5: QtCore.QByteArray(b"description"),
    }

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)

        self._profile = shared_state.current_profile
        signal.profileChanged.connect(self._profile_changed_cb)
        signal.inputItemChanged.connect(self.refreshInput)

    def _profile_changed_cb(self) -> None:
        self._profile = shared_state.current_profile
        self.beginResetModel()
        self.endResetModel()

    @QtCore.Slot(int, result=InputIdentifier)
    def inputIdentifier(self, index: int) -> InputIdentifier:
        identifier = InputIdentifier(parent=self)
        identifier.device_guid = dill.UUID_Keyboard
        identifier.input_type = InputType.Keyboard
        identifier.input_id = self._all_keyboard_inputs()[index].input_id

        return identifier

    @QtCore.Slot(int)
    def deleteInput(self, index: int) -> None:
        self.beginResetModel()
        item = self._all_keyboard_inputs()[index]
        self._profile.inputs[dill.UUID_Keyboard].remove(item)
        self.endResetModel()

    @QtCore.Slot(list)
    def addKey(self, data: list[event_handler.Event]) -> None:
        if not data:
            return

        self.beginResetModel()
        self._profile.get_input_item(
            dill.UUID_Keyboard,
            InputType.Keyboard,
            data[0].identifier,
            backend.Backend().ui_state.currentMode,
            True,
        )
        self.endResetModel()

    @QtCore.Slot(int)
    def refreshInput(self, index: int) -> None:
        """Refreshes the input at the given index.

        Args:
            index: linear index of the input to refresh
        """
        self.dataChanged.emit(self.createIndex(index, 0), self.createIndex(index, 0))

    def _all_keyboard_inputs(self) -> list[InputItem]:
        return sorted(
            self._profile.inputs.get(dill.UUID_Keyboard, []),
            key=lambda item: keyboard.key_from_code(*item.input_id).virtual_code,
        )

    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._all_keyboard_inputs())

    def data(
        self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> str | int:
        if role not in self.roles:
            return "Unknown"

        input_item = self._all_keyboard_inputs()[index.row()]
        match cast(str, self.roles[role]):
            case "name":
                return keyboard.key_from_code(*input_item.input_id).name
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

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles


@ta.QmlElement
class DeviceAxisSeries(QtCore.QObject):
    windowSizeChanged = QtCore.Signal()
    deviceChanged = QtCore.Signal()
    axisCountChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)

        el = event_handler.EventListener()
        el.joystick_event.connect(self._event_callback)

        self._device = None
        self._device_uuid = None
        self._state = []
        self._identifier_map = {}
        self._window_size = 20

    def _get_guid(self) -> str:
        return str(self._device.device_guid) if self._device is not None else ""

    def _set_guid(self, guid: str) -> None:
        if self._device is not None and guid == str(self._device.device_guid):
            return

        self._device = dill.DILL.get_device_information_by_guid(
            dill.GUID.from_str(guid)
        )
        self._device_uuid = uuid.UUID(guid)

        self._state = []
        for i in range(self._device.axis_count):
            self._identifier_map[self._device.axis_map[i].axis_index] = i
            self._state.append(
                {"identifier": self._device.axis_map[i].axis_index, "timeSeries": []}
            )
        self.deviceChanged.emit()

    def _get_window_size(self) -> int:
        return self._window_size

    def _set_window_size(self, value: int) -> None:
        if value != self._window_size:
            self._window_size = value
            self.windowSizeChanged.emit()

    @QtCore.Slot(event_handler.Event)
    def _event_callback(self, event: event_handler.Event) -> None:
        if event.device_guid != self._device_uuid:
            return

        if event.event_type == InputType.JoystickAxis:
            index = self._identifier_map[event.identifier]
            self._state[index]["timeSeries"].append((time.time(), event.value))

    @QtCore.Property(int, notify=axisCountChanged)
    def axisCount(self) -> int:
        return self._device.axis_count

    @QtCore.Slot(QtCharts.QLineSeries, int)
    def updateSeries(self, series: QtCharts.QLineSeries, identifier: int) -> None:
        data = self._state[identifier]["timeSeries"]

        if len(data) < 2:
            series.replace(
                [
                    QtCore.QPointF(0.0, 0.0),
                    QtCore.QPointF(self._window_size, 0.0),
                ]
            )
            return

        now = time.time()
        try:
            while now - data[0][0] > self._window_size:
                data.pop(0)
        except IndexError as e:
            logging.getLogger("system").warning(f"Unexpected exception: {e}")
            return

        time_series = []
        for p0, p1 in zip(data[:-1], data[1:]):
            time_series.append(QtCore.QPointF(p0[0] - now, p0[1]))
            time_series.append(QtCore.QPointF(p1[0] - now, p0[1]))

        time_series.append(QtCore.QPointF(data[-1][0] - now, data[-1][1]))
        time_series.append(QtCore.QPointF(0, data[-1][1]))
        series.replace(time_series)

    @QtCore.Slot(int, result=int)
    def axisIdentifier(self, index: int) -> int:
        return self._state[index]["identifier"]

    guid = QtCore.Property(str, fget=_get_guid, fset=_set_guid, notify=deviceChanged)

    windowSize = QtCore.Property(
        int, fset=_set_window_size, fget=_get_window_size, notify=windowSizeChanged
    )


@ta.QmlElement
class AxisCalibration(QtCore.QAbstractListModel):
    deviceChanged = QtCore.Signal()

    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"identifier"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"calibratedValue"),
        QtCore.Qt.ItemDataRole.UserRole + 3: QtCore.QByteArray(b"rawValue"),
        QtCore.Qt.ItemDataRole.UserRole + 4: QtCore.QByteArray(b"low"),
        QtCore.Qt.ItemDataRole.UserRole + 5: QtCore.QByteArray(b"centerLow"),
        QtCore.Qt.ItemDataRole.UserRole + 6: QtCore.QByteArray(b"centerHigh"),
        QtCore.Qt.ItemDataRole.UserRole + 7: QtCore.QByteArray(b"high"),
        QtCore.Qt.ItemDataRole.UserRole + 8: QtCore.QByteArray(b"withCenter"),
        QtCore.Qt.ItemDataRole.UserRole + 9: QtCore.QByteArray(b"unsavedChanges"),
    }

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)

        self._event_listener = event_handler.EventListener()
        self._event_listener.joystick_event.connect(self._event_callback)

        self._device = None
        self._device_uuid = None
        self._module_slug = ""
        self._state = []
        self._calibration_fn = []
        self._active_calibrations = []

        self._config = Configuration()
        self._device_db = DeviceDatabase()
        self._device_mapping = None

    def data(
        self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> str | int | bool | None:
        if role not in self.roles:
            return None

        state = self._state[index.row()]
        match cast(str, self.roles.get(role, "")):
            case "identifier":
                return state["identifier"]
            case "calibratedValue":
                return state["calibratedValue"]
            case "rawValue":
                return state["rawValue"]
            case "low":
                return state["low"]
            case "centerLow":
                return state["centerLow"]
            case "centerHigh":
                return state["centerHigh"]
            case "high":
                return state["high"]
            case "withCenter":
                return state["withCenter"]
            case "unsavedChanges":
                return state["unsavedChanges"]
            case _:
                return None

    def setData(
        self,
        index: ta.ModelIndex,
        value: str | int | bool | None,
        role: int = QtCore.Qt.ItemDataRole.EditRole,
    ) -> bool:
        if role not in self.roles:
            return False

        # Update internal representation
        state = self._state[index.row()]
        match cast(str, self.roles.get(role, "")):
            case "identifier":
                state["identifier"] = value
            case "calibratedValue":
                state["calibratedValue"] = value
            case "rawValue":
                state["rawValue"] = value
            case "low":
                state["low"] = value
            case "centerLow":
                state["centerLow"] = value
            case "centerHigh":
                state["centerHigh"] = value
            case "high":
                state["high"] = value
            case "withCenter":
                state["withCenter"] = value
            case "unsavedChanges":
                state["unsavedChanges"] = value
            case _:
                return False

        if self.roles.get(role) != "unsavedChanges":
            state["unsavedChanges"] = not self._matches_saved(index.row())
        self._update_calibration(index.row())

        # Signal that the model has changed for a UI update
        self.emit_update(index.row())
        return True

    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        if self._device is None:
            return 0

        return len(self._state)

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles

    def emit_update(self, index: int) -> None:
        """Emits the data update signal for the given index."""
        self.dataChanged.emit(self.index(index, 0), self.index(index, 0))

    @QtCore.Slot(int)
    def reset(self, index: int) -> None:
        """Resets the calibration data of the specified axis.

        Args:
            index: index of the axis to reset
        """
        if not (0 <= index < len(self._state)):
            return

        # Reset values to defaults
        self._state[index]["low"] = -32768
        self._state[index]["centerLow"] = 0
        self._state[index]["centerHigh"] = 0
        self._state[index]["high"] = 32767
        self._state[index]["unsavedChanges"] = not self._matches_saved(index)

        # Reset calibration tracking data to continue calibration after a
        # reset.
        self._active_calibrations[index]["cvalues"] = [0, 0]
        self._active_calibrations[index]["evalues"] = [0, 0]

        # Update models
        self._update_calibration(index)
        self.emit_update(index)

    @QtCore.Slot(int, bool)
    def calibrateCenter(self, index: int, is_active: bool) -> None:
        self._active_calibrations[index]["center"] = is_active
        self._active_calibrations[index]["extrema"] = False
        self._active_calibrations[index]["cvalues"] = [0, 0]
        if is_active:
            self._state[index]["centerLow"] = 0
            self._state[index]["centerHigh"] = 0
            self.emit_update(index)

    @QtCore.Slot(int, bool)
    def calibrateExtrema(self, index: int, is_active: bool) -> None:
        self._active_calibrations[index]["extrema"] = is_active
        self._active_calibrations[index]["center"] = False
        self._active_calibrations[index]["evalues"] = [0, 0]
        if is_active:
            self._state[index]["low"] = 0
            self._state[index]["high"] = 0
            self.emit_update(index)

    @QtCore.Slot(int, result=bool)
    def save(self, index: int) -> bool:
        """Saves the current calibration data to the configuration system.

        Args:
            index: index of the axis whose data to save
        """
        if self._device_uuid is None or self._device is None or not self._module_slug:
            persist_log(f"Persist calibration skipped index={index} reason='no module'")
            return False
        if not (0 <= index < len(self._state)):
            persist_log(f"Persist calibration skipped index={index} reason='bad index'")
            return False

        axis_id = self._device.axis_map[index].axis_index
        saved = write_axis(
            self._module_slug,
            axis_id,
            (
                self._state[index]["low"],
                self._state[index]["centerLow"],
                self._state[index]["centerHigh"],
                self._state[index]["high"],
                self._state[index]["withCenter"],
            ),
        )
        if not saved:
            persist_log(
                f"Persist calibration skipped slug={self._module_slug} axis={axis_id} reason='write failed'"
            )
            return False
        self._state[index]["unsavedChanges"] = False
        self._event_listener.reload_calibration(
            self._device.device_guid,
            axis_id,
        )
        self.emit_update(index)
        persist_log(
            f"Persist calibration ok slug={self._module_slug} guid={self._device_uuid} axis={axis_id}"
        )
        return True

    @QtCore.Slot(result=str)
    def moduleFilePath(self) -> str:
        from gremlin.modules.calibration import module_for_slug

        row = module_for_slug(self._module_slug)
        if not row:
            return ""
        return str(row.get("path") or "")

    @QtCore.Slot(result=bool)
    def hasUnsaved(self) -> bool:
        return any(bool(row.get("unsavedChanges")) for row in self._state)

    @QtCore.Slot(result=bool)
    def saveAll(self) -> bool:
        ok = True
        for index, row in enumerate(list(self._state)):
            if row.get("unsavedChanges"):
                ok = self.save(index) and ok
        return ok

    @QtCore.Slot()
    def discard(self) -> None:
        if self._device is None or self._device_uuid is None:
            return
        self.beginResetModel()
        self._state = []
        self._calibration_fn = []
        self._active_calibrations = []
        self._initialize_state()
        self.endResetModel()
        self.deviceChanged.emit()

    def _matches_saved(self, index: int) -> bool:
        """True when the axis limits equal what is saved, so nothing is unsaved."""
        if self._device is None or self._device_uuid is None:
            return False
        state = self._state[index]
        saved = values_for_module(
            self._module_slug, self._device_uuid, self._device.axis_map[index].axis_index
        )
        current = (state["low"], state["centerLow"], state["centerHigh"], state["high"])
        return [int(v) for v in current] == [int(v) for v in saved[:4]] and bool(
            state["withCenter"]
        ) == bool(saved[4])

    def _update_calibration(self, index: int) -> None:
        """Creates the calibration function based on the stored values.

        Args:
            index: index of the axis to update the calibration function of
        """
        self._calibration_fn[index] = util.create_calibration_function(
            self._state[index]["low"],
            self._state[index]["centerLow"],
            self._state[index]["centerHigh"],
            self._state[index]["high"],
            self._state[index]["withCenter"],
        )

    def _set_guid(self, guid: str) -> None:
        return

    def _initialize_state(self) -> None:
        if self._device_uuid is None or self._device is None:
            return

        for i in range(self._device.axis_count):
            key = (self._device_uuid, self._device.axis_map[i].axis_index)
            calibration_data = values_for_module(
                self._module_slug, self._device_uuid, key[1]
            )
            self._state.append(
                {
                    "identifier": common.input_to_ui_string(
                        InputType.JoystickAxis, key[1]
                    ),
                    "rawValue": 0,
                    "calibratedValue": 0,
                    "low": calibration_data[0],
                    "centerLow": calibration_data[1],
                    "centerHigh": calibration_data[2],
                    "high": calibration_data[3],
                    "withCenter": calibration_data[4],
                    "unsavedChanges": False,
                }
            )

            self._calibration_fn.append(None)
            self._active_calibrations.append({"center": False, "extrema": False})
            self._update_calibration(i)

    @QtCore.Slot(event_handler.Event)
    def _event_callback(self, event: event_handler.Event) -> None:
        if event.device_guid != self._device_uuid:
            return

        if self._device is None:
            return

        if event.event_type == InputType.JoystickAxis:
            if event.raw_value is None:
                return

            index = self._device.axis_lookup[event.identifier] - 1
            state = self._state[index]

            # Update axis value information
            state["rawValue"] = event.raw_value
            state["calibratedValue"] = math.floor(
                self._calibration_fn[index](event.raw_value) * 65535 / 2
            )

            # Check if we're calibrating the axis and if so record possible
            # new calibration values
            calibration_changed = False
            if self._active_calibrations[index]["center"]:
                data = self._active_calibrations[index]["cvalues"]
                if data[0] > event.raw_value:
                    data[0] = event.raw_value
                    state["centerLow"] = event.raw_value
                    calibration_changed = True
                if data[1] < event.raw_value:
                    data[1] = event.raw_value
                    state["centerHigh"] = event.raw_value
                    calibration_changed = True
            elif self._active_calibrations[index]["extrema"]:
                data = self._active_calibrations[index]["evalues"]
                if data[0] > event.raw_value:
                    data[0] = event.raw_value
                    state["low"] = event.raw_value
                    calibration_changed = True
                if data[1] < event.raw_value:
                    data[1] = event.raw_value
                    state["high"] = event.raw_value
                    calibration_changed = True

            # Recompute the calibration function if we're actively calibrating
            if (
                self._active_calibrations[index]["center"]
                or self._active_calibrations[index]["extrema"]
            ):
                self._update_calibration(index)
                if calibration_changed:
                    self._state[index]["unsavedChanges"] = True

            # Signal that the model has changed for a UI update
            self.emit_update(index)

    def _get_module_slug(self) -> str:
        return self._module_slug

    def _set_module_slug(self, slug: str) -> None:
        slug = str(slug or "").strip().lower()
        if not slug or slug == self._module_slug:
            return
        from gremlin.modules.calibration import module_for_slug

        row = module_for_slug(slug)
        if row is None:
            return
        try:
            device_uuid = uuid.UUID(str(row["guid"]))
            device = dill.DILL.get_device_information_by_guid(
                dill.GUID.from_str(str(row["guid"]))
            )
        except Exception:
            return
        if device is None:
            return

        self.beginResetModel()
        self._module_slug = slug
        self._device = device
        self._device_uuid = device_uuid
        self._device_mapping = self._device_db.get_mapping(self._device)
        self._state = []
        self._calibration_fn = []
        self._active_calibrations = []
        self._initialize_state()
        self.deviceChanged.emit()
        self.modelReset.emit()
        self.endResetModel()

    moduleSlug = QtCore.Property(
        str, fget=_get_module_slug, fset=_set_module_slug, notify=deviceChanged
    )

    guid = QtCore.Property(str, fset=_set_guid, notify=deviceChanged)


Configuration().register(
    "ui",
    "general",
    "display-mode",
    PropertyType.Selection,
    "Numerical and Label",
    "Defines how input name is displayed.",
    {"valid_options": ["Numerical", "Numerical and Label", "Label"]},
    True,
)

Configuration().register(
    "global",
    "general",
    "action-sequence-information",
    PropertyType.Selection,
    "Full",
    "Defines how action sequences associated with inputs are displayed.",
    {"valid_options": ["Full", "Count"]},
    True,
)
