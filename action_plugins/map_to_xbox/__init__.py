# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, override
from xml.etree import ElementTree

from PySide6 import QtCore

from gremlin import event_handler, signal, util
from gremlin.base_classes import (
    AbstractActionData,
    AbstractFunctor,
    UserFeedback,
    Value,
)
from gremlin.modules import output
from gremlin.profile import Library
from gremlin.types import (
    ActionProperty,
    HatDirection,
    InputType,
    PropertyType,
)
from gremlin.ui.action_model import ActionModel, SequenceIndex
from vigem.xbox import XboxError, XboxTarget

if TYPE_CHECKING:
    from gremlin.ui.profile import InputItemBindingModel

_LOG = logging.getLogger("event")


def _default_target(behavior: InputType) -> XboxTarget:
    if behavior == InputType.JoystickAxis:
        return XboxTarget.LEFT_STICK_X
    if behavior == InputType.JoystickHat:
        return XboxTarget.DPAD
    return XboxTarget.A


TRIGGER_FULL = "full"
TRIGGER_UPPER = "upper"


def _is_pressed(current: object) -> bool:
    """A hat is pressed when it is off center.

    A centered hat is (0, 0), which bool() calls true.
    """
    if isinstance(current, HatDirection):
        return current != HatDirection.Center
    if isinstance(current, tuple):
        return any(part != 0 for part in current)
    return bool(current)


def _trigger_value(current: object, trigger_range: str) -> float:
    """Axis value for a trigger. Upper half: rest at 0 is 0% and +1 is 100%.
    A button, key or hat: pressed is a full pull, released none (it used to
    rest at 50%, its False read as the axis middle)."""
    if isinstance(current, (bool, HatDirection, tuple)):
        return 1.0 if _is_pressed(current) else -1.0
    if trigger_range == TRIGGER_UPPER:
        return util.clamp(float(current), 0.0, 1.0) * 2.0 - 1.0
    return float(current)


def _stick_value(current: object, target: XboxTarget) -> float:
    """Stick position. A hat moves it in the hat's direction: on an X target
    left -1 / right +1, on a Y target up +1 / down -1 (it used to fail)."""
    hat = current.value if isinstance(current, HatDirection) else current
    if isinstance(hat, tuple) and len(hat) == 2:
        x, y = hat
        is_y = target in (XboxTarget.LEFT_STICK_Y, XboxTarget.RIGHT_STICK_Y)
        return float(y if is_y else x)
    return float(current)  # type: ignore[arg-type]


# The Xbox controls an input can drive: an axis moves sticks and triggers; a
# button or key presses buttons and pulls triggers; a hat drives the D-pad,
# its directions and sticks.
_KINDS_FOR_INPUT = {
    InputType.JoystickAxis: {"stick", "trigger"},
    InputType.JoystickButton: {"button", "trigger"},
    InputType.Keyboard: {"button", "trigger"},
    InputType.JoystickHat: {"hat", "button", "stick"},
}


def targets_for(behavior: InputType) -> list[XboxTarget]:
    """The Xbox controls that make sense for this input."""
    kinds = _KINDS_FOR_INPUT.get(behavior)
    return [t for t in XboxTarget if kinds is None or t.kind in kinds]


def _read_xml_property(node: ElementTree.Element, name: str, ptype: PropertyType, default):
    # A missing property (older profiles) quietly takes the default.
    try:
        return util.read_property(node, name, ptype, default)
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
        # The Xbox output module passes only the controls it claims.
        pad_id = self.data.xbox_device_id
        target = self.data.xbox_target
        try:
            if target.kind == "button":
                pressed = _is_pressed(value.current)
                if self.data.button_inverted:
                    pressed = not pressed
                output.write_xbox(pad_id, target, pressed)
            elif target.kind == "trigger":
                raw = _trigger_value(value.current, self.data.trigger_range)
                output.write_xbox(pad_id, target, raw)
            elif target.kind == "stick":
                output.write_xbox(pad_id, target, _stick_value(value.current, target))
            else:
                output.write_xbox(pad_id, target, value.current)
        except Exception as exc:
            _LOG.error("Map to Xbox failed: %s", exc)


class MapToXboxModel(ActionModel):
    xboxDeviceIdChanged = QtCore.Signal()
    xboxTargetChanged = QtCore.Signal()
    buttonInvertedChanged = QtCore.Signal()
    triggerRangeChanged = QtCore.Signal()
    targetChoicesChanged = QtCore.Signal()
    padChoicesChanged = QtCore.Signal()

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
        self.targetChoicesChanged.emit()
        self.padChoicesChanged.emit()
        self._notify_item()

    def _get_xbox_target(self) -> str:
        return self._data.xbox_target.value

    def _set_xbox_target(self, target: str) -> None:
        parsed = XboxTarget.from_string(target)
        if parsed == self._data.xbox_target:
            return
        self._data.xbox_target = parsed
        self.xboxTargetChanged.emit()
        self.targetChoicesChanged.emit()
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

    def _get_trigger_range(self) -> str:
        return self._data.trigger_range

    def _set_trigger_range(self, trigger_range: str) -> None:
        value = TRIGGER_UPPER if trigger_range == TRIGGER_UPPER else TRIGGER_FULL
        if value == self._data.trigger_range:
            return
        self._data.trigger_range = value
        self.triggerRangeChanged.emit()
        self._notify_item()

    def _get_target_choices(self) -> list:
        """The Xbox controls this input can drive (targets_for); a saved
        target outside them stays listed so the action keeps working."""
        items = targets_for(self._data.behavior_type)
        if self._data.xbox_target not in items:
            items = [*items, self._data.xbox_target]
        return [{"value": item.value, "label": item.label} for item in items]

    def _get_pad_choices(self) -> list:
        """The Xbox output module(s) by name. Pad 1 is always there; a saved
        pad 2-4 stays listed and still sends (one pad for now, to-do 16)."""
        names = {pad: module.name for pad, module in output.xbox_modules().items()}
        names.setdefault(1, "Xbox 360 Controller")
        current = int(self._data.xbox_device_id)
        names.setdefault(current, f"Xbox pad {current}")
        return [{"value": pad, "label": name} for pad, name in sorted(names.items())]

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
    triggerRange = QtCore.Property(
        str,
        fget=_get_trigger_range,
        fset=_set_trigger_range,
        notify=triggerRangeChanged,
    )
    targetChoices = QtCore.Property(
        "QVariant", fget=_get_target_choices, notify=targetChoicesChanged
    )
    padChoices = QtCore.Property(
        "QVariant", fget=_get_pad_choices, notify=padChoicesChanged
    )


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
        self.trigger_range = TRIGGER_FULL

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
        trigger_range = _read_xml_property(
            node, "trigger-range", PropertyType.String, TRIGGER_FULL
        )
        self.trigger_range = (
            TRIGGER_UPPER if str(trigger_range) == TRIGGER_UPPER else TRIGGER_FULL
        )

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
        node.append(
            util.create_property_node(
                "trigger-range", self.trigger_range, PropertyType.String
            )
        )
        return node

    @override
    def user_feedback(self) -> List[UserFeedback]:
        # Warning only. An Error makes is_valid() false, and an explicit
        # profile save then drops the action. A warning does not.
        if not output.xbox_available():
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
