# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import logging
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    List,
    override,
)
from xml.etree import ElementTree

from PySide6 import QtCore

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
from gremlin.profile import Library
from gremlin.signal import signal
from gremlin.types import (
    ActionProperty,
    InputType,
    PropertyType,
)
from gremlin.ui import backend
from gremlin.ui.action_model import (
    ActionModel,
    SequenceIndex,
)
from gremlin.util import file_exists_and_is_accessible

if TYPE_CHECKING:
    from gremlin.ui.profile import InputItemBindingModel


class LoadProfileFunctor(AbstractFunctor):
    """Executes a load profile action callback."""

    def __init__(self, action: LoadProfileData) -> None:
        super().__init__(action)

    @override
    def __call__(
        self, event: event_handler.Event, value: Value, properties: list[ActionProperty]
    ) -> None:
        if not self._should_execute(value):
            return

        name = Path(self.data.profile_filename).name
        be = backend.Backend()
        # As auto-load does: never over unsaved edits.
        if be.profile.has_unsaved_changes():
            signal.showNotification.emit(
                "Load Profile Waited",
                f"{name} was not loaded because the open profile has unsaved "
                "changes. Save or discard them first.",
            )
            return
        if not file_exists_and_is_accessible(self.data.profile_filename):
            signal.showNotification.emit(
                "Load Profile", f"{name} was not loaded: the file is missing."
            )
            return
        logging.getLogger("system").debug(
            f"Loading profile ... {self.data.profile_filename}"
        )
        be.loadProfile(self.data.profile_filename)
        be.activate_gremlin(False)
        be.activate_gremlin(True)


class LoadProfileModel(ActionModel):
    fileChanged = QtCore.Signal()

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
            + QtCore.QFile("core_plugins:load_profile/LoadProfileAction.qml").fileName()
        )

    def _action_behavior(self) -> str:
        return self._binding_model.get_action_model_by_sidx(
            self._parent_sequence_index.index
        ).actionBehavior

    def _get_profile_filename(self) -> str:
        return self._data.profile_filename

    def _set_profile_filename(self, value: str) -> None:
        if str(value) == self._data.profile_filename:
            return
        self._data.profile_filename = str(value)
        self.fileChanged.emit()

    profile_filename = QtCore.Property(
        str, fget=_get_profile_filename, fset=_set_profile_filename, notify=fileChanged
    )


class LoadProfileData(AbstractActionData):
    """Model of a load profile action."""

    version = 1
    name = "Load Profile"
    tag = "load-profile"
    icon = "\uf37b"

    functor = LoadProfileFunctor
    model = LoadProfileModel

    properties = [ActionProperty.ActivateOnPress, ActionProperty.AlwaysExecute]
    input_types = [InputType.JoystickButton, InputType.Keyboard]

    def __init__(self, behavior_type: InputType = InputType.JoystickButton) -> None:
        super().__init__(behavior_type)

        # Model variables
        self.profile_filename = ""

    @override
    def _from_xml(self, node: ElementTree.Element, library: Library) -> None:
        self._id = util.read_action_id(node)
        # A file that is missing now doesn't stop the profile loading: the
        # action says so (user_feedback) and keeps its file name.
        self.profile_filename = util.read_property(
            node, "load-profile", PropertyType.String
        )

    @override
    def _to_xml(self) -> ElementTree.Element:
        node = util.create_action_node(LoadProfileData.tag, self._id)
        node.append(
            util.create_property_node(
                "load-profile", self.profile_filename, PropertyType.String
            )
        )
        return node

    @override
    def user_feedback(self) -> List[UserFeedback]:
        messages = []
        if not self.profile_filename:
            messages.append(
                UserFeedback(UserFeedback.FeedbackType.Error, "Choose a profile file.")
            )
        elif not file_exists_and_is_accessible(self.profile_filename):
            # A warning: the action (and its file name) is kept when saved.
            messages.append(
                UserFeedback(
                    UserFeedback.FeedbackType.Warning,
                    f"Profile file '{self.profile_filename}' does not exist or "
                    f"is not accessible.",
                )
            )
        return messages

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


create = LoadProfileData
