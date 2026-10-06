# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import logging
import time
import uuid
from typing import (
    TYPE_CHECKING,
    Any,
    cast,
    override,
)

from PySide6 import QtCore

import dill
import gremlin.profile
import gremlin.ui.type_aliases as ta
from gremlin import (
    action_analysis,
    common,
    device_initialization,
    event_handler,
    shared_state,
    swap_devices,
    tree,
)
from gremlin.error import GremlinError
from gremlin.signal import signal
from gremlin.types import (
    AxisButtonDirection,
    DataInsertionMode,
    HatDirection,
    InputType,
)
from gremlin.ui.action_model import (
    ActionModel,
    SequenceIndex,
)
from gremlin.util import clamp

if TYPE_CHECKING:
    from action_plugins.root import RootModel
    from gremlin.base_classes import AbstractActionData


QML_IMPORT_NAME = "Gremlin.Profile"
QML_IMPORT_MAJOR_VERSION = 1


@ta.QmlElement
class VirtualButtonModel(QtCore.QObject):
    """Represents both axis and hat virtual buttons."""

    lowerLimitChanged = QtCore.Signal()
    upperLimitChanged = QtCore.Signal()
    directionChanged = QtCore.Signal()
    hatDirectionChanged = QtCore.Signal()

    def __init__(
        self,
        virtual_button: gremlin.profile.AbstractVirtualButton,
        parent: ta.OQO = None,
    ) -> None:
        """Creates a new instance.

        Args:
            virtual_button: the profile class representing the instance's data
            parent: parent object of the widget
        """
        super().__init__(parent)

        self.virtual_button = virtual_button

    def _get_lower_limit(self) -> float:
        return self.virtual_button.lower_limit

    def _set_lower_limit(self, value: float) -> None:
        if value != self.virtual_button.lower_limit:
            self.virtual_button.lower_limit = clamp(value, -1.0, 1.0)
            self.lowerLimitChanged.emit()

    def _get_upper_limit(self) -> float:
        return self.virtual_button.upper_limit

    def _set_upper_limit(self, value: float) -> None:
        if value != self.virtual_button.upper_limit:
            self.virtual_button.upper_limit = clamp(value, -1.0, 1.0)
            self.upperLimitChanged.emit()

    def _get_direction(self) -> str:
        return AxisButtonDirection.to_string(self.virtual_button.direction)

    def _set_direction(self, value: str) -> None:
        direction = AxisButtonDirection.to_enum(value.lower())
        if direction != self.virtual_button.direction:
            self.virtual_button.direction = direction
            self.directionChanged.emit()

    def _get_hat_state(self, hat_direction: HatDirection) -> bool:
        return hat_direction in self.virtual_button.directions

    def _set_hat_state(self, hat_direction: HatDirection, is_active: bool) -> None:
        if is_active:
            if hat_direction not in self.virtual_button.directions:
                self.virtual_button.directions.append(hat_direction)
                self.hatDirectionChanged.emit()
        else:
            if hat_direction in self.virtual_button.directions:
                index = self.virtual_button.directions.index(hat_direction)
                del self.virtual_button.directions[index]
                self.hatDirectionChanged.emit()

    lowerLimit = QtCore.Property(
        float, fget=_get_lower_limit, fset=_set_lower_limit, notify=lowerLimitChanged
    )
    upperLimit = QtCore.Property(
        float, fget=_get_upper_limit, fset=_set_upper_limit, notify=upperLimitChanged
    )
    direction = QtCore.Property(
        str, fget=_get_direction, fset=_set_direction, notify=directionChanged
    )

    hatNorth = QtCore.Property(
        bool,
        fget=lambda cls: VirtualButtonModel._get_hat_state(cls, HatDirection.North),
        fset=lambda cls, x: VirtualButtonModel._set_hat_state(
            cls, HatDirection.North, x
        ),
        notify=hatDirectionChanged,
    )
    hatNorthEast = QtCore.Property(
        bool,
        fget=lambda cls: VirtualButtonModel._get_hat_state(cls, HatDirection.NorthEast),
        fset=lambda cls, x: VirtualButtonModel._set_hat_state(
            cls, HatDirection.NorthEast, x
        ),
        notify=hatDirectionChanged,
    )
    hatEast = QtCore.Property(
        bool,
        fget=lambda cls: VirtualButtonModel._get_hat_state(cls, HatDirection.East),
        fset=lambda cls, x: VirtualButtonModel._set_hat_state(
            cls, HatDirection.East, x
        ),
        notify=hatDirectionChanged,
    )
    hatSouthEast = QtCore.Property(
        bool,
        fget=lambda cls: VirtualButtonModel._get_hat_state(cls, HatDirection.SouthEast),
        fset=lambda cls, x: VirtualButtonModel._set_hat_state(
            cls, HatDirection.SouthEast, x
        ),
        notify=hatDirectionChanged,
    )
    hatSouth = QtCore.Property(
        bool,
        fget=lambda cls: VirtualButtonModel._get_hat_state(cls, HatDirection.South),
        fset=lambda cls, x: VirtualButtonModel._set_hat_state(
            cls, HatDirection.South, x
        ),
        notify=hatDirectionChanged,
    )
    hatSouthWest = QtCore.Property(
        bool,
        fget=lambda cls: VirtualButtonModel._get_hat_state(cls, HatDirection.SouthWest),
        fset=lambda cls, x: VirtualButtonModel._set_hat_state(
            cls, HatDirection.SouthWest, x
        ),
        notify=hatDirectionChanged,
    )
    hatWest = QtCore.Property(
        bool,
        fget=lambda cls: VirtualButtonModel._get_hat_state(cls, HatDirection.West),
        fset=lambda cls, x: VirtualButtonModel._set_hat_state(
            cls, HatDirection.West, x
        ),
        notify=hatDirectionChanged,
    )
    hatNorthWest = QtCore.Property(
        bool,
        fget=lambda cls: VirtualButtonModel._get_hat_state(cls, HatDirection.NorthWest),
        fset=lambda cls, x: VirtualButtonModel._set_hat_state(
            cls, HatDirection.NorthWest, x
        ),
        notify=hatDirectionChanged,
    )


@ta.QmlElement
class HatDirectionModel(QtCore.QObject):
    """QML model representing the directions of a hat."""

    directionsChanged = QtCore.Signal()

    def __init__(self, directions: list[HatDirection], parent: ta.OQO = None) -> None:
        super().__init__(parent)

        self.directions = directions

    def _get_hat_state(self, direction: HatDirection) -> bool:
        return direction in self.directions

    def _set_hat_state(self, direction: HatDirection, is_active: bool) -> None:
        if is_active:
            if direction not in self.directions:
                self.directions.append(direction)
                self.directionsChanged.emit()
        else:
            if direction in self.directions:
                index = self.directions.index(direction)
                del self.directions[index]
                self.directionsChanged.emit()

    hatNorth = QtCore.Property(
        bool,
        fget=lambda cls: HatDirectionModel._get_hat_state(cls, HatDirection.North),
        fset=lambda cls, x: HatDirectionModel._set_hat_state(
            cls, HatDirection.North, x
        ),
        notify=directionsChanged,
    )
    hatNorthEast = QtCore.Property(
        bool,
        fget=lambda cls: HatDirectionModel._get_hat_state(cls, HatDirection.NorthEast),
        fset=lambda cls, x: HatDirectionModel._set_hat_state(
            cls, HatDirection.NorthEast, x
        ),
        notify=directionsChanged,
    )
    hatEast = QtCore.Property(
        bool,
        fget=lambda cls: HatDirectionModel._get_hat_state(cls, HatDirection.East),
        fset=lambda cls, x: HatDirectionModel._set_hat_state(cls, HatDirection.East, x),
        notify=directionsChanged,
    )
    hatSouthEast = QtCore.Property(
        bool,
        fget=lambda cls: HatDirectionModel._get_hat_state(cls, HatDirection.SouthEast),
        fset=lambda cls, x: HatDirectionModel._set_hat_state(
            cls, HatDirection.SouthEast, x
        ),
        notify=directionsChanged,
    )
    hatSouth = QtCore.Property(
        bool,
        fget=lambda cls: HatDirectionModel._get_hat_state(cls, HatDirection.South),
        fset=lambda cls, x: HatDirectionModel._set_hat_state(
            cls, HatDirection.South, x
        ),
        notify=directionsChanged,
    )
    hatSouthWest = QtCore.Property(
        bool,
        fget=lambda cls: HatDirectionModel._get_hat_state(cls, HatDirection.SouthWest),
        fset=lambda cls, x: HatDirectionModel._set_hat_state(
            cls, HatDirection.SouthWest, x
        ),
        notify=directionsChanged,
    )
    hatWest = QtCore.Property(
        bool,
        fget=lambda cls: HatDirectionModel._get_hat_state(cls, HatDirection.West),
        fset=lambda cls, x: HatDirectionModel._set_hat_state(cls, HatDirection.West, x),
        notify=directionsChanged,
    )
    hatNorthWest = QtCore.Property(
        bool,
        fget=lambda cls: HatDirectionModel._get_hat_state(cls, HatDirection.NorthWest),
        fset=lambda cls, x: HatDirectionModel._set_hat_state(
            cls, HatDirection.NorthWest, x
        ),
        notify=directionsChanged,
    )


@ta.QmlElement
class InputItemBindingModel(QtCore.QObject):
    """Model representing an ActionTree instance."""

    behaviorChanged = QtCore.Signal()
    virtualButtonChanged = QtCore.Signal()
    rootActionChanged = QtCore.Signal()
    inputTypeChanged = QtCore.Signal()
    userFeedbackChanged = QtCore.Signal()

    def __init__(
        self,
        input_item_binding: gremlin.profile.InputItemBinding,
        parent: ta.OQO = None,
    ) -> None:
        super().__init__(parent)

        self._input_item_binding = input_item_binding
        self._virtual_button_model = VirtualButtonModel(
            self._input_item_binding.virtual_button
        )

        self._last_feedback_check = 0.0
        signal.inputItemChanged.connect(self._check_user_feedback)

        self._action_models = {}
        self._index_lookup = {}
        self._child_lookup = {}
        self._container_index_lookup = {}
        self._create_action_models()

    def _create_action_models(self) -> None:
        # Disconnect stale models so they stop reacting to behaviorChanged
        for model in self._action_models.values():
            model.dispose()

        # Reset storage
        self._action_models = {}
        self._index_lookup = {}
        self._child_lookup = {}
        self._container_index_lookup = {}

        # Initialize action queue
        actions = [
            (self.root_action, None),
        ]
        parent_indices = [
            SequenceIndex(None, None, None),
        ]
        container_indices = [
            0,
        ]
        count = 0

        while len(actions) > 0:
            # Grab first item from the queue
            action, container = actions.pop(0)
            parent_index = parent_indices.pop(0)
            container_index = container_indices.pop(0)

            # Create model for the action and store it
            index = SequenceIndex(parent_index.index, container, count)
            model = action.model(action, self, index, parent_index, self)
            self._action_models[index] = model
            self._index_lookup[index.index] = index
            self._container_index_lookup[index] = container_index
            key = (index.parent_index, index.container_name)
            if key not in self._child_lookup:
                self._child_lookup[key] = []
            self._child_lookup[key].append(model)

            # Add all children to the list of items to process
            c_actions, c_containers = action.get_actions()
            c_index = 0
            for i in range(len(c_actions)):
                actions.append((c_actions[i], c_containers[i]))
                parent_indices.append(index)
                if i > 0:
                    if c_containers[i] != c_containers[i - 1]:
                        c_index = 0
                container_indices.append(c_index)
                c_index += 1

            count += 1

    def get_child_actions(
        self, index: SequenceIndex | int, container: str
    ) -> list[ActionModel]:
        if isinstance(index, int):
            index = self._index_lookup[index]
        return self._child_lookup.get((index.index, container), [])

    def get_action_model_by_sidx(self, sidx: int) -> ActionModel:
        if sidx not in self._index_lookup:
            raise GremlinError(f"No action with sequence index {sidx} exists")
        return self._action_models[self._index_lookup[sidx]]

    def get_action_container_index(self, index: SequenceIndex) -> int:
        """Returns the linear index into the container storing the action.

        Args:
            index: sequence index of the action

        Returns:
            Linear index into the container holding the action
        """
        return self._container_index_lookup[index]

    def sync_data(self) -> None:
        self._create_action_models()
        self.rootActionChanged.emit()

    def move_action(
        self, source_idx: int, target_idx: int, container: str | None = None
    ) -> None:
        """Moves the source action to the spot after the target action.

        If a container name is given then the source action will be appended to
        the container with the given name of the target action.

        Args:
            source_idx: sequence index of the action to move
            target_idx: sequence index of the action after which to place the
                moved action
            container: name of the container to insert the action into
        """
        if _edit_refused():
            return
        s_model = self.get_action_model_by_sidx(source_idx)
        t_model = self.get_action_model_by_sidx(target_idx)

        s_parent_identifier = (
            s_model.sequence_index.parent_index,
            s_model.sequence_index.container_name,
        )
        t_parent_identifier = (
            t_model.sequence_index.parent_index,
            t_model.sequence_index.container_name,
        )

        if container is not None:
            self.remove_action(s_model.sequence_index, False, drop_unused=False)
            self.append_action(s_model.action_data, t_model.sequence_index, container)
        else:
            # If source and target are in the same container special care has to
            # be taken to ensure removal and insertion happen in a valid order
            move_performed = False
            if s_parent_identifier == t_parent_identifier:
                # Determine container indices of the source and target actions
                s_lid = self.get_action_container_index(s_model.sequence_index)
                t_lid = self.get_action_container_index(t_model.sequence_index)

                # Perform the action that affects a change in the rear part
                # of the container
                if s_lid < t_lid:
                    move_performed = True
                    self.append_action(s_model.action_data, t_model.sequence_index)
                    self.remove_action(s_model.sequence_index, False, drop_unused=False)

            # This is the default case if the source and target actions are part
            # of different parent actions or containers. Also, if the source
            # action is after the target action, performing the removal first
            # is safe.
            if not move_performed:
                self.remove_action(s_model.sequence_index, False, drop_unused=False)
                self.append_action(s_model.action_data, t_model.sequence_index)

        self._create_action_models()
        self.rootActionChanged.emit()

    def remove_action(
        self,
        action_index: int | SequenceIndex,
        perform_sync: bool = True,
        drop_unused: bool = True,
    ) -> None:
        """Removes the specified action from its parent.

        The provided action_index can be either a SequenceIndex instance or an
        integer corresponding to the unique index of the action.

        Args:
            action_index: index identifying the action to remove
            perform_sync: if True data will be resynchronized and a change
                event emitted
            drop_unused: the action and its children leave the profile's
                library unless used elsewhere (False when it is being moved);
                else Merge Axis 'Reuse' offered deleted ones
        """
        if _edit_refused():
            return
        if isinstance(action_index, int):
            action_index = self._index_lookup[action_index]

        removed = self.get_action_model_by_sidx(action_index.index).action_data
        parent_data = self.get_action_model_by_sidx(
            action_index.parent_index
        ).action_data
        parent_data.remove_action(
            self.get_action_container_index(action_index), action_index.container_name
        )
        if drop_unused:
            # The one removal rule, in this input's own library.
            self._input_item_binding.library.release([removed])

        if perform_sync:
            self._create_action_models()
            self.rootActionChanged.emit()

    def append_action(
        self,
        action_data: AbstractActionData,
        target_index: SequenceIndex,
        container: str | None = None,
    ) -> None:
        """Appends the provided action data after the specified action.

        Args:
            action_data: data of the action to append
            target_index: sequence index of the action after which to insert
                the new action's data
        """
        if _edit_refused():
            return
        # If the parent index of the target is None the target is the single
        # RootAction and thus should be used to insert into directly.
        if target_index.parent_index is None:
            data = self.get_action_model_by_sidx(target_index.index).action_data
            data.insert_action(action_data, "children", DataInsertionMode.Prepend, 0)
        elif container is None:
            parent_data = self.get_action_model_by_sidx(
                target_index.parent_index
            ).action_data
            parent_data.insert_action(
                action_data,
                target_index.container_name,
                DataInsertionMode.Append,
                self.get_action_container_index(target_index),
            )
        else:
            target_data = self.get_action_model_by_sidx(target_index.index).action_data
            target_data.insert_action(
                action_data, container, DataInsertionMode.Prepend, 0
            )

    def is_last_action_in_container(self, index: SequenceIndex) -> bool:
        """Returns whether the specified action is the last one in a container.

        Args:
            index: SequenceIndex corresponding to an action

        Returns:
            True if the specified action is the last one in its container, False
            otherwise.
        """
        indices = sorted(
            [
                self._container_index_lookup[m.sequence_index]
                for m in self.get_child_actions(
                    index.parent_index, index.container_name
                )
            ]
        )
        return self._container_index_lookup[index] >= indices[-1]

    @QtCore.Property(type=str, notify=inputTypeChanged)
    def inputType(self) -> str:
        return InputType.to_string(self._input_item_binding.input_item.input_type)

    @QtCore.Property(type=VirtualButtonModel, notify=virtualButtonChanged)
    def virtualButton(self) -> VirtualButtonModel:
        return self._virtual_button_model

    @QtCore.Property(type=ActionModel, notify=rootActionChanged)
    def rootAction(self) -> RootModel:
        return self._action_models[self._index_lookup[0]]

    @QtCore.Property(type=list, notify=userFeedbackChanged)
    def userFeedback(self) -> list[dict]:
        data = action_analysis.action_sequence_feedback(self._input_item_binding)
        return [
            {"type": entry.feedback_type.value, "message": entry.message}
            for entry in data
        ]

    def _check_user_feedback(self, index: int) -> None:
        # Only perform updates for matching items that still have a parent.
        parent = self.parent()
        if parent is None or parent.enumeration_index != index:
            return

        # Rate limit updates on user feedback.
        if time.time() - self._last_feedback_check > 0.1:
            self._last_feedback_check = time.time()
            self.userFeedbackChanged.emit()

    @property
    def root_action(self) -> AbstractActionData:
        return self._input_item_binding.root_action

    @property
    def input_item_binding(self) -> gremlin.profile.InputItemBinding:
        return self._input_item_binding

    @QtCore.Slot(result=int)
    def actionCount(self) -> int:
        """Actions a change of behavior would remove."""
        return len(self.root_action.get_actions()[0])

    def _get_behavior(self) -> str:
        if self._input_item_binding.behavior == InputType.Keyboard:
            return InputType.to_string(InputType.JoystickButton)
        return InputType.to_string(self._input_item_binding.behavior)

    def _set_behavior(self, text: str) -> None:
        if _edit_refused():
            return
        behavior = InputType.to_enum(text)
        if behavior != self._input_item_binding.behavior:
            self._input_item_binding.behavior = behavior
            self._input_item_binding.virtual_button = None

            # Ensure a virtual button instance exists of the correct type
            # if one is needed
            input_type = self._input_item_binding.input_item.input_type
            if (
                input_type == InputType.JoystickAxis
                and behavior == InputType.JoystickButton
            ):
                if not isinstance(
                    self._input_item_binding.virtual_button,
                    gremlin.profile.VirtualAxisButton,
                ):
                    self._input_item_binding.virtual_button = (
                        gremlin.profile.VirtualAxisButton()
                    )
                    self._virtual_button_model = VirtualButtonModel(
                        self._input_item_binding.virtual_button
                    )
            elif (
                input_type == InputType.JoystickHat
                and behavior == InputType.JoystickButton
            ):
                if not isinstance(
                    self._input_item_binding.virtual_button,
                    gremlin.profile.VirtualHatButton,
                ):
                    self._input_item_binding.virtual_button = (
                        gremlin.profile.VirtualHatButton()
                    )
                    self._virtual_button_model = VirtualButtonModel(
                        self._input_item_binding.virtual_button
                    )

            # Remove all actions when the behavior changes.
            root_action = self.root_action
            children, selectors = root_action.get_actions()
            for i in range(len(children) - 1, -1, -1):
                root_action.remove_action(i, selectors[i])
            self._input_item_binding.library.release(children)

            # Tree topology changed, so the model cache needs rebuilding
            self._create_action_models()

            # Force full redraw of the action
            self.behaviorChanged.emit()
            self.rootActionChanged.emit()
            signal.reloadCurrentInputItem.emit()

    @property
    def behavior_type(self) -> None:
        return self._input_item_binding.behavior

    behavior = QtCore.Property(
        str, fget=_get_behavior, fset=_set_behavior, notify=behaviorChanged
    )


@ta.QmlElement
class InputItemModel(QtCore.QAbstractListModel):
    """QML model class representing an InputItem instance and acting as a
    model to display the individual InputItemBindingModel instances.
    """

    # This fake single role and the roleName function are needed to have the
    # modelData property available in the QML delegate
    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"fake"),
    }

    bindingsChanged = QtCore.Signal()

    def __init__(
        self,
        input_item: gremlin.profile.InputItem,
        enumeration_index: int,
        parent: ta.OQO = None,
    ) -> None:
        """Exposes the list of all action sequences to the UI.

        Args:
            input_item: Profile InputItem instance to expose
            enumeration_index: Linear index reflecting the position in the
                list of device inputs
            parent: Widget to which this model is parented to
        """
        super().__init__(parent)

        self._input_item = input_item
        self._enumeration_index = enumeration_index

    @property
    def enumeration_index(self) -> int:
        return self._enumeration_index

    @QtCore.Slot()
    def newActionSequence(self) -> None:
        if _edit_refused():
            return
        self.beginInsertRows(QtCore.QModelIndex(), self.rowCount(), self.rowCount())
        self._input_item.add_item_binding()
        self.endInsertRows()
        signal.inputItemChanged.emit(self._enumeration_index)

    @QtCore.Slot(InputItemBindingModel)
    def deleteActionSequnce(self, binding: InputItemBindingModel) -> None:
        if _edit_refused():
            return
        try:
            index = self._input_item.action_sequences.index(binding.input_item_binding)
            self.beginRemoveRows(QtCore.QModelIndex(), index, index)
            self._input_item.remove_item_binding(binding.input_item_binding)
            self.endRemoveRows()
            # The one removal rule, in this input's own library (not the
            # open profile's: a pane's draft input shares the profile's).
            self._input_item.library.release(
                [binding.input_item_binding.root_action]
            )
            signal.inputItemChanged.emit(self._enumeration_index)
        except ValueError:
            pass

    @QtCore.Slot(str, str, str)
    def dropAction(self, source: str, target: str, method: str) -> None:
        """Move one action sequence before or after another on this control.

        Args:
            source: root action id of the sequence being dragged
            target: root action id of the sequence dropped on
            method: "before" places the source above the target, anything else
                places it below
        """
        if _edit_refused():
            return
        if not source or not target or source == target:
            return
        try:
            source_id = uuid.UUID(source)
            target_id = uuid.UUID(target)
        except ValueError:
            return

        sequences = self._input_item.action_sequences
        src = -1
        dst = -1
        for index, entry in enumerate(sequences):
            root = entry.root_action
            if root is None:
                continue
            if root.id == source_id:
                src = index
            if root.id == target_id:
                dst = index
        if src < 0 or dst < 0 or src == dst:
            return

        if method == "before":
            final = dst if src > dst else dst - 1
        else:
            final = dst if src < dst else dst + 1
        if final == src or not 0 <= final < len(sequences):
            return

        destination = final + 1 if src < final else final
        if not self.beginMoveRows(
            QtCore.QModelIndex(), src, src, QtCore.QModelIndex(), destination
        ):
            return
        entry = sequences.pop(src)
        sequences.insert(final, entry)
        self.endMoveRows()

    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._input_item.action_sequences)

    def data(
        self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> InputItemBindingModel:
        return InputItemBindingModel(
            self._input_item.action_sequences[index.row()], parent=self
        )

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return InputItemModel.roles


@ta.QmlElement
class ModeListModel(QtCore.QAbstractListModel):
    """List containing model instances for each mode."""

    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"name"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"parentName"),
        QtCore.Qt.ItemDataRole.UserRole + 3: QtCore.QByteArray(b"depth"),
    }

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)

        self._lookup: dict[str, tree.TreeNode] = {}
        self._names: list[str] = []
        self._reset()

        signal.profileChanged.connect(self._reset)
        signal.modesChanged.connect(self._reset)

    def _reset(self) -> None:
        self.beginResetModel()
        self._lookup = {}
        self._names = []
        for mode in shared_state.current_profile.modes.mode_list():
            self._names.append(mode.value)
            self._lookup[mode.value] = mode
        self._names = sorted(self._names)
        self.endResetModel()

    def rowCount(self, parent: ta.MI = QtCore.QModelIndex()) -> int:
        return len(self._lookup)

    def data(
        self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> str | int | None:
        if role not in self.roleNames():
            raise GremlinError(f"Invalid role {role} in ModeListModel")

        node = self._lookup[self._names[index.row()]]
        match cast(str, self.roles.get(role, "")):
            case "name":
                return node.value
            case "parentName":
                return "" if node.parent is None else node.parent.value
            case "depth":
                return node.depth
            case _:
                return None

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles


def _edit_refused() -> bool:
    """Bindings are not edited while the profile runs: the one edit lock
    (binding_catalog.editing_locked, GL-171); the pages are disabled too."""
    from gremlin.ui.binding_catalog import editing_locked

    if not editing_locked():
        return False
    logging.getLogger("system").info("Edit refused: the profile is running")
    return True


def _clean_mode_name(name: str) -> str:
    return gremlin.profile.clean_mode_name(name)


# Mode deletes that Manage Modes can undo, newest last: (profile, what
# ModeHierarchy.restore_mode needs). Only the open profile's count (GL-027).
_deleted_modes: list[tuple[object, dict]] = []


def _undoable_deletes() -> list[dict]:
    """The open profile's undoable mode deletes (others are dropped)."""
    profile = shared_state.current_profile
    _deleted_modes[:] = [
        entry for entry in _deleted_modes if entry[0] is profile
    ]
    return [memo for _, memo in _deleted_modes]


def _follow_editor(old_name: str, new_name: str) -> None:
    """The mode shown in the main window follows a renamed or deleted mode."""
    from gremlin.ui.backend import Backend

    # No main window (tests, tools): nothing to follow.
    if Backend.instance is None:
        return
    state = Backend().ui_state
    if state.currentMode == old_name and new_name:
        state.setCurrentMode(new_name)


def rename_mode(old_name: str, new_name: str) -> None:
    """Renames a mode of the open profile everywhere it is named: the
    profile, the running mode stack, the main window and the pages
    (modeRenamed). Every rename goes through here."""
    from gremlin.mode_manager import ModeManager

    profile = shared_state.current_profile
    if profile is None:
        return
    profile.modes.rename_mode(old_name, new_name)
    ModeManager().rename_mode(old_name, new_name)
    _follow_editor(old_name, new_name)
    signal.modeRenamed.emit(old_name, new_name)
    signal.modesChanged.emit()


def delete_mode(name: str) -> dict | None:
    """Deletes a mode of the open profile everywhere: the profile, the
    running mode stack, the main window (moves to the first mode) and the
    pages (modeDeleted). Every delete goes through here (Undo Import
    skipped all but the profile). Returns what undo_delete_mode needs."""
    from gremlin.mode_manager import ModeManager

    profile = shared_state.current_profile
    if profile is None:
        return None
    modes = profile.modes
    memo = modes.delete_mode(name)
    ModeManager().drop_mode(name)
    _follow_editor(name, modes.first_mode)
    signal.modeDeleted.emit(name)
    signal.modesChanged.emit()
    return memo


def undo_delete_mode(memo: dict) -> None:
    """Puts a deleted mode of the open profile back, with its bindings
    (GL-027, 04 Q6). Raises GremlinError when it can't (a mode with that
    name was added since)."""
    profile = shared_state.current_profile
    if profile is None:
        return
    profile.modes.restore_mode(memo)
    signal.modesChanged.emit()
    signal.reloadCurrentInputItem.emit()


@ta.QmlElement
class ModeHierarchyModel(QtCore.QObject):
    """Model exposing the mode hierarchy and allows managing it."""

    modesChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)

        # A method of this object, not modesChanged.emit, so the connection ends
        # when the model is deleted (a closed Manage Modes window).
        signal.profileChanged.connect(self._on_profile_changed)

    @QtCore.Slot()
    def _on_profile_changed(self) -> None:
        self.modesChanged.emit()

    @property
    def current_modes(self) -> gremlin.profile.ModeHierarchy:
        return shared_state.current_profile.modes

    @QtCore.Slot(str, str, result=bool)
    def nameTaken(self, name: str, ignore: str) -> bool:
        """True when name is blank or matches another mode, ignoring capitals and
        spacing (the rule Logical Device groups use). ignore is the mode being renamed.
        The rule is the mode tree's own (ModeHierarchy.name_taken)."""
        return self.current_modes.name_taken(name, ignore)

    @QtCore.Slot(str)
    def newMode(self, name: str) -> None:
        name = _clean_mode_name(name)
        if not self.nameTaken(name, ""):
            self.current_modes.add_mode(name)
            self.modesChanged.emit()
            signal.modesChanged.emit()

    @QtCore.Slot(str, str)
    def renameMode(self, old_name: str, new_name: str) -> None:
        new_name = _clean_mode_name(new_name)
        if old_name != new_name and not self.nameTaken(new_name, old_name):
            rename_mode(old_name, new_name)
            self.modesChanged.emit()

    @QtCore.Slot(str, result=int)
    def bindingCount(self, name: str) -> int:
        return self.current_modes.bindings_in_mode(name)

    @QtCore.Slot(str)
    def deleteMode(self, name: str) -> None:
        # A profile keeps at least one mode (the window disables Delete).
        if len(self.current_modes.mode_names()) <= 1:
            return
        memo = delete_mode(name)
        if memo is not None:
            _deleted_modes.append((shared_state.current_profile, memo))
        self.modesChanged.emit()

    def _can_undo_delete(self) -> bool:
        return bool(_undoable_deletes())

    canUndoDelete = QtCore.Property(bool, fget=_can_undo_delete, notify=modesChanged)

    def _undo_delete_name(self) -> str:
        deletes = _undoable_deletes()
        return str(deletes[-1]["name"]) if deletes else ""

    # The mode Undo Delete brings back ("" when none).
    undoDeleteName = QtCore.Property(str, fget=_undo_delete_name, notify=modesChanged)

    @QtCore.Slot(result=str)
    def undoDelete(self) -> str:
        """Brings back the mode deleted last, with its bindings; returns why
        it couldn't ("" when it did)."""
        deletes = _undoable_deletes()
        if not deletes:
            return ""
        memo = deletes[-1]
        try:
            undo_delete_mode(memo)
        except GremlinError as e:
            logging.getLogger("system").warning(f"Undo Delete Mode: {e}")
            signal.showNotification.emit("Undo Delete Mode", str(e))
            return str(e)
        finally:
            _deleted_modes[:] = [e for e in _deleted_modes if e[1] is not memo]
            self.modesChanged.emit()
        return ""

    @QtCore.Slot(str, str)
    def setParent(self, mode_name: str, parent_name: str) -> None:
        node = self.current_modes.find_mode(mode_name)
        if parent_name != node.parent.value:
            self.current_modes.set_parent(mode_name, parent_name)
            self.modesChanged.emit()
            signal.modesChanged.emit()

    @QtCore.Slot(str, result=list)
    def validParents(self, name: str) -> list[dict[str, str]]:
        options = [{"value": ""}]
        for entry in self.current_modes.valid_parents(name):
            options.append({"value": entry})
        return options

    @QtCore.Slot(result=list)
    def modeStringList(self) -> list[str]:
        return self.current_modes.mode_names()


@ta.QmlElement
class LabelValueSelectionModel(QtCore.QAbstractListModel):
    """Generic class presenting an interface for use with Comboboxes."""

    selectionChanged = QtCore.Signal()

    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"label"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"value"),
        QtCore.Qt.ItemDataRole.UserRole + 3: QtCore.QByteArray(b"bootstrap"),
        QtCore.Qt.ItemDataRole.UserRole + 4: QtCore.QByteArray(b"imageIcon"),
    }

    def __init__(
        self,
        labels: list[Any],
        values: list[str],
        bootstrap: list[str] = [],
        icons: list[str] = [],
        parent: ta.OQO = None,
    ) -> None:
        super().__init__(parent)

        assert len(values) == len(labels)

        self._labels = labels
        self._values = values
        self._bootstrap = bootstrap
        self._icons = icons
        self._current_index = 0

    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._labels)

    def data(
        self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> str:
        if role not in self.roleNames():
            raise GremlinError(f"Invalid role {role} in LabelValueSelectionModel")

        row = index.row()
        match cast(str, self.roles.get(role, "")):
            case "label":
                return self._labels[row]
            case "value":
                return str(self._values[row])
            case "bootstrap":
                return "" if row >= len(self._bootstrap) else self._bootstrap[row]
            case "imageIcon":
                return "" if row >= len(self._icons) else self._icons[row]
            case _:
                return ""

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return LabelValueSelectionModel.roles

    def _get_current_value(self) -> str:
        return str(self._values[self._current_index])

    def _set_current_value(self, value_str: str) -> None:
        value = value_str
        try:
            index = self._values.index(value)
            if index != self._current_index:
                self._current_index = index
                self.selectionChanged.emit()
        except ValueError:
            logging.error(
                f"LabelValueSelectionModel: Attempting to set invalid value {value_str}"
            )

    def _get_current_selection_index(self) -> int:
        return self._current_index

    currentValue = QtCore.Property(
        str, fget=_get_current_value, fset=_set_current_value, notify=selectionChanged
    )

    currentSelectionIndex = QtCore.Property(
        int, fget=_get_current_selection_index, notify=selectionChanged
    )


@ta.QmlElement
class StartupModeModel(QtCore.QAbstractListModel):
    """Model representing the startup mode setting of the current profile."""

    selectionChanged = QtCore.Signal()

    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray("label".encode()),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray("value".encode()),
    }

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)

        self._profile = cast(gremlin.profile.Profile, shared_state.current_profile)
        self._valid_names = [
            "Use Heuristic",
            "Last Active",
        ] + self._profile.modes.mode_names()
        signal.profileChanged.connect(self._reset)
        signal.modesChanged.connect(self._reset)

    def _reset(self) -> None:
        self.beginResetModel()
        self._profile = cast(gremlin.profile.Profile, shared_state.current_profile)
        self._valid_names = [
            "Use Heuristic",
            "Last Active",
        ] + self._profile.modes.mode_names()
        self.endResetModel()
        self.selectionChanged.emit()

    @override
    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._valid_names)

    @override
    def data(
        self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> Any:
        if not index.isValid() or index.row() >= len(self._valid_names):
            return None

        match cast(str, self.roles[role]):
            case "label":
                return self._valid_names[index.row()]
            case "value":
                return index.row()

    @override
    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles

    def _get_current_selection_index(self) -> int:
        # A Startup Mode that isn't listed shows as Use Heuristic (GL-039).
        name = self._profile.settings.startup_mode
        return self._valid_names.index(name) if name in self._valid_names else 0

    def _set_current_selection_index(self, index: int) -> None:
        if index != self._get_current_selection_index():
            self._profile.settings.startup_mode = self._valid_names[index]
            self.selectionChanged.emit()

    currentSelectionIndex = QtCore.Property(
        int,
        fget=_get_current_selection_index,
        fset=_set_current_selection_index,
        notify=selectionChanged,
    )


@ta.QmlElement
class VJoyInputOrOutputModel(QtCore.QAbstractListModel):
    """Model representign if a vJoy device is treated as input or output
    device."""

    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"vid"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"isInput"),
    }

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)

        self._profile = shared_state.current_profile
        self._vjoy_devices = device_initialization.vjoy_devices()
        signal.profileChanged.connect(self._reset)

    def _reset(self) -> None:
        self.beginResetModel()
        self._profile = shared_state.current_profile
        self._vjoy_devices = device_initialization.vjoy_devices()
        self.endResetModel()

    @override
    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._vjoy_devices)

    @override
    def data(
        self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> Any:
        if not index.isValid() or index.row() >= len(self._vjoy_devices):
            return None

        match cast(str, self.roles[role]):
            case "vid":
                return self._vjoy_devices[index.row()].vjoy_id
            case "isInput":
                vid = self._vjoy_devices[index.row()].vjoy_id
                return self._profile.settings.vjoy_as_input.get(vid, False)
            case _:
                return None

    @override
    def setData(
        self,
        index: ta.ModelIndex,
        value: Any,
        role: int = QtCore.Qt.ItemDataRole.EditRole,
    ) -> bool:
        match cast(str, self.roles[role]):
            case "isInput":
                vid = self._vjoy_devices[index.row()].vjoy_id
                self._profile.settings.vjoy_as_input[vid] = bool(value)
                # Device lists and claims follow profileChanged; only a device
                # scan sends device_change_event, which with Device change
                # behavior Stop or Reload stopped or restarted a Run (GL-119,
                # 02 Q1, 04 Q12).
                signal.profileChanged.emit()
                listener = event_handler.EventListener.instance
                if listener is not None and listener.gremlin_active:
                    signal.showNotification.emit(
                        "vJoy Behavior",
                        "This change takes effect at the next Run.",
                    )
                return True
            case _:
                return False

    @override
    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles


@ta.QmlElement
class OutputVJoyListModel(QtCore.QAbstractListModel):
    """Model representing the initial vJoy values of the current profile."""

    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"vjoyId"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"initialValuesModel"),
    }

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)

        self._profile = shared_state.current_profile
        self._vjoy_devices = self._output_devices()
        signal.profileChanged.connect(self._reset)

    def _reset(self) -> None:
        self.beginResetModel()
        self._profile = shared_state.current_profile
        self._vjoy_devices = self._output_devices()
        self.endResetModel()

    @override
    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._vjoy_devices)

    @override
    def data(
        self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> Any:
        if not index.isValid() or index.row() >= len(self._vjoy_devices):
            return None

        match cast(str, self.roles[role]):
            case "vjoyId":
                return self._vjoy_devices[index.row()].vjoy_id
            case "initialValuesModel":
                return OutputVJoyInitialValuesModel(
                    self._vjoy_devices[index.row()], self
                )

    @override
    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles

    def _output_devices(self) -> list[dill.DeviceSummary]:
        return [
            d
            for d in device_initialization.vjoy_devices()
            if self._profile.settings.vjoy_as_input.get(d.vjoy_id, False) is False
        ]


@ta.QmlElement
class OutputVJoyInitialValuesModel(QtCore.QAbstractListModel):
    """Model representing the initial vJoy values for a specific vJoy device."""

    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray("label".encode()),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray("value".encode()),
    }

    def __init__(self, device: dill.DeviceSummary, parent: ta.OQO = None) -> None:
        super().__init__(parent)

        self._device = device
        self._profile = shared_state.current_profile
        signal.profileChanged.connect(self._reset)

    def _reset(self) -> None:
        self.beginResetModel()
        self._profile = shared_state.current_profile
        self.endResetModel()

    @override
    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return self._device.axis_count

    @override
    def data(
        self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> Any:
        if not index.isValid() or index.row() >= self._device.axis_count:
            return None

        match cast(str, self.roles[role]):
            case "label":
                return common.input_to_ui_string(
                    InputType.JoystickAxis,
                    self._device.axis_map[index.row()].axis_index,
                )
            case "value":
                return self._profile.settings.get_initial_vjoy_axis_value(
                    self._device.vjoy_id, self._device.axis_map[index.row()].axis_index
                )

    @override
    def setData(
        self,
        index: ta.ModelIndex,
        value: Any,
        role: int = QtCore.Qt.ItemDataRole.EditRole,
    ) -> bool:
        if not index.isValid() or index.row() >= self._device.axis_count:
            return False

        match cast(str, self.roles[role]):
            case "value":
                self._profile.settings.set_initial_vjoy_axis_value(
                    self._device.vjoy_id,
                    self._device.axis_map[index.row()].axis_index,
                    value,
                )
                return True
            case _:
                return False

    @override
    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles


@ta.QmlElement
class ProfileSettingsModel(QtCore.QObject):
    """QML model exposing profile settings to the UI."""

    settingsChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)

        self._profile = shared_state.current_profile
        signal.profileChanged.connect(self._reset)
        # The Options macro delay shows here while the profile follows it.
        signal.configChanged.connect(self.settingsChanged)

    def _reset(self) -> None:
        self._profile = shared_state.current_profile
        self.settingsChanged.emit()

    def _set_macro_default_delay(self, delay: float) -> None:
        """Gives the profile its own delay (it stops following Options)."""
        if delay >= 0.0 and delay != self._profile.settings.macro_default_delay:
            self._profile.settings.macro_default_delay = delay
            self.settingsChanged.emit()

    # The delay macros use: the profile's own, or the Options default.
    macroDefaultDelay = QtCore.Property(
        float,
        fget=lambda self: self._profile.settings.effective_macro_delay(),
        fset=_set_macro_default_delay,
        notify=settingsChanged,
    )

    def _set_macro_delay_from_options(self, follow: bool) -> None:
        settings = self._profile.settings
        if follow == (settings.macro_default_delay is None):
            return
        # Leaving Options keeps today's value as the profile's own start.
        settings.macro_default_delay = (
            None if follow else settings.effective_macro_delay()
        )
        self.settingsChanged.emit()

    macroDelayFromOptions = QtCore.Property(
        bool,
        fget=lambda self: self._profile.settings.macro_default_delay is None,
        fset=_set_macro_delay_from_options,
        notify=settingsChanged,
    )


@ta.QmlElement
class ProfileDeviceListModel(QtCore.QAbstractListModel):
    """Model listing devices with bindings in the profile."""

    selectedIndexChanged = QtCore.Signal()

    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"name"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"nameAndActions"),
        QtCore.Qt.ItemDataRole.UserRole + 3: QtCore.QByteArray(b"uuid"),
    }

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)

        self._devices: list[swap_devices.ProfileDeviceInfo] = []
        self.update_model()
        event_handler.EventListener().device_change_event.connect(self.update_model)
        # A swap or another profile loaded: the list showed the old devices
        # and counts, and a second Swap swapped everything back.
        signal.profileChanged.connect(self.update_model)

    @QtCore.Slot()
    def update_model(self) -> None:
        """Lists the open profile's devices again (devices plugged in or out,
        a swap, another profile)."""
        self.beginResetModel()
        self._devices = swap_devices.get_profile_devices(shared_state.current_profile)
        self.endResetModel()

    def rowCount(self, parent: ta.MI = QtCore.QModelIndex()) -> int:
        return len(self._devices)

    def data(
        self, index: ta.MI, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> str | None:
        if not index.isValid() or not (0 <= index.row() < len(self._devices)):
            return None

        device = self._devices[index.row()]
        match cast(str, self.roles[role]):
            case "name":
                return device.name
            case "nameAndActions":
                count = device.num_bindings
                actions = f"{count} action" + ("" if count == 1 else "s")
                if device.name:
                    return f"{device.name} - {actions}"
                # No name known (not plugged in): a short id tells two apart.
                short = str(device.device_uuid).split("-")[0]
                return f"Unknown device ({short}) - {actions}"
            case "uuid":
                return str(device.device_uuid)

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles
