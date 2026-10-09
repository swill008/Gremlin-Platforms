# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import contextlib
import dataclasses
import logging
import re
import uuid
from abc import (
    ABCMeta,
    abstractmethod,
)
from collections.abc import Iterable, Iterator
from pathlib import Path
from types import EllipsisType
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
from gremlin.edits import EditNoted, edit_count, note_edit
from gremlin.logical_device import LogicalDevice, LogicalRows
from gremlin.osc import OscDevice
from gremlin.tree import TreeNode
from gremlin.types import (
    ActionProperty,
    AxisButtonDirection,
    DataCreationMode,
    HatDirection,
    InputType,
    ScanCode,
)
from gremlin.user_script import Script, rename_mode_settings
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


def _note_signals() -> None:
    """Edits the program announces count too (an action pane's properties,
    modes, Logical Device and OSC rows, Options a profile writes)."""
    from gremlin.signal import signal

    for each in (
        signal.actionsChanged,
        signal.inputItemChanged,
        signal.reloadCurrentInputItem,
        signal.modesChanged,
        signal.modeRenamed,
        signal.modeDeleted,
        signal.logicalDeviceModified,
        signal.oscDeviceModified,
        signal.configChanged,
    ):
        each.connect(lambda *_: note_edit())


_note_signals()


class AbstractVirtualButton(EditNoted, metaclass=ABCMeta):
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


class Settings(EditNoted):
    """Stores general profile specific settings."""

    def __init__(self, parent: Profile) -> None:
        """Creates a new instance.

        Args:
            parent the parent profile
        """
        self.parent = parent
        self.vjoy_as_input = {}
        self.vjoy_initial_values = {}
        self.startup_mode: str = "Last Active"
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
        note_edit()
        settings_node = node.find("settings")
        if settings_node is None:
            raise error.ProfileError("Missing settings node in profile.")

        self.startup_mode = read_subelement_custom(
            settings_node, "startup-mode", lambda x: str(x.text)
        )
        # Use Heuristic is gone: it loads as Last Active (D-04-LAST-ACTIVE).
        if self.startup_mode == "Use Heuristic":
            self.startup_mode = "Last Active"

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
        note_edit()
        if vid not in self.vjoy_initial_values:
            self.vjoy_initial_values[vid] = {}
        # Kept in -1..1 as a load does (GL-156, 04 S67).
        self.vjoy_initial_values[vid][aid] = clamp(float(value), -1.0, 1.0)


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


def reachable(
    roots: Iterable[AbstractActionData | None],
) -> list[AbstractActionData]:
    """Every action in these trees, each object once, parents first."""
    found: list[AbstractActionData] = []
    seen: set[int] = set()
    pending = [root for root in roots if root is not None]
    while pending:
        action = pending.pop(0)
        if action is None or id(action) in seen:
            continue
        seen.add(id(action))
        found.append(action)
        pending.extend(action.get_actions()[0])
    return found


def _unwritable_state(action: AbstractActionData) -> str:
    """The fields of an action to_xml can't write yet, as text."""

    def plain(value: object) -> object:
        if hasattr(value, "device_guid") and hasattr(value, "input_id"):
            names = ("device_guid", "input_type", "input_id")
            return tuple(getattr(value, name) for name in names)
        if hasattr(value, "tag") and hasattr(value, "id"):
            return str(getattr(value, "id"))
        if isinstance(value, (list, tuple)):
            return [plain(entry) for entry in value]
        return value

    try:
        fields = sorted(vars(action).items())
    except TypeError:
        return ""
    return repr([(name, plain(value)) for name, value in fields])


def binding_fingerprint(binding: InputItemBinding) -> str:
    """A binding and every action in it as text: equal text, equal content.
    Unfinished actions too (an edit to one must count)."""
    chunks: list[str] = []
    for action in reachable([binding.root_action]):
        node = action.to_xml(True)
        if node is not None:
            chunks.append(ElementTree.tostring(node, encoding="unicode"))
        else:
            chunks.append(f"{getattr(action, 'tag', '')}:{_unwritable_state(action)}")
    node = binding.to_xml()
    if node is not None:
        chunks.append(ElementTree.tostring(node, encoding="unicode"))
    return "\n".join(chunks)


def bindings_fingerprint(bindings: Iterable[InputItemBinding]) -> str:
    """binding_fingerprint of several bindings, in order."""
    return "\n--\n".join(binding_fingerprint(binding) for binding in bindings)


class DraftOutdated(error.GremlinError):
    """OK refused: the input changed under the open pane (History Restore,
    Auto Mapper, a Device Pack import, or another pane's OK on an action it
    shares), so writing the pane's copy would undo that change (05 Q8)."""


class Draft:
    """An action pane's copy of an input's actions.

    item is the copy the pane edits (an InputItem that is not in the
    profile). Nothing reaches the real input until Library.commit;
    Library.discard throws it away. Every action the input had is copied;
    originals maps copy id -> the action it stands in for, so OK writes an
    edit back into a shared action instead of splitting it (decision A1).
    Drafts never count as users and never hold a live action.
    """

    def __init__(
        self,
        library: Library,
        item: InputItem,
        real: InputItem | None,
        index: int | None,
    ) -> None:
        self.library = library
        self.item = item
        self.real = real
        # None: every binding of the input; else that one binding (< 0: a
        # new binding).
        self.index = index
        # True when the draft holds every binding the input had.
        self.whole = False
        self.originals: dict[uuid.UUID, uuid.UUID] = {}
        # original id -> copy id (one copy per original in a draft).
        self._copies: dict[uuid.UUID, uuid.UUID] = {}
        # The input's bindings as they were when the draft began.
        self.base = ""

    def adopt(self, action: AbstractActionData) -> AbstractActionData:
        """The action to put into this draft for a picked one: a live action
        (one an input uses) comes in as a copy until OK (decision A4). A new
        action, or one already in this draft, comes back as it is."""
        return self.library._adopt(self, action)

    def original(self, action: AbstractActionData) -> AbstractActionData | None:
        """The action this copy stands in for, if it is one."""
        oid = self.originals.get(action.id)
        if oid is None:
            return None
        return self.library._actions.get(oid)


class Library:
    """The one owner of a profile's action objects (map 2, "Who owns an
    action object", in claude/system-maps.md).

    Each action is stored under its UUID; inputs reference them through
    their bindings. Only the library adds or removes actions (create,
    commit, restore, release); "in use" is always worked out from its own
    profile's inputs. Editors work on a Draft: drafts never count as users
    and never hold a live action.

    API:
        in_use() / users(action) / used_elsewhere / shared_with
        create(name, behavior, item=None)      the only way an action is added
        draft(real, index) -> Draft            pane copy; Draft.adopt(action)
        adopt(item, action)                    Draft.adopt by the pane's input
        commit(draft, real, index) -> int      OK; shared actions stay shared
        discard(draft)                         Cancel / close
        release(roots)                         the one removal rule
        snapshot(item) / restore(key, snap)    Undo and History
        with change():                         all-or-nothing change
        prune_for_save()                       a save's clean-up
    """

    def __init__(self, profile: Profile | None = None) -> None:
        """Creates a new library instance.

        Args:
            profile: the profile whose inputs use these actions (None for a
                scratch library: nothing is in use)
        """
        self._actions: dict[uuid.UUID, AbstractActionData] = {}
        self._profile = profile
        self._drafts: list[Draft] = []
        # TODO(batch1): legacy copy -> original marks from
        # clone_action(draft=True), until gremlin/validate.py and the panes
        # of other pages use draft(); held like a draft's actions.
        self._copied_from: dict[uuid.UUID, uuid.UUID] = {}
        # Action types in the last file read that this program doesn't have.
        self.unknown_types: list[str] = []

    @staticmethod
    def remap_ids(
        node: ElementTree.Element, id_map: dict[uuid.UUID, uuid.UUID]
    ) -> None:
        """Swaps the action ids in this XML (attributes and text) by id_map."""
        for entry in node.iter():
            if "id" in entry.attrib:
                try:
                    old = uuid.UUID(entry.attrib["id"])
                except ValueError:
                    old = None
                if old is not None and old in id_map:
                    entry.attrib["id"] = str(id_map[old])
            text = (entry.text or "").strip()
            if not text:
                continue
            try:
                old = uuid.UUID(text)
            except ValueError:
                continue
            if old in id_map:
                entry.text = str(id_map[old])

    # --- Who uses what ------------------------------------------------------

    def _inputs(self) -> list[InputItem]:
        if self._profile is None:
            return []
        return [item for items in self._profile.inputs.values() for item in items]

    def in_use(self) -> set[uuid.UUID]:
        """Ids of every action an input of this library's profile uses, with
        every action inside them. Drafts are not inputs."""
        return {action.id for action in reachable(Profile.roots_of(self._inputs()))}

    def users(self, action: AbstractActionData) -> list[InputItem]:
        """The inputs that use this action (directly or inside another)."""
        return self._users_of(action.id)

    def _users_of(self, aid: uuid.UUID) -> list[InputItem]:
        return [
            item
            for item in self._inputs()
            if any(a.id == aid for a in reachable(Profile.roots_of([item])))
        ]

    def used_elsewhere(
        self, action: AbstractActionData, item: InputItem | None
    ) -> bool:
        """True when an input other than item uses the action. In a pane
        (item is a draft's input) a copy counts as its original, and the
        pane's own input doesn't count."""
        return bool(self.shared_with(action, item))

    def shared_with(
        self, action: AbstractActionData, item: InputItem | None
    ) -> list[InputItem]:
        """The other inputs an edit to this action reaches: those using it,
        other than item. In a pane that is the inputs using the action the
        copy stands in for, other than the pane's own input (OK changes it
        for all of them, decision A1)."""
        draft = self.draft_of(item)
        if draft is None:
            return [user for user in self.users(action) if user is not item]
        oid = draft.originals.get(action.id)
        if oid is None:
            return []
        return [user for user in self._users_of(oid) if user is not draft.real]

    def draft_held(self) -> set[uuid.UUID]:
        """Actions an open draft holds: not users, but not removed under it."""
        roots = [d.item for d in self._drafts]
        held = {action.id for action in reachable(Profile.roots_of(roots))}
        legacy = [self._actions[a] for a in self._copied_from if a in self._actions]
        held |= {action.id for action in reachable(legacy)}
        return held

    def draft_of(self, item: InputItem | None) -> Draft | None:
        """The open draft whose copy this input is, if it is one."""
        if item is None:
            return None
        for draft in self._drafts:
            if draft.item is item:
                return draft
        return None

    def drafts(self) -> list[Draft]:
        """The open drafts (panes), oldest first."""
        return list(self._drafts)

    # --- Creating -------------------------------------------------------------

    def create(
        self,
        name: str,
        behavior: InputType | None,
        item: InputItem | None = None,
        reuse: bool = True,
    ) -> AbstractActionData | None:
        """A new action of that plugin name in this library: the only way
        one is added.

        An action that reuses by default (Merge Axis) hands back the first
        one an input of this profile uses; reuse=False always makes a new
        one. item: the input being edited; when it is a pane's draft input,
        a reused live action comes in as a copy until OK (decision A4).
        None when the action can't be created here (no vJoy for Map to
        vJoy).
        """
        note_edit()
        cls = plugin_manager.PluginManager().get_class(name)
        if not cls.can_create():
            return None
        if behavior is None:
            behavior = InputType.JoystickButton
        if reuse and ActionProperty.ReuseByDefault in cls.properties:
            used = self.in_use()
            for action in self._actions.values():
                if type(action) is cls and action.id in used:
                    draft = self.draft_of(item)
                    return draft.adopt(action) if draft is not None else action
        action = cls.create(DataCreationMode.Create, behavior)
        self.add_action(action)
        return action

    def duplicate(self, action: AbstractActionData) -> AbstractActionData | None:
        """An independent copy of the action and everything inside it, under
        new ids (Reference > Duplicate). None: it can't be copied."""
        return self.clone_action(action)

    def clone_action(
        self,
        action: AbstractActionData | None,
        id_map: dict[uuid.UUID, uuid.UUID] | None = None,
        draft: Draft | bool | None = None,
    ) -> AbstractActionData | None:
        """Copies an action, and every action inside it, into the library
        under new ids (id_map collects old -> new).

        Unfinished actions are copied too, so editing a copy never changes
        the original. None: the action can't be copied and is shared.
        draft: the copy stands in for the original in that draft (True:
        the legacy mark, TODO(batch1) until every pane uses draft()).
        """
        note_edit()
        if action is None:
            return None
        if id_map is None:
            id_map = {}
        if action.id in id_map:
            existing = self._actions.get(id_map[action.id])
            if existing is not None:
                return existing
            del id_map[action.id]
        for child in list(action.get_actions()[0] or []):
            self.clone_action(child, id_map, draft)
        node = action.to_xml(True)
        if node is not None:
            id_map[action.id] = uuid.uuid4()
            self.remap_ids(node, id_map)
            copy = type(action)(action.behavior_type)
            copy.from_xml(node, self)
        else:
            # Not writable yet (a Reference placeholder, a Merge Axis with no
            # axes): copied field by field, its children as copied above.
            copy = action.copy_unfinished()
            if copy is None:
                return None
            id_map[action.id] = copy.id
            for selector in action._valid_selectors():
                for child in action.get_actions(selector)[0]:
                    if child.id in id_map and id_map[child.id] in self._actions:
                        child = self._actions[id_map[child.id]]
                    copy.insert_action(child, selector)
        self.add_action(copy)
        if isinstance(draft, Draft):
            draft.originals[copy.id] = action.id
        elif draft:
            self._copied_from[copy.id] = action.id
        return copy

    # --- Drafts (the action pane) ------------------------------------------------

    def draft(
        self,
        real: InputItem | None,
        index: int | None = None,
        *,
        key: tuple | None = None,
        blank: bool = False,
    ) -> Draft:
        """A pane copy of an input: every binding (index None or < 0), the
        binding at index, or one new empty binding (blank, or an input with
        none). key (device id, input type, input id, mode) names the input
        when real doesn't exist yet. Draft.whole tells whether it holds
        every binding the input had."""
        shadow = InputItem(self)
        if key is not None:
            shadow.device_id, shadow.input_type, shadow.input_id, shadow.mode = key
        elif real is not None:
            shadow.device_id = real.device_id
            shadow.input_type = real.input_type
            shadow.input_id = real.input_id
            shadow.mode = real.mode
        if index is not None and index < 0:
            index = None
        draft = Draft(self, shadow, real, -1 if blank else index)
        self._drafts.append(draft)
        chosen = [] if blank else self._chosen(real, draft.index)
        if chosen is None:
            chosen = []
        draft.base = bindings_fingerprint(chosen)
        for binding in chosen:
            self._copy_binding(binding, draft)
        draft.whole = draft.index is None and bool(chosen)
        if not shadow.action_sequences:
            shadow.add_item_binding()
            if draft.index is not None:
                # A binding that went: OK adds the new one.
                draft.index = -1
        return draft

    @staticmethod
    def _chosen(
        real: InputItem | None, index: int | None
    ) -> list[InputItemBinding] | None:
        """The bindings a draft of real at index covers; None: no such one."""
        if real is None:
            return [] if index is None or index < 0 else None
        if index is None:
            return list(real.action_sequences)
        if index < 0:
            return []
        if index >= len(real.action_sequences):
            return None
        return [real.action_sequences[index]]

    def _copy_binding(self, binding: InputItemBinding, draft: Draft) -> None:
        self.clone_action(binding.root_action, draft._copies, draft)
        node = binding.to_xml()
        self.remap_ids(node, draft._copies)
        copy = InputItemBinding(draft.item)
        copy.from_xml(node)
        draft.item.action_sequences.append(copy)

    def adopt(
        self, item: InputItem | None, action: AbstractActionData
    ) -> AbstractActionData:
        """The action to put into the input being edited for a picked one:
        in a pane (item is a draft's input) a live action comes in as a copy
        until OK (decision A4); elsewhere it is the action itself."""
        draft = self.draft_of(item)
        return draft.adopt(action) if draft is not None else action

    def _adopt(self, draft: Draft, action: AbstractActionData) -> AbstractActionData:
        if action is None or action.id in draft.originals:
            return action
        if action.id in draft._copies:
            existing = self._actions.get(draft._copies[action.id])
            if existing is not None:
                return existing
        if action.id not in self.in_use():
            # New ("+"), or already this pane's own.
            return action
        copy = self.clone_action(action, draft._copies, draft)
        return copy if copy is not None else action

    def commit(
        self,
        draft: Draft,
        real: InputItem,
        index: int | None | EllipsisType = ...,
    ) -> int:
        """Writes the draft onto the input (OK): every binding (index None),
        the binding at index, or a new binding (index < 0); left out, the
        bindings the draft covers (draft.index). real is the input (made at
        OK when the draft began without one). Returns the binding's index
        (0 for every binding). The draft is closed; open a new one to keep
        editing.

        A copy takes its original's place: the original gets the copy's
        content and keeps its id and object, so every input using a shared
        action gets the edit (decision A1). What the old bindings held and
        nothing uses any more is released. DraftOutdated (nothing written)
        when the input changed since the draft began (05 Q8).
        """
        note_edit()
        if draft not in self._drafts:
            raise error.GremlinError("That action editor copy is closed.")
        if index is ...:
            index = draft.index
        assert not isinstance(index, EllipsisType)
        if index is None or index >= 0:
            now = self._chosen(real, index)
            if now is None or bindings_fingerprint(now) != draft.base:
                raise DraftOutdated(
                    "This input was changed while its action editor was open."
                )
        if index is None:
            old = list(real.action_sequences)
        elif index >= 0:
            old = [real.action_sequences[index]]
        else:
            old = []
        old_actions = reachable([b.root_action for b in old])

        tree = reachable(Profile.roots_of([draft.item]))
        target: dict[int, AbstractActionData] = {}
        for action in tree:
            oid = draft.originals.get(action.id)
            original = self._actions.get(oid) if oid is not None else None
            if (
                original is not None
                and original is not action
                and type(original) is type(action)
            ):
                target[id(action)] = original
        for action in tree:
            original = target.get(id(action))
            if original is not None:
                state = {k: v for k, v in vars(action).items() if k != "_id"}
                vars(original).update(state)
        final = [target.get(id(action), action) for action in tree]
        self._point_at(final, target)
        moved = list(draft.item.action_sequences)
        for binding in moved:
            if binding.root_action is not None:
                binding.root_action = target.get(
                    id(binding.root_action), binding.root_action
                )
            binding.input_item = real
        for action in tree:
            if id(action) in target and self._actions.get(action.id) is action:
                del self._actions[action.id]
        for action in final:
            if action.id not in self._actions:
                self._actions[action.id] = action

        if index is None:
            real.action_sequences = moved
            result = 0
        elif index >= 0:
            if moved:
                real.action_sequences[index] = moved[0]
            else:
                del real.action_sequences[index]
            result = index
        else:
            real.action_sequences.extend(moved[:1])
            result = len(real.action_sequences) - 1
        draft.item.action_sequences.clear()
        self._drafts.remove(draft)
        # Copies the pane made but no longer holds go too.
        self.release(old_actions + self._copies_of(draft))
        return result

    def _copies_of(self, draft: Draft) -> list[AbstractActionData]:
        return [self._actions[c] for c in draft.originals if c in self._actions]

    @staticmethod
    def _point_at(
        actions: Iterable[AbstractActionData],
        target: dict[int, AbstractActionData],
    ) -> None:
        """Makes these actions hold each target instead of what it replaces."""
        if not target:
            return
        for action in actions:
            for selector in action._valid_selectors():
                container = action.get_actions(selector)[0]
                for i, child in enumerate(container):
                    if id(child) in target:
                        container[i] = target[id(child)]

    def discard(self, draft: Draft | None) -> None:
        """Throws a draft away (Cancel, close); nothing it made stays."""
        note_edit()
        if draft is None:
            return
        if draft in self._drafts:
            self._drafts.remove(draft)
        roots = Profile.roots_of([draft.item]) + self._copies_of(draft)
        draft.item.action_sequences.clear()
        self.release(roots)

    @contextlib.contextmanager
    def keeping_drafts_current(self) -> Iterator[None]:
        """A change made to the inputs and drafts alike (a mode rename, a
        save's clean-up): a draft that matched its input before still
        matches after, so OK isn't refused for it."""
        current = [
            d for d in self._drafts
            if d.real is not None
            and (chosen := self._chosen(d.real, d.index)) is not None
            and bindings_fingerprint(chosen) == d.base
        ]
        yield
        for d in current:
            chosen = self._chosen(d.real, d.index)
            if chosen is not None:
                d.base = bindings_fingerprint(chosen)

    # --- Removing -----------------------------------------------------------------

    def release(
        self,
        roots: Iterable[AbstractActionData | None],
        recursive: bool = True,
    ) -> None:
        """The one removal rule: these actions (and, recursive, everything
        inside them) leave the library unless an input uses them or an open
        draft holds them. A kept action keeps what is inside it."""
        note_edit()
        keep = self.in_use() | self.draft_held()
        actions = (
            reachable(roots)
            if recursive
            else [root for root in roots if root is not None]
        )
        for action in actions:
            if action.id in keep:
                continue
            if self._actions.get(action.id) is action:
                del self._actions[action.id]
                self._copied_from.pop(action.id, None)

    def remove_unused(self, action: AbstractActionData, recursive: bool = True) -> None:
        """release([action], recursive): kept for callers not moved yet."""
        self.release([action], recursive)

    def pick_list(
        self,
        predicate: Callable[[AbstractActionData], bool],
        current: AbstractActionData | None,
        item: InputItem | None,
    ) -> list[AbstractActionData]:
        """The actions an action's pick list offers: the current one, those in
        the input being edited (item, the pane's draft), and those an input
        uses. A draft copy hides the action it stands in for, so it isn't
        listed twice."""
        mine = ([current] if current is not None else []) + reachable(
            Profile.roots_of([item] if item is not None else [])
        )
        draft = self.draft_of(item)
        originals = dict(self._copied_from)
        if draft is not None:
            originals.update(draft.originals)
        hidden = {originals[a.id] for a in mine if a.id in originals}
        used = self.in_use()
        in_use = [a for a in self._actions.values() if a.id in used]
        found: list[AbstractActionData] = []
        ids: set[uuid.UUID] = set()
        for action in mine + in_use:
            if action.id in ids or action.id in hidden or not predicate(action):
                continue
            ids.add(action.id)
            found.append(action)
        return found

    # --- Undo and History ---------------------------------------------------------

    def snapshot(self, item: InputItem | None) -> dict | None:
        """An input and its actions as XML ({"input", "actions"}); None
        when it has no actions. restore() puts it back."""
        if item is None or not item.action_sequences:
            return None
        tree = reachable(Profile.roots_of([item]))
        written = {}
        for action in tree:
            node = action.to_xml(True)
            if node is not None:
                written[action.id] = node
        # An action that couldn't be written is left out of the actions that
        # hold it too, or the snapshot couldn't be read back.
        left_out = {str(a.id) for a in tree if a.id not in written}
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

    def restore(
        self, key: tuple, snapshot: dict | None, check_only: bool = False
    ) -> None:
        """Replaces an input's actions with a snapshot (None: no actions).

        key is (device id, input type, input id, mode). The snapshot is read
        first: one that can't be read changes nothing (ProfileError);
        check_only stops after that check. An action in the snapshot that
        is still in the library keeps its id and object and gets the kept
        settings back, so a shared action is restored for every input using
        it (decision A2).
        """
        note_edit()
        device_id, input_type, input_id, mode = key
        profile = self._profile
        if profile is None:
            raise error.ProfileError("This library has no profile.")
        if snapshot:
            if not profile.modes.mode_exists(mode):
                # An Undo or History entry from a mode deleted since.
                raise error.ProfileError(f"The mode '{mode}' isn't in the profile.")
            _check_snapshot(snapshot)
        if check_only:
            return
        items = profile.inputs.get(device_id, [])
        current = [
            item
            for item in items
            if item.input_type == input_type
            and item.input_id == input_id
            and item.mode == mode
        ]
        old_actions = reachable(Profile.roots_of(current))
        if device_id in profile.inputs:
            profile.inputs[device_id] = [i for i in items if i not in current]
        if snapshot:
            scratch = Library()
            root = ElementTree.Element("profile")
            library = ElementTree.SubElement(root, "library")
            for block in snapshot["actions"]:
                library.append(ElementTree.fromstring(block))
            scratch.from_xml(root)
            target: dict[int, AbstractActionData] = {}
            for aid, fresh in scratch._actions.items():
                existing = self._actions.get(aid)
                if existing is not None and type(existing) is type(fresh):
                    state = {k: v for k, v in vars(fresh).items() if k != "_id"}
                    vars(existing).update(state)
                    target[id(fresh)] = existing
                else:
                    self._actions[aid] = fresh
            self._point_at(
                [target.get(id(a), a) for a in scratch._actions.values()], target
            )
            item = InputItem(self)
            item.from_xml(ElementTree.fromstring(snapshot["input"]))
            item.device_id = device_id
            item.mode = str(item.mode or "Default")
            for binding in item.action_sequences:
                binding.input_item = item
            profile.inputs.setdefault(device_id, []).append(item)
        self.release(old_actions)

    @contextlib.contextmanager
    def change(self) -> Iterator[Library]:
        """An all-or-nothing change: if the block raises, the library, the
        profile's inputs and their bindings, the modes, the Logical Device
        inputs and the device list are put back as they were, then the
        error goes on. Actions changed in place (not added) are not put
        back: a change does its in-place edits last."""
        note_edit()
        profile = self._profile
        actions = dict(self._actions)
        drafts = list(self._drafts)
        if profile is None:
            try:
                yield self
            except BaseException:
                self._actions = actions
                self._drafts = drafts
                note_edit()
                raise
            return
        inputs = {guid: list(items) for guid, items in profile.inputs.items()}
        bindings = [
            (item, list(item.action_sequences))
            for items in profile.inputs.values()
            for item in items
        ]
        modes = ElementTree.Element("profile")
        modes.append(profile.modes.to_xml())
        logical = ElementTree.Element("profile")
        logical.append(profile._logical_devices_to_xml())
        devices = dict(profile.device_database.devices)
        try:
            yield self
        except BaseException:
            self._actions = actions
            self._drafts = drafts
            profile.inputs.clear()
            profile.inputs.update(inputs)
            for item, sequences in bindings:
                item.action_sequences = sequences
                for binding in sequences:
                    binding.input_item = item
            profile.modes.from_xml(modes)
            profile._logical_devices_from_xml(logical)
            profile.device_database.devices = devices
            note_edit()
            raise

    # --- Lookup ---------------------------------------------------------------------

    def add_action(self, action: AbstractActionData) -> None:
        """Stores an action made outside create() (a copy, a loaded one).
        TODO(batch1): editors still call this; they move to create()."""
        note_edit()
        if action.id in self._actions:
            logging.getLogger("system").warning(
                f"Action with id {action.id} already exists, skipping."
            )
        self._actions[action.id] = action

    def delete_action(self, key: uuid.UUID) -> None:
        """Deletes the action with the given key from the library, used or
        not (release() is the removal rule; this is for the library's own
        bookkeeping and tests).

        Args:
            key: the key of the action to delete
        """
        note_edit()
        if key not in self._actions:
            logging.getLogger("system").warning(
                f"Attempting to remove non-existant action with id {key}."
            )
        if key in self._actions:
            del self._actions[key]
        self._copied_from.pop(key, None)

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

        An action of a type this program doesn't have is kept as it is
        (unknown_types names the types, for a warning) instead of refusing
        the profile (04 Q7).

        Args:
            node: XML node containing the library information
        """
        note_edit()
        parse_later = []
        self.unknown_types = []

        def can_parse(entry: ElementTree.Element) -> bool:
            return all([aid in self._actions for aid in read_action_ids(entry)])

        # Parse all actions
        for entry in node.findall("./library/action"):
            # Ensure all required attributes are present
            if not set(["id", "type"]).issubset(entry.keys()):
                raise error.ProfileError("Incomplete library action specification")

            type_key = str(entry.get("type"))
            if (
                type_key not in plugin_manager.PluginManager().tag_map
                and type_key not in self.unknown_types
            ):
                self.unknown_types.append(type_key)

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

        if self.unknown_types:
            logging.getLogger("system").warning(
                "The profile has actions of a type this program doesn't have "
                f"({', '.join(self.unknown_types)}); they are kept as they are."
            )

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

    def _save_scope(self) -> set[uuid.UUID]:
        """What a save looks at: the actions inputs use (every action for a
        library without a profile)."""
        if self._profile is None:
            return set(self._actions)
        return self.in_use()

    def unfinished_actions(self) -> list[str]:
        """What a save would leave out: "<action>: <first error>" for each
        unfinished action an input uses, so the user can be asked first."""
        scope = self._save_scope()
        out = []
        for aid, action in self._actions.items():
            if aid not in scope:
                continue
            errors = [
                uf.message
                for uf in action.user_feedback()
                # By name: base_classes imports this module.
                if uf.feedback_type.name == "Error"
            ]
            if errors:
                out.append(f"{action.name}: {errors[0]}")
        return out

    def prune_for_save(self) -> None:
        """An explicit save: unfinished actions leave the actions inputs use.
        Drafts (an open pane) and actions kept for Undo are not touched
        (05 S34). Checking for unsaved work must not call this."""
        note_edit()
        with self.keeping_drafts_current():
            self._drop_invalid(self._save_scope)

    def drop_invalid_actions(self) -> None:
        """Removes unfinished children from every library action, drafts and
        unused ones included. A save uses prune_for_save instead."""
        note_edit()
        self._drop_invalid(lambda: set(self._actions))

    def _drop_invalid(self, scope: Callable[[], set[uuid.UUID]]) -> None:
        # A child that is unfinished, or not in the library (a file listing
        # it couldn't be loaded), goes. Again until nothing changes: a
        # container a removal left unfinished goes from its parent too.
        changed = True
        while changed:
            changed = False
            parents = scope()
            for action in list(self._actions.values()):
                if action.id not in parents:
                    continue
                for selector in action._valid_selectors():
                    to_remove = []
                    for i, child in enumerate(action.get_actions(selector)[0]):
                        if child.id not in self._actions or not child.is_valid():
                            to_remove.append(i)
                    # Delete from the end so earlier removals do not shift the
                    # positions still waiting to be removed.
                    for i in reversed(to_remove):
                        action.remove_action(i, selector)
                        changed = True

    def actions_in_use_by_type(self, action_type: type) -> list[AbstractActionData]:
        """Actions of that type that an input of this profile uses (the
        library also holds deleted and replaced ones until the next save,
        which Reuse and the pick lists must not hand back)."""
        used = self.in_use()
        return [a for a in self.actions_by_type(action_type) if a.id in used]

    def to_xml(self, used: set[uuid.UUID] | None = None) -> ElementTree.Element:
        """Returns an XML node encoding the content of this library.

        Invalid actions are left out of the node. They stay in the open
        profile until prune_for_save is called. used: when given, only
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
        tag_map = plugin_manager.PluginManager().tag_map
        if type_key in tag_map:
            action_obj = tag_map[type_key]()
        else:
            from gremlin.unknown_action import UnknownActionData

            action_obj = UnknownActionData()
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

    def __init__(self, bind: bool = True) -> None:
        self.inputs: dict[uuid.UUID, list[InputItem]] = {}
        self.library = Library(self)
        # Said after a load (an action type this program doesn't have).
        self.load_warnings: list[str] = []
        self.device_database = DeviceDatabase()
        self.settings = Settings(self)
        self.modes = ModeHierarchy(self)
        self.scripts = ScriptManager(self)
        self.fpath: Path | None = None
        # The profile as it would be written right after the last load or save.
        self._saved_snapshot: str | None = None
        # The last unsaved answer and the edit count it was worked out at.
        self._unsaved_seen: tuple[int, bool] | None = None
        # The Logical Device and OSC rows saved with this profile (04 S2).
        # Owned here, so another Profile object no longer wipes them (GL-074).
        self.logical_device = LogicalRows()
        self._osc_inputs: dict[str, OscDevice.Input] = {}
        self._osc_by_id: dict[tuple[InputType, int], str] = {}
        # A new profile is the one shown until another is bound; one read
        # without opening it (bind=False, the Device Library, 10 S33) never is.
        if bind:
            self.bind_devices()

    def bind_devices(self) -> None:
        """LogicalDevice() and OscDevice() show this profile's rows (the open
        profile; the Backend binds it whenever the open profile changes)."""
        LogicalDevice().bind(self.logical_device)
        osc = OscDevice()
        # Shared, not copied: edits through OscDevice() land in this profile.
        osc._inputs = self._osc_inputs
        osc._by_id = self._osc_by_id

    def from_xml(self, fpath: Path) -> None:
        """Reads the content of an XML file and initializes the profile.

        Args:
            fpath: path to the XML file to parse
        """
        note_edit()
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
        self.load_warnings = []
        if self.library.unknown_types:
            self.load_warnings.append(
                "This profile has actions of a type this program doesn't have: "
                + ", ".join(self.library.unknown_types)
                + ". They are kept as they are and saved with the profile, "
                "but do nothing."
            )
        self.device_database.from_xml(root)
        self.load_warnings.extend(self.modes.from_xml(root))
        self._check_startup_mode()
        self.scripts.from_xml(root)

        # Parse individual inputs.
        for node in root.findall("./inputs/input"):
            self._process_input(node)
        self._warn_unlisted_modes()

        self._set_saved(self._xml_text())

    def _check_startup_mode(self) -> None:
        """A Startup Mode that is neither a mode nor Last Active (a damaged
        or hand-edited file) is Last Active (GL-039, 04 S52,
        D-04-LAST-ACTIVE)."""
        name = self.settings.startup_mode
        if name == "Last Active" or self.modes.mode_exists(name):
            return
        logging.getLogger("system").warning(
            f"Startup Mode '{name}' isn't a mode of this profile; "
            "Last Active is used instead."
        )
        self.settings.startup_mode = "Last Active"

    def _warn_unlisted_modes(self) -> None:
        """Inputs saved in a mode the mode list doesn't have never show and
        never run: they are listed in a load warning (GL-028, 04 Q8)."""
        counts: dict[str, int] = {}
        for items in self.inputs.values():
            for item in items:
                mode = str(item.mode or "")
                if item.action_sequences and not self.modes.mode_exists(mode):
                    counts[mode] = counts.get(mode, 0) + 1
        if not counts:
            return
        listed = ", ".join(
            f"{mode} ({count} input{'' if count == 1 else 's'})"
            for mode, count in sorted(counts.items())
        )
        self.load_warnings.append(
            "Some bindings are in modes this profile doesn't list, so they "
            f"don't show or run: {listed}."
        )

    def to_xml(self, fpath: Path, *, prune: bool = True) -> None:
        """Writes the profile's content to an XML file.

        Args:
            fpath: path to the XML file in which to write the content
            prune: when True, unfinished actions are removed from the open
                profile before the file is written. The unsaved check passes
                False so looking does not delete anything.
        """
        if prune:
            self.library.prune_for_save()
        # Device names are filled only here, at a save: the unsaved check
        # (every 1.5 s) changed the profile when a stick was plugged in
        # (GL-153, 04 Q18, R14).
        self.device_database.update_for_uuids(self.inputs)
        text = self._xml_text()
        # Safely (a temporary file, then a swap), as module files are: a
        # crash mid-save leaves the old profile whole.
        from gremlin.modules import module_file

        module_file.write_text(Path(fpath), text, encoding="utf-8-sig", newline="")
        before = self._saved_snapshot
        self._set_saved(text)
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
        Pack, a History entry). All or nothing: on an error the profile is
        as before (Library.change). remap=False: the caller made sure no id
        clashes, so ids, and references to actions already in the library,
        are kept."""
        note_edit()
        if remap:
            action_xml, input_xml = remap_action_ids(
                action_xml, input_xml, self.library
            )
        added = []
        with self.library.change():
            if action_xml:
                root = ElementTree.Element("profile")
                library = ElementTree.SubElement(root, "library")
                for block in action_xml:
                    library.append(ElementTree.fromstring(block))
                self.library.from_xml(root)
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
        """An input and its actions as XML (Library.snapshot)."""
        return self.library.snapshot(item)

    def put_input(
        self,
        device_id: uuid.UUID,
        input_type: InputType,
        input_id: int | tuple,
        mode: str,
        snapshot: dict | None,
        check_only: bool = False,
    ) -> None:
        """Replaces an input's actions with a snapshot (Library.restore)."""
        self.library.restore(
            (device_id, input_type, input_id, mode), snapshot, check_only
        )

    def drop_inputs(self, device_id: uuid.UUID, doomed: Iterable[InputItem]) -> None:
        """Removes these inputs of a device and the actions only they used."""
        note_edit()
        gone = {id(item) for item in doomed}
        items = self.inputs.get(device_id, [])
        removed = [item for item in items if id(item) in gone]
        if device_id in self.inputs:
            self.inputs[device_id] = [item for item in items if id(item) not in gone]
        self.library.release(self.roots_of(removed))

    def remember_device(self, device_id: uuid.UUID, name: str) -> None:
        """Records a device's name in the profile's device list (saved with
        it). Library.change puts the list back if the change fails."""
        note_edit()
        self.device_database.devices[device_id] = DeviceInfo(device_id, name)

    def move_inputs(
        self, items: list[InputItem], source: uuid.UUID, target: uuid.UUID
    ) -> int:
        """Moves these inputs of source to target (Swap leaves controls the
        other stick lacks where they were, 10 S27). Returns how many of them
        have actions."""
        note_edit()
        moving = {id(item) for item in items}
        self.inputs[source] = [
            i for i in self.inputs.get(source, []) if id(i) not in moving
        ]
        for item in items:
            item.device_id = target
        self.inputs.setdefault(target, []).extend(items)
        return sum(1 for item in items if item.action_sequences)

    def swap_device_inputs(self, first: uuid.UUID, second: uuid.UUID) -> int:
        """Every input of one device moves to the other and back (Swap
        Devices, 04 S77, S78), inputs with no actions too. Returns how many
        moved inputs have actions."""
        note_edit()
        if first == second:
            raise error.GremlinError("A device can't be swapped with itself.")
        moved = 0
        first_items = self.inputs.get(first, [])
        second_items = self.inputs.get(second, [])
        for item in first_items:
            item.device_id = second
            moved += 1 if item.action_sequences else 0
        for item in second_items:
            item.device_id = first
            moved += 1 if item.action_sequences else 0
        self.inputs[second] = first_items
        self.inputs[first] = second_items
        return moved

    def actions_in_use(self) -> set[uuid.UUID]:
        """Ids of every action an input uses (Library.in_use)."""
        return self.library.in_use()

    def drop_unused_actions(self, roots: list[AbstractActionData]) -> None:
        """Removes these actions, and every action inside them, unless an
        input still uses them (Library.release)."""
        self.library.release(roots)

    def has_unsaved_changes(self) -> bool:
        """Checks if the profile has unsaved changes.

        Compares against the profile as it was right after the last load or
        save, not the file on disk: a file saved by an older version (for
        example without a newer default property) is not an edit. Always
        compares: the questions (Save, Discard, quit) use this.

        Returns:
            True if there are unsaved changes, False otherwise
        """
        if self._saved_snapshot is None:
            result = True
        else:
            result = self._xml_text() != self._saved_snapshot
        self._unsaved_seen = (edit_count(), result)
        return result

    def looks_unsaved(self) -> bool:
        """has_unsaved_changes for the title's "*" (every 1.5 s): its last
        answer again while no edit was noted since (04 Q19), so a large
        profile isn't rebuilt each time."""
        seen = self._unsaved_seen
        if seen is not None and seen[0] == edit_count():
            return seen[1]
        return self.has_unsaved_changes()

    def note_edit(self) -> None:
        """Something this profile saves changed where no hook sees it."""
        note_edit()

    def mark_clean(self) -> None:
        """A new, untouched profile has nothing to lose: only edits after
        this count as unsaved changes."""
        self._set_saved(self._xml_text())

    def _set_saved(self, text: str) -> None:
        """text is the profile as saved now: nothing unsaved."""
        self._saved_snapshot = text
        self._unsaved_seen = (edit_count(), False)

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
        note_edit()
        logical = self.logical_device
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
        logical = self.logical_device
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
        # Into this profile's own rows (cleared in place: OscDevice() may be
        # showing them), with the checks OscDevice.create makes.
        note_edit()
        self._osc_inputs.clear()
        self._osc_by_id.clear()
        for node in root_node.findall("./osc-device/input"):
            kind = read_subelement(node, "input-type")
            if kind not in (InputType.JoystickAxis, InputType.JoystickButton):
                raise error.GremlinError(
                    f"OSC inputs must be axis or button, got {kind}"
                )
            input_id = int(read_subelement(node, "input-id"))
            label = str(read_subelement(node, "label")).casefold()
            if label in self._osc_inputs:
                raise error.GremlinError(f"OSC address '{label}' already exists")
            self._osc_inputs[label] = OscDevice.Input(label, input_id, kind)
            self._osc_by_id[(kind, input_id)] = label

    def _osc_devices_to_xml(self) -> ElementTree.Element:
        node = ElementTree.Element("osc-device")
        for item in sorted(
            self._osc_inputs.values(), key=lambda x: (x.type.name, x.id)
        ):
            input_node = ElementTree.Element("input")
            input_node.append(create_subelement_node("input-type", item.type))
            input_node.append(create_subelement_node("input-id", item.id))
            input_node.append(create_subelement_node("label", item.label))
            node.append(input_node)
        return node


class InputItem(EditNoted):
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
        # The user's name for this input (05 Q15), saved as <action-name>.
        self.action_name: str = ""

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

        child = node.find("action-name")
        self.action_name = "" if child is None or child.text is None else child.text

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

        if self.action_name:
            ElementTree.SubElement(node, "action-name").text = self.action_name

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
        root_action = self.library.create("Root", self.input_type)
        binding = InputItemBinding(self)
        binding.root_action = root_action
        binding.behavior = self.input_type
        self.action_sequences.append(binding)
        note_edit()
        return binding

    def remove_item_binding(self, binding: InputItemBinding) -> None:
        """Removes the given binding instance if present.

        Args:
            binding: InputItemBinding instance to remove from the item
        """
        if binding in self.action_sequences:
            del self.action_sequences[self.action_sequences.index(binding)]
            note_edit()


class InputItemBinding(EditNoted):
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


def clean_mode_name(name: str | None) -> str:
    """A mode name as it is compared: spacing collapsed, ends trimmed."""
    return " ".join(str(name or "").split())


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
    except error.ProfileError:
        raise
    except Exception as e:
        # A damaged copy fails in many ways (bad XML, a missing property, a
        # missing action): all of them mean it can't be put back.
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
        return min(roots, key=str.casefold)

    def top_listed_mode(self) -> str:
        """The top row of the mode list (Manage Modes): alphabetical,
        capitals not first, child modes included (04 S52)."""
        names = [str(node.value) for node in self.mode_list()]
        if not names:
            return "Default"
        return min(names, key=lambda n: (n.casefold(), n))

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
        # The hidden root (named "") is not a mode.
        nodes = self._hierarchy.nodes_matching(
            lambda x: x is not self._hierarchy and mode_name == x.value
        )
        if len(nodes) > 1:
            raise error.GremlinError(f"More than one mode named '{mode_name}' exists")
        elif len(nodes) == 0:
            raise error.GremlinError(f"No node with the name '{mode_name}' exists")
        return nodes[0]

    def name_taken(self, name: str, ignore: str = "") -> bool:
        """True when name is blank or matches a mode other than ignore,
        ignoring capitals and spacing: the one mode name rule (04 S40, Q21),
        for Manage Modes, Device Pack and scripts alike."""
        text = clean_mode_name(name)
        if not text:
            return True
        return any(
            existing != ignore
            and clean_mode_name(existing).casefold() == text.casefold()
            for existing in self.mode_names()
        )

    def add_mode(self, mode_name: str) -> None:
        """Adds a new mode to the hierarchy.

        Args:
            mode_name: name of the new mode to add

        Raises:
            GremlinError: the name is blank or looks like another mode's
        """
        note_edit()
        if not clean_mode_name(mode_name):
            raise error.GremlinError("A mode needs a name.")
        if self.name_taken(mode_name):
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

    def delete_mode(self, mode_name: str) -> dict:
        """Deletes the mode with the given name from the hierarchy.

        Args:
            mode_name: name of the mode to delete

        Returns:
            What restore_mode needs to put it back (GL-027, 04 Q6)
        """
        note_edit()
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
        profile = self._profile
        memo = {
            "name": mode_name,
            "parent": self._parent_name(node),
            "children": [child.value for child in node.children],
            "startup": profile.settings.startup_mode == mode_name,
            "inputs": [
                (device_id, item.input_type, item.input_id, snapshot)
                for device_id, items in profile.inputs.items()
                for item in items
                if item.mode == mode_name
                and (snapshot := profile.library.snapshot(item)) is not None
            ],
        }
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
            self._profile.settings.startup_mode = "Last Active"
        return memo

    def _parent_name(self, node: TreeNode) -> str:
        """The name of a mode's parent mode, "" at the top."""
        parent = node.parent
        if parent is None or parent is self._hierarchy:
            return ""
        return str(parent.value)

    def restore_mode(self, memo: dict) -> None:
        """Puts back a mode delete_mode removed: the mode under its parent,
        its child modes that are still where the delete moved them, its
        bindings and the Startup Mode. All or nothing (Library.change)."""
        note_edit()
        name = memo["name"]
        if self.name_taken(name):
            raise error.GremlinError(
                f"The mode '{name}' can't be put back: a mode with that name "
                "is in the profile now."
            )
        profile = self._profile
        parent = memo["parent"]
        with profile.library.change():
            self.add_mode(name)
            if parent and self.mode_exists(parent):
                self.set_parent(name, parent)
            for child in memo["children"]:
                if not self.mode_exists(child):
                    continue
                if self._parent_name(self.find_mode(child)) == parent:
                    self.set_parent(child, name)
            for device_id, input_type, input_id, snapshot in memo["inputs"]:
                profile.put_input(device_id, input_type, input_id, name, snapshot)
            if memo["startup"] and profile.settings.startup_mode == "Last Active":
                profile.settings.startup_mode = name

    def rename_mode(self, old_name: str, new_name: str) -> None:
        """Changes the name of an existing mode.

        Args:
            old_name: name of the mode to rename
            new_name: new name for the mode
        """
        note_edit()
        # Don't do anything if the names are the same
        if old_name == new_name:
            return

        # Handle missing mode to rename
        if not self.mode_exists(old_name):
            raise error.GremlinError(
                f"Attempting to rename non-existant mode '{old_name}'"
            )
        elif not clean_mode_name(new_name):
            raise error.GremlinError("A mode needs a name.")
        # Raise an error if renaming to an existing name, or one that only
        # differs in capitals or spacing (the mode's own capitals may change).
        elif self.name_taken(new_name, old_name):
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
        # Actions that switch to the mode (Change Mode) follow the new name,
        # in an open pane's copy too (its OK still goes through).
        library = self._profile.library
        with library.keeping_drafts_current():
            for action in library.actions_by_predicate(
                lambda a: old_name in (getattr(a, "_target_modes", None) or [])
            ):
                change: Any = action
                # In place: a running Cycle holds this list.
                change._target_modes[:] = [
                    new_name if mode == old_name else mode
                    for mode in change._target_modes
                ]
        # Script settings that name the mode (it was left on the old name,
        # the script stopped running and the setting was dropped on save),
        # also in a script that could not be loaded.
        for script in self._profile.scripts.scripts:
            rename_mode_settings(script, old_name, new_name)

        if self._profile.settings.startup_mode == old_name:
            self._profile.settings.startup_mode = new_name

    def set_parent(self, mode_name: str, parent_name: str | None) -> None:
        """Sets the parent of the specified mode.

        Args:
            mode_name: name of the mode to set the parent of
            parent_name: name of the new parent mode
        """
        note_edit()
        mode_node = self.find_mode(mode_name)
        # None or "": no parent (top level).
        parent_node = (
            self._hierarchy if not parent_name else self.find_mode(parent_name)
        )
        # Checked before detaching: the mode itself or one under it as the
        # parent is refused, and a refusal after detaching lost the mode.
        if parent_node is mode_node or mode_node.is_descendant(parent_node):
            raise error.GremlinError(
                f"Mode '{parent_name}' can't be the parent of '{mode_name}': "
                "it would cause a cycle"
            )
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
        # The hidden root (named "") is not a mode (GL-154).
        found = self._hierarchy.nodes_matching(
            lambda x: x is not self._hierarchy and name == x.value
        )
        return len(found) > 0

    def from_xml(self, root: ElementTree.Element) -> list[str]:
        """Reads the modes; returns what to warn about (04 Q9): a mode list
        with no modes gets "Default", a name listed twice is kept once."""
        note_edit()
        warnings: list[str] = []
        # Parse individual nodes
        nodes = {}
        node_parents = {}
        for node in root.findall("./modes/mode"):
            name = node.text or ""
            if not clean_mode_name(name):
                warnings.append("A mode with no name was left out.")
                continue
            if name in nodes:
                warnings.append(
                    f"The mode '{name}' is listed more than once; it is kept once."
                )
                continue
            if "parent" in node.attrib:
                node_parents[name] = node.get("parent")
            nodes[name] = TreeNode(name)
        if not nodes:
            warnings.append("This profile has no modes; the mode Default was added.")
            nodes["Default"] = TreeNode("Default")

        # Reconstruct tree structure
        for child, parent in node_parents.items():
            if parent not in nodes:
                logging.getLogger("system").warning(
                    f"Mode '{child}' names a parent mode '{parent}' that isn't "
                    "in the profile; it is kept as a top-level mode."
                )
                continue
            # A mode that is its own parent, or a loop of parents, stopped
            # the profile loading (or lost the mode).
            try:
                nodes[child].set_parent(nodes[parent])
            except error.GremlinError:
                logging.getLogger("system").warning(
                    f"Mode '{child}' names a parent mode '{parent}' that "
                    "makes a loop of parents; it is kept as a top-level mode."
                )

        self._hierarchy = TreeNode("")
        for node in nodes.values():
            if node.parent is None:
                node.set_parent(self._hierarchy)
        return warnings

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
        note_edit()
        self._scripts.append(Script(path, self._default_name(path)))
        self._scripts.sort(key=lambda s: (s.path, s.name))

    def remove_script(self, path: Path, name: str) -> None:
        """Removes the specified script.

        Args:
            path: path to the script
            name: name of the script
        """
        note_edit()
        script = self._find_instance(path, name)
        if script:
            self._scripts.remove(script)
            # Its settings go with it (GL-155, 04 S85).
            Script.variable_registry.remove_script(script)

    def rename_script(self, path: Path, old_name: str, new_name: str) -> None:
        """Renames the specified script.

        Args:
            path: path to the script
            old_name: current name of the script
            new_name: new name to use for the script
        """
        note_edit()
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
        note_edit()
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
