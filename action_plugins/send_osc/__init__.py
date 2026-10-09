# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Send OSC: sends one OSC message to a target, or back to the last sender
(decision D-09-OSC-OUTPUT). Sends only while a profile runs."""

from __future__ import annotations

import json
from typing import (
    TYPE_CHECKING,
    List,
    cast,
    override,
)
from xml.etree import ElementTree

from PySide6 import QtCore

from gremlin import (
    event_handler,
    osc_output,
    util,
)
from gremlin.base_classes import (
    AbstractActionData,
    AbstractFunctor,
    UserFeedback,
    Value,
)
from gremlin.error import GremlinError
from gremlin.profile import Library
from gremlin.types import (
    ActionActivationMode,
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

FIXED = "fixed"
INPUT = "input"


def clean_values(raw: object) -> list[dict]:
    """Values as {source: fixed|input, value: str, type: auto|int|...}."""
    out = []
    for entry in raw if isinstance(raw, list) else []:
        if not isinstance(entry, dict):
            continue
        source = INPUT if entry.get("source") == INPUT else FIXED
        kind = str(entry.get("type") or "auto")
        out.append(
            {
                "source": source,
                "value": "" if entry.get("value") is None else str(entry["value"]),
                "type": kind if kind in osc_output.VALUE_TYPES else "auto",
            }
        )
    return out


def _first_target() -> str:
    try:
        from gremlin import osc_device_file

        targets = osc_device_file.read_targets()
    except Exception:
        targets = []
    return str(targets[0]["id"]) if targets else osc_output.REPLY


class SendOscFunctor(AbstractFunctor):
    def __init__(self, instance: SendOscData) -> None:
        super().__init__(instance)
        self._osc = instance

    def input_value(self, value: Value) -> float:
        """A button gives 1 or 0; an axis (-1..1) is scaled to min..max."""
        current = value.current
        if isinstance(current, bool):
            return 1.0 if current else 0.0
        try:
            position = (float(current) + 1.0) / 2.0  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 0.0
        low, high = self._osc.input_min, self._osc.input_max
        return low + max(0.0, min(1.0, position)) * (high - low)

    @override
    def __call__(
        self,
        event: event_handler.Event,
        value: Value,
        properties: List[ActionProperty] = [],
    ) -> None:
        if isinstance(value.current, bool):
            if not self._should_execute(value):
                return
        elif self.data.activation_mode == ActionActivationMode.Deactivated:
            return
        values = []
        types = []
        for entry in self._osc.values:
            if entry["source"] == INPUT:
                values.append(self.input_value(value))
            else:
                values.append(entry["value"])
            types.append(entry["type"])
        osc_output.send(self._osc.target, self._osc.address, values, types)


class SendOscModel(ActionModel):
    targetChanged = QtCore.Signal()
    addressChanged = QtCore.Signal()
    valuesChanged = QtCore.Signal()
    inputMinChanged = QtCore.Signal()
    inputMaxChanged = QtCore.Signal()

    def __init__(
        self,
        data: AbstractActionData,
        binding_model: InputItemBindingModel,
        action_index: SequenceIndex,
        parent_index: SequenceIndex,
        parent: QtCore.QObject,
    ) -> None:
        super().__init__(data, binding_model, action_index, parent_index, parent)

    @property
    def _osc(self) -> SendOscData:
        return cast("SendOscData", self._data)

    def _qml_path_impl(self) -> str:
        return (
            "file:///"
            + QtCore.QFile("core_plugins:send_osc/SendOscAction.qml").fileName()
        )

    def _action_behavior(self) -> str:
        return str(
            self._binding_model.get_action_model_by_sidx(
                self._parent_sequence_index.index
            ).actionBehavior
        )

    @QtCore.Property(list, notify=targetChanged)
    def targetChoices(self) -> list:
        """[{id, name}] of every target, then "Reply to sender"."""
        try:
            from gremlin import osc_device_file

            targets = osc_device_file.read_targets()
        except Exception:
            targets = []
        choices = []
        for t in targets:
            name = t.get("name") or "Target"
            where = f"{t.get('host')}:{t.get('port')}"
            choices.append({"id": str(t["id"]), "name": f"{name} ({where})"})
        choices.append({"id": osc_output.REPLY, "name": "Reply to sender"})
        if self._osc.target not in [c["id"] for c in choices]:
            choices.append({"id": self._osc.target, "name": "Missing target"})
        return choices

    def _get_target(self) -> str:
        return self._osc.target

    def _set_target(self, value: str) -> None:
        if str(value) != self._osc.target:
            self._osc.target = str(value)
            self.targetChanged.emit()

    def _get_address(self) -> str:
        return self._osc.address

    def _set_address(self, value: str) -> None:
        if str(value) != self._osc.address:
            self._osc.address = str(value)
            self.addressChanged.emit()

    def _get_values(self) -> list:
        return [dict(v) for v in self._osc.values]

    def _put_values(self, values: list) -> None:
        cleaned = clean_values(values)
        if cleaned != self._osc.values:
            self._osc.values = cleaned
            self.valuesChanged.emit()

    @QtCore.Slot()
    def addValue(self) -> None:
        self._put_values(
            self._get_values() + [{"source": FIXED, "value": "1", "type": "auto"}]
        )

    @QtCore.Slot(int)
    def removeValue(self, index: int) -> None:
        values = self._get_values()
        if 0 <= index < len(values):
            del values[index]
            self._put_values(values)

    @QtCore.Slot(int, str, str)
    def setValueField(self, index: int, field: str, text: str) -> None:
        values = self._get_values()
        if 0 <= index < len(values) and field in ("source", "value", "type"):
            values[index][field] = text
            self._put_values(values)

    def _get_input_min(self) -> float:
        return self._osc.input_min

    def _set_input_min(self, value: float) -> None:
        if float(value) != self._osc.input_min:
            self._osc.input_min = float(value)
            self.inputMinChanged.emit()

    def _get_input_max(self) -> float:
        return self._osc.input_max

    def _set_input_max(self, value: float) -> None:
        if float(value) != self._osc.input_max:
            self._osc.input_max = float(value)
            self.inputMaxChanged.emit()

    target = QtCore.Property(
        str, fget=_get_target, fset=_set_target, notify=targetChanged
    )
    address = QtCore.Property(
        str, fget=_get_address, fset=_set_address, notify=addressChanged
    )
    values = QtCore.Property(list, fget=_get_values, notify=valuesChanged)
    inputMin = QtCore.Property(
        float, fget=_get_input_min, fset=_set_input_min, notify=inputMinChanged
    )
    inputMax = QtCore.Property(
        float, fget=_get_input_max, fset=_set_input_max, notify=inputMaxChanged
    )


class SendOscData(AbstractActionData):
    """Sends an OSC message (D-09-OSC-OUTPUT)."""

    version = 1
    name = "Send OSC"
    tag = "send-osc"
    icon = ""

    functor = SendOscFunctor
    model = SendOscModel

    properties = (ActionProperty.ActivateOnPress,)
    input_types = (
        InputType.JoystickAxis,
        InputType.JoystickButton,
        InputType.Keyboard,
    )

    def __init__(self, behavior_type: InputType = InputType.JoystickButton) -> None:
        super().__init__(behavior_type)

        # Model variables
        self.target: str = _first_target()
        self.address: str = ""
        self.values: list[dict] = [{"source": INPUT, "value": "", "type": "auto"}]
        self.input_min: float = 0.0
        self.input_max: float = 1.0

    @override
    def _from_xml(self, node: ElementTree.Element, library: Library) -> None:
        self._id = util.read_action_id(node)
        self.target = util.read_property(
            node, "target", PropertyType.String, osc_output.REPLY
        )
        self.address = util.read_property(node, "address", PropertyType.String, "")
        try:
            raw = json.loads(
                util.read_property(node, "values", PropertyType.String, "[]") or "[]"
            )
        except ValueError:
            raw = []
        self.values = clean_values(raw)
        self.input_min = util.read_property(
            node, "input-min", PropertyType.Float, 0.0
        )
        self.input_max = util.read_property(
            node, "input-max", PropertyType.Float, 1.0
        )

    @override
    def _to_xml(self) -> ElementTree.Element:
        node = util.create_action_node(SendOscData.tag, self._id)
        util.append_property_nodes(
            node,
            [
                ["target", self.target, PropertyType.String],
                ["address", self.address, PropertyType.String],
                ["values", json.dumps(self.values), PropertyType.String],
                ["input-min", self.input_min, PropertyType.Float],
                ["input-max", self.input_max, PropertyType.Float],
            ],
        )
        return node

    @override
    def user_feedback(self) -> List[UserFeedback]:
        if not self.address.strip().startswith("/"):
            return [
                UserFeedback(
                    UserFeedback.FeedbackType.Error,
                    "An OSC address starts with /.",
                )
            ]
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
        pass


create = SendOscData
