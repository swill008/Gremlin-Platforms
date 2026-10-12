# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import (
    TYPE_CHECKING,
    List,
    cast,
    override,
)
from xml.etree import ElementTree

from PySide6 import QtCore

from action_plugins.common import RelativeAxisLoop
from gremlin import (
    event_handler,
    event_helpers,
    mode_manager,
    references,
    util,
)
from gremlin.base_classes import (
    AbstractActionData,
    AbstractFunctor,
    UserFeedback,
    Value,
)
from gremlin.error import GremlinError
from gremlin.logical_device import (
    LogicalDevice,
    resolve_logical_reference,
)
from gremlin.modules import ids, output
from gremlin.profile import Library
from gremlin.signal import signal
from gremlin.types import (
    ActionProperty,
    AxisMode,
    DataCreationMode,
    InputType,
    PropertyType,
)
from gremlin.ui.action_model import (
    ActionModel,
    SequenceIndex,
)
from gremlin.ui.device import InputIdentifier

if TYPE_CHECKING:
    from gremlin.ui.profile import InputItemBindingModel


class MapToLogicalDeviceFunctor(RelativeAxisLoop, AbstractFunctor):
    _loop_name = "logical device relative axis"

    def __init__(self, instance: MapToLogicalDeviceData) -> None:
        super().__init__(instance)
        self._logical = LogicalDevice()
        self._event_listener = event_handler.EventListener()
        self._init_relative()
        # The chain of the event that started the relative loop: its sends
        # continue it (06 S94a).
        self._relative_chain: tuple = ()
        # Drives the control the uid names, by its current number; a missing
        # one does nothing (D-04-LD-FILE).
        self._identifier, _ = resolve_logical_reference(
            instance.logical_input_uid,
            instance.logical_input_type,
            instance.logical_input_id,
        )

    @override
    def __call__(
        self,
        event: event_handler.Event,
        value: Value,
        properties: List[ActionProperty] = [],
    ) -> None:
        if not self._should_execute(value):
            return
        if self._identifier is None or not self._logical.exists(self._identifier):
            return
        input = self._logical[self._identifier]
        # The guard follows the chain the event came through (06 S94a).
        chain = getattr(event, "ld_chain", ())

        # Determine correct event values and update the logical device's
        # internal state.
        is_pressed = None
        input_value = None
        if input.type == InputType.JoystickAxis:
            if self.data.axis_mode == AxisMode.Absolute:
                input_value = value.current
                input.update(input_value)
            else:
                self._relative_chain = chain
                self._relative_input(
                    event.value, value.current, self.data.axis_scaling
                )
                # Don't emit an event in relative mode.
                return

        elif input.type == InputType.JoystickButton:
            is_pressed = value.current
            if self.data.button_inverted:
                is_pressed = not is_pressed
            input.update(is_pressed)

            if is_pressed and ActionProperty.DisableAutoRelease not in properties:
                event_helpers.ButtonReleaseActions().register_logical_button_release(
                    input.id, event, self.data.button_inverted
                )
        elif input.type == InputType.JoystickHat:
            input_value = value.current
            input.update(input_value)

        # Emit an event with the LogicalDevice guid and the rest of the
        # system will then take care of executing it; a loop between
        # controls is stopped by the guard (06 S94).
        mode = mode_manager.ModeManager().current.name
        self._guarded_emit(
            input,
            lambda path: event_handler.Event(
                event_type=input.type,
                identifier=input.id,
                device_guid=self._logical.device_guid,
                mode=mode,
                value=input_value,
                is_pressed=is_pressed,
                raw_value=value.raw,
                ld_chain=path,
                # Made by the program: never moves a page (05 S131).
                synthetic=True,
            ),
            chain,
        )

    def _guarded_emit(
        self,
        input: LogicalDevice.Input,
        make_event: Callable[[tuple], event_handler.Event],
        chain: tuple,
    ) -> bool:
        """Sends the event make_event(path) builds for the chain with this
        control added, unless the loop guard stops it."""
        from gremlin import logical_loop

        return logical_loop.guarded(
            (input.type, input.id),
            input.choice_label,
            lambda path: self._event_listener.joystick_event.emit(make_event(path)),
            chain,
        )

    def _relative_axis(self) -> LogicalDevice.Input:
        assert self._identifier is not None
        return self._logical[self._identifier]

    def _relative_read(self) -> float:
        return cast(LogicalDevice.Axis, self._relative_axis()).value

    def _relative_write(self, value: float) -> bool:
        input = self._relative_axis()
        input.update(value)
        # A loop the guard stopped ends this relative loop too (06 S94).
        mode = mode_manager.ModeManager().current.name
        return self._guarded_emit(
            input,
            lambda path: event_handler.Event(
                event_type=input.type,
                identifier=input.id,
                device_guid=self._logical.device_guid,
                mode=mode,
                value=value,
                raw_value=value,
                ld_chain=path,
                synthetic=True,
            ),
            self._relative_chain,
        )


class MapToLogicalDeviceModel(ActionModel):
    logicalInputIdentifierChanged = QtCore.Signal()
    axisModeChanged = QtCore.Signal()
    axisScalingChanged = QtCore.Signal()
    buttonInvertedChanged = QtCore.Signal()

    def __init__(
        self,
        data: AbstractActionData,
        binding_model: InputItemBindingModel,
        action_index: SequenceIndex,
        parent_index: SequenceIndex,
        parent: QtCore.QObject,
    ) -> None:
        # Opening an editor changes nothing on the Logical Device: no
        # logicalDeviceModified here (each one rebuilt the Logical page, 05 RB21).
        super().__init__(data, binding_model, action_index, parent_index, parent)
        # Its own object: a list refresh is not an edit of the action
        # (ActionModel reports every property notify as one).
        self._picker = ControlPicker(self)
        self.logicalInputIdentifierChanged.connect(self._picker.refresh)

    def _qml_path_impl(self) -> str:
        return (
            "file:///"
            + QtCore.QFile(
                "core_plugins:map_to_logical_device/MapToLogicalDeviceAction.qml"
            ).fileName()
        )

    def _action_behavior(self) -> str:
        return self._binding_model.get_action_model_by_sidx(
            self._parent_sequence_index.index
        ).actionBehavior

    def _get_logical_input_identifier(self) -> InputIdentifier:
        return InputIdentifier(
            LogicalDevice().device_guid,
            self._data.logical_input_type,
            self._data.logical_input_id,
            parent=self,
        )

    def _set_logical_input_identifier(self, identifier: InputIdentifier) -> None:
        new_identifier = InputIdentifier(
            LogicalDevice().device_guid,
            self._data.logical_input_type,
            self._data.logical_input_id,
            parent=self,
        )
        if new_identifier != identifier:
            self._data.logical_input_id = identifier.input_id
            self._data.logical_input_type = identifier.input_type
            self.logicalInputIdentifierChanged.emit()

    def _get_logical_input_type(self) -> str:
        return InputType.to_string(self._data.logical_input_type)

    def _get_axis_mode(self) -> str:
        return AxisMode.to_string(self._data.axis_mode)

    def _set_axis_mode(self, axis_mode: str) -> None:
        axis_mode_tmp = AxisMode.to_enum(axis_mode)
        if axis_mode_tmp == self._data.axis_mode:
            return
        self._data.axis_mode = axis_mode_tmp
        self.axisModeChanged.emit()

    def _get_axis_scaling(self) -> float:
        return self._data.axis_scaling

    def _set_axis_scaling(self, axis_scaling: float) -> None:
        if axis_scaling == self._data.axis_scaling:
            return
        self._data.axis_scaling = axis_scaling
        self.axisScalingChanged.emit()

    def _get_button_inverted(self) -> bool:
        return self._data.button_inverted

    def _set_button_inverted(self, button_inverted: bool) -> None:
        if button_inverted == self._data.button_inverted:
            return
        self._data.button_inverted = button_inverted
        self.buttonInvertedChanged.emit()

    logicalInputIdentifier = QtCore.Property(
        InputIdentifier,
        fget=_get_logical_input_identifier,
        fset=_set_logical_input_identifier,
        notify=logicalInputIdentifierChanged,
    )
    logicalInputType = QtCore.Property(
        str, fget=_get_logical_input_type, notify=logicalInputIdentifierChanged
    )
    axisMode = QtCore.Property(
        str, fget=_get_axis_mode, fset=_set_axis_mode, notify=axisModeChanged
    )
    axisScaling = QtCore.Property(
        float, fget=_get_axis_scaling, fset=_set_axis_scaling, notify=axisScalingChanged
    )
    buttonInverted = QtCore.Property(
        bool,
        fget=_get_button_inverted,
        fset=_set_button_inverted,
        notify=buttonInvertedChanged,
    )

    def _get_control_picker(self) -> ControlPicker:
        return self._picker

    controlPicker = QtCore.Property(
        QtCore.QObject, fget=_get_control_picker, constant=True
    )

    def own_control(self) -> tuple[InputType, int] | None:
        """The Logical Device control this action sits on (None: another
        device's input)."""
        item = self._binding_model.input_item_binding.input_item
        if item is None or item.device_id != LogicalDevice().device_guid:
            return None
        if item.input_type is None or not isinstance(item.input_id, int):
            return None
        return (item.input_type, item.input_id)

    def set_target(self, input_type: InputType, input_id: int) -> None:
        """Drive that Logical Device control (as the picker's choice)."""
        self._set_logical_input_identifier(
            InputIdentifier(LogicalDevice().device_guid, input_type, input_id)
        )

    def map_data(self) -> MapToLogicalDeviceData:
        return cast(MapToLogicalDeviceData, self._data)


class ControlPicker(QtCore.QObject):
    """The editor's control list: the controls of the action's type, never
    the one it sits on as a new choice (06 S93). An action loaded with its
    own control as the target shows it selected and marked (S96). Follows
    controls added, removed or renamed."""

    changed = QtCore.Signal()

    SELF_MARK = " (this control: blocked by the loop guard)"

    def __init__(self, owner: MapToLogicalDeviceModel) -> None:
        super().__init__(owner)
        self._owner = owner
        # Choices follow the Logical Device's controls; the ⚠ follows the
        # output layer's can't-be-sent notice (D-05-CANT-SEND-LIVE).
        signal.logicalDeviceModified.connect(self.refresh)
        signal.cantSendChanged.connect(self.refresh)

    @QtCore.Slot()
    def refresh(self) -> None:
        self.changed.emit()

    def _choices(self) -> list[tuple[LogicalDevice.Input, str]]:
        """(control, row text): the own control only while it's the target."""
        own = self._owner.own_control()
        data = self._owner.map_data()
        kind = data.logical_input_type
        rows = []
        for entry in LogicalDevice().inputs_of_type([kind]):
            if (entry.type, entry.id) != own:
                rows.append((entry, entry.choice_label))
            elif entry.id == data.logical_input_id:
                rows.append((entry, entry.choice_label + self.SELF_MARK))
        return rows

    def _get_choices(self) -> list[str]:
        return [label for _, label in self._choices()]

    def _get_index(self) -> int:
        current = self._owner.map_data().logical_input_id
        for index, (entry, _) in enumerate(self._choices()):
            if entry.id == current:
                return index
        return -1

    @QtCore.Slot(int)
    def pick(self, index: int) -> None:
        """The row chosen: the action drives that control."""
        choices = self._choices()
        if not 0 <= index < len(choices):
            return
        entry = choices[index][0]
        self._owner.set_target(entry.type, entry.id)

    def _get_cant_send_text(self) -> str:
        """Why the action can't send ("" when it can): its control was
        deleted (D-05-CANT-SEND-ALL)."""
        return output.logical_cant_send_text(self._owner.map_data()) or ""

    def _get_missing_label(self) -> str:
        data = self._owner.map_data()
        return output.logical_control_label(
            data.logical_input_type, data.logical_input_id
        )

    choices = QtCore.Property(list, fget=_get_choices, notify=changed)
    index = QtCore.Property(int, fget=_get_index, notify=changed)
    cantSendText = QtCore.Property(str, fget=_get_cant_send_text, notify=changed)
    missingLabel = QtCore.Property(str, fget=_get_missing_label, notify=changed)


class MapToLogicalDeviceData(AbstractActionData):
    """Action propagating data to the logical device inputs."""

    version = 1
    name = "Map to Logical Device"
    tag = "map-to-logical-device"
    icon = "\uf6e7"

    functor = MapToLogicalDeviceFunctor
    model = MapToLogicalDeviceModel

    properties = (ActionProperty.ActivateOnBoth,)
    input_types = (
        InputType.JoystickAxis,
        InputType.JoystickButton,
        InputType.JoystickHat,
        InputType.Keyboard,
    )

    def __init__(self, behavior_type: InputType = InputType.JoystickButton) -> None:
        super().__init__(behavior_type)

        # The first control of the type; with none, number 1 and no uid.
        # Building (profile read, copies) never adds a control: only a new
        # action made in the editor does, in create() (D-04-LD-FILE).
        input_type = self._control_type(behavior_type)
        try:
            first_id = LogicalDevice().inputs_of_type([input_type])[0].id
        except (GremlinError, IndexError):
            first_id = 1

        # Model variables; setting the type or number repoints the uid.
        self._logical_input_uid: str | None = None
        self._logical_input_type = input_type
        self.logical_input_id = first_id
        self.axis_mode = AxisMode.Absolute
        self.axis_scaling = 1.0
        self.button_inverted = False

    @staticmethod
    def _control_type(behavior_type: InputType) -> InputType:
        if behavior_type == InputType.Keyboard:
            return InputType.JoystickButton
        return behavior_type

    @classmethod
    @override
    def create(
        cls, mode: DataCreationMode, behavior_type: InputType = InputType.JoystickButton
    ) -> AbstractActionData:
        # A new action in the editor gets a control to drive: the first of
        # its type, made when the Logical Device has none.
        if mode == DataCreationMode.Create:
            input_type = cls._control_type(behavior_type)
            logical = LogicalDevice()
            if not logical.inputs_of_type([input_type]):
                logical.create(input_type)
        return super().create(mode, behavior_type)

    def start_new(self, profile: object, item: object) -> None:
        """A new action added on a Logical Device control never drives that
        control: the first other one of its type, else a new one (06 S92).
        Called by Add Action only, never on load."""
        logical = LogicalDevice()
        if getattr(item, "device_id", None) != logical.device_guid:
            return
        own = (getattr(item, "input_type", None), getattr(item, "input_id", None))
        if (self.logical_input_type, self.logical_input_id) != own:
            return
        others = [
            entry
            for entry in logical.inputs_of_type([self.logical_input_type])
            if entry.id != self.logical_input_id
        ]
        target = others[0] if others else logical.create(self.logical_input_type)
        self.logical_input_id = target.id

    @property
    def logical_input_type(self) -> InputType:
        return self._logical_input_type

    @logical_input_type.setter
    def logical_input_type(self, value: InputType) -> None:
        self._logical_input_type = value
        self._repoint_uid()

    @property
    def logical_input_id(self) -> int:
        return self._logical_input_id

    @logical_input_id.setter
    def logical_input_id(self, value: int) -> None:
        self._logical_input_id = value
        self._repoint_uid()

    @property
    def logical_input_uid(self) -> str | None:
        """Permanent id of the control this action drives (None: unknown)."""
        return self._logical_input_uid

    def _repoint_uid(self) -> None:
        if hasattr(self, "_logical_input_id"):
            self._logical_input_uid = LogicalDevice().uid_of(
                self._logical_input_type, int(self._logical_input_id)
            )

    @property
    def logical_missing(self) -> bool:
        """The saved control isn't on the Logical Device (D-04-LD-FILE)."""
        identifier, _ = resolve_logical_reference(
            self._logical_input_uid, self._logical_input_type, self._logical_input_id
        )
        return identifier is None

    @override
    def references(self) -> Iterable[references.Reference]:
        target = references.input_ref(
            ids.LOGICAL_DEVICE, self.logical_input_type, self.logical_input_id
        )
        missing = output.logical_cant_send_text(self)
        return (
            references.Reference(
                "sends-output", target, not_found=bool(missing), why=missing or ""
            ),
        )

    @override
    def _from_xml(self, node: ElementTree.Element, library: Library) -> None:
        self._id = util.read_action_id(node)
        saved_id = util.read_property(node, "logical-input-id", PropertyType.Int)
        saved_type = util.read_property(
            node, "logical-input-type", PropertyType.InputType
        )
        saved_uid = util.read_property(
            node, "logical-input-uid", PropertyType.String, ""
        )
        identifier, uid = resolve_logical_reference(saved_uid, saved_type, saved_id)
        if identifier is not None:
            saved_type, saved_id = identifier.type, identifier.id
        self._logical_input_type = saved_type
        self._logical_input_id = saved_id
        self._logical_input_uid = uid
        if self.logical_input_type == InputType.JoystickAxis:
            self.axis_mode = util.read_property(
                node, "axis-mode", PropertyType.AxisMode
            )
            self.axis_scaling = util.read_property(
                node, "axis-scaling", PropertyType.Float
            )
        if self.logical_input_type == InputType.JoystickButton:
            self.button_inverted = util.read_property(
                node, "button-inverted", PropertyType.Bool
            )

    @override
    def _to_xml(self) -> ElementTree.Element:
        node = util.create_action_node(MapToLogicalDeviceData.tag, self._id)
        node.append(
            util.create_property_node(
                "logical-input-id", self.logical_input_id, PropertyType.Int
            )
        )
        node.append(
            util.create_property_node(
                "logical-input-type", self.logical_input_type, PropertyType.InputType
            )
        )
        if self._logical_input_uid:
            node.append(
                util.create_property_node(
                    "logical-input-uid", self._logical_input_uid, PropertyType.String
                )
            )
        if self.logical_input_type == InputType.JoystickAxis:
            node.append(
                util.create_property_node(
                    "axis-mode", self.axis_mode, PropertyType.AxisMode
                )
            )
            node.append(
                util.create_property_node(
                    "axis-scaling", self.axis_scaling, PropertyType.Float
                )
            )
        if self.logical_input_type == InputType.JoystickButton:
            node.append(
                util.create_property_node(
                    "button-inverted", self.button_inverted, PropertyType.Bool
                )
            )
        return node

    @override
    def user_feedback(self) -> List[UserFeedback]:
        return []

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
        self.logical_input_type = new_behavior


create = MapToLogicalDeviceData
