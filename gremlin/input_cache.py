# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, cast

import jsonschema

from dill import (
    DILL,
    GUID,
    DeviceSummary,
    UUID_LogicalDevice,
)
from gremlin import (
    common,
    error,
    keyboard,
    logical_device,
    types,
    util,
)
from gremlin.config import Configuration

_device_database_schema = {
    "type": "object",
    "required": ["revision", "devices", "mapping"],
    "additionalProperties": False,
    "properties": {
        "revision": {
            "type": "integer",
        },
        "devices": {"type": "array", "items": {"$ref": "#/$defs/device"}},
        "mapping": {
            "type": "object",
            "additionalProperties": {"$ref": "#/$defs/mappingEntry"},
        },
    },
    "$defs": {
        "device": {
            "type": "object",
            "required": ["vendor_id", "product_id", "name", "mapping"],
            "additionalProperties": False,
            "properties": {
                "vendor_id": {"type": "integer"},
                "product_id": {"type": "integer"},
                "name": {"type": "string", "minLength": 1},
                "mapping": {"type": "string", "minLength": 1},
            },
        },
        "mappingEntry": {
            "type": "object",
            "additionalProperties": False,
            "patternProperties": {
                "^Axis [1-8]$": {"type": "string"},
                "^Button [1-9]\\d*$": {"type": "string"},
                "^Hat [1-4]$": {"type": "string"},
            },
        },
    },
}


class DeviceMapping:
    def __init__(self, input_map: dict[tuple[types.InputType, int], Any]) -> None:
        self._input_map = input_map

    def input_name(self, identifier: tuple[types.InputType, int]) -> str:
        """Returns the label of an input formatted based on user preferences.

        Name formatting is based on the global configuration option and the
        availability of information about the input in the device mapping.

        If a device exists in the device database and its mapping or the input
        are not defined, input_name() returns the base input name.

        Args:
            identifier: Containes input type and index of the input.

        Returns:
            Formatted input name based on user settings.
        """
        input_name_display_mode = Configuration().value(
            "ui", "general", "display-mode"
        )
        ui_input_name = common.input_to_ui_string(*identifier)

        # Return base input name if it is not present in the database, otherwise
        # apply the desired formatting.
        db_input_name = self._input_map.get(identifier, "").strip()
        if len(db_input_name) == 0 or input_name_display_mode == "Numerical":
            return ui_input_name
        elif input_name_display_mode == "Numerical and Label":
            return f"{ui_input_name} - {db_input_name}"
        elif input_name_display_mode == "Label":
            return db_input_name
        else:
            return ui_input_name


class DeviceDatabase(metaclass=common.SingletonMetaclass):
    """Provides device specific names of axis, buttons, and hats if available
    for a given device.
    """

    # TODO: Some devices have configurable number of buttons and/or axes
    #       so adjusting device database information might be required in the
    #       future.

    def __init__(self) -> None:
        # Empty first: without the file every lookup gives plain names.
        self._device_db = {"revision": 0, "devices": [], "mapping": {}}
        db_file = util.resource_path("device_db.json")
        if not util.file_exists_and_is_accessible(db_file):
            return

        try:
            with open(db_file, encoding="utf-8") as f:
                json_data = json.load(f)
            jsonschema.validate(json_data, _device_database_schema)
            self._device_db = self._parse_database(json_data)
        except (
            OSError,
            UnicodeDecodeError,
            json.decoder.JSONDecodeError,
            jsonschema.ValidationError,
        ) as e:
            logging.getLogger("system").error(
                f"There was an error loading device database {db_file}: {e}"
            )

    def _parse_database(self, json_data: dict[str, Any]) -> dict[str, Any]:
        """Processes the raw JSON data for internal usage.

        Converts string based input identifiers into tuples of
        (InputType, index).

        Args:
            json_data: Raw JSON data loaded from the device database file.

        Returns:
            Processed JSON data with tuple based input identifiers.
        """
        processed_data = {
            "revision": json_data["revision"],
            "devices": json_data["devices"],
            "mapping": {},
        }

        # Split string identifier into its constituent parts and build the
        # corresponding identifier.
        for device_name in json_data["mapping"]:
            processed_data["mapping"][device_name] = {}
            for key, value in json_data["mapping"][device_name].items():
                type_string, index_string = key.split(" ")
                identifier = (
                    types.InputType.to_enum(type_string.lower()),
                    int(index_string),
                )
                processed_data["mapping"][device_name][identifier] = value

        return processed_data

    def _device_matches(
        self, device_data: dict[str, Any], device: DeviceSummary
    ) -> bool:
        return (
            device_data["product_id"] == device.product_id
            and device_data["vendor_id"] == device.vendor_id
        )

    def get_mapping_by_uuid(self, device_uuid: uuid.UUID) -> DeviceMapping | None:
        """Returns: DeviceMapping object for the given device GUID.

        Args:
            device_guid: Unique identifier of the device instance.

        Returns:
            A DeviceMapping instance matching the given device, or None if no
            mapping is available.
        """
        return self.get_mapping(
            DILL.get_device_information_by_guid(GUID.from_uuid(device_uuid))
        )

    def get_mapping(self, device: DeviceSummary) -> DeviceMapping | None:
        """Returns: DeviceMapping object for the given device.

        Args:
            device: Raw device data from DILL representing the device.

        Returns:
            A DeviceMapping instance matching the given device, or None if no
            mapping is available.
        """
        for dev in self._device_db["devices"]:
            if self._device_matches(dev, device):
                if dev["mapping"] not in self._device_db["mapping"]:
                    logging.getLogger("system").warning(
                        f"Device database lacks a mapping for device with pid: "
                        f"{device.product_id} and vid: {device.vendor_id}."
                    )
                    return None
                return DeviceMapping(self._device_db["mapping"][dev["mapping"]])
        return None


class JoystickWrapper:
    """Wraps joysticks and presents an API similar to vjoy."""

    class Input:
        """Represents a joystick input."""

        def __init__(self, joystick_guid: uuid.UUID, index: int) -> None:
            """Creates a new instance.

            Args:
                joystick_guid: unique id of the device instance
                index: index of the input
            """
            self._joystick_guid = joystick_guid
            self._index = index
            self._value = None

        def update(self, value: float | bool | types.HatDirection) -> None:
            """Updates the cached state of the specific input.

            Args:
                value: new value of the input
            """
            self._value = value

    class Axis(Input):
        """Represents a single axis of a joystick."""

        def __init__(self, joystick_guid: uuid.UUID, index: int) -> None:
            super().__init__(joystick_guid, index)

            self._value = 0.0
            self._seen = False

        def update(self, value: float | bool | types.HatDirection) -> None:
            self._value = value
            self._seen = True

        @property
        def seen(self) -> bool:
            """False until the axis has a value (it moved, or was read from
            the driver: EventListener.axis_value)."""
            return self._seen

        @property
        def value(self) -> float:
            return cast(float, self._value) if self._value else 0.0

    class Button(Input):
        """Represents a single button of a joystick."""

        def __init__(self, joystick_guid: uuid.UUID, index: int) -> None:
            super().__init__(joystick_guid, index)

            self._value = False

        @property
        def is_pressed(self) -> bool:
            return self._value

    class Hat(Input):
        """Represents a single hat of a joystick,"""

        def __init__(self, joystick_guid: uuid.UUID, index: int) -> None:
            super().__init__(joystick_guid, index)

            self._value = types.HatDirection.Center

        @property
        def direction(self) -> types.HatDirection:
            return self._value

    def __init__(self, device_guid: uuid.UUID) -> None:
        """Creates a new wrapper object for the given joystick.

        Args:
            device_guid: unique id of the joystick instance to wrap
        """
        self._device_guid = device_guid
        self._dill_guid = GUID.from_uuid(device_guid)
        if DILL.device_exists(self._dill_guid) is False:
            raise error.GremlinError(
                f"No device with the provided GUID '{device_guid}' exist"
            )

        self._info = DILL.get_device_information_by_guid(self._dill_guid)
        self._axis = self._init_axes()
        self._buttons = self._init_buttons()
        self._hats = self._init_hats()

    @property
    def device_guid(self) -> uuid.UUID:
        """Returns the unique ID of the joystick.

        Returns:
            Unique identifier of the joystick
        """
        return self._device_guid

    @property
    def name(self) -> str:
        """Returns the name of the joystick as the program shows it (an
        identical second stick is "<name> (2)"), not the driver's name.

        Returns:
            Name of the joystick
        """
        from gremlin import device_initialization

        return device_initialization.device_name(self._device_guid) or self._info.name

    def is_axis_valid(self, axis_index: int) -> bool:
        """Returns whether the specified axis exists for this device.

        Iterates over all known axes of this device and checks if one maps
        onto the named axis value.

        Args:
            axis_index: index of the axis in the AxisNames enum

        Returns:
            True the specified axis exists, False otherwise
        """
        for i in range(self._info.axis_count):
            if self._info.axis_map[i].axis_index == axis_index:
                return True
        return False

    def axis_reverse_lookup(self, axis_index: int) -> int:
        """Returns the linear index corresponding to the given axis index.

        Args:
            axis_index: index of the axis adhering to the AxisNames enum order

        Returns:
            linear index corresponding to the given axis index
        """
        for i in range(self._info.axis_count):
            if self._info.axis_map[i].axis_index == axis_index:
                return i + 1
        raise error.GremlinError(
            f"Axis reverse lookup failed for axis index {axis_index}"
        )

    def axis(self, index: int) -> Axis:
        """Returns the axis for the given index.

        The index is 1 based, i.e. the first axis starts with index 1.

        Args:
            index: index of the axis to return

        Returns:
            Axis instance corresponding to the given index
        """
        if index not in self._axis:
            raise error.GremlinError(
                f"Invalid axis {index} specified for device {self._device_guid}"
            )
        return self._axis[index]

    def button(self, index: int) -> Button:
        """Returns the Button instance for the given index.

        The index is 1 based, i.e. the first button starts with index 1.

        Args:
            index: index of the button to return

        Returns:
            Button instance corresponding to the given index
        """
        if not (0 < index < len(self._buttons)):
            raise error.GremlinError(
                f"Invalid button {index} specified for device {self._device_guid}"
            )
        return self._buttons[index]

    def hat(self, index: int) -> Hat:
        """Returns the Hat instance for the given index.

        The index is 1 based, i.e. the first hat starts with index 1.

        Args:
            index: index of the hat to return

        Returns:
            Hat instance corresponding to given index
        """
        if not (0 < index < len(self._hats)):
            raise error.GremlinError(
                f"Invalid hat {index} specified for device {self._device_guid}"
            )
        return self._hats[index]

    @property
    def axis_count(self) -> int:
        """Returns the number of axes of the joystick.

        Returns:
            Number of axes
        """
        return self._info.axis_count

    @property
    def button_count(self) -> int:
        """Returns the number of buttons on the joystick.

        Returns:
            Number of buttons
        """
        return self._info.button_count

    @property
    def hat_count(self) -> int:
        """Returns the number of hats on the joystick.

        Returns:
            Number of hats
        """
        return self._info.hat_count

    def _init_axes(self) -> dict[int, JoystickWrapper.Axis]:
        """Initializes the axes of the joystick.

        Returns:
            dictionary of JoystickWrapper.Axis objects with their axis index
            as key rather than the axis number
        """
        axes = {}
        for i in range(self._info.axis_count):
            aid = self._info.axis_map[i].axis_index
            axes[aid] = JoystickWrapper.Axis(self._device_guid, aid)
        return axes

    def reload(self) -> None:
        """Reads the layout again (the stick came back). Inputs it still
        has keep their objects and values (scripts and conditions hold
        them); new ones start empty, gone ones are dropped."""
        info = DILL.get_device_information_by_guid(self._dill_guid)
        old_axes, old_buttons, old_hats = self._axis, self._buttons, self._hats
        self._info = info
        axes = self._init_axes()
        for aid in axes:
            if aid in old_axes:
                axes[aid] = old_axes[aid]
        buttons = self._init_buttons()
        for i in range(1, min(len(buttons), len(old_buttons))):
            buttons[i] = old_buttons[i]
        hats = self._init_hats()
        for i in range(1, min(len(hats), len(old_hats))):
            hats[i] = old_hats[i]
        self._axis, self._buttons, self._hats = axes, buttons, hats

    def let_go(self) -> tuple[list[int], list[int]]:
        """The stick is gone: its pressed buttons are let go and its hats
        centred. Returns the ids of the buttons and hats this changed."""
        buttons = []
        for button in self._buttons[1:]:
            if button is not None and button.is_pressed:
                button.update(False)
                buttons.append(button._index)
        hats = []
        for hat in self._hats[1:]:
            centre = (None, types.HatDirection.Center)
            if hat is not None and hat.direction not in centre:
                hat.update(types.HatDirection.Center)
                hats.append(hat._index)
        return buttons, hats

    def _init_buttons(self) -> list[JoystickWrapper.Button]:
        """Initializes the buttons of the joystick.

        Returns:
            list of JoystickWrapper.Button objects
        """
        buttons = [
            None,
        ]
        for i in range(self._info.button_count):
            buttons.append(JoystickWrapper.Button(self._device_guid, i + 1))
        return buttons

    def _init_hats(self) -> list[JoystickWrapper.Hat]:
        """Initializes the hats of the joystick.

        Returns:
            list of JoystickWrapper.Hat objects
        """
        hats = [
            None,
        ]
        for i in range(self._info.hat_count):
            hats.append(JoystickWrapper.Hat(self._device_guid, i + 1))
        return hats


class Joystick(metaclass=common.SingletonMetaclass):
    """Allows read access to joystick state information."""

    # Dictionary of initialized joystick devices
    devices = {}

    def __getitem__(
        self, device_guid: uuid.UUID
    ) -> logical_device.LogicalDevice | JoystickWrapper:
        """Returns the requested joystick instance.

        If the joystick instance exists it is returned directly, otherwise
        it is first created and then returned.

        Args:
            device_guid: unique identifier of the joystick device

        Returns:
            The corresponding joystick device.
        """
        if device_guid not in self.devices:
            # Handle the intermediate output device first
            if device_guid == UUID_LogicalDevice:
                self.devices[device_guid] = logical_device.LogicalDevice()
            else:
                # If the device exists add process it and add it, otherwise
                # throw an exception
                if DILL.device_exists(GUID.from_uuid(device_guid)):
                    self.devices[device_guid] = JoystickWrapper(device_guid)
                else:
                    raise error.GremlinError(
                        f"No device with guid '{device_guid}' exists"
                    )

        return self.devices[device_guid]

    def reconnected(self, device_guid: uuid.UUID) -> None:
        """A stick came back (maybe with another layout under the same id):
        its cached inputs follow the layout the driver reports now."""
        wrapper = self.devices.get(device_guid)
        if isinstance(wrapper, JoystickWrapper):
            wrapper.reload()


class Keyboard(metaclass=common.SingletonMetaclass):
    """Provides access to the keyboard state."""

    def __init__(self) -> None:
        """Initialises a new object."""
        self._keyboard_state = {}

    def update(self, key: keyboard.Key, is_pressed: bool) -> None:
        """Updates the state of a key.

        Args:
            key: input being changed
            is_pressed: whether the key is pressed
        """
        self._keyboard_state[key] = is_pressed

    def is_pressed(self, key: keyboard.Key | str) -> bool:
        """Returns whether or not the key is pressed.

        Args:
            key: input whose state to return

        Returns:
            True if the key is pressed, False otherwise
        """
        if isinstance(key, str):
            key = keyboard.key_from_name(key)
        return self._keyboard_state.get(key, False)
