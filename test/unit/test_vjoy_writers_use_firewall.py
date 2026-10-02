# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Every vJoy writer goes through the output module (the firewall)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

from gremlin.modules import output
from gremlin.types import ActionActivationMode, InputType

_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def writes() -> list[tuple]:
    sent: list[tuple] = []

    def fake_write(vjoy_id: int, kind: str, input_id: int, value: object) -> bool:
        sent.append((vjoy_id, kind, input_id, value))
        return input_id <= 56  # buttons 1-56 claimed, like the user's vJoy 3

    with mock.patch.object(output, "write_vjoy", side_effect=fake_write):
        yield sent


def _map_to_vjoy(button: int) -> object:
    from action_plugins.map_to_vjoy import MapToVjoyFunctor

    data = SimpleNamespace(
        vjoy_device_id=3,
        vjoy_input_id=button,
        vjoy_input_type=InputType.JoystickButton,
        button_inverted=False,
        activation_mode=ActionActivationMode.Both,
        name="Map to vJoy",
        _valid_selectors=lambda: [],
        get_actions=lambda: ([], []),
    )
    return MapToVjoyFunctor(data)


def test_map_to_vjoy_writes_through_the_output_module(writes: list[tuple]) -> None:
    from gremlin import event_helpers

    releases = event_helpers.ButtonReleaseActions()
    with mock.patch.object(releases, "register_vjoy_button_release") as register:
        _map_to_vjoy(10)(SimpleNamespace(), SimpleNamespace(current=True))
        _map_to_vjoy(57)(SimpleNamespace(), SimpleNamespace(current=True))
    assert writes == [(3, "button", 10, True), (3, "button", 57, True)]
    # Only the button that reached vJoy gets an auto-release.
    assert register.call_count == 1


def test_scripts_get_the_firewalled_vjoy(writes: list[tuple]) -> None:
    from gremlin.user_script import VJoyPlugin

    vjoy = VJoyPlugin.vjoy
    assert isinstance(vjoy, output.ScriptVJoy)
    vjoy[3].button(57).is_pressed = True
    vjoy[3].axis(2).value = 0.5
    assert writes == [(3, "button", 57, True), (3, "axis", 2, 0.5)]


def test_only_the_output_module_holds_the_vjoy_driver() -> None:
    files = [
        *_ROOT.joinpath("gremlin").rglob("*.py"),
        *_ROOT.joinpath("action_plugins").rglob("*.py"),
        _ROOT / "joystick_gremlin.py",
    ]
    owner = _ROOT / "gremlin" / "modules" / "output.py"
    hits = [
        str(path.relative_to(_ROOT))
        for path in files
        if path != owner and "VJoyProxy" in path.read_text(encoding="utf-8")
    ]
    assert hits == []
