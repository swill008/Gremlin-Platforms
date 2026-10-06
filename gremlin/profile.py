# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import dataclasses
import logging
import re
import uuid
from abc import (
    ABCMeta,
    abstractmethod,
)
from collections.abc import Iterable
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
)
from xml.dom import minidom
from xml.etree import ElementTree

import dill
from gremlin import (
    device_initialization,
    error,
    plugin_manager,
)
from gremlin.logical_device import LogicalDevice
from gremlin.osc import OscDevice
from gremlin.tree import TreeNode
from gremlin.types import (
    AxisButtonDirection,
    HatDirection,
    InputType,
    ScanCode,
)
from gremlin.user_script import Script
from gremlin.util import (
    clamp,
    create_subelement_node,
    create_subelement_node_custom,
    read_action_ids,
    read_subelement,
    read_subelement_custom,
    safe_format,
    safe_read,
)

if TYPE_CHECKING:
    from gremlin.base_classes import AbstractActionData


class AbstractVirtualButton(metaclass=ABCMeta):
    """Base class of all virtual buttons."""

    def __init__(self) -> None:
        """Creates a new instance."""
        pass

    @abstractmethod
    def from_xml(self, node: ElementTree.Element) -> None:
        """Populates the virtual button based on the node's data.

        Args:
            node: the XML node containing data for this instance
        """
        pass

    @abstractmethod
    def to_xml(self) -> ElementTree.Element:
        """Returns an XML node representing the data of this instance.

        Returns:
            XML node containing the instance's data
        """
        pass


class VirtualAxisButton(AbstractVirtualButton):
    """Virtual button which turns an axis range into a button."""

    def __init__(self, lower_limit: float = -0.1, upper_limit: float = 0.1) -> None:
        """Creates a new instance.

        Args:
            lower_limit: the lower limit of the virtual button
            upper_limit: the upper limit of the virtual button
        """
        super().__init__()

        self.lower_limit = lower_limit
        self.upper_limit = upper_limit
        self.direction = AxisButtonDirection.Anywhere

    def from_xml(self, node: ElementTree.Element) -> None:
        """Populates the virtual button based on the node's data.

        Args:
            node: the node containing data for this instance
        """
        self.lower_limit = read_subelement(node, "lower-limit")
        self.upper_limit = read_subelement(node, "upper-limit")
        self.direction = read_subelement(node, "axis-button-direction")

    def to_xml(self) -> ElementTree.Element:
        """Returns an XML node representing the data of this instance.

        Returns:
            XML node containing the instance's data
        """
        node = ElementTree.Element("virtual-button")
        node.append(create_subelement_node("lower-limit", self.lower_limit))
        node.append(create_subelement_node("upper-limit", self.upper_limit))
        node.append(create_subelement_node("axis-button-direction", self.direction))
        return node


class VirtualHatButton(AbstractVirtualButton):
    """Virtual button which combines hat directions into a button."""

    def __init__(self, directions: set = set()) -> None:
        """Creates a instance.

        Args:
            directions: list of direction that form the virtual button
        """
        super().__init__()

        self.directions = list(set(directions))

    def from_xml(self, node: ElementTree.Element) -> None:
        """Populates the activation condition based on the node's data.

        Args:
            node: the node containing data for this instance
        """
        self.directions = []
        for hd_node in node.findall("hat-direction"):
            self.directions.append(HatDirection.to_enum(str(hd_node.text)))

    def to_xml(self) -> ElementTree.Element:
        """Returns an XML node representing the data of this instance.

        Returns:
            XML node containing the instance's data
        """
        node = ElementTree.Element("virtual-button")
        for direction in self.directions:
            hd_node = ElementTree.Element("hat-direction")
            hd_node.text = HatDirection.to_string(direction)
            node.append(hd_node)
        return node



# Every profile saved before the Options fallback carried this value.
_OLD_MACRO_DELAY = 0.05


def options_macro_delay() -> float:
    """Options > Action > Macro > Default delay (registered by gremlin.macro)."""
    from gremlin import macro  # noqa: F401  (registers the option)
    from gremlin.config import Configuration

    try:
        return float(Configuration().value("action", "macro", "default-delay"))
    except (error.GremlinError, TypeError, ValueError):
        return _OLD_MACRO_DELAY


class Settings:
    """Stores general profile specific settings."""

    def __init__(self, parent: Profile) -> None:
        """Creates a new instance.

        Args:
            parent the parent profile
        """
        self.parent = parent
        self.vjoy_as_input = {}
        self.vjoy_initial_values = {}
        self.startup_mode: str = "Use Heuristic"
        # None: use the Options default (Action > Macro > Default delay).
        self.macro_default_delay: float | None = None

    def effective_macro_delay(self) -> float:
        """The profile's own macro delay, or the Options default."""
        if self.macro_default_delay is not None:
            return self.macro_default_delay
        return options_macro_delay()

    def from_xml(self, node: ElementTree.Element) -> None:
        """Populates the data storage with the XML node's contents.

        Args:
            node the node containing the settings data
        """
        settings_node = node.find("settings")
        if settings_node is None:
            raise error.ProfileError("Missing settings node in profile.")

        self.startup_mode = read_subelement_custom(
            settings_node, "startup-mode", lambda x: str(x.text)
        )

        delay = read_subelement_custom(
            settings_node, "macro-default-delay", lambda x: float(x.text)
        )
        source = settings_node.find("macro-delay-source")
        if source is not None and (source.text or "").strip() == "options":
            self.macro_default_delay = None
        elif abs(delay - _OLD_MACRO_DELAY) < 1e-9:
            # Older profiles always saved 0.05, chosen or not: follow Options.
            self.macro_default_delay = None
        else:
            self.macro_default_delay = delay

        # vJoy as input settings
        self.vjoy_as_input = {}
        for vjoy_node in settings_node.findall("vjoy-input-id"):
            vid = int(vjoy_node.text)
            self.vjoy_as_input[vid] = True

        # vjoy initialization values
        self.vjoy_initial_values = {}
        for vjoy_node in settings_node.findall("vjoy-initial-value"):
            vid = read_subelement_custom(vjoy_node, "vjoy-id", lambda x: int(x.text))
            aid = read_subelement_custom(vjoy_node, "axis-id", lambda x: int(x.text))
            value = read_subelement_custom(vjoy_node, "value", lambda x: float(x.text))

            if vid not in self.vjoy_initial_values:
                self.vjoy_initial_values[vid] = {}
            self.vjoy_initial_values[vid][aid] = clamp(value, -1.0, 1.0)

    def to_xml(self) -> ElementTree.Element:
        """Returns an XML node containing the settings.

        Returns:
            XML node containing the settings
        """
        node = ElementTree.Element("settings")

        node.append(
            create_subelement_node_custom("startup-mode", self.startup_mode, str)
        )
        # Always write a number so older Gremlin builds can still open the
        # profile; the source element says it follows Options.
        node.append(
            create_subelement_node_custom(
                "macro-default-delay", self.effective_macro_delay(), str
            )
        )
        if self.macro_default_delay is None:
            node.append(
                create_subelement_node_custom("macro-delay-source", "options", str)
            )

        # Process vJoy as input settings.
        for vid, value in self.vjoy_as_input.items():
            if value is True:
                node.append(create_subelement_node_custom("vjoy-input-id", vid, str))

        # Process vJoy axis initial values.
        for vid, data in self.vjoy_initial_values.items():
            for aid, value in data.items():
                e_node = ElementTree.Element("vjoy-initial-value")
                e_node.append(create_subelement_node_custom("vjoy-id", vid, str))
                e_node.append(create_subelement_node_custom("axis-id", aid, str))
                e_node.append(create_subelement_node_custom("value", value, str))
                node.append(e_node)

        return node

    def get_initial_vjoy_axis_value(self, vid: int, aid: int) -> float:
        """Returns the initial value a vJoy axis should use.

        Args:
            vid the id of the virtual joystick
            aid the id of the axis

        Returns:
            default value for the specified axis
        """
        value = 0.0
        if vid in self.vjoy_initial_values:
            if aid in self.vjoy_initial_values[vid]:
                value = self.vjoy_initial_values[vid][aid]
        return value

    def set_initial_vjoy_axis_value(self, vid: int, aid: int, value: float) -> None:
        """Sets the default value for a particular vJoy axis.

        Args:
            vid the id of the virtual joystick
            aid the id of the axis
            value the default value to use with the specified axis
        """
        if vid not in self.vjoy_initial_values:
            self.vjoy_initial_values[vid] = {}
        self.vjoy_initial_values[vid][aid] = value


_ACTION_ID = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)


def remap_action_ids(
    action_xml: list[str], input_xml: list[str], library: Library
) -> tuple[list[str], list[str]]:
    """Gives the actions in this XML new ids where the library already has
    those ids (the same actions added twice must not clash)."""
    mapping: dict[str, str] = {}
    for block in action_xml:
        for found in _ACTION_ID.findall(block):
            try:
                key = uuid.UUID(found)
            except ValueError:
                continue
            if library.has_action(key):
                mapping[found.lower()] = str(uuid.uuid4())
    if not mapping:
        return action_xml, input_xml

    def swap(text: str) -> str:
        for old, new in mapping.items():
            text = re.sub(old, new, text, flags=re.IGNORECASE)
        return text

    return [swap(block) for block in action_xml], [swap(block) for block in input_xml]


class Library:
    """Stores actions in order to be reference by input binding instances.

    Each item is a self-contained entry with a UUID assigned to it which
    is used by the input items to reference the actual content.
    """

    def __init__(self) -> None:
        """Creates a new library instance.

        The library contains both the individual action configurations as well
        as the items composed of them.
        """
        self._actions: dict[uuid.UUID, AbstractActionData] = {}

    def add_action(self, action: AbstractActionData) -> None:
        if action.id in self._actions:
            logging.getLogger("system").warning(
                f"Action with id {action.id} already exists, skipping."
            )
        self._actions[action.id] = action

    def delete_action(self, key: uuid.UUID) -> None:
        """Deletes the action with the given key from the library.

        Args:
            key: the key of the action to delete
        """
        if key not in self._actions:
            logging.getLogger("system").warning(
                f"Attempting to remove non-existant action with id {key}."
            )
        if key in self._actions:
            del self._actions[key]

    def remove_unused(self, action: AbstractActionData, recursive: bool = True) -> None:
        """Removes the provided action and all its children if unsued.

        Args:
            action: the action to remove
            recursive: if true all children of the action will be subjected
                to the same removal check
        """
        self._remove_unused(action, recursive, self._used_by_inputs())

    def _used_by_inputs(self) -> set[uuid.UUID]:
        """Actions the open profile's inputs use, when this is its library."""
        from gremlin import shared_state

        profile = shared_state.current_profile
        if profile is None or profile.library is not self:
            return set()
        return profile.actions_in_use()

    def _remove_unused(
        self, action: AbstractActionData, recursive: bool, used: set[uuid.UUID]
    ) -> None:
        # An input still uses it (an action can be shared): it stays.
        if action.id in used:
            return
        # If the action occurs in another action we can abort any further
        # processing
        for entry in self._actions.values():
            if action in entry.get_actions()[0]:
                return

        # Delete before recursing, else children see this as still referenced
        children = action.get_actions()[0] if recursive else []
        self._actions.pop(action.id, None)

        for child in children:
            self._remove_unused(child, True, used)

    def actions_by_type(
        self, action_type: type[AbstractActionData]
    ) -> list[AbstractActionData]:
        """Returns all actions in the library matching the given type.

        Args:
            action_type: type of the action to return

        Returns:
            All actions of the given type
        """
        return [a for a in self._actions.values() if isinstance(a, action_type)]

    def actions_by_predicate(
        self, predicate: Callable[[AbstractActionData], bool]
    ) -> list[AbstractActionData]:
        """Returns the list of actions fulfilling the given predicate.

        Args:
            predicate: the predicate to evaluate on each action

        Returns:
            List of all actions fulfilling the given predicate
        """
        actions = []
        for action in self._actions.values():
            if predicate(action):
                actions.append(action)
        return actions

    def get_action(self, key: uuid.UUID) -> AbstractActionData:
        """Returns the action specified by the key.

        If there is no action with the specified key an exception is throw.

        Args:
            key: the key to return an action for

        Returns:
            The  instance stored at the given key
        """
        if key not in self._actions:
            raise error.GremlinError(f"Invalid key for library action: {key}")
        return self._actions[key]

    def has_action(self, key: uuid.UUID) -> bool:
        """Checks if an action exists with the given key.

        Args:
            key: the key to check for

        Returns:
            True if an action exists for the specific key, False otherwise
        """
        return key in self._actions

    def from_xml(self, node: ElementTree.Element) -> None:
        """Parses a library node to populate this instance.

        Args:
            node: XML node containing the library information
        """
        parse_later = []

        def can_parse(entry: ElementTree.Element) -> bool:
            return all([aid in self._actions for aid in read_action_ids(entry)])

        # Parse all actions
        for entry in node.findall("./library/action"):
            # Ensure all required attributes are present
            if not set(["id", "type"]).issubset(entry.keys()):
                raise error.ProfileError("Incomplete library action specification")

            # Ensure the action type is known
            type_key = entry.get("type")
            if type_key not in plugin_manager.PluginManager().tag_map:
                action_id = safe_read(entry, "id", uuid.UUID)
                raise error.ProfileError(
                    f"Unknown type '{type_key}' in action with id '{action_id}'"
                )

            # Check if all actions referenced by this action have already
            # been parsed, if yes parse it otherwise attempt to process it
            # again at a later stage.
            if can_parse(entry):
                self._parse_xml_action(entry)
            else:
                parse_later.append(entry)

        # Parse the actions whose child actions were not parsed yet, pass after
        # pass, until a pass parses nothing more.
        while parse_later:
            waiting = []
            for entry in parse_later:
                if can_parse(entry):
                    self._parse_xml_action(entry)
                else:
                    waiting.append(entry)
            if len(waiting) == len(parse_later):
                logging.getLogger("system").error(
                    "Loading profile failed due to action resolution chain"
                )
                break
            parse_later = waiting

        # Restore action sequence as it appears in the file to maintain serialization
        # consistency for change detection tests. Actions already here (a
        # Device Pack adds its actions to an open profile) stay, before them.
        file_ids = [
            safe_read(entry, "id", uuid.UUID)
            for entry in node.findall("./library/action")
        ]
        in_file = set(file_ids)
        kept = {
            aid: action for aid, action in self._actions.items() if aid not in in_file
        }
        self._actions = kept | {
            fid: self._actions[fid] for fid in file_ids if fid in self._actions
        }

    def unfinished_actions(self) -> list[str]:
        """What a save would leave out: "<action>: <first error>" for each
        unfinished action, so the user can be asked first."""
        out = []
        for action in self._actions.values():
            errors = [
                uf.message
                for uf in action.user_feedback()
                # By name: base_classes imports this module.
                if uf.feedback_type.name == "Error"
            ]
            if errors:
                out.append(f"{action.name}: {errors[0]}")
        return out

    def drop_invalid_actions(self) -> None:
        """Remove unfinished actions from the open profile.

        An explicit save does this. Checking for unsaved work must not.
        """
        invalid_aids = [n.id for n in self._actions.values() if not n.is_valid()]
        for action in self._actions.values():
            for selector in action._valid_selectors():
                to_remove = []
                for i, child in enumerate(action.get_actions(selector)[0]):
                    if child.id in invalid_aids:
                        to_remove.append(i)
                # Delete from the end so earlier removals do not shift the
                # positions still waiting to be removed.
                for i in reversed(to_remove):
                    action.remove_action(i, selector)

    def actions_in_use_by_type(self, action_type: type) -> list[AbstractActionData]:
        """Actions of that type that an input of the open profile uses (the
        library also holds deleted and replaced ones until the next save,
        which Reuse and the pick lists must not hand back)."""
        from gremlin import shared_state

        found = self.actions_by_type(action_type)
        profile = shared_state.current_profile
        if profile is None or profile.library is not self:
            return found
        used = profile.actions_in_use()
        return [action for action in found if action.id in used]

    def to_xml(self, used: set[uuid.UUID] | None = None) -> ElementTree.Element:
        """Returns an XML node encoding the content of this library.

        Invalid actions are left out of the node. They stay in the open
        profile until drop_invalid_actions is called. used: when given, only
        these actions are written (the profile passes the ones its inputs
        use, so deleted, replaced and draft actions don't reach the file).

        Returns:
            XML node holding the instance's content
        """
        node = ElementTree.Element("library")
        for action in [n for n in self._actions.values() if n.is_valid()]:
            if used is None or action.id in used:
                node.append(action.to_xml())
        return node

    def _parse_xml_action(self, action: ElementTree.Element) -> None:
        """Parses an action XML node and stores it within the library.

        Args:
            action: XML node to parse
        """
        type_key = action.get("type")
        action_obj = plugin_manager.PluginManager().tag_map[type_key]()
        action_obj.from_xml(action, self)
        if action_obj.id in self._actions:
            raise error.ProfileError(
                f"Duplicate library action entry with id '{action_obj.id}'"
            )
        self._actions[action_obj.id] = action_obj


@dataclasses.dataclass
class DeviceInfo:
    """Captures information about a generic device."""

    device_uuid: uuid.UUID = dill.UUID_Invalid
    name: str = ""

    def from_xml(self, node: ElementTree.Element) -> None:
        """Sets attributes from an XML node.

        Args:
            node: XML node containing the device information
        """
        self.device_uuid = read_subelement(node, "device-id")
        self.name = read_subelement(node, "device-name")

    def to_xml(self) -> ElementTree.Element:
        """Returns an XML node representing this device information.

        Returns:
            XML node containing the device's information
        """
        node = ElementTree.Element("device")
        node.append(create_subelement_node("device-id", self.device_uuid))
        node.append(create_subelement_node("device-name", self.name))
        return node


class DeviceDatabase:
    """Database tracking devices used in a profile.

    This information can be useful when a device present in a profile is
    disconnected.
    """

    def __init__(self) -> None:
        self.devices: dict[uuid.UUID, DeviceInfo] = {}

    def update_for_uuids(self, uuids: Iterable[uuid.UUID]) -> None:
        """Update information for given UUIDs for any connected devices."""
        for device_uuid in uuids:
            try:
                dev = device_initialization.device_for_uuid(device_uuid)
                self.devices[device_uuid] = DeviceInfo(device_uuid, dev.name)
            except KeyError:
                # Device is not connected, we have no information to add.
                continue

    def from_xml(self, node: ElementTree.Element) -> None:
        """Populates the device database from an XML node.

        Args:
            node: XML node containing device information
        """
        self.devices.clear()
        for device_node in node.findall("./devices/device"):
            device_info = DeviceInfo()
            device_info.from_xml(device_node)
            self.devices[device_info.device_uuid] = device_info

    def to_xml(self) -> ElementTree.Element:
        """Returns an XML node representing all devices in the database.

        Returns:
            XML node containing all device information
        """
        node = ElementTree.Element("devices")
        for device_info in self.devices.values():
            node.append(device_info.to_xml())
        return node


class Profile:
    """Stores the contents and an entire configuration profile."""

    current_version = 14

    def __init__(self) -> None:
        self.inputs: dict[uuid.UUID, list[InputItem]] = {}
        self.library = Library()
        self.device_database = DeviceDatabase()
        self.settings = Settings(self)
        self.modes = ModeHierarchy(self)
        self.scripts = ScriptManager(self)
        self.fpath: Path | None = None
        # The profile as it would be written right after the last load or save.
        self._saved_snapshot: str | None = None
        LogicalDevice().reset()
        OscDevice().reset()

    def from_xml(self, fpath: Path) -> None:
        """Reads the content of an XML file and initializes the profile.

        Args:
            fpath: path to the XML file to parse
        """
        # Parse file into an XML document.
        from gremlin.ui.live_debug import trace
        try:
            tree = ElementTree.parse(str(fpath))
        except Exception:
            trace("READ", "Profile", "from_xml", fpath, "error")
            raise
        root = tree.getroot()
        trace("READ", "Profile", "from_xml", fpath, "ok")

        version = int(root.get("version", "0"))
        if version != Profile.current_version:
            # Raised, not just shown: the caller then puts back the profile
            # that was open (an empty one used to replace it and go into
            # Recent).
            raise error.ProfileError(
                f"This profile is of version {version}; only version "
                f"{Profile.current_version} can be read."
            )

        # Create library entries and modes.
        self.fpath = fpath
        self.settings.from_xml(root)
        self._logical_devices_from_xml(root)
        self._osc_devices_from_xml(root)
        self.library.from_xml(root)
        self.device_database.from_xml(root)
        self.modes.from_xml(root)
        self.scripts.from_xml(root)

        # Parse individual inputs.
        for node in root.findall("./inputs/input"):
            self._process_input(node)

        self._saved_snapshot = self._xml_text()

    def to_xml(self, fpath: Path, *, prune: bool = True) -> None:
        """Writes the profile's content to an XML file.

        Args:
            fpath: path to the XML file in which to write the content
            prune: when True, unfinished actions are removed from the open
                profile before the file is written. The unsaved check passes
                False so looking does not delete anything.
        """
        if prune:
            self.library.drop_invalid_actions()
        text = self._xml_text()
        # Safely (a temporary file, then a swap), as module files are: a
        # crash mid-save leaves the old profile whole.
        from gremlin.modules import module_file

        module_file.write_text(Path(fpath), text, encoding="utf-8-sig", newline="")
        before, self._saved_snapshot = self._saved_snapshot, text
        if before != text:
            # Tools > History: what this save changed (worked out off this thread).
            from gremlin import history_profile

            history_profile.record_save(Path(fpath), before, text)
        from gremlin.ui.live_debug import trace
        trace("SAVE", "Profile", "to_xml", fpath, "ok")

    def _xml_text(self) -> str:
        """The profile as pretty XML text, exactly as to_xml writes it."""
        root = ElementTree.Element("profile")
        root.set("version", str(Profile.current_version))

        # Serialize inputs entries.
        inputs = ElementTree.Element("inputs")

        # Process physical inputs.
        for device_data in self.inputs.values():
            for input_data in device_data:
                if len(input_data.action_sequences) > 0:
                    inputs.append(input_data.to_xml())
        root.append(inputs)

        # Managed content.
        root.append(self.settings.to_xml())
        root.append(self._logical_devices_to_xml())
        root.append(self._osc_devices_to_xml())
        # Only what an input uses: what was deleted or replaced (kept in
        # memory for Undo) and editor drafts stay out of the file.
        root.append(self.library.to_xml(self.actions_in_use()))
        root.append(self.modes.to_xml())
        root.append(self.scripts.to_xml())
        self.device_database.update_for_uuids(self.inputs)
        root.append(self.device_database.to_xml())

        # Serialize XML document.
        ugly_xml = ElementTree.tostring(root, encoding="utf-8")
        return minidom.parseString(ugly_xml).toprettyxml(indent="    ")

    def get_input_count(
        self,
        device_guid: uuid.UUID,
        input_type: InputType,
        input_id: int | ScanCode,
        mode: str,
    ) -> int:
        """Returns the number of InputItem instances corresponding to the
        provided information.

        Args:
            device_guid: GUID of the device
            input_type: type of the input
            input_id: id of the input
            mode: name of the mode

        Returns:
            Number of InputItem instances linked with the given information
        """
        if device_guid not in self.inputs:
            return 0

        for item in self.inputs[device_guid]:
            if (
                item.input_type == input_type
                and item.input_id == input_id
                and item.mode == mode
            ):
                return len(item.action_sequences)

        return 0

    def get_input_item(
        self,
        device_guid: uuid.UUID,
        input_type: InputType,
        input_id: int | ScanCode,
        mode: str,
        create_if_missing: bool = False,
    ) -> InputItem | None:
        """Returns the InputItem corresponding to the provided information.

        Args:
            device_guid: GUID of the device
            input_type: type of the input
            input_id: id of the input
            mode: name of the mode of the input item
            create_if_missing: If True will create an empty InputItem if none
                exists

        Returns:
            InputItem corresponding to the given information
        """
        # Verify provided information has correct type information
        if not (
            isinstance(device_guid, uuid.UUID)
            and isinstance(input_type, InputType)
            and type(input_id) in [int, tuple]
            and isinstance(mode, str)
        ):
            raise error.ProfileError("Invalid input specification provided.")

        if device_guid not in self.inputs:
            if create_if_missing:
                self.inputs[device_guid] = []
            else:
                return None

        for item in self.inputs[device_guid]:
            if (
                item.input_type == input_type
                and item.input_id == input_id
                and item.mode == mode
            ):
                return item

        if create_if_missing:
            item = InputItem(self.library)
            item.device_id = device_guid
            item.input_type = input_type
            item.input_id = input_id
            item.mode = mode
            self.inputs[device_guid].append(item)
            return item
        else:
            return None

    @staticmethod
    def roots_of(items: Iterable[InputItem]) -> list[AbstractActionData]:
        """The root action of every binding of these inputs."""
        return [
            binding.root_action
            for item in items
            for binding in item.action_sequences
            if binding.root_action is not None
        ]

    def add_inputs(
        self,
        device_id: uuid.UUID,
        input_xml: list[str],
        action_xml: list[str],
        remap: bool = True,
    ) -> list[InputItem]:
        """Adds inputs, and the actions they use, given as XML (a Device
        Pack, a History entry, an Undo step). remap=False: the caller made
        sure no id clashes (put_input), so ids, and references to actions
        already in the library, are kept."""
        if remap:
            action_xml, input_xml = remap_action_ids(
                action_xml, input_xml, self.library
            )
        if action_xml:
            root = ElementTree.Element("profile")
            library = ElementTree.SubElement(root, "library")
            for block in action_xml:
                library.append(ElementTree.fromstring(block))
            self.library.from_xml(root)
        added = []
        for block in input_xml:
            item = InputItem(self.library)
            item.from_xml(ElementTree.fromstring(block))
            item.device_id = device_id
            item.mode = str(item.mode or "Default")
            for binding in item.action_sequences:
                binding.input_item = item
            self.inputs.setdefault(device_id, []).append(item)
            added.append(item)
        return added

    def input_snapshot(self, item: InputItem | None) -> dict | None:
        """An input and its actions as XML ({"input", "actions"}); None
        when it has no actions. put_input() puts it back."""
        if item is None or not item.action_sequences:
            return None
        seen: dict[uuid.UUID, AbstractActionData] = {}
        pending = list(self.roots_of([item]))
        while pending:
            action = pending.pop()
            if action.id in seen:
                continue
            seen[action.id] = action
            pending.extend(action.get_actions()[0])
        written = {}
        for action in seen.values():
            node = action.to_xml(True)
            if node is not None:
                written[action.id] = node
        # An action that couldn't be written is left out of the actions that
        # hold it too, or the snapshot couldn't be read back.
        left_out = {str(aid) for aid in seen if aid not in written}
        if left_out:
            for node in written.values():
                for parent in list(node.iter()):
                    for entry in list(parent.findall("action-id")):
                        if (entry.text or "").strip() in left_out:
                            parent.remove(entry)
        return {
            "input": ElementTree.tostring(item.to_xml(), encoding="unicode"),
            "actions": [
                ElementTree.tostring(node, encoding="unicode")
                for node in written.values()
            ],
        }

    def put_input(
        self,
        device_id: uuid.UUID,
        input_type: InputType,
        input_id: int | tuple,
        mode: str,
        snapshot: dict | None,
    ) -> None:
        """Replaces an input's actions with a snapshot (None: no actions).
        The snapshot is read first: one that can't be read changes nothing."""
        if snapshot:
            _check_snapshot(snapshot)
        current = [
            item
            for item in self.inputs.get(device_id, [])
            if item.input_type == input_type
            and item.input_id == input_id
            and item.mode == mode
        ]
        self.drop_inputs(device_id, current)
        if not snapshot:
            return
        # The same profile: an action another input still uses (a shared
        # Merge Axis) is that action, not a new copy; an unused one left in
        # the library gives way to the copy.
        used = self.actions_in_use()
        blocks = []
        for block in snapshot["actions"]:
            try:
                aid = uuid.UUID(str(ElementTree.fromstring(block).get("id")))
            except ValueError:
                blocks.append(block)
                continue
            if self.library.has_action(aid):
                if aid in used:
                    continue
                self.library.delete_action(aid)
            blocks.append(block)
        self.add_inputs(device_id, [snapshot["input"]], blocks, remap=False)

    def drop_inputs(self, device_id: uuid.UUID, doomed: Iterable[InputItem]) -> None:
        """Removes these inputs of a device and the actions only they used."""
        gone = {id(item) for item in doomed}
        items = self.inputs.get(device_id, [])
        removed = [item for item in items if id(item) in gone]
        if device_id in self.inputs:
            self.inputs[device_id] = [item for item in items if id(item) not in gone]
        self.drop_unused_actions(self.roots_of(removed))

    def actions_in_use(self) -> set[uuid.UUID]:
        """Ids of every action an input uses, with every action inside them."""
        used: set[uuid.UUID] = set()
        pending = [
            binding.root_action
            for items in self.inputs.values()
            for item in items
            for binding in item.action_sequences
            if binding.root_action is not None
        ]
        while pending:
            action = pending.pop()
            if action is None or action.id in used:
                continue
            used.add(action.id)
            pending.extend(action.get_actions()[0])
        return used

    def drop_unused_actions(self, roots: list[AbstractActionData]) -> None:
        """Removes these actions, and every action inside them, from the
        library, except those an input still uses (an action can be shared)."""
        used = self.actions_in_use()
        seen: set[uuid.UUID] = set()
        pending = [root for root in roots if root is not None]
        while pending:
            action = pending.pop()
            if action.id in seen:
                continue
            seen.add(action.id)
            pending.extend(action.get_actions()[0])
            if action.id not in used and self.library.has_action(action.id):
                self.library.delete_action(action.id)

    def has_unsaved_changes(self) -> bool:
        """Checks if the profile has unsaved changes.

        Compares against the profile as it was right after the last load or
        save, not the file on disk: a file saved by an older version (for
        example without a newer default property) is not an edit.

        Returns:
            True if there are unsaved changes, False otherwise
        """
        if self._saved_snapshot is None:
            return True
        return self._xml_text() != self._saved_snapshot

    def mark_clean(self) -> None:
        """A new, untouched profile has nothing to lose: only edits after
        this count as unsaved changes."""
        self._saved_snapshot = self._xml_text()

    def _process_input(self, node: ElementTree.Element) -> None:
        """Processes an InputItem XML node and stores it.

        Args:
            node: XML node containing InputItem data
        """
        item = InputItem(self.library)
        item.from_xml(node)

        if item.device_id not in self.inputs:
            self.inputs[item.device_id] = []
        self.inputs[item.device_id].append(item)

    def _logical_devices_from_xml(self, root_node: ElementTree.Element) -> None:
        logical = LogicalDevice()
        logical.reset()
        groups = []
        for node in root_node.findall("./logical-device/groups/group"):
            name = (node.text or "").strip()
            if name and name not in groups:
                groups.append(name)
        logical.set_groups(groups)
        for node in root_node.findall("./logical-device/input"):
            kind = read_subelement(node, "input-type")
            input_id = read_subelement(node, "input-id")
            label = read_subelement(node, "label")
            user_node = node.find("user-label")
            group_node = node.find("group")
            user_label = (user_node.text or "").strip() if user_node is not None and user_node.text else ""
            group = (group_node.text or "").strip() if group_node is not None and group_node.text else ""
            hide_node = node.find("hide-system")
            hide_system = (
                hide_node is not None
                and (hide_node.text or "").strip().lower() in ("1", "true", "yes")
            )
            system = f"{InputType.to_string(kind).capitalize()} {input_id}"
            if not user_label and label != system:
                user_label = label
            made = logical.create(kind, input_id, label, user_label=user_label, group=group)
            made.hide_system = hide_system and bool(made.second_name)

    def _logical_devices_to_xml(self) -> ElementTree.Element:
        node = ElementTree.Element("logical-device")
        logical = LogicalDevice()
        if logical.group_names():
            groups = ElementTree.Element("groups")
            for name in logical.group_names():
                entry = ElementTree.Element("group")
                entry.text = name
                groups.append(entry)
            node.append(groups)
        for item in logical.ordered():
            input_node = ElementTree.Element("input")
            input_node.append(create_subelement_node("input-type", item.type))
            input_node.append(create_subelement_node("input-id", item.id))
            input_node.append(create_subelement_node("label", item.label))
            if item.user_label:
                user = ElementTree.Element("user-label")
                user.text = item.user_label
                input_node.append(user)
            if item.group:
                folder = ElementTree.Element("group")
                folder.text = item.group
                input_node.append(folder)
            if item.hide_system:
                hidden = ElementTree.Element("hide-system")
                hidden.text = "true"
                input_node.append(hidden)
            node.append(input_node)
        return node

    def _osc_devices_from_xml(self, root_node: ElementTree.Element) -> None:
        osc = OscDevice()
        osc.reset()
        for node in root_node.findall("./osc-device/input"):
            osc.create(
                read_subelement(node, "input-type"),
                label=read_subelement(node, "label"),
                input_id=read_subelement(node, "input-id"),
            )

    def _osc_devices_to_xml(self) -> ElementTree.Element:
        node = ElementTree.Element("osc-device")
        for label in OscDevice().labels_of_type():
            item = OscDevice()[label]
            input_node = ElementTree.Element("input")
            input_node.append(create_subelement_node("input-type", item.type))
            input_node.append(create_subelement_node("input-id", item.id))
            input_node.append(create_subelement_node("label", item.label))
            node.append(input_node)
        return node


class InputItem:
    """Represents the configuration of a single input in a particular mode."""

    def __init__(self, library: Library) -> None:
        """Creates a new instance.

        Args:
            library: library instance that contains all action definitions
        """
        self.device_id: uuid.UUID | None = None
        self.input_type: InputType | None = None
        # Int for joysticks, tuple of two ints for keyboard.
        self.input_id: int | ScanCode | None = None
        self.mode: str | None = None
        self.library = library
        self.action_sequences: list[InputItemBinding] = []
        self.is_active = True

    def from_xml(self, node: ElementTree.Element) -> None:
        self.device_id = read_subelement(node, "device-id")
        self.input_type = read_subelement(node, "input-type")
        self.input_id = read_subelement(node, "input-id")
        self.mode = read_subelement(node, "mode")

        # If the input is from a keyboard convert the input id into
        # the scan code and extended input flag
        if self.input_type == InputType.Keyboard:
            self.input_id = (self.input_id & 0xFF, self.input_id >> 8 == 1)

        # Parse every action configuration entry
        for entry in node.findall("action-configuration"):
            action = InputItemBinding(self)
            action.from_xml(entry)
            self.action_sequences.append(action)

    def to_xml(self) -> ElementTree.Element:
        node = ElementTree.Element("input")

        # Input item specification
        node.append(create_subelement_node("device-id", self.device_id))
        node.append(create_subelement_node("input-type", self.input_type))
        node.append(create_subelement_node("mode", self.mode))
        input_id = self.input_id

        # To convert keyboard input tuples (scan_code, extended_bit) to integer:
        # input_id = extended_bit << 8 | scan_code
        if self.input_type == InputType.Keyboard:
            assert isinstance(self.input_id, tuple) and len(self.input_id) == 2
            input_id = self.input_id[1] << 8 | self.input_id[0]
        node.append(create_subelement_node("input-id", input_id))

        # Action configurations
        for entry in self.action_sequences:
            node.append(entry.to_xml())

        return node

    def descriptor(self) -> str:
        """Returns a string representation describing the input item.

        Returns:
            String identifying this input item in a textual manner
        """
        return (
            f"{self.device_id}: {InputType.to_string(self.input_type)} {self.input_id}"
        )

    def add_item_binding(self) -> InputItemBinding:
        """Adds a new binding to this input item and returns it."""
        p_manager = plugin_manager.PluginManager()
        root_action = p_manager.create_instance("Root", self.input_type)
        binding = InputItemBinding(self)
        binding.root_action = root_action
        binding.behavior = self.input_type
        self.action_sequences.append(binding)
        return binding

    def remove_item_binding(self, binding: InputItemBinding) -> None:
        """Removes the given binding instance if present.

        Args:
            binding: InputItemBinding instance to remove from the item
        """
        if binding in self.action_sequences:
            del self.action_sequences[self.action_sequences.index(binding)]


class InputItemBinding:
    """Links together a LibraryItem and it's activation behavior."""

    def __init__(self, input_item: InputItem) -> None:
        self.input_item = input_item
        self.root_action: AbstractActionData | None = None
        self.behavior: InputType | None = None
        self.virtual_button: AbstractVirtualButton | None = None

    def from_xml(self, node: ElementTree.Element) -> None:
        root_id = read_subelement(node, "root-action")
        if not self.input_item.library.has_action(root_id):
            raise error.ProfileError(
                f"{self.input_item.descriptor()} links to an invalid library "
                f"item {root_id}"
            )
        self.root_action = self.input_item.library.get_action(root_id)
        self.behavior = read_subelement(node, "behavior")
        self.virtual_button = self._parse_virtual_button(node)

    def to_xml(self) -> ElementTree.Element:
        node = ElementTree.Element("action-configuration")
        node.append(create_subelement_node("root-action", self.root_action.id))
        node.append(create_subelement_node("behavior", self.behavior))
        vb_node = self._write_virtual_button()
        if vb_node is not None:
            node.append(vb_node)

        return node

    @property
    def library(self) -> Library:
        """Returns the profile's library instance.

        Returns:
            Library instance of the profile
        """
        return self.input_item.library

    def _parse_virtual_button(self, node: ElementTree.Element) -> AbstractVirtualButton:
        # Ensure the configuration requires a virtual button
        virtual_button = None
        if (
            self.input_item.input_type == InputType.JoystickAxis
            and self.behavior == InputType.JoystickButton
        ):
            virtual_button = VirtualAxisButton()
        elif (
            self.input_item.input_type == InputType.JoystickHat
            and self.behavior == InputType.JoystickButton
        ):
            virtual_button = VirtualHatButton()

        # Ensure we have a virtual button entry to parse
        if virtual_button is not None:
            vb_node = node.find("virtual-button")
            if vb_node is None:
                raise error.ProfileError(
                    f"Missing virtual-button entry for input "
                    f"{self.input_item.input_id} of device {self.input_item.device_id}"
                )
            virtual_button.from_xml(vb_node)

        return virtual_button

    def _write_virtual_button(self) -> ElementTree.Element | None:
        # Ascertain whether or not a virtual button node needs to be created
        needs_virtual_button = False
        if (
            self.input_item.input_type == InputType.JoystickAxis
            and self.behavior == InputType.JoystickButton
        ):
            needs_virtual_button = True
        elif (
            self.input_item.input_type == InputType.JoystickHat
            and self.behavior == InputType.JoystickButton
        ):
            needs_virtual_button = True

        # Ensure there is no virtual button information present
        # if it is not needed
        if not needs_virtual_button:
            self.virtual_button = None
            return None

        # Check we have virtual button data
        if self.virtual_button is None:
            raise error.ProfileError(
                f"Virtual button specification not present for action "
                f"configuration part of input {self.input_item.descriptor()}."
            )
        return self.virtual_button.to_xml()


def _check_snapshot(snapshot: dict) -> None:
    """Raises ProfileError when an input snapshot can't be read back, before
    anything in the profile is changed."""
    trial = Library()
    root = ElementTree.Element("profile")
    library = ElementTree.SubElement(root, "library")
    try:
        for block in snapshot.get("actions") or []:
            library.append(ElementTree.fromstring(block))
        trial.from_xml(root)
        item = InputItem(trial)
        item.from_xml(ElementTree.fromstring(snapshot["input"]))
    except ElementTree.ParseError as e:
        raise error.ProfileError(f"The kept copy of the input can't be read: {e}")


class ModeHierarchy:
    """Contains all the modes and their hierarchical information."""

    def __init__(self, parent_profile: Profile) -> None:
        """Creates a new mode hierarchy.

        Args:
            parent_profile: the profile this mode hierarchy is associated with
        """
        self._profile = parent_profile
        self._hierarchy = TreeNode("")
        self._hierarchy.add_child(TreeNode("Default"))

    @property
    def first_mode(self) -> str:
        """Returns the alphabetically first mode without a parent.

        Returns:
            Name of the first mode
        """
        roots = [child.value for child in self._hierarchy.children]
        if len(roots) == 0:
            return "Default"
        return min(roots)

    def mode_names(self) -> list[str]:
        """Returns a list containing the names of all modes.

        Returns:
            List of all mode names
        """
        return sorted([node.value for node in self.mode_list()])

    def mode_list(self) -> list[TreeNode]:
        """Returns a list of all mode nodes.

        Returns:
            List containing TreeNodes of all modes
        """
        modes = self._hierarchy.nodes_matching(lambda x: True)
        modes.remove(self._hierarchy)
        return modes

    def valid_parents(self, mode_name: str) -> list[str]:
        """Returns the list of parents that are valid for the given mode.

        Args:
            mode_name: name of the mode for which to return valid parents

        Returns:
            List of valid parents for the specified mode
        """
        parent_candidates = []
        mode_node = self.find_mode(mode_name)
        for node in self.mode_list():
            if not mode_node.is_descendant(node) and node != mode_node:
                parent_candidates.append(node.value)
        return sorted(parent_candidates)

    def find_mode(self, mode_name: str) -> TreeNode:
        """Returns the node corresponding to the name with the given name.

        Args:
            mode_name: name of the mode to find and return

        Returns:
            Node corresponding to the node with the provided name
        """
        nodes = self._hierarchy.nodes_matching(lambda x: mode_name == x.value)
        if len(nodes) > 1:
            raise error.GremlinError(f"More than one mode named '{mode_name}' exists")
        elif len(nodes) == 0:
            raise error.GremlinError(f"No node with the name '{mode_name}' exists")
        return nodes[0]

    def add_mode(self, mode_name: str) -> None:
        """Adds a new mode to the hierarchy.

        Args:
            mode_name: name of the new mode to add
        """
        if self.mode_exists(mode_name):
            raise error.GremlinError(
                f"Attempting to add an already existing mode '{mode_name}'."
            )
        self._hierarchy.add_child(TreeNode(mode_name))

    def bindings_in_mode(self, mode_name: str) -> int:
        """Returns how many bindings deleting the given mode would remove."""
        return sum(
            len(item.action_sequences)
            for items in self._profile.inputs.values()
            for item in items
            if item.mode == mode_name
        )

    def delete_mode(self, mode_name: str) -> None:
        """Deletes the mode with the given name from the hierarchy.

        Args:
            mode_name: name of the mode to delete
        """
        if not self.mode_exists(mode_name):
            raise error.GremlinError(
                f"Attempting to delete a non-existant mode '{mode_name}'."
            )

        if len(self.mode_list()) <= 1:
            raise error.GremlinError("A profile needs at least one mode.")

        # Find node and remove it from the hierarchy tree but reconnect its
        # children to their grandparent. A copy of the list: set_parent
        # takes each child out of it (every other child was lost).
        node = self.find_mode(mode_name)
        parent_node = node.parent
        node.detach()
        for child in list(node.children):
            child.set_parent(parent_node)

        # Find all InputItem actions using the mode being deleted and remove
        # them as well, with the actions only they used.
        for device_id, input_items in list(self._profile.inputs.items()):
            self._profile.drop_inputs(
                device_id, [x for x in input_items if x.mode == mode_name]
            )

        if self._profile.settings.startup_mode == mode_name:
            self._profile.settings.startup_mode = "Use Heuristic"

    def rename_mode(self, old_name: str, new_name: str) -> None:
        """Changes the name of an existing mode.

        Args:
            old_name: name of the mode to rename
            new_name: new name for the mode
        """
        # Don't do anything if the names are the same
        if old_name == new_name:
            return

        # Handle missing mode to rename
        if not self.mode_exists(old_name):
            raise error.GremlinError(
                f"Attempting to rename non-existant mode '{old_name}'"
            )
        # Raise an error if renaming to an existing name
        elif self.mode_exists(new_name):
            raise error.GremlinError(
                f"Unable to rename '{old_name}' to '{new_name}' as a mode "
                f"with that name already exists"
            )

        # Perform renaming of the mode
        node = self.find_mode(old_name)
        node.value = new_name

        # Find all actions associated to the old mode name
        for action in self._actions_with_mode(old_name):
            action.mode = new_name
        # Actions that switch to the mode (Change Mode) follow the new name.
        for action in self._profile.library.actions_by_predicate(
            lambda a: old_name in (getattr(a, "_target_modes", None) or [])
        ):
            change: Any = action
            change._target_modes = [
                new_name if mode == old_name else mode for mode in change._target_modes
            ]

        if self._profile.settings.startup_mode == old_name:
            self._profile.settings.startup_mode = new_name

    def set_parent(self, mode_name: str, parent_name: str | None) -> None:
        """Sets the parent of the specified mode.

        Args:
            mode_name: name of the mode to set the parent of
            parent_name: name of the new parent mode
        """
        mode_node = self.find_mode(mode_name)
        parent_node = self.find_mode(parent_name)
        # Detach node before setting new parent to avoid cycle detection
        mode_node.detach()
        mode_node.set_parent(parent_node)

    def mode_exists(self, name: str) -> bool:
        """Checks if a mode with a given name already exists.

        Args:
            name: name of the mode to check for existence

        Returns:
            True if the mode exists, False otherwise
        """
        return len(self._hierarchy.nodes_matching(lambda x: name == x.value)) > 0

    def from_xml(self, root: ElementTree.Element) -> None:
        # Parse individual nodes
        nodes = {}
        node_parents = {}
        for node in root.findall("./modes/mode"):
            if "parent" in node.attrib:
                node_parents[node.text] = node.get("parent")
            nodes[node.text] = TreeNode(node.text)

        # Reconstruct tree structure
        for child, parent in node_parents.items():
            if parent not in nodes:
                logging.getLogger("system").warning(
                    f"Mode '{child}' names a parent mode '{parent}' that isn't "
                    "in the profile; it is kept as a top-level mode."
                )
                continue
            nodes[child].set_parent(nodes[parent])

        self._hierarchy = TreeNode("")
        for node in nodes.values():
            if node.parent is None:
                node.set_parent(self._hierarchy)

    def to_xml(self) -> ElementTree.Element:
        node = ElementTree.Element("modes")
        for mode in self._hierarchy.nodes_matching(lambda x: True):
            if mode.parent is None:
                continue

            n_mode = ElementTree.Element("mode")
            n_mode.text = mode.value
            if mode.parent != self._hierarchy:
                n_mode.set("parent", safe_format(mode.parent.value, str))
            node.append(n_mode)
        return node

    def _actions_with_mode(self, mode: str) -> list[AbstractActionData]:
        """Returns all actions belonging to the given mode.

        Args:
            mode: name of the mode for which to return all actions
        """
        actions = []
        for action_list in self._profile.inputs.values():
            actions.extend([x for x in action_list if x.mode == mode])
        return actions


class ScriptManager:
    def __init__(self, profile: Profile) -> None:
        """Creates a new instance.

        Each script is uniquely identified by the path to the script as well
        as its assigned name.

        Args:
            profile: the profile whose scripts to manage
        """
        self._profile = profile
        self._scripts: list[Script] = []

    @property
    def scripts(self) -> list[Script]:
        """Returns all managed scripts.

        Returns:
            List of all managed scripts
        """
        return self._scripts

    def add_script(self, path: Path) -> None:
        """Adds a new script to the manager.

        Args:
            path: path to the script's location
        """
        self._scripts.append(Script(path, self._default_name(path)))
        self._scripts.sort(key=lambda s: (s.path, s.name))

    def remove_script(self, path: Path, name: str) -> None:
        """Removes the specified script.

        Args:
            path: path to the script
            name: name of the script
        """
        script = self._find_instance(path, name)
        if script:
            self._scripts.remove(script)

    def rename_script(self, path: Path, old_name: str, new_name: str) -> None:
        """Renames the specified script.

        Args:
            path: path to the script
            old_name: current name of the script
            new_name: new name to use for the script
        """
        names = [s.name for s in self.scripts if s.path == path]
        if new_name not in names:
            script = self._find_instance(path, old_name)
            script.name = new_name
            self._scripts.sort(key=lambda s: (s.path, s.name))

    def index_of(self, path: Path, name: str) -> int:
        """Returns the index of the specified script.

        Args:
            path: path to the script
            name: name of the script

        Returns:
            Index of the script in the list of scripts
        """
        instance = self._find_instance(path, name)
        if not instance:
            raise error.GremlinError(f"Unable to find script {path} with name '{name}'")
        return self._scripts.index(instance)

    def _default_name(self, path: Path) -> str:
        """Generates a valid default name for the given script path.

        Args:
            path: path to the script

        Returns:
            Valid name to use for the script that doesn't clash with other
            existing scripts.
        """
        names = [s.name for s in self.scripts if s.path == path]
        for i in range(len(names) + 1):
            candidate = f"Instance {i + 1}"
            if candidate not in names:
                return candidate
        raise error.GremlinError(f"Unablle to find a valid default name for {path}")

    def from_xml(self, root: ElementTree.Element) -> None:
        for node in root.findall("./scripts/script"):
            try:
                script_instance = Script()
                script_instance.from_xml(node)
                self._scripts.append(script_instance)
            except error.GremlinError as e:
                logging.getLogger("system").error(f"Failure to load a user script: {e}")
        self._scripts.sort(key=lambda s: (s.path, s.name))

    def to_xml(self) -> ElementTree.Element:
        script_node = ElementTree.Element("scripts")
        for script in self._scripts:
            node = script.to_xml()
            if node is not None:
                script_node.append(node)
        return script_node

    def _find_instance(self, path: Path, name: str) -> Script | None:
        """Attempts to find the specified script.

        Args:
            path: path to the script
            name: name of the script

        Returns:
            The script instance if one is found, else None
        """
        for script in self._scripts:
            if script.path == path and script.name == name:
                return script
        return None
