# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The automatic release (06 S38) reads the mode from the mode system when
the button is released, not from a copy kept up to date by `mode_changed`.

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

from gremlin import event_handler, event_helpers, mode_manager
from gremlin.base_classes import Value
from gremlin.event_handler import Event
from gremlin.logical_device import LogicalDevice
from gremlin.types import InputType

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
    bra = event_helpers.ButtonReleaseActions()
    bra.reset()
    yield mm
    bra.reset()
    mm._mode_stack = stack
    mm.mode_changed.emit(mm.current.name)


@pytest.fixture
def ld_button(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[Any, Any, list]]:
    """A Map to Logical Device button functor, its control and its updates."""
    from action_plugins.map_to_logical_device import (
        MapToLogicalDeviceData,
        MapToLogicalDeviceFunctor,
    )

    control = LogicalDevice().create(InputType.JoystickButton)
    updates: list[tuple[Any, Any]] = []
    monkeypatch.setattr(
        LogicalDevice.Input,
        "update",
        lambda self, value: updates.append((self, value)),
    )
    data = MapToLogicalDeviceData(InputType.JoystickButton)
    data.logical_input_id = control.id
    functor = MapToLogicalDeviceFunctor(data)
    yield functor, control, updates
    LogicalDevice().delete(control.identifier)


def _switch(name: str) -> None:
    mode_manager.ModeManager().switch_to(mode_manager.Mode(name, None))


def _button(mode: str, pressed: bool) -> Event:
    return Event(InputType.JoystickButton, 3, _GUID, mode, is_pressed=pressed)


def _press_release(functor: Any, mode_at_release: str) -> None:  # noqa: ANN401
    """Press in Default; release in mode_at_release (the old mode's action
    only sees the release when the mode stayed the same)."""
    functor(_button("Default", True), Value(True))
    if mode_at_release != "Default":
        _switch(mode_at_release)
    release = _button(mode_at_release, False)
    if mode_at_release == "Default":
        functor(release, Value(False))
    event_handler.EventHandler().process_event(release)


def test_a_missed_mode_change_sends_no_extra_logical_release(
    modes: Any,  # noqa: ANN401
    ld_button: tuple[Any, Any, list],
) -> None:
    functor, control, updates = ld_button
    _switch("Flight")
    # The release registry misses this change (as on CI): only the mode
    # system knows the mode is Default again.
    modes.blockSignals(True)
    try:
        _switch("Default")
    finally:
        modes.blockSignals(False)
    _press_release(functor, "Default")
    assert [v for c, v in updates if c is control] == [True, False]


def test_a_mode_change_while_held_releases_the_logical_button_once(
    modes: Any,  # noqa: ANN401
    ld_button: tuple[Any, Any, list],
) -> None:
    functor, control, updates = ld_button
    _switch("Default")
    _press_release(functor, "Flight")
    assert [v for c, v in updates if c is control] == [True, False]
    assert event_helpers.ButtonReleaseActions()._registry == {}


def test_a_mode_change_the_registry_missed_still_releases_the_button(
    modes: Any,  # noqa: ANN401
    ld_button: tuple[Any, Any, list],
) -> None:
    """The reverse: a copy left on the old mode used to skip the release
    and leave the Logical Device button held."""
    functor, control, updates = ld_button
    _switch("Default")
    functor(_button("Default", True), Value(True))
    modes.blockSignals(True)
    try:
        _switch("Flight")
    finally:
        modes.blockSignals(False)
    event_handler.EventHandler().process_event(_button("Flight", False))
    assert [v for c, v in updates if c is control] == [True, False]
