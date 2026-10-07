# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Edits in the action pane show at once: "Off: never runs" when Press and
Release are both switched off (05 S44), and the Button Map's chips follow an
action edit (07 S73, AU-112)."""

from __future__ import annotations

import sys
import uuid

sys.path.append(".")

import pytest
from PySide6 import QtCore

from gremlin import shared_state
from gremlin.profile import Profile
from gremlin.types import ActionActivationMode, InputType
from gremlin.ui import hardware_profile
from gremlin.ui.hardware_profile import HardwareProfile
from gremlin.ui.profile import InputItemBindingModel

_GUID = uuid.UUID("{11111111-2222-3333-4444-555555555555}")


@pytest.fixture(scope="session", autouse=True)
def terminate_event_listener(request: pytest.FixtureRequest) -> None:
    import gremlin.event_handler

    request.addfinalizer(lambda: gremlin.event_handler.EventListener().terminate())


class _Item(QtCore.QObject):
    """What a binding model's parent offers the action models: the input's
    place in the input list."""

    def __init__(self) -> None:
        super().__init__()
        self.enumeration_index = 0


@pytest.fixture
def profile(monkeypatch: pytest.MonkeyPatch) -> Profile:
    p = Profile()
    monkeypatch.setattr(shared_state, "current_profile", p)
    return p


def _binding_model(
    profile: Profile, button: int, *actions: str
) -> tuple[InputItemBindingModel, _Item, list]:
    item = profile.get_input_item(
        _GUID, InputType.JoystickButton, button, "Default", create_if_missing=True
    )
    binding = item.add_item_binding()
    made = []
    for name in actions:
        action = profile.library.create(name, InputType.JoystickButton, item=item)
        binding.root_action.insert_action(action, "children")
        made.append(action)
    owner = _Item()
    model = InputItemBindingModel(binding, owner)
    return model, owner, made


def _labels(hp: HardwareProfile) -> dict[str, str]:
    return hp.actionLabels(str(_GUID), "Default", True, False)


# --- 05 S44 ----------------------------------------------------------------


def test_press_and_release_off_tell_the_pane_at_once(
    qtbot: object, profile: Profile
) -> None:
    model, _owner, (vjoy,) = _binding_model(profile, 1, "Map to vJoy")
    action = model.rootAction.getActions("children")[0]
    told: list[int] = []
    action.actionChanged.connect(lambda: told.append(1))

    action.activateOnPress = False
    assert told, "switching Press off must notify activateOnPress"
    told.clear()
    action.activateOnRelease = False
    assert told, "switching Release off must notify activateOnRelease"

    assert vjoy.activation_mode == ActionActivationMode.Deactivated
    assert action.activateOnPress is False and action.activateOnRelease is False

    # Setting the same value again says nothing.
    told.clear()
    action.activateOnPress = False
    assert not told


# --- 07 S73 ----------------------------------------------------------------


def test_chips_follow_a_description_edit(qtbot: object, profile: Profile) -> None:
    model, _owner, (desc,) = _binding_model(profile, 2, "Description")
    desc.description = "Gear up"
    hp = HardwareProfile()
    assert _labels(hp).get("btn:2") == "Gear up"

    pane_desc = model.rootAction.getActions("children")[0]
    with qtbot.waitSignal(hp.profileLabelsChanged, timeout=2000):  # type: ignore[attr-defined]
        pane_desc.description = "Landing gear"
    assert _labels(hp).get("btn:2") == "Landing gear"


def test_chips_follow_an_added_action(qtbot: object, profile: Profile) -> None:
    model, _owner, _made = _binding_model(profile, 3)
    hp = HardwareProfile()
    assert "btn:3" not in _labels(hp)
    generation = hardware_profile._profile_generation

    with qtbot.waitSignal(hp.profileLabelsChanged, timeout=2000):  # type: ignore[attr-defined]
        model.rootAction.appendAction("Map to vJoy", "children")
    assert _labels(hp).get("btn:3"), _labels(hp)
    # The pool rows' key moves on too, so the card reads its chips again.
    assert hardware_profile._profile_generation != generation


def test_many_edits_refresh_the_chips_once(qtbot: object, profile: Profile) -> None:
    model, _owner, (desc,) = _binding_model(profile, 4, "Description")
    hp = HardwareProfile()
    told: list[int] = []
    hp.profileLabelsChanged.connect(lambda: told.append(1))
    pane_desc = model.rootAction.getActions("children")[0]
    with qtbot.waitSignal(hp.profileLabelsChanged, timeout=2000):  # type: ignore[attr-defined]
        for text in ("L", "La", "Lan", "Land"):
            pane_desc.description = text
    assert told == [1]
    assert _labels(hp).get("btn:4") == "Land"
