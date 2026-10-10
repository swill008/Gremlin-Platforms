# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import uuid
from enum import Enum
from typing import (
    TYPE_CHECKING,
    List,
    override,
)
from xml.etree import ElementTree

from PySide6 import QtCore

from action_plugins import axis_pair
from action_plugins.axis_pair import AxisRef, AxisView, is_set
from gremlin import (
    event_handler,
    util,
)
from gremlin.base_classes import (
    AbstractActionData,
    AbstractFunctor,
    UserFeedback,
    Value,
)
from gremlin.error import GremlinError
from gremlin.modules import inputs
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
from gremlin.ui.device import InputIdentifier
from gremlin.ui.profile import LabelValueSelectionModel

if TYPE_CHECKING:
    from gremlin.ui.profile import InputItemBindingModel


class MergeOperation(Enum):
    """Represents the available merge operations."""

    Average = 0
    Minimum = 1
    Maximum = 2
    Sum = 3
    Bidirectional = 4
    Prefercenter = 5
    MaximumDeflection = 6

    @classmethod
    def to_string(cls, value: MergeOperation) -> str:
        """The name profiles store (also the drop-down's value)."""
        res = _NAMES.get(value, None)
        if res is None:
            raise GremlinError(f"MergeOperation: invalid value in lookup '{value}'")
        return res[0]

    @classmethod
    def to_enum(cls, value: str) -> MergeOperation:
        for operation, (stored, _) in _NAMES.items():
            if stored == value.lower():
                return operation
        raise GremlinError(f"MergeOperation: invalid value in lookup '{value.lower()}'")

    @classmethod
    def to_display(cls, value: MergeOperation) -> str:
        """The name shown in the editor."""
        res = _NAMES.get(value, None)
        if res is None:
            raise GremlinError(f"MergeOperation: invalid value in lookup '{value}'")
        return res[1]


# Each operation: stored name -> shown name. One table, so the drop-down's
# values are exactly what profiles store and the editor's getter returns.
_NAMES: dict[MergeOperation, tuple[str, str]] = {
    MergeOperation.Average: ("average", "Average"),
    MergeOperation.Minimum: ("minimum", "Minimum"),
    MergeOperation.Maximum: ("maximum", "Maximum"),
    MergeOperation.Sum: ("sum", "Sum"),
    MergeOperation.Bidirectional: ("bidirectional", "Bidirectional"),
    MergeOperation.Prefercenter: ("prefercenter", "Prefer Center"),
    MergeOperation.MaximumDeflection: ("maximum-deflection", "Maximum Deflection"),
}


class MergeAxisFunctor(AbstractFunctor):
    def __init__(self, action: MergeAxisData) -> None:
        super().__init__(action)

    @override
    def __call__(
        self,
        event: event_handler.Event,
        value: Value,
        properties: list[ActionProperty] = [],
    ) -> None:
        # Through the input modules: an unclaimed axis reads as centred.
        in1, in2 = self.data.axis_in1, self.data.axis_in2
        axis1 = inputs.axis_value(in1.device_guid, in1.input_id)
        axis2 = inputs.axis_value(in2.device_guid, in2.input_id)

        value.current = MergeAxisFunctor.actions[self.data.operation](axis1, axis2)

        for functor in self.functors["children"]:
            functor(event, value, properties)

    @staticmethod
    def _average(value1: float, value2: float) -> float:
        return (value2 + value1) / 2.0

    @staticmethod
    def _minimum(value1: float, value2: float) -> float:
        return min(value1, value2)

    @staticmethod
    def _maximum(value1: float, value2: float) -> float:
        return max(value1, value2)

    @staticmethod
    def _sum(value1: float, value2: float) -> float:
        return util.clamp(value1 + value2, -1.0, 1.0)

    @staticmethod
    def _bidirectional(value1: float, value2: float) -> float:
        """Merges two axes into one:
            - the 1st axis controls the lower half of the value range
            - the 2nd axis controls the upper half

        Allows full deflection either way if only one axis is used.
        Performs differential mixing if both are used.

        Use case example: merging two pedal axes into a single left/right axis.
        """
        return (value2 - value1) / 2.0

    @staticmethod
    def _prefercenter(value1: float, value2: float) -> float:
        """Use the axis closest to center."""
        return value1 if abs(value1) < abs(value2) else value2

    @staticmethod
    def _maximum_deflection(value1: float, value2: float) -> float:
        """Use the axis furthest from center; a tie goes to the 2nd axis."""
        return value1 if abs(value1) > abs(value2) else value2

    actions = {
        MergeOperation.Average: _average,
        MergeOperation.Minimum: _minimum,
        MergeOperation.Maximum: _maximum,
        MergeOperation.Sum: _sum,
        MergeOperation.Bidirectional: _bidirectional,
        MergeOperation.Prefercenter: _prefercenter,
        MergeOperation.MaximumDeflection: _maximum_deflection,
    }


class MergeAxisModel(ActionModel):
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
        self._axis_views = {1: AxisView(self), 2: AxisView(self)}

    def _qml_path_impl(self) -> str:
        return (
            "file:///"
            + QtCore.QFile("core_plugins:merge_axis/MergeAxisAction.qml").fileName()
        )

    def _action_behavior(self) -> str:
        return self._binding_model.get_action_model_by_sidx(
            self._parent_sequence_index.index
        ).actionBehavior

    @QtCore.Property(LabelValueSelectionModel, notify=modelChanged)
    def operationList(self) -> LabelValueSelectionModel:
        """Returns the list of all valid operation names.

        Returns:
            List of valid operation names
        """
        # Shown as words, in alphabetical order; the values are the stored names.
        operations = sorted(MergeOperation, key=MergeOperation.to_display)
        labels = [MergeOperation.to_display(o) for o in operations]
        values = [MergeOperation.to_string(o) for o in operations]
        return LabelValueSelectionModel(labels, values, parent=self)

    @QtCore.Property(LabelValueSelectionModel, notify=modelChanged)
    def mergeActionList(self) -> LabelValueSelectionModel:
        return axis_pair.pick_list(self, MergeAxisData)

    def _get_label(self) -> str:
        return self._data.label

    def _set_label(self, label: str) -> None:
        if label != self._data.label:
            self._data.label = label
            self.modelChanged.emit()

    def _get_merge_action(self) -> str:
        """Returns the UUID of the merge action being configured.

        Returns:
            string representation of an action UUID
        """
        return str(self._data.id)

    def _set_merge_action(self, uuid_str: str) -> None:
        """Shows the merge action with that id (string UUID) here."""
        axis_pair.switch_instance(self, uuid_str, ("axis_in1", "axis_in2"))

    def _get_axis(self, idx: int) -> InputIdentifier:
        return self._axis_views[idx].show(
            self._data.axis_in1 if idx == 1 else self._data.axis_in2
        )

    def _set_axis(self, idx: int, value: InputIdentifier) -> None:
        # A copy: the page's current input changes after this.
        name = "axis_in1" if idx == 1 else "axis_in2"
        if value != getattr(self._data, name):
            setattr(self._data, name, AxisRef.of(value))
            self.modelChanged.emit()

    def _get_operation(self) -> str:
        return MergeOperation.to_string(self._data.operation)

    def _set_operation(self, value: str) -> None:
        operation = MergeOperation.to_enum(value)
        if operation != self._data.operation:
            self._data.operation = operation
            self.modelChanged.emit()

    @QtCore.Slot()
    def newMergeAxis(self) -> None:
        # Always a new one ("+"), added by the library.
        action = axis_pair.new_instance(self, MergeAxisData)
        if action is not None:
            # The new one is the one shown (as picking it from the list).
            self._set_merge_action(str(action.id))

    label = QtCore.Property(str, fget=_get_label, fset=_set_label, notify=modelChanged)

    mergeAction = QtCore.Property(
        str, fget=_get_merge_action, fset=_set_merge_action, notify=modelChanged
    )

    firstAxis = QtCore.Property(
        InputIdentifier,
        fget=lambda c: MergeAxisModel._get_axis(c, 1),
        fset=lambda c, x: MergeAxisModel._set_axis(c, 1, x),
        notify=modelChanged,
    )

    secondAxis = QtCore.Property(
        InputIdentifier,
        fget=lambda c: MergeAxisModel._get_axis(c, 2),
        fset=lambda c, x: MergeAxisModel._set_axis(c, 2, x),
        notify=modelChanged,
    )

    operation = QtCore.Property(
        str, fget=_get_operation, fset=_set_operation, notify=modelChanged
    )


class MergeAxisData(AbstractActionData):
    version = 1
    name = "Merge Axis"
    tag = "merge-axis"
    icon = "\uf85c"

    functor = MergeAxisFunctor
    model = MergeAxisModel

    properties = (
        ActionProperty.ReuseByDefault,
        ActionProperty.ActivateDisabled,
    )
    input_types = (InputType.JoystickAxis,)

    def __init__(self, behavior_type: InputType = InputType.JoystickButton) -> None:
        super().__init__(behavior_type)

        self.label = ""
        self.axis_in1 = AxisRef()
        self.axis_in2 = AxisRef()
        self.operation = MergeOperation.Average

        self.children = []

    @override
    def _from_xml(self, node: ElementTree.Element, library: Library) -> None:
        self._id = util.read_action_id(node)
        self.label = util.read_property(node, "label", PropertyType.String)
        self.axis_in1.input_type = InputType.JoystickAxis
        self.axis_in1.device_guid = util.read_property(
            node, "axis1-guid", PropertyType.UUID
        )
        self.axis_in1.input_id = util.read_property(
            node, "axis1-axis", [PropertyType.Int, PropertyType.UUID]
        )
        self.axis_in2.input_type = InputType.JoystickAxis
        self.axis_in2.device_guid = util.read_property(
            node, "axis2-guid", PropertyType.UUID
        )
        self.axis_in2.input_id = util.read_property(
            node, "axis2-axis", [PropertyType.Int, PropertyType.UUID]
        )
        self.operation = MergeOperation.to_enum(
            util.read_property(node, "operation", PropertyType.String)
        )
        child_ids = util.read_action_ids(node.find("actions"))
        self.children = [library.get_action(aid) for aid in child_ids]

    @override
    def _to_xml(self) -> ElementTree.Element:
        node = util.create_action_node(MergeAxisData.tag, self._id)
        entries = [
            ["label", self.label, PropertyType.String],
            ["axis1-guid", self.axis_in1.device_guid, PropertyType.UUID],
            [
                "axis1-axis",
                self.axis_in1.input_id,
                [PropertyType.Int, PropertyType.UUID],
            ],
            ["axis2-guid", self.axis_in2.device_guid, PropertyType.UUID],
            [
                "axis2-axis",
                self.axis_in2.input_id,
                [PropertyType.Int, PropertyType.UUID],
            ],
            [
                "operation",
                MergeOperation.to_string(self.operation),
                PropertyType.String,
            ],
        ]
        util.append_property_nodes(node, entries)
        node.append(
            util.create_action_ids("actions", [child.id for child in self.children])
        )
        return node

    def start_new(self, profile: object, item: object) -> None:
        """Added with Add Action: a new, named instance (05 S120)."""
        axis_pair.start_new(self, profile, item)

    @override
    def user_feedback(self) -> List[UserFeedback]:
        messages = []
        if not (is_set(self.axis_in1) and is_set(self.axis_in2)):
            messages.append(
                UserFeedback(
                    UserFeedback.FeedbackType.Error, "Both axes have to be assigned."
                )
            )
        return messages

    @override
    def swap_uuid(self, old_uuid: uuid.UUID, new_uuid: uuid.UUID) -> bool:
        performed_swap = False
        if self.axis_in1.device_guid == old_uuid:
            self.axis_in1.device_guid = new_uuid
            performed_swap = True
        if self.axis_in2.device_guid == old_uuid:
            self.axis_in2.device_guid = new_uuid
            performed_swap = True
        return performed_swap

    @override
    def copy_unfinished(self) -> MergeAxisData:
        copy = MergeAxisData(self.behavior_type)
        copy.action_label = self.action_label
        copy.activation_mode = self.activation_mode
        copy.label = self.label
        copy.operation = self.operation
        copy.axis_in1 = AxisRef.of(self.axis_in1)
        copy.axis_in2 = AxisRef.of(self.axis_in2)
        return copy

    @override
    def _valid_selectors(self) -> list[str]:
        return ["children"]

    @override
    def _get_container(self, selector: str) -> list[AbstractActionData]:
        if selector == "children":
            return self.children

    @override
    def _handle_behavior_change(
        self, old_behavior: InputType, new_behavior: InputType
    ) -> None:
        pass


create = MergeAxisData
