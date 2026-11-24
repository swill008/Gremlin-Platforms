# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""More outputs that let go after a mode change (06 S38, S38a-S38d,
D-06-MODE-RELEASE; claude/plans/b3-mode-change-release.md).

The same rig as test_mode_change_release.py: a real CodeRunner, the real
EventHandler and ModeManager. Logical Device events are recorded at the
listener, mouse buttons at gremlin.sendinput, Xbox writes at the output
module (no ViGEm, no real vJoy).
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

sys.path.append(".")

import pytest

from gremlin import mode_manager, sendinput
from gremlin.logical_device import LogicalDevice
from gremlin.types import HatDirection, InputType, MouseButton
from test.unit import test_mode_change_release as _base
from test.unit.test_mode_change_release import (
    _bind,
    _button,
    _hat,
    _pending,
    _profile,
    _send,
    _switch,
)

# The rig's fixtures, shared with test_mode_change_release.py.
_app = _base._app
rig = _base.rig


# --- Map to Logical Device hat (S38) ------------------------------------------


@pytest.fixture
def ld_hat() -> Iterator[Any]:
    """A Logical Device hat, removed after."""
    logical = LogicalDevice()
    hat = logical.create(InputType.JoystickHat)
    yield hat
    logical.delete(hat.identifier)


def test_a_logical_device_hat_centres_after_a_mode_change(
    rig: SimpleNamespace,
    ld_hat: Any,  # noqa: ANN401
) -> None:
    profile = _profile()
    action = profile.library.create("Map to Logical Device", InputType.JoystickHat)
    action.logical_input_type = InputType.JoystickHat
    action.logical_input_id = ld_hat.id
    _bind(profile, "Default", InputType.JoystickHat, 5, action)
    rig.run.start(profile, "Default")
    sent: list[Any] = []
    from gremlin import event_handler

    event_handler.EventListener().joystick_event.connect(
        lambda e: (
            sent.append(e.value) if e.event_type == InputType.JoystickHat else None
        )
    )
    _send(rig, _hat(5, HatDirection.North))
    assert ld_hat.direction == HatDirection.North
    _switch("B")  # the hat is unbound in B
    _send(rig, _hat(5, HatDirection.Center))
    assert ld_hat.direction in (HatDirection.Center, HatDirection.Center.value)
    assert sent == [HatDirection.North, HatDirection.Center]
    assert _pending(rig.run.event_handler) == 0


# --- Map to Mouse button (S38) ----------------------------------------------


def test_a_mouse_button_is_released_after_a_mode_change(
    rig: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    clicks: list[tuple[MouseButton, bool]] = []
    monkeypatch.setattr(sendinput, "mouse_press", lambda b: clicks.append((b, True)))
    monkeypatch.setattr(sendinput, "mouse_release", lambda b: clicks.append((b, False)))
    profile = _profile()
    action = profile.library.create("Map to Mouse", InputType.JoystickButton)
    action.button = MouseButton.Right
    _bind(profile, "Default", InputType.JoystickButton, 15, action)
    rig.run.start(profile, "Default")
    _send(rig, _button(15, True))
    _switch("B")
    _send(rig, _button(15, False))
    _send(rig, _button(15, False))  # a repeated release: no second one
    assert clicks == [(MouseButton.Right, True), (MouseButton.Right, False)]
    assert _pending(rig.run.event_handler) == 0


# --- Map to Xbox button (S38) -----------------------------------------------


def test_an_xbox_button_is_released_after_a_mode_change(
    rig: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.modules import output
    from gremlin.modules.output import XboxTarget

    writes: list[tuple[int, Any, Any]] = []
    monkeypatch.setattr(
        output,
        "write_xbox",
        lambda pad, target, value: writes.append((pad, target, value)) or True,
    )
    profile = _profile()
    action = profile.library.create("Map to Xbox", InputType.JoystickButton)
    action.xbox_target = XboxTarget.A
    _bind(profile, "Default", InputType.JoystickButton, 16, action)
    rig.run.start(profile, "Default")
    _send(rig, _button(16, True))
    _switch("B")
    _send(rig, _button(16, False))
    _send(rig, _button(16, False))
    pad = action.xbox_device_id
    assert writes == [(pad, XboxTarget.A, True), (pad, XboxTarget.A, False)]
    assert _pending(rig.run.event_handler) == 0


# --- Change Mode Temporary (S38) --------------------------------------------


def _temporary(profile: Any, target: str) -> Any:  # noqa: ANN401
    from action_plugins.change_mode import ChangeType

    action = profile.library.create("Change Mode", InputType.JoystickButton)
    action.change_type = ChangeType.Temporary
    action.target_modes = [target]
    return action


def test_a_temporary_mode_unwinds_after_another_mode_change(
    rig: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Button 17 holds B; in B button 18 holds C. Each release comes in a
    mode that doesn't bind it and still unwinds its own temporary mode."""
    from gremlin import shared_state

    profile = _profile()
    profile.modes.add_mode("C")
    monkeypatch.setattr(shared_state, "current_profile", profile)
    _bind(profile, "Default", InputType.JoystickButton, 17, _temporary(profile, "B"))
    _bind(profile, "B", InputType.JoystickButton, 18, _temporary(profile, "C"))
    rig.run.start(profile, "Default")
    mm = mode_manager.ModeManager()
    _send(rig, _button(17, True))
    assert mm.current.name == "B"
    _send(rig, _button(18, True))  # the mode changes again, 17 held
    assert mm.current.name == "C"
    _send(rig, _button(18, False))  # pressed in B, released in C
    assert mm.current.name == "B"
    _send(rig, _button(17, False))  # pressed in Default, released in B
    assert mm.current.name == "Default"
    assert _pending(rig.run.event_handler) == 0
