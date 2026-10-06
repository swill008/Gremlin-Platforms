# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""An action of a type this program doesn't have (a user plugin removed or
failed to load). The profile still opens: the action is kept exactly as the
file had it, saved back with the profile, and does nothing at Run (04 Q7)."""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, override
from xml.etree import ElementTree

from PySide6 import QtCore

from gremlin import util
from gremlin.base_classes import AbstractActionData, AbstractFunctor, UserFeedback
from gremlin.types import ActionProperty, InputType
from gremlin.ui.action_model import ActionModel

if TYPE_CHECKING:
    from gremlin.base_classes import Value
    from gremlin.event_handler import Event
    from gremlin.profile import Library


def unknown_note(type_name: str) -> str:
    """What the editor and the action's warning say."""
    return (
        f"This program has no '{type_name}' action. It is kept as it is and "
        "saved with the profile, but does nothing."
    )


class UnknownFunctor(AbstractFunctor):
    """Does nothing: the program doesn't know what the action does."""

    @override
    def __call__(
        self, event: Event, value: Value, properties: list[ActionProperty] = []
    ) -> None:
        pass


class UnknownActionModel(ActionModel):
    """Editor of an unknown action: a note, nothing to edit."""

    def _qml_path_impl(self) -> str:
        return "file:///" + QtCore.QFile("qml:UnknownAction.qml").fileName()

    def _action_behavior(self) -> str:
        parent = self._binding_model.get_action_model_by_sidx(
            self._parent_sequence_index.index
        )
        return str(getattr(parent, "actionBehavior"))

    def _get_note(self) -> str:
        return unknown_note(str(getattr(self._data, "tag", "")))

    note = QtCore.Property(str, fget=_get_note, constant=True)


class UnknownActionData(AbstractActionData):
    """Keeps an action of an unknown type as its XML, with its children."""

    version = 1
    name = "Unknown Action"
    tag = "unknown"
    icon = ""

    functor = UnknownFunctor
    model = UnknownActionModel

    properties = (ActionProperty.ActivateDisabled,)
    input_types = (
        InputType.JoystickAxis,
        InputType.JoystickButton,
        InputType.JoystickHat,
        InputType.Keyboard,
    )

    def __init__(self, behavior_type: InputType = InputType.JoystickButton) -> None:
        super().__init__(behavior_type)
        self.tag = "unknown"
        self._raw = ElementTree.Element("action")
        # The actions the file listed inside it, in file order (None: not
        # in the library); children is what is still there, so Undo, Save
        # and "in use" see them.
        self._slots: list[AbstractActionData | None] = []
        self.children: list[AbstractActionData] = []

    @override
    def _from_xml(self, node: ElementTree.Element, library: Library) -> None:
        self._id = util.read_action_id(node)
        self.tag = str(node.get("type") or "unknown")
        raw = copy.deepcopy(node)
        # Written again by to_xml.
        for prop in list(raw.findall("property")):
            name = (prop.findtext("name") or "").strip()
            if name in ("action-label", "activation-mode"):
                raw.remove(prop)
        self._raw = raw
        self._slots = [
            library.get_action(aid) if library.has_action(aid) else None
            for aid in util.read_action_ids(node)
        ]
        self.children = [slot for slot in self._slots if slot is not None]

    @override
    def _to_xml(self) -> ElementTree.Element:
        node = copy.deepcopy(self._raw)
        node.set("id", str(self._id))
        node.set("type", self.tag)
        parents = {child: parent for parent in node.iter() for child in parent}
        # A child id follows its action (a copy has new ids; OK puts the
        # originals back in their places); one that is gone is left out.
        live = [slot for slot in self._slots if slot is not None]
        positional = len(live) == len(self.children)
        in_order = iter(self.children)
        for index, entry in enumerate(list(node.iter("action-id"))):
            slot = self._slots[index] if index < len(self._slots) else None
            child = None
            if slot is not None:
                if positional:
                    child = next(in_order, None)
                else:
                    child = next((c for c in self.children if c is slot), None)
            if child is not None:
                entry.text = str(child.id)
            elif entry in parents:
                parents[entry].remove(entry)
        return node

    @override
    def user_feedback(self) -> list[UserFeedback]:
        return [UserFeedback(UserFeedback.FeedbackType.Warning, unknown_note(self.tag))]

    @override
    def _valid_selectors(self) -> list[str]:
        return ["children"]

    @override
    def _get_container(self, selector: str) -> list[AbstractActionData]:
        return self.children

    @override
    def _handle_behavior_change(
        self, old_behavior: InputType, new_behavior: InputType
    ) -> None:
        pass
