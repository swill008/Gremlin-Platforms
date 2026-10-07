# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""What Merge Axis and Dual Axis Deadzone share: the two axes they read, kept
as plain values in the action data (05 RB7), and the editor's instance pick
list, "+" and switching (05 RB14)."""

from __future__ import annotations

import dataclasses
import uuid
from typing import TYPE_CHECKING, Any, cast

from gremlin import util
from gremlin.types import InputType
from gremlin.ui.device import InputIdentifier
from gremlin.ui.profile import LabelValueSelectionModel

if TYPE_CHECKING:
    from gremlin.ui.action_model import ActionModel


@dataclasses.dataclass
class AxisRef:
    """An input as action data keeps it: no Qt type in the data."""

    device_guid: uuid.UUID | None = None
    input_type: InputType | None = None
    input_id: int | uuid.UUID | None = None

    @classmethod
    def of(cls, source: Any) -> AxisRef:  # noqa: ANN401
        """A copy of any input identifier (an InputIdentifier from a page)."""
        if source is None:
            return cls()
        return cls(
            getattr(source, "device_guid", None),
            getattr(source, "input_type", None),
            getattr(source, "input_id", None),
        )

    @property
    def is_valid(self) -> bool:
        return is_set(self)

    def __eq__(self, other: object) -> bool:
        return (
            self.device_guid == getattr(other, "device_guid", None)
            and self.input_type == getattr(other, "input_type", None)
            and self.input_id == getattr(other, "input_id", None)
        )


def is_set(ref: Any) -> bool:  # noqa: ANN401
    """The axis is chosen (device, type and id all set)."""
    return (
        getattr(ref, "device_guid", None) is not None
        and getattr(ref, "input_type", None) is not None
        and getattr(ref, "input_id", None) is not None
    )


class AxisView:
    """The QML side of one AxisRef: one InputIdentifier per editor axis,
    kept up to date (a new QObject on every read would pile up)."""

    def __init__(self, parent: ActionModel) -> None:
        self._view = InputIdentifier(parent=parent)

    def show(self, ref: Any) -> InputIdentifier:  # noqa: ANN401
        fields = (
            getattr(ref, "device_guid", None),
            getattr(ref, "input_type", None),
            getattr(ref, "input_id", None),
        )
        view = self._view
        if (view.device_guid, view.input_type, view.input_id) != fields:
            view.device_guid, view.input_type, view.input_id = fields
            view.changed.emit()
        return view


def pick_list(model: ActionModel, data_cls: type) -> LabelValueSelectionModel:
    """The instances the editor offers: the one shown, those in the input
    being edited (the pane edits copies; "+" makes one no input uses yet)
    and those an input uses, by label."""
    actions = sorted(
        model.library.pick_list(
            lambda a: isinstance(a, data_cls),
            model.action_data,
            model._binding_model.input_item_binding.input_item,
        ),
        key=lambda x: getattr(x, "label", ""),
    )
    return LabelValueSelectionModel(
        [getattr(a, "label", "") for a in actions],
        [str(a.id) for a in actions],
        parent=model,
    )


def new_instance(model: ActionModel, data_cls: type) -> Any | None:  # noqa: ANN401
    """"+": always a new one, added by the library and numbered after the
    action's name ("Merge Axis 2"), so each has its own name (05 Q14)."""
    action: Any = model.library.create(
        data_cls.name, model._binding_model.behavior_type, reuse=False
    )
    if action is None:
        return None
    taken = {getattr(a, "label", "") for a in model.library.actions_by_type(data_cls)}
    number = 1
    while f"{data_cls.name} {number}" in taken:
        number += 1
    action.label = f"{data_cls.name} {number}"
    return action


def switch_instance(model: ActionModel, uuid_str: str, axes: tuple[str, str]) -> None:
    """Shows another instance in the editor's place.

    The one left has this input taken off its axes (axes: the data's two
    attribute names), unless another input still uses it: clearing an axis
    would leave it unfinished there, and a save would drop it.
    """
    data = model.action_data
    if util.parse_id_or_uuid(uuid_str) == data.id:
        return
    item = model._binding_model.input_item_binding.input_item
    here = AxisRef(item.device_id, item.input_type, cast(int, item.input_id))
    if not model.library.used_elsewhere(data, item):
        for name in axes:
            if here == getattr(data, name):
                setattr(data, name, AxisRef())

    # Put the picked one in its place; a shared one is edited as a copy
    # until OK (decision A4).
    action_id = cast(uuid.UUID, util.parse_id_or_uuid(uuid_str))
    picked = model.adopt_action(model.library.get_action(action_id))
    model._binding_model.append_action(picked, model.sequence_index)
    model._binding_model.remove_action(model.sequence_index)
    model._binding_model.rootActionChanged.emit()
