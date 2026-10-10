# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""An input with no actions can get its first action (09 S12, 05 Q4/G10):
the shared action pane's draft (Library.draft, used by beginPane and
beginNewAction) gives any device's empty input one empty binding, and OK
writes the first action onto it. Nothing reaches the profile before OK."""

from __future__ import annotations

import sys
import uuid
from collections.abc import Iterator

import pytest

sys.path.append(".")

import dill
from gremlin import osc_device_file, shared_state
from gremlin.osc import OSC_DEVICE_UUID, OscDevice
from gremlin.profile import Profile
from gremlin.types import InputType

_DEVICES = {
    "osc": (OSC_DEVICE_UUID, InputType.JoystickButton, 1),
    "keyboard": (dill.UUID_Keyboard, InputType.Keyboard, (0x1E, False)),
    "logical": (dill.UUID_LogicalDevice, InputType.JoystickButton, 1),
    "stick": (uuid.uuid4(), InputType.JoystickButton, 3),
}


@pytest.fixture
def profile() -> Iterator[Profile]:
    # OSC's shared rows hold one new address (button 1, as Add makes it).
    rows = OscDevice().rows
    saved = rows.to_dict()
    rows.load_dict({"inputs": []})
    made = rows.create(InputType.JoystickButton, "/first")
    assert made.input_id == _DEVICES["osc"][2]
    old = shared_state.current_profile
    profile = Profile()
    shared_state.current_profile = profile
    yield profile
    shared_state.current_profile = old
    osc_device_file.current_uid_map = None
    rows.load_dict(saved)


@pytest.mark.parametrize("device", sorted(_DEVICES))
@pytest.mark.parametrize("blank", [False, True], ids=["open", "new-action"])
def test_empty_input_gets_its_first_action(
    profile: Profile, device: str, blank: bool
) -> None:
    guid, kind, ident = _DEVICES[device]
    key = (guid, kind, ident, "Default")
    assert profile.get_input_item(guid, kind, ident, "Default") is None

    # The pane opens on an input that doesn't exist yet: one empty binding
    # to add to, and the profile is untouched.
    draft = profile.library.draft(None, key=key, blank=blank)
    assert len(draft.item.action_sequences) == 1
    root = draft.item.action_sequences[0].root_action
    assert root is not None and root.get_actions()[0] == []
    assert profile.get_input_item(guid, kind, ident, "Default") is None

    action = profile.library.create("Description", kind)
    root.insert_action(action, "children")

    # OK: the input is made and holds the first action.
    real = profile.get_input_item(guid, kind, ident, "Default", True)
    profile.library.commit(draft, real)
    assert len(real.action_sequences) == 1
    assert real.action_sequences[0].root_action.get_actions()[0] == [action]


@pytest.mark.parametrize("device", sorted(_DEVICES))
def test_existing_input_with_no_bindings_gets_one(
    profile: Profile, device: str
) -> None:
    """An input the profile has but with no bindings (a new OSC input, an
    Add Key, every action deleted) opens on one empty binding too."""
    guid, kind, ident = _DEVICES[device]
    real = profile.get_input_item(guid, kind, ident, "Default", True)
    assert real.action_sequences == []

    draft = profile.library.draft(real)
    assert len(draft.item.action_sequences) == 1
    assert real.action_sequences == []

    action = profile.library.create("Description", kind)
    draft.item.action_sequences[0].root_action.insert_action(action, "children")
    profile.library.commit(draft, real)
    assert len(real.action_sequences) == 1
    assert real.action_sequences[0].root_action.get_actions()[0] == [action]
