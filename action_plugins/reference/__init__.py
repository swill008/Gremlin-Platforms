# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import uuid
from typing import (
    TYPE_CHECKING,
    List,
    override,
)
from xml.etree import ElementTree

from PySide6 import QtCore

from gremlin.base_classes import (
    AbstractActionData,
    AbstractFunctor,
    UserFeedback,
    Value,
)
from gremlin.error import GremlinError
from gremlin.profile import Library
from gremlin.types import (
    ActionProperty,
    InputType,
)
from gremlin.ui.action_model import (
    ActionModel,
    SequenceIndex,
)
from gremlin.ui.profile import LabelValueSelectionModel

if TYPE_CHECKING:
    from gremlin.event_handler import Event
    from gremlin.ui.profile import InputItemBindingModel


class ReferenceFunctor(AbstractFunctor):
    """A placeholder does nothing at Run (05 Q3: Run skips unfinished
    actions), so one left in an input can't make Run fail."""

    @override
    def __call__(
        self, event: Event, value: Value, properties: list[ActionProperty] = []
    ) -> None:
        pass


class ReferenceModel(ActionModel):
    modelChanged = QtCore.Signal()

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
            "file:///"
            + QtCore.QFile("core_plugins:reference/ReferenceAction.qml").fileName()
        )

    def _action_behavior(self) -> str:
        return self._binding_model.get_action_model_by_sidx(
            self._parent_sequence_index.index
        ).actionBehavior

    def _get_actions(self) -> LabelValueSelectionModel:
        # Discover all actions that are an ancestor of the present action
        ancestor_action_ids = []
        queue = [self._data.id]
        while len(queue) > 0:
            aid = queue.pop(0)
            action_ids = [
                a.id
                for a in self.library.actions_by_predicate(
                    lambda x: aid in [v.id for v in x.get_actions()[0]]
                )
            ]
            ancestor_action_ids.extend(action_ids)
            queue.extend(action_ids)

        # Predicate to select only valid actions to show in the reference
        # list. Excludes all actions that:
        # - result in circular inclusions
        # - are of an incompatible input type
        # - are a reference action or an input's root (05 S60a)
        def selector(action: AbstractActionData) -> bool:
            # Only consider actions that are of a valid type
            if action.tag in ["reference", "root"]:
                return False
            if action.behavior_type != self.input_type:
                return False

            # Reject all actions that would result in a loop
            if action.id in ancestor_action_ids:
                return False
            return True

        # Grab library and get all actions that fit with the given input
        # modality: those an input uses (not deleted or replaced ones) and
        # those in the input being edited.
        actions = self.library.pick_list(
            selector, self._data, self._binding_model.input_item_binding.input_item
        )
        return LabelValueSelectionModel(
            [a.action_label for a in actions],
            [str(a.id) for a in actions],
            bootstrap=[a.icon for a in actions],
            parent=self,
        )

    @QtCore.Slot(str)
    def referenceAction(self, value: str) -> None:
        # Shared with the inputs that use it; in a pane it is edited as a
        # copy until OK writes it back into the shared one (A1, A4).
        self._replace_reference(
            self.adopt_action(self.library.get_action(uuid.UUID(value)))
        )

    @QtCore.Slot(str)
    def duplicateAction(self, value: str) -> None:
        # Duplicate the action, and every action inside it, under new ids
        # into the library before adding it to the tree.
        action = self.library.duplicate(self.library.get_action(uuid.UUID(value)))
        if action is None:
            raise GremlinError("Reference: this action can't be duplicated.")
        self._replace_reference(action)

    def _replace_reference(self, action: AbstractActionData) -> None:
        # Replace the placeholder with the action; removing it releases the
        # placeholder through the library's one removal rule.
        self._binding_model.append_action(action, self.sequence_index)
        self._binding_model.remove_action(self.sequence_index)

    actions = QtCore.Property(
        LabelValueSelectionModel, fget=_get_actions, notify=modelChanged
    )


class ReferenceData(AbstractActionData):
    """Data for the library reference action."""

    version = 1
    name = "Reference"
    tag = "reference"
    icon = "\uf470"

    functor = ReferenceFunctor
    model = ReferenceModel

    properties = (ActionProperty.ActivateDisabled,)
    input_types = (
        InputType.JoystickAxis,
        InputType.JoystickButton,
        InputType.JoystickHat,
        InputType.Keyboard,
    )

    def __init__(self, behavior_type: InputType = InputType.JoystickButton) -> None:
        super().__init__(behavior_type)

    @override
    def _from_xml(self, node: ElementTree.Element, library: Library) -> None:
        pass

    @override
    def _to_xml(self) -> ElementTree.Element:
        return ElementTree.Element("")

    @override
    def user_feedback(self) -> List[UserFeedback]:
        return [
            UserFeedback(
                UserFeedback.FeedbackType.Error,
                "Always invalid, use to insert an existing action into the profile.",
            )
        ]

    @override
    def copy_unfinished(self) -> ReferenceData:
        copy = ReferenceData(self.behavior_type)
        copy.action_label = self.action_label
        copy.activation_mode = self.activation_mode
        return copy

    @override
    def _valid_selectors(self) -> List[str]:
        return []

    @override
    def _get_container(self, selector: str) -> List[AbstractActionData]:
        raise GremlinError(f"{self.name}: has no containers")

    @override
    def _handle_behavior_change(
        self, old_behavior: InputType, new_behavior: InputType
    ) -> None:
        pass


create = ReferenceData
