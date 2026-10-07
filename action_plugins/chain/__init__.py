# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    override,
)
from xml.etree import ElementTree

from PySide6 import QtCore

from gremlin import (
    clock,
    event_handler,
    util,
)
from gremlin.base_classes import (
    AbstractActionData,
    AbstractFunctor,
    UserFeedback,
    Value,
)
from gremlin.edits import note_edit
from gremlin.error import GremlinError
from gremlin.profile import Library
from gremlin.types import (
    ActionProperty,
    InputType,
    PropertyType,
)
from gremlin.ui.action_model import (
    ActionModel,
    SequenceIndex,
)

if TYPE_CHECKING:
    from gremlin.ui.profile import InputItemBindingModel


class ChainFunctor(AbstractFunctor["ChainData"]):
    """Implements the function executed of the Description action at runtime."""

    def __init__(self, action: ChainData) -> None:
        super().__init__(action)

        self.current_index = 0
        self.last_execution = 0.0
        # The step the current press went to: its release goes there too.
        self._pressed_index: int | None = None

    @override
    def __call__(
        self,
        event: event_handler.Event,
        value: Value,
        properties: list[ActionProperty] = [],
    ) -> None:
        # Every sequence removed: nothing to run (it used to raise KeyError).
        if not self.data.chain_sequences:
            return
        count = len(self.data.chain_sequences)
        pressed = getattr(self, "_pressed_index", None)
        if value.current:
            # The timeout is checked on a press only: checked on a release
            # too, a step held past it was reset to step 0 before its release
            # was sent, and stayed down.
            if self.data.timeout > 0.0:
                now = clock.monotonic()
                if self.last_execution + self.data.timeout < now:
                    self.current_index = 0
                self.last_execution = now
            self.current_index %= count
            index = self._pressed_index = self.current_index
        else:
            if self.data.timeout > 0.0:
                self.last_execution = clock.monotonic()
            index = pressed if pressed is not None else self.current_index % count

        for functor in self.functors.get(str(index), []):
            functor(event, value, properties)

        if not value.current:
            self.current_index = (index + 1) % count
            self._pressed_index = None


class ChainModel(ActionModel):
    # Signal emitted when the description variable's content changes
    changed = QtCore.Signal()

    def __init__(
        self,
        data: AbstractActionData,
        binding_model: InputItemBindingModel,
        action_index: SequenceIndex,
        parent_index: SequenceIndex,
        parent: QtCore.QObject,
    ) -> None:
        super().__init__(data, binding_model, action_index, parent_index, parent)

    def _qml_path_impl(self) -> str:
        return (
            "file:///" + QtCore.QFile("core_plugins:chain/ChainAction.qml").fileName()
        )

    @QtCore.Property(int, notify=changed)
    def chainCount(self) -> int:
        return len(self._data.chain_sequences)

    @QtCore.Slot()
    def addSequence(self) -> None:
        self._data.chain_sequences.append([])
        note_edit()
        self.changed.emit()

    @QtCore.Slot(int)
    def removeSequence(self, index: int) -> None:
        if index < 0 or index >= len(self._data.chain_sequences):
            raise GremlinError(f"Index {index} invalid as chain container")

        removed = self._data.chain_sequences.pop(index)
        note_edit()
        # Its actions leave the profile unless another input uses them (the
        # one removal rule, 05 Q12).
        self.library.release(removed)
        self.changed.emit()
        self._binding_model.sync_data()

    def _action_behavior(self) -> str:
        return self._binding_model.get_action_model_by_sidx(
            self._parent_sequence_index.index
        ).actionBehavior

    def _get_timeout(self) -> float:
        return self._data.timeout

    def _set_timeout(self, value: float) -> None:
        if value != self._data.timeout:
            self._data.timeout = value
            self.changed.emit()

    timeout = QtCore.Property(
        type=float, fget=_get_timeout, fset=_set_timeout, notify=changed
    )


class ChainData(AbstractActionData):
    """Model of a description action."""

    version = 1
    name = "Chain"
    tag = "chain"
    icon = "\uf813"

    functor = ChainFunctor
    model = ChainModel

    properties = (ActionProperty.ActivateDisabled,)
    input_types = (InputType.JoystickButton, InputType.Keyboard)

    def __init__(self, behavior_type: InputType = InputType.JoystickButton) -> None:
        super().__init__(behavior_type)

        self.chain_sequences = [
            [],
        ]
        self.timeout = 0.0

    @override
    def _from_xml(self, node: ElementTree.Element, library: Library) -> None:
        self._id = util.read_action_id(node)
        self.timeout = util.read_property(node, "timeout", PropertyType.Float)
        chain_dict = {}
        # Every chain-N entry, empty ones included; reading only entries with an
        # action-id dropped empty sequences and shifted the later ones down.
        for elem in node:
            parts = elem.tag.split("-")
            if len(parts) != 2 or parts[0] != "chain" or not parts[1].isdigit():
                continue
            action_ids = util.read_action_ids(elem)
            chain_dict[int(parts[1])] = [library.get_action(aid) for aid in action_ids]
        self.chain_sequences = [chain_dict[idx] for idx in sorted(chain_dict)]
        if not self.chain_sequences:
            self.chain_sequences = [[]]

    @override
    def _to_xml(self) -> ElementTree.Element:
        node = util.create_action_node(ChainData.tag, self._id)
        for i, chain in enumerate(self.chain_sequences):
            node.append(
                util.create_action_ids(f"chain-{i}", [action.id for action in chain])
            )
        node.append(
            util.create_property_node("timeout", self.timeout, PropertyType.Float)
        )
        return node

    @override
    def user_feedback(self) -> list[UserFeedback]:
        return self._empty_feedback()

    @override
    def _valid_selectors(self) -> list[str]:
        return [str(i) for i in range(len(self.chain_sequences))]

    @override
    def _get_container(self, selector: str) -> list[AbstractActionData]:
        index = int(selector)
        if index < 0 or index >= len(self.chain_sequences):
            raise GremlinError(f"Index {index} invalid as chain container")
        return self.chain_sequences[index]

    @override
    def _handle_behavior_change(
        self, old_behavior: InputType, new_behavior: InputType
    ) -> None:
        pass


create = ChainData
