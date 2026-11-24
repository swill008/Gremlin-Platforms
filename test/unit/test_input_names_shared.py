# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""02 S10, D-05-UPSTREAM-B2: the editors (Merge Axis, Dual Axis Deadzone,
the script physical-input variable) name inputs as the rest of the program
does ("X Axis"), through the one helper references.input_label, which
applies Options > Input names and the device database; an Input names change
sends the device names notice, so open editors read their labels again."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from pytestqt.qtbot import QtBot
from shiboken6 import Shiboken

from gremlin import input_cache, references
from gremlin.config import Configuration
from gremlin.types import InputType

_GUID = uuid.UUID("5DA7C1B0-0000-0000-0000-0000000000B2")
_KEY = ("ui", "general", "display-mode")


@pytest.fixture
def stick(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, Any]]:
    """A stick named "Stick" whose device database entry calls axis 1
    "Pitch"; Input names read from `state["mode"]`."""
    from gremlin import device_initialization

    state: dict[str, Any] = {"mode": "Label"}
    monkeypatch.setattr(device_initialization, "shown_name", lambda uid: "Stick")
    mapping = input_cache.DeviceMapping({(InputType.JoystickAxis, 1): "Pitch"})
    monkeypatch.setattr(
        input_cache.DeviceDatabase,
        "get_mapping_by_uuid",
        lambda self, uid: mapping if uid == _GUID else None,
    )
    real_value = Configuration.value

    def value(self: Any, *key: str) -> Any:  # noqa: ANN401
        if key == _KEY:
            return state["mode"]
        return real_value(self, *key)

    monkeypatch.setattr(Configuration, "value", value)
    yield state


def _release(obj: object) -> None:
    if Shiboken.isValid(obj):
        Shiboken.delete(obj)


def test_an_axis_label_uses_the_axis_name(stick: dict[str, Any]) -> None:
    from gremlin.ui.device import InputIdentifier

    stick["mode"] = "Numerical"
    ident = InputIdentifier(_GUID, InputType.JoystickAxis, 1)
    try:
        assert ident.label == "Stick - X Axis"
    finally:
        _release(ident)


def test_the_device_database_name_shows_when_input_names_asks(
    stick: dict[str, Any],
) -> None:
    from gremlin.ui.device import InputIdentifier

    ident = InputIdentifier(_GUID, InputType.JoystickAxis, 1)
    try:
        assert ident.label == "Stick - Pitch"
        stick["mode"] = "Numerical and Label"
        assert ident.label == "Stick - X Axis - Pitch"
        # An input the database doesn't name keeps the plain name.
        other = InputIdentifier(_GUID, InputType.JoystickButton, 3)
        assert other.label == "Stick - Button 3"
        _release(other)
    finally:
        _release(ident)


def test_one_helper_names_inputs_everywhere(stick: dict[str, Any]) -> None:
    """InputIdentifier, the action model and references all give the same
    input part."""
    from gremlin.profile import InputItem
    from gremlin.ui import action_model

    assert references.input_label(InputType.JoystickAxis, 1, _GUID) == "Pitch"
    # Without a device there is no database entry.
    assert references.input_label(InputType.JoystickAxis, 1) == "X Axis"
    item = InputItem(None)
    item.device_id = _GUID
    item.input_type = InputType.JoystickAxis
    item.input_id = 1
    item.mode = "Default"
    assert action_model.input_name(item).endswith(" Pitch (Default)")


def test_an_open_editor_follows_an_input_names_change(
    qtbot: QtBot, stick: dict[str, Any]
) -> None:
    """Options > Input names sends the device names notice; the label is
    read again."""
    from gremlin import device_aliases
    from gremlin.signal import signal
    from gremlin.ui.device import InputIdentifier

    assert device_aliases.watch_names() is not None
    signal.configChanged.emit()  # settle the announced state
    qtbot.wait(10)
    ident = InputIdentifier(_GUID, InputType.JoystickAxis, 1)
    try:
        assert ident.label == "Stick - Pitch"
        stick["mode"] = "Numerical"
        with qtbot.waitSignal(ident.changed, timeout=2000):
            signal.configChanged.emit()
        assert ident.label == "Stick - X Axis"
    finally:
        _release(ident)
