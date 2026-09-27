# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, override
from xml.etree import ElementTree

from PySide6 import QtCore

from gremlin import event_handler, signal, util
from gremlin.base_classes import AbstractActionData, AbstractFunctor, UserFeedback, Value
from gremlin.profile import Library
from gremlin.types import ActionProperty, InputType, PropertyType
from gremlin.ui.action_model import ActionModel, SequenceIndex
from vigem.xbox import XboxError, XboxProxy, XboxTarget

if TYPE_CHECKING:
    from gremlin.ui.profile import InputItemBindingModel

_LOG = logging.getLogger("event")


def _default_target(behavior: InputType) -> XboxTarget:
    if behavior == InputType.JoystickAxis:
        return XboxTarget.LEFT_STICK_X
    if behavior == InputType.JoystickHat:
        return XboxTarget.DPAD
    return XboxTarget.A


def _read_xml_property(node: ElementTree.Element, name: str, ptype: PropertyType, default):
    try:
        return util.read_property(node, name, ptype)
    except Exception:
        return default


class MapToXboxFunctor(AbstractFunctor):
    def __init__(self, action: MapToXboxData) -> None:
        super().__init__(action)

    @override
    def __call__(
        self,
        event: event_handler.Event,
        value: Value,
        properties: list[ActionProperty] = [],
    ) -> None:
        if not self._should_execute(value):
            return
        try:
            pad = XboxProxy()[self.data.xbox_device_id]
            target = self.data.xbox_target
            if target.kind == "button":
                pressed = bool(value.current)
                if self.data.button_inverted:
                    pressed = not pressed
                pad.apply(target, pressed)
            else:
                pad.apply(target, value.current)
        except Exception as exc:
            _LOG.error("Map to Xbox failed: %s", exc)


class MapToXboxModel(ActionModel):
    xboxDeviceIdChanged = QtCore.Signal()
    xboxTargetChanged = QtCore.Signal()
    buttonInvertedChanged = QtCore.Signal()

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
            + QtCore.QFile("core_plugins:map_to_xbox/MapToXboxAction.qml").fileName()
        )

    def _action_behavior(self) -> str:
        return self._binding_model.get_action_model_by_sidx(
            self._parent_sequence_index.index
        ).actionBehavior

    def _notify_item(self) -> None:
        try:
            signal.signal.inputItemChanged.emit(
                self._binding_model.parent().enumeration_index
            )
        except Exception:
            pass

    def _get_xbox_device_id(self) -> int:
        return self._data.xbox_device_id

    def _set_xbox_device_id(self, xbox_device_id: int) -> None:
        ident = int(xbox_device_id)
        if ident == self._data.xbox_device_id:
            return
        self._data.xbox_device_id = ident
        self.xboxDeviceIdChanged.emit()
        self._notify_item()

    def _get_xbox_target(self) -> str:
        return self._data.xbox_target.value

    def _set_xbox_target(self, target: str) -> None:
        parsed = XboxTarget.from_string(target)
        if parsed == self._data.xbox_target:
            return
        self._data.xbox_target = parsed
        self.xboxTargetChanged.emit()
        self._notify_item()

    def _get_xbox_target_kind(self) -> str:
        return self._data.xbox_target.kind

    def _get_button_inverted(self) -> bool:
        return self._data.button_inverted

    def _set_button_inverted(self, button_inverted: bool) -> None:
        if button_inverted == self._data.button_inverted:
            return
        self._data.button_inverted = button_inverted
        self.buttonInvertedChanged.emit()
        self._notify_item()

    def _get_target_choices(self) -> list:
        return [{"value": item.value, "label": item.label} for item in XboxTarget]

    xboxDeviceId = QtCore.Property(
        int,
        fget=_get_xbox_device_id,
        fset=_set_xbox_device_id,
        notify=xboxDeviceIdChanged,
    )
    xboxTarget = QtCore.Property(
        str, fget=_get_xbox_target, fset=_set_xbox_target, notify=xboxTargetChanged
    )
    xboxTargetKind = QtCore.Property(
        str, fget=_get_xbox_target_kind, notify=xboxTargetChanged
    )
    buttonInverted = QtCore.Property(
        bool,
        fget=_get_button_inverted,
        fset=_set_button_inverted,
        notify=buttonInvertedChanged,
    )
    targetChoices = QtCore.Property("QVariant", fget=_get_target_choices, constant=True)


class MapToXboxData(AbstractActionData):
    version = 1
    name = "Map to Xbox"
    tag = "map-to-xbox"
    icon = "\uf11b"

    functor = MapToXboxFunctor
    model = MapToXboxModel

    properties = (ActionProperty.ActivateOnBoth,)
    input_types = (
        InputType.JoystickAxis,
        InputType.JoystickButton,
        InputType.JoystickHat,
        InputType.Keyboard,
    )

    def __init__(self, behavior_type: InputType = InputType.JoystickButton) -> None:
        super().__init__(behavior_type)
        self.xbox_device_id = 1
        self.xbox_target = _default_target(behavior_type)
        self.button_inverted = False

    @classmethod
    @override
    def can_create(cls) -> bool:
        return True

    @override
    def _from_xml(self, node: ElementTree.Element, library: Library) -> None:
        self._id = util.read_action_id(node)
        ident = _read_xml_property(node, "xbox-device-id", PropertyType.Int, 1)
        try:
            ident = int(ident)
        except Exception:
            ident = 1
        self.xbox_device_id = max(1, min(4, ident))
        raw_target = _read_xml_property(
            node, "xbox-target", PropertyType.String, _default_target(self.behavior_type).value
        )
        try:
            self.xbox_target = XboxTarget.from_string(str(raw_target))
        except Exception:
            self.xbox_target = _default_target(self.behavior_type)
        inverted = _read_xml_property(
            node, "button-inverted", PropertyType.Bool, False
        )
        self.button_inverted = bool(inverted)

    @override
    def _to_xml(self) -> ElementTree.Element:
        node = util.create_action_node(MapToXboxData.tag, self._id)
        node.append(
            util.create_property_node(
                "xbox-device-id", self.xbox_device_id, PropertyType.Int
            )
        )
        node.append(
            util.create_property_node(
                "xbox-target", self.xbox_target.value, PropertyType.String
            )
        )
        node.append(
            util.create_property_node(
                "button-inverted", self.button_inverted, PropertyType.Bool
            )
        )
        return node

    @override
    def user_feedback(self) -> List[UserFeedback]:
        # Warning only. An Error makes is_valid() false, and an explicit
        # profile save then drops the action. A warning does not.
        if not XboxProxy().available():
            return [
                UserFeedback(
                    UserFeedback.FeedbackType.Warning,
                    "ViGEmBus / ViGEmClient.dll not available. "
                    "Install ViGEmBus 1.22.0 and place ViGEmClient.dll in vigem/.",
                )
            ]
        return []

    @override
    def _valid_selectors(self) -> List[str]:
        return []

    @override
    def _get_container(self, selector: str) -> List[AbstractActionData]:
        raise XboxError(f"{self.name}: has no containers")

    @override
    def _handle_behavior_change(
        self, old_behavior: InputType, new_behavior: InputType
    ) -> None:
        self.xbox_target = _default_target(new_behavior)


create = MapToXboxData
