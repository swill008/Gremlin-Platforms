# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The release after a mode change (06 S38) reads the mode from the mode
system when the button is released, not from a copy kept up to date by
`mode_changed`; since D-06-MODE-RELEASE the event handler's pending table
sends it to the press mode's binding.

A copy out of step sent an extra Logical Device release in the mode the
button was pressed in (CI 7bfde51b, seed 836062: [True, False, False])."""

from __future__ import annotations

import sys

sys.path.append(".")

import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from PySide6 import QtCore

from gremlin import event_handler, mode_manager
from gremlin.logical_device import LogicalDevice
from gremlin.profile import Profile
from gremlin.types import Event, InputType

_GUID = uuid.UUID("77777777-5555-2222-3333-666666666666")
_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


@pytest.fixture
def modes(monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    """The real mode system, any mode name allowed, back as it was after."""
    monkeypatch.setattr(mode_manager, "_known_modes", lambda: set())
    mm = mode_manager.ModeManager()
    stack = list(mm._mode_stack)
    handler = event_handler.EventHandler()
    handler.clear()
    handler.resume()
    yield mm
    handler.clear()
    mm._mode_stack = stack
    mm.mode_changed.emit(mm.current.name)


@pytest.fixture
def ld_button(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[Any, list]]:
    """A Map to Logical Device button bound in Default (a real
    CallbackObject in the event handler), its control and its updates."""
    from gremlin import code_runner

    control = LogicalDevice().create(InputType.JoystickButton)
    updates: list[tuple[Any, Any]] = []
    real_update = LogicalDevice.Input.update

    def update(self: Any, value: Any) -> None:  # noqa: ANN401
        # Record and keep the state: Map to Logical Device's waits_for_end
        # reads is_pressed (06 S38).
        updates.append((self, value))
        real_update(self, value)

    monkeypatch.setattr(LogicalDevice.Input, "update", update)
    profile = Profile()
    item = profile.get_input_item(
        _GUID, InputType.JoystickButton, 3, "Default", create_if_missing=True
    )
    action = profile.library.create("Map to Logical Device", InputType.JoystickButton)
    action.logical_input_id = control.id
    item.add_item_binding().root_action.insert_action(action, "children")
    event_handler.EventHandler().add_callback(
        _GUID,
        "Default",
        Event(InputType.JoystickButton, 3, _GUID, "Default"),
        code_runner.CallbackObject(item.action_sequences[0]),
    )
    yield control, updates
    LogicalDevice().delete(control.identifier)


def _switch(name: str) -> None:
    mode_manager.ModeManager().switch_to(mode_manager.Mode(name, None))


def _button(pressed: bool) -> Event:
    # No mode, as from the hardware: the handler reads the live one.
    return Event(InputType.JoystickButton, 3, _GUID, "", is_pressed=pressed)


def _send(pressed: bool) -> None:
    event_handler.EventHandler().process_event(_button(pressed))


def test_a_missed_mode_change_sends_no_extra_logical_release(
    modes: Any,  # noqa: ANN401
    ld_button: tuple[Any, list],
) -> None:
    control, updates = ld_button
    _switch("Flight")
    # No listener sees this change: only the mode system knows the mode
    # is Default again.
    modes.blockSignals(True)
    try:
        _switch("Default")
    finally:
        modes.blockSignals(False)
    _send(True)
    _send(False)
    assert [v for c, v in updates if c is control] == [True, False]


def test_a_mode_change_while_held_releases_the_logical_button_once(
    modes: Any,  # noqa: ANN401
    ld_button: tuple[Any, list],
) -> None:
    control, updates = ld_button
    _switch("Default")
    _send(True)
    _switch("Flight")
    _send(False)
    _send(False)  # a repeated release: nothing more
    assert [v for c, v in updates if c is control] == [True, False]
    # The press mode's entry is spent (D-06-MODE-RELEASE pending table).
    assert not any(event_handler.EventHandler()._pending.values())


def test_a_mode_change_the_listeners_missed_still_releases_the_button(
    modes: Any,  # noqa: ANN401
    ld_button: tuple[Any, list],
) -> None:
    """The reverse: a copy left on the old mode used to skip the release
    and leave the Logical Device button held."""
    control, updates = ld_button
    _switch("Default")
    _send(True)
    modes.blockSignals(True)
    try:
        _switch("Flight")
    finally:
        modes.blockSignals(False)
    _send(False)
    assert [v for c, v in updates if c is control] == [True, False]
