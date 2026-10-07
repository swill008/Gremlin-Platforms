# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import collections
import copy
import logging
import math
import uuid
from typing import (
    TYPE_CHECKING,
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


Vector2 = collections.namedtuple("Vector2", ["x", "y"])


# Smallest gap kept between the inner and outer deadzone.
_MIN_GAP = 0.01


class DualAxisDeadzoneFunctor(AbstractFunctor):
    """Implements the function executed of the Description action at runtime."""

    def __init__(self, action: DualAxisDeadzoneData) -> None:
        super().__init__(action)

    @override
    def __call__(
        self,
        event: event_handler.Event,
        value: Value,
        properties: list[ActionProperty] = [],
    ) -> None:
        # Retrieve current joystick values
        # Through the input modules: an unclaimed axis reads as centred.
        axis1, axis2 = self.data.axis1, self.data.axis2
        x_value = inputs.axis_value(axis1.device_guid, axis1.input_id)
        y_value = inputs.axis_value(axis2.device_guid, axis2.input_id)

        # Apply the deadzones, a circular one around the center and a
        # rectangular around the outside.
        alpha = math.atan2(y_value, x_value)
        lower = Vector2(
            abs(math.cos(alpha) * self.data.inner_deadzone),
            abs(math.sin(alpha) * self.data.inner_deadzone),
        )
        upper = Vector2(self.data.outer_deadzone, self.data.outer_deadzone)

        try:
            px = max(0.0, min(1.0, (abs(x_value) - lower.x) / (upper.x - lower.x)))
            py = max(0.0, min(1.0, (abs(y_value) - lower.y) / (upper.y - lower.y)))

            # Create separate value instances and set their values before passing
            # everything on to the child functors. The event will not necessarily
            # corespond to the correct axis but that should be fine.
            value_x = copy.deepcopy(value)
            value_x.current = math.copysign(px, x_value)
            for functor in self.functors["first"]:
                functor(event, value_x, properties)

            value_y = copy.deepcopy(value)
            value_y.current = math.copysign(py, y_value)
            for functor in self.functors["second"]:
                functor(event, value_y, properties)
        except ZeroDivisionError:
            logging.getLogger("system").error(
                f"DualAxisDeadzone: ({self.data.label}) deadzone limits too "
                + "close to each other"
            )


class DualAxisDeadzoneModel(ActionModel):
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
            + QtCore.QFile(
                "core_plugins:dual_axis_deadzone/DualAxisDeadzoneAction.qml"
            ).fileName()
        )

    def _action_behavior(self) -> str:
        return self._binding_model.get_action_model_by_sidx(
            self._parent_sequence_index.index
        ).actionBehavior

    @QtCore.Slot()
    def newDeadzone(self) -> None:
        # Always a new one ("+"), numbered like Merge Axis (05 Q14).
        action = axis_pair.new_instance(self, DualAxisDeadzoneData)
        if action is not None:
            # The new one is the one shown (as picking it from the list).
            self._set_deadzone(str(action.id))

    @QtCore.Property(LabelValueSelectionModel, notify=modelChanged)
    def deadzoneActionList(self) -> LabelValueSelectionModel:
        return axis_pair.pick_list(self, DualAxisDeadzoneData)

    def _get_axis(self, idx: int) -> InputIdentifier:
        return self._axis_views[idx].show(
            self._data.axis1 if idx == 1 else self._data.axis2
        )

    def _set_axis(self, idx: int, value: InputIdentifier) -> None:
        # A copy: the page's current input changes after this.
        name = "axis1" if idx == 1 else "axis2"
        if value != getattr(self._data, name):
            setattr(self._data, name, AxisRef.of(value))
            self.modelChanged.emit()

    def _get_deadzone(self) -> str:
        return str(self._data.id)

    def _set_deadzone(self, uuid_str: str) -> None:
        axis_pair.switch_instance(self, uuid_str, ("axis1", "axis2"))

    @QtCore.Property(float, notify=modelChanged)
    def innerDeadzone(self) -> float:
        return self._data.inner_deadzone

    @innerDeadzone.setter
    def innerDeadzone(self, value: float) -> None:
        # Keep inner at least _MIN_GAP below outer; take the nearest allowed
        # value instead of ignoring the edit.
        value = min(value, round(self._data.outer_deadzone - _MIN_GAP, 4))
        if value != self._data.inner_deadzone:
            self._data.inner_deadzone = value
        self.modelChanged.emit()

    @QtCore.Property(str, notify=modelChanged)
    def label(self) -> str:
        return self._data.label

    @label.setter
    def label(self, label: str) -> None:
        if label != self._data.label:
            self._data.label = label
            self.modelChanged.emit()

    @QtCore.Property(float, notify=modelChanged)
    def outerDeadzone(self) -> float:
        return self._data.outer_deadzone

    @outerDeadzone.setter
    def outerDeadzone(self, value: float) -> None:
        value = max(value, round(self._data.inner_deadzone + _MIN_GAP, 4))
        if value != self._data.outer_deadzone:
            self._data.outer_deadzone = value
        self.modelChanged.emit()

    axis1 = QtCore.Property(
        InputIdentifier,
        fget=lambda c: DualAxisDeadzoneModel._get_axis(c, 1),
        fset=lambda c, x: DualAxisDeadzoneModel._set_axis(c, 1, x),
        notify=modelChanged,
    )

    axis2 = QtCore.Property(
        InputIdentifier,
        fget=lambda c: DualAxisDeadzoneModel._get_axis(c, 2),
        fset=lambda c, x: DualAxisDeadzoneModel._set_axis(c, 2, x),
        notify=modelChanged,
    )

    deadzone = QtCore.Property(
        str, fget=_get_deadzone, fset=_set_deadzone, notify=modelChanged
    )


class DualAxisDeadzoneData(AbstractActionData):
    """Model of a description action."""

    version = 1
    name = "Dual Axis Deadzone"
    tag = "dual-axis-deadzone"
    icon = "\uf1de"

    functor = DualAxisDeadzoneFunctor
    model = DualAxisDeadzoneModel

    properties = (ActionProperty.ActivateDisabled,)
    input_types = (InputType.JoystickAxis,)

    def __init__(self, behavior_type: InputType = InputType.JoystickAxis) -> None:
        super().__init__(behavior_type)

        self.label = ""
        self.inner_deadzone = 0.0
        self.outer_deadzone = 1.0
        self.axis1 = AxisRef()
        self.axis2 = AxisRef()

        self.output1_actions = []
        self.output2_actions = []

    @override
    def _from_xml(self, node: ElementTree.Element, library: Library) -> None:
        self._id = util.read_action_id(node)

        # Parse deadzone information
        self.label = util.read_property(node, "label", PropertyType.String)
        self.inner_deadzone = util.read_property(
            node, "inner-deadzone", PropertyType.Float
        )
        self.outer_deadzone = util.read_property(
            node, "outer-deadzone", PropertyType.Float
        )

        # Parse axes data
        self.axis1.input_type = InputType.JoystickAxis
        self.axis1.device_guid = util.read_property(
            node, "axis1-guid", PropertyType.UUID
        )
        self.axis1.input_id = util.read_property(
            node, "axis1-axis", [PropertyType.Int, PropertyType.UUID]
        )
        self.axis2.input_type = InputType.JoystickAxis
        self.axis2.device_guid = util.read_property(
            node, "axis2-guid", PropertyType.UUID
        )
        self.axis2.input_id = util.read_property(
            node, "axis2-axis", [PropertyType.Int, PropertyType.UUID]
        )

        # Parse child actions
        output1_actions = util.read_action_ids(node.find("output1-actions"))
        self.output1_actions = [library.get_action(aid) for aid in output1_actions]
        output2_actions = util.read_action_ids(node.find("output2-actions"))
        self.output2_actions = [library.get_action(aid) for aid in output2_actions]

    @override
    def _to_xml(self) -> ElementTree.Element:
        node = util.create_action_node(DualAxisDeadzoneData.tag, self._id)

        # Write axis and deadzone data
        entries = [
            ["label", self.label, PropertyType.String],
            ["inner-deadzone", self.inner_deadzone, PropertyType.Float],
            ["outer-deadzone", self.outer_deadzone, PropertyType.Float],
            ["axis1-guid", self.axis1.device_guid, PropertyType.UUID],
            ["axis1-axis", self.axis1.input_id, [PropertyType.Int, PropertyType.UUID]],
            ["axis2-guid", self.axis2.device_guid, PropertyType.UUID],
            ["axis2-axis", self.axis2.input_id, [PropertyType.Int, PropertyType.UUID]],
        ]
        util.append_property_nodes(node, entries)

        # Write action ids
        node.append(
            util.create_action_ids(
                "output1-actions", [action.id for action in self.output1_actions]
            )
        )
        node.append(
            util.create_action_ids(
                "output2-actions", [action.id for action in self.output2_actions]
            )
        )

        return node

    @override
    def user_feedback(self) -> list[UserFeedback]:
        messages = []
        if not (is_set(self.axis1) and is_set(self.axis2)):
            messages.append(
                UserFeedback(
                    UserFeedback.FeedbackType.Error, "Both axes must be assigned."
                )
            )
        if abs(self.outer_deadzone - self.inner_deadzone) < 0.01:
            messages.append(
                UserFeedback(
                    UserFeedback.FeedbackType.Error,
                    "Outer and inner deadzone are too close to each other.",
                )
            )
        return messages

    @override
    def _valid_selectors(self) -> list[str]:
        return ["first", "second"]

    @override
    def _get_container(self, selector: str) -> list[AbstractActionData]:
        if selector == "first":
            return self.output1_actions
        elif selector == "second":
            return self.output2_actions

    @override
    def swap_uuid(self, old_uuid: uuid.UUID, new_uuid: uuid.UUID) -> bool:
        performed_swap = False
        if self.axis1.device_guid == old_uuid:
            self.axis1.device_guid = new_uuid
            performed_swap = True
        if self.axis2.device_guid == old_uuid:
            self.axis2.device_guid = new_uuid
            performed_swap = True
        return performed_swap

    @override
    def copy_unfinished(self) -> DualAxisDeadzoneData:
        copy = DualAxisDeadzoneData(self.behavior_type)
        copy.action_label = self.action_label
        copy.activation_mode = self.activation_mode
        copy.label = self.label
        copy.inner_deadzone = self.inner_deadzone
        copy.outer_deadzone = self.outer_deadzone
        copy.axis1 = AxisRef.of(self.axis1)
        copy.axis2 = AxisRef.of(self.axis2)
        return copy

    @override
    def _handle_behavior_change(
        self, old_behavior: InputType, new_behavior: InputType
    ) -> None:
        pass


create = DualAxisDeadzoneData
