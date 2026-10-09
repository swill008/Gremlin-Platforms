# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import collections
import re
import threading
import uuid
from typing import cast

import dill
from gremlin.common import SingletonMetaclass
from gremlin.edits import note_edit
from gremlin.error import (
    GremlinError,
    MissingImplementationError,
)
from gremlin.types import (
    HatDirection,
    InputType,
)

# Values are written from the main thread, the relative axis loop and macro
# threads (06 RB11): each change is made under this lock.
_VALUE_LOCK = threading.Lock()


def _same_group(first: str, second: str) -> bool:
    """True when two group names differ only in capitals or spacing."""
    return " ".join(first.split()).casefold() == " ".join(second.split()).casefold()


_DIGITS = re.compile(r'(\d+)')


def _natural_key(text: str) -> tuple[tuple[str | int, ...], str]:
    # From R16 (58499ab9): numbers sort by value, so Button 2 comes before Button 10.
    parts = _DIGITS.split(text)
    key = tuple(
        int(part) if index % 2 else part.casefold()
        for index, part in enumerate(parts)
    )
    return key, text


class _RowData:
    """The rows themselves; a LogicalRows and the LogicalDevice showing it
    share one of these."""

    def __init__(self) -> None:
        self.inputs: dict = {}
        self.label_lookup: dict = {}
        self.groups: list[str] = []
        self.order: list = []
        # Changed since the Logical Device file was last saved or loaded.
        self.dirty: bool = False

    def changed(self) -> None:
        self.dirty = True
        note_edit()


class LogicalRows:
    """Implements a device like system for arbitrary amonuts of logical device
    inputs that can be used to combine and further modify inputs before
    ultimately feeding them to a vJoy device.

    Every row has a permanent random id (uid); its number is a display name
    (06 S78). The rows are saved in the Logical Device module file
    (decision D-04-LD-FILE); LogicalDevice() shows them."""

    device_guid = dill.UUID_LogicalDevice

    class Input:
        """General input class, base class for all other inputs."""

        Identifier = collections.namedtuple("Identifier", ["type", "id"])

        def __init__(self, label: str, id: int) -> None:
            """Creates a new Input instance.

            Args:
                label: textual label associated with this input
                index: per InputType index
            """
            self._owner: _RowData | None = None
            self._label = label
            self._id = id
            self._value = None
            self._uid = uuid.uuid4().hex
            self._user_label = ""
            self._group = ""
            self._hide_system = False

        def _changed(self) -> None:
            if self._owner is not None:
                self._owner.changed()

        @property
        def uid(self) -> str:
            """Permanent id: kept through rename, regroup, move and sort."""
            return self._uid

        @uid.setter
        def uid(self, value: str) -> None:
            if value != self._uid:
                self._uid = value
                self._changed()

        @property
        def user_label(self) -> str:
            return self._user_label

        @user_label.setter
        def user_label(self, value: str) -> None:
            if value != self._user_label:
                self._user_label = value
                self._changed()

        @property
        def group(self) -> str:
            return self._group

        @group.setter
        def group(self, value: str) -> None:
            if value != self._group:
                self._group = value
                self._changed()

        @property
        def hide_system(self) -> bool:
            return self._hide_system

        @hide_system.setter
        def hide_system(self, value: bool) -> None:
            if value != self._hide_system:
                self._hide_system = value
                self._changed()

        def update(self, value: float | bool | HatDirection) -> None:
            with _VALUE_LOCK:
                self._value = value

        def nudge(self, delta: float) -> float:
            """Moves an axis value by delta, kept in -1..1, in one step (no
            other writer in between); returns the new value."""
            with _VALUE_LOCK:
                moved = float(cast(float, self._value) or 0.0) + delta
                self._value = max(-1.0, min(1.0, moved))
                return self._value

        def to_neutral(self) -> None:
            """Back to rest: axis 0, button up, hat centre."""
            with _VALUE_LOCK:
                self._value = self._neutral()

        def _neutral(self) -> float | bool | HatDirection | None:
            return None

        @property
        def label(self) -> str:
            return self._label

        @property
        def system_name(self) -> str:
            """The name the system assigned. It does not change when the user renames the row."""
            kind = InputType.to_string(self.type).capitalize()
            return f"{kind} {self.id}"

        @property
        def second_name(self) -> str:
            """The user's name. Empty means the row shows only the system name."""
            text = (self.user_label or "").strip()
            if text and text != self.system_name:
                return text
            return ""

        @property
        def row_title(self) -> str:
            second = self.second_name
            if second and self.hide_system:
                return second
            if second:
                return f"{self.system_name}   {second}"
            return self.system_name

        @property
        def choice_label(self) -> str:
            second = self.second_name
            if second and self.hide_system:
                return second
            if second:
                return f"{self.system_name} — {second}"
            return self.system_name

        def key(self) -> str:
            return f"{InputType.to_string(self.type)}:{self.id}"

        @property
        def id(self) -> int:
            return self._id

        @property
        def type(self) -> InputType:
            return self._input_type()

        @property
        def identifier(self) -> Identifier:
            return self.Identifier(self.type, self.id)

        def _input_type(self) -> InputType:
            raise MissingImplementationError("Input._input_type not implemented")

    class Axis(Input):
        def __init__(self, label: str, id: int) -> None:
            super().__init__(label, id)
            self._value = 0.0

        def _neutral(self) -> float:
            return 0.0

        def _input_type(self) -> InputType:
            return InputType.JoystickAxis

        @property
        def value(self) -> float:
            return self._value

    class Button(Input):
        def __init__(self, label: str, id: int) -> None:
            super().__init__(label, id)
            self._value = False

        def _neutral(self) -> bool:
            return False

        def _input_type(self) -> InputType:
            return InputType.JoystickButton

        @property
        def is_pressed(self) -> bool:
            return self._value

    class Hat(Input):
        def __init__(self, label: str, id: int) -> None:
            super().__init__(label, id)
            self._value = HatDirection.Center

        def _neutral(self) -> HatDirection:
            return HatDirection.Center

        def _input_type(self) -> InputType:
            return InputType.JoystickHat

        @property
        def direction(self) -> HatDirection:
            return self._value

    def __init__(self) -> None:
        self._data = _RowData()

    @property
    def _inputs(self) -> dict:
        return self._data.inputs

    @_inputs.setter
    def _inputs(self, value: dict) -> None:
        self._data.inputs = value

    @property
    def _label_lookup(self) -> dict:
        return self._data.label_lookup

    @_label_lookup.setter
    def _label_lookup(self, value: dict) -> None:
        self._data.label_lookup = value

    @property
    def _groups(self) -> list[str]:
        return self._data.groups

    @_groups.setter
    def _groups(self, value: list[str]) -> None:
        self._data.groups = value

    @property
    def _order(self) -> list:
        return self._data.order

    @_order.setter
    def _order(self, value: list) -> None:
        self._data.order = value

    @property
    def dirty(self) -> bool:
        """True when the rows changed since the last save or load."""
        return self._data.dirty

    def mark_saved(self) -> None:
        self._data.dirty = False

    def _changed(self) -> None:
        self._data.changed()

    def by_uid(self, uid: str) -> Input | None:
        for item in self._inputs.values():
            if item.uid == uid:
                return item
        return None

    def uid_of(self, input_type: InputType, input_id: int) -> str | None:
        item = self._inputs.get(self.Input.Identifier(input_type, int(input_id)))
        return item.uid if item is not None else None

    def identifier_of_uid(self, uid: str) -> Input.Identifier | None:
        """The control's current type and number."""
        item = self.by_uid(uid)
        return item.identifier if item is not None else None

    def to_dict(self) -> dict:
        """The layout as stored in the module file; keys mirror the XML names."""
        return {
            "controls": [
                {
                    "uid": item.uid,
                    "type": InputType.to_string(item.type),
                    "id": item.id,
                    "label": item.label,
                    "user-label": item.user_label,
                    "group": item.group,
                    "hide-system": bool(item.hide_system),
                }
                for item in self.ordered()
            ],
            "groups": list(self._groups),
        }

    def load_dict(self, data: dict) -> None:
        """Replaces the rows with a to_dict() layout, then counts as saved."""
        self.reset()
        self.set_groups(list(data.get("groups", [])))
        for entry in data.get("controls", []):
            kind = entry["type"]
            if isinstance(kind, str):
                kind = InputType.to_enum(kind)
            made = self.create(
                kind,
                int(entry["id"]),
                entry.get("label") or None,
                user_label=entry.get("user-label", "") or "",
                group=entry.get("group", "") or "",
                uid=entry.get("uid") or None,
            )
            hidden = bool(entry.get("hide-system", False))
            made.hide_system = hidden and bool(made.second_name)
        self.mark_saved()

    def __getitem__(self, identifier_or_label: Input.Identifier | str) -> Input:
        return self._inputs[self._resolve_to_identifier(identifier_or_label)]

    def exists(self, identifier_or_label: Input.Identifier | str) -> bool:
        """Returns whether an input with the specified identifier or label
        exists.

        Args:
            identifier_or_label: Identifier or label of the input to check for

        Returns:
            True if an input with the specified identifier or label exists,
            False otherwise
        """
        try:
            identifier = self._resolve_to_identifier(identifier_or_label)
            return identifier in self._inputs
        except GremlinError:
            return False

    def create(
        self,
        type: InputType,
        input_id: int | None = None,
        label: str | None = None,
        user_label: str = "",
        group: str = "",
        uid: str | None = None,
    ) -> Input:
        """Creates a new input instance of the given type.

        Args:
            type: the type of input to create
            input_id: unique id identifying this input
            label: if given will be used as the label of the new input
            uid: permanent id to keep; a new one when None
        """
        self._changed()
        if label in self.labels_of_type():
            raise GremlinError(f"An input named {label} already exists")

        do_create = {
            InputType.JoystickAxis: self.Axis,
            InputType.JoystickButton: self.Button,
            InputType.JoystickHat: self.Hat,
        }

        # Use provided input id or generate a new onw if the provided one is
        # currently in use.
        if input_id is None or self._is_id_in_use(input_id, type):
            input_id = self._lowest_available_id(type)

        # Generate a valid label if none has been provided.
        if label is None:
            # Create a key and check it is valid and if not, make it valid.
            base = f"{InputType.to_string(type).capitalize()} {input_id}"
            # A rename may have taken the plain name: add the lowest free (2), (3)...
            label, copy = base, 1
            while label in self._label_lookup:
                copy += 1
                label = f"{base} ({copy})"

        # Create input store information and return it.
        new_input = do_create[type](label, input_id)
        if uid:
            new_input._uid = uid
        new_input._owner = self._data
        new_input.user_label = (user_label or "").strip()
        new_input.group = (group or "").strip()
        if new_input.group and new_input.group not in self._groups:
            self._groups.append(new_input.group)
        self._inputs[new_input.identifier] = new_input
        self._label_lookup[label] = new_input.identifier
        if new_input.identifier not in self._order:
            self._order.append(new_input.identifier)
        return new_input

    def reset_values(self) -> None:
        """Every input back to neutral (axis 0, button up, hat centre): at
        Stop, so the next Run starts from rest (decision R1, 06 S85)."""
        for item in list(self._inputs.values()):
            item.to_neutral()

    def reset(self) -> None:
        """Resets the IO system to contain no entries."""
        self._changed()
        self._inputs = {}
        self._label_lookup = {}
        self._groups = []
        self._order = []

    def set_label(self, old_label: str, new_label: str) -> None:
        """Changes the label of an existing input instance.

        Args:
            old_label: label of the instance to change the label of
            new_label: new label to use
        """
        self._changed()
        if old_label == new_label:
            return

        if old_label not in self._label_lookup:
            raise GremlinError(f"No input with label '{old_label}' exists")
        if new_label in self._label_lookup:
            raise GremlinError(f"Input with label '{new_label}' already exists")

        input = self._inputs[self._label_lookup[old_label]]
        input._label = new_label
        self._label_lookup[new_label] = input.identifier
        del self._label_lookup[old_label]

    def delete(self, identifier_or_label: Input.Identifier | str) -> None:
        """Deletes the specified input if it is present.

        Args:
            identifier_or_label: Identifier or label of the input to delete
        """
        self._changed()
        input = self[identifier_or_label]
        del self._inputs[input.identifier]
        del self._label_lookup[input.label]
        self._order = [ident for ident in self._order if ident != input.identifier]
        del input

    def labels_of_type(self, type_list: list[InputType] = []) -> list[str]:
        """Returns all labels for inputs of the matching types.

        Args:
            type_list: List of input types to match against, if empty all types
                are matched against.

        Returns:
            List of all labels matching the specified inputs types
        """
        x = [e.label for e in self.inputs_of_type(type_list)]
        return x

    def inputs_of_type(self, type_list: list[InputType] = []) -> list[Input]:
        """Returns input corresponding to the specified types.

        Args:
            type_list: List of input types to match against, if empty all types
                are matched against.

        Returns:
            List of inputs that have the specified type
        """
        if len(type_list) == 0:
            type_list = [
                InputType.JoystickAxis,
                InputType.JoystickButton,
                InputType.JoystickHat,
            ]
        return [
            e
            for e in sorted(
                self._inputs.values(),
                key=lambda x: (x.type.name, _natural_key(x.label)),
            )
            if e.type in type_list
        ]

    def input_by_offset(self, type: InputType, offset: int) -> Input:
        """Returns an input item based on the input type and the offset.

        The offset is the index an input instance has based on a linear internal
        index-based ordering of the inputs of the specified type.

        Args:
            type: the InputType to perform the lookup over
            offset: linear offset into the ordered list of inputs

        Returns:
            Input instance of the correct type with the specified offset
        """
        inputs = self.inputs_of_type([type])
        if len(inputs) <= offset:
            raise GremlinError(
                "Attempting to access an input item of type "
                + f"{InputType.to_string(type)} with invalid offset {offset}"
            )
        return inputs[offset]

    @property
    def axis_count(self) -> int:
        return len(self.inputs_of_type([InputType.JoystickAxis]))

    @property
    def button_count(self) -> int:
        return len(self.inputs_of_type([InputType.JoystickButton]))

    @property
    def hat_count(self) -> int:
        return len(self.inputs_of_type([InputType.JoystickHat]))

    def axis(self, index: int) -> Axis:
        if index not in [e.id for e in self.inputs_of_type([InputType.JoystickAxis])]:
            raise GremlinError(f"No logical axis with id {index} exists.")
        return cast(
            LogicalDevice.Axis,
            self[LogicalDevice.Input.Identifier(InputType.JoystickAxis, index)],
        )

    def button(self, index: int) -> Button:
        if index not in [e.id for e in self.inputs_of_type([InputType.JoystickButton])]:
            raise GremlinError(f"No logical button with id {index} exists.")
        return cast(
            LogicalDevice.Button,
            self[LogicalDevice.Input.Identifier(InputType.JoystickButton, index)],
        )

    def hat(self, index: int) -> Hat:
        if index not in [e.id for e in self.inputs_of_type([InputType.JoystickHat])]:
            raise GremlinError(f"No logical hat with id {index} exists.")
        return cast(
            LogicalDevice.Hat,
            self[LogicalDevice.Input.Identifier(InputType.JoystickHat, index)],
        )

    def ordered(self) -> list[Input]:
        """Parents in the saved order. This is not the system-name sort."""
        seen: set[LogicalDevice.Input.Identifier] = set()
        rows: list[LogicalDevice.Input] = []
        for ident in self._order:
            item = self._inputs.get(ident)
            if item is None or ident in seen:
                continue
            rows.append(item)
            seen.add(ident)
        for ident, item in self._inputs.items():
            if ident not in seen:
                rows.append(item)
        return rows

    def set_groups(self, names: list[str]) -> None:
        self._changed()
        self._groups = []
        for name in names:
            text = (name or "").strip()
            if text and text not in self._groups:
                self._groups.append(text)

    def group_names(self) -> list[str]:
        return list(self._groups)

    def ensure_group(self, name: str) -> str:
        """Returns the group for a typed name, creating it only when it is new.

        A name that differs from an existing group only in capitals or spacing
        is that group, so a typo in case or spaces cannot make a look-alike.
        """
        text = " ".join((name or "").split())
        if not text:
            return text
        for existing in self._groups:
            if _same_group(existing, text):
                return existing
        self._changed()
        self._groups.append(text)
        return text

    def create_many(
        self,
        type: InputType,
        count: int,
        group: str = "",
        user_label: str = "",
    ) -> list[Input]:
        """Create up to 180 parents. A group name is the folder, not a copy on every row."""
        self._changed()
        total = max(0, min(180, int(count)))
        folder = self.ensure_group(group)
        made: list[LogicalDevice.Input] = []
        for _ in range(total):
            made.append(self.create(type, user_label=user_label, group=folder))
        return made

    def set_user_label(self, identifier_or_label: Input.Identifier | str, text: str) -> None:
        self._changed()
        item = self[identifier_or_label]
        cleaned = (text or "").strip()
        if cleaned == item.system_name:
            cleaned = ""
        item.user_label = cleaned
        if not item.second_name:
            item.hide_system = False

    def set_member_group(self, identifier_or_label: Input.Identifier | str, group: str) -> None:
        self._changed()
        item = self[identifier_or_label]
        item.group = self.ensure_group(group)

    def rename_group(self, old_name: str, new_name: str) -> None:
        self._changed()
        old = (old_name or "").strip()
        new = " ".join((new_name or "").split())
        if not old or old not in self._groups:
            raise GremlinError(f"No group named '{old_name}' exists")
        if not new:
            raise GremlinError("A group needs a name")
        # Capitals or spacing on the same group are a rename; another group's name is not.
        clash = next(
            (name for name in self._groups if name != old and _same_group(name, new)),
            None,
        )
        if clash is not None:
            raise GremlinError(f"A group named '{clash}' already exists")
        self._groups = [new if name == old else name for name in self._groups]
        for item in self._inputs.values():
            if item.group == old:
                item.group = new

    def delete_group(self, name: str) -> None:
        """Remove the folder. The parents stay, in Ungrouped."""
        self._changed()
        text = (name or "").strip()
        self._groups = [entry for entry in self._groups if entry != text]
        for item in self._inputs.values():
            if item.group == text:
                item.group = ""

    def place(
        self,
        identifier_or_label: Input.Identifier | str,
        group: str,
        before: Input.Identifier | None = None,
    ) -> None:
        self._changed()
        item = self[identifier_or_label]
        item.group = self.ensure_group(group)
        ident = item.identifier
        self._order = [entry for entry in self._order if entry != ident]
        if before is not None and before in self._order and before != ident:
            self._order.insert(self._order.index(before), ident)
        else:
            self._order.append(ident)

    def move_group_before(self, name: str, before: str | None) -> None:
        self._changed()
        text = (name or "").strip()
        if text not in self._groups:
            return
        self._groups = [entry for entry in self._groups if entry != text]
        if before and before in self._groups:
            self._groups.insert(self._groups.index(before), text)
        else:
            self._groups.append(text)

    def sort_within(self, key_name: str) -> None:
        """Reorder parents inside each group without mixing buttons, axes, and hats."""
        self._changed()
        types = (
            InputType.JoystickButton,
            InputType.JoystickAxis,
            InputType.JoystickHat,
        )
        folders = [""] + list(self._groups)
        new_order: list[LogicalDevice.Input.Identifier] = []
        for folder in folders:
            for kind in types:
                bucket = [
                    item
                    for item in self.ordered()
                    if (item.group or "") == folder and item.type == kind
                ]
                if key_name == "user":
                    bucket.sort(
                        key=lambda item: (
                            _natural_key(item.second_name or item.system_name),
                            item.id,
                        )
                    )
                else:
                    bucket.sort(key=lambda item: item.id)
                new_order.extend(item.identifier for item in bucket)
        self._order = new_order

    def sort_groups(self) -> None:
        self._changed()
        self._groups.sort(key=_natural_key)

    def memento(self) -> dict:
        return {
            "groups": list(self._groups),
            "inputs": [
                {
                    "type": item.type,
                    "id": item.id,
                    "label": item.label,
                    "user": item.user_label,
                    "group": item.group,
                    "hide": bool(item.hide_system),
                    "uid": item.uid,
                }
                for item in self.ordered()
            ],
        }

    def restore(self, memo: dict) -> None:
        self._changed()
        wanted = {
            (entry["type"], int(entry["id"])): entry for entry in memo.get("inputs", [])
        }
        for item in list(self.ordered()):
            if (item.type, item.id) not in wanted:
                self.delete(item.identifier)
        ordered_inputs = []
        for entry in memo.get("inputs", []):
            ident = self.Input.Identifier(entry["type"], int(entry["id"]))
            if not self.exists(ident):
                self.create(
                    entry["type"],
                    int(entry["id"]),
                    entry["label"],
                    user_label=entry.get("user", ""),
                    group=entry.get("group", ""),
                    uid=entry.get("uid"),
                )
            item = self[ident]
            if entry.get("uid"):
                item.uid = entry["uid"]
            item.user_label = entry.get("user", "") or ""
            item.group = entry.get("group", "") or ""
            item.hide_system = bool(entry.get("hide", False)) and bool(item.second_name)
            if item.label != entry["label"]:
                try:
                    self.set_label(item.label, entry["label"])
                except GremlinError:
                    pass
                item = self[ident]
            ordered_inputs.append(item.identifier)
        self.set_groups(list(memo.get("groups", [])))
        for item in self._inputs.values():
            if item.group and item.group not in self._groups:
                self._groups.append(item.group)
        self._order = ordered_inputs

    def _lowest_available_id(self, type: InputType) -> int:
        """Returns the next lowest available id for the specified input type.

        Args:
            type: The input type to return the next id for

        Returns:
            The next available id for the specified input type
        """
        next_id = 1
        while next_id in sorted([e.id for e in self.inputs_of_type([type])]):
            next_id += 1
        return next_id

    def _is_id_in_use(self, id: int, type: InputType) -> bool:
        """Returns whether the specified id is already in use by the given type.

        Args:
            id: The id to check for usage
            type: The input type to check for usage of the id
        """
        return id in [e.id for e in self.inputs_of_type([type])]

    def _resolve_to_identifier(
        self, identifier_or_label: Input.Identifier | str
    ) -> Input.Identifier:
        """Returns the identifier associated with the given lookup.

        Args:
            identifier_or_label: The query key that may need to be converted to
                an identifier

        Returns:
            Identifier corresponding to the provided input
        """
        try:
            if isinstance(identifier_or_label, str):
                return self._label_lookup[identifier_or_label]
            elif isinstance(identifier_or_label, self.Input.Identifier):
                return identifier_or_label
            else:
                raise GremlinError(
                    f"Provided lookup '{identifier_or_label}' is invalid."
                )
        except KeyError:
            raise GremlinError(f"No input exists for '{identifier_or_label}'.")


class LogicalDevice(LogicalRows, metaclass=SingletonMetaclass):
    """The Logical Device rows of the open profile, for the screens and the
    runtime. The rows belong to the profile (Profile.logical_device); this
    shows the ones bound last, so a new Profile object no longer wipes
    another's rows (GL-074)."""

    def __init__(self) -> None:
        super().__init__()

    def bind(self, rows: LogicalRows) -> None:
        """Shows these rows from now on (they are shared, not copied)."""
        self._data = rows._data

    def shows(self, rows: LogicalRows) -> bool:
        """True when these are the rows shown."""
        return self._data is rows._data


def resolve_logical_reference(
    uid: str | None, input_type: InputType | None, input_id: int | None
) -> tuple[LogicalDevice.Input.Identifier | None, str | None]:
    """Current (type, number) and uid of a saved Logical Device reference.

    A uid wins; one the Logical Device doesn't have is missing (None), never
    re-targeted by number (D-04-LD-FILE decision 4). No uid (old data): the
    v14 load map (logical_device_file.current_uid_map, keyed by the XML type
    name or the enum name), then type+number. (None, None): nothing matches.
    """
    logical = LogicalDevice()
    if uid:
        return logical.identifier_of_uid(uid), uid
    if input_type is None or input_id is None:
        return None, None
    try:
        from gremlin import logical_device_file

        remap = getattr(logical_device_file, "current_uid_map", None) or {}
    except ImportError:
        remap = {}
    for key in (
        (InputType.to_string(input_type), int(input_id)),
        (input_type.name, int(input_id)),
    ):
        mapped = remap.get(key)
        if mapped:
            return logical.identifier_of_uid(mapped), mapped
    found = logical.uid_of(input_type, int(input_id))
    if found is None:
        return None, None
    return LogicalDevice.Input.Identifier(input_type, int(input_id)), found
