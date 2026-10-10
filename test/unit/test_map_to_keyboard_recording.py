# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Recording a key combination for Map to Keyboard.

05 S85: modifiers (Shift, Ctrl, Alt, Win) are pressed first.
05 S119: a recorded combination keeps the order the keys were pressed in.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Any, cast

import pytest
from PySide6 import QtCore

from gremlin import event_handler, keyboard, shared_state
from gremlin.types import InputType

_KB = uuid.UUID("05850585-0585-0585-0585-058505850585")
_KEEP: list[object] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    yield app


@pytest.fixture(autouse=True)
def _highlighting_kept() -> Iterator[None]:
    before = shared_state.suspend_input_highlighting()
    yield
    shared_state.set_suspend_input_highlighting(before)


class _Binding(QtCore.QObject):
    behaviorChanged = QtCore.Signal()


def _key(name: str, pressed: bool = True) -> event_handler.Event:
    key = keyboard.key_from_name(name)
    return event_handler.Event(
        InputType.Keyboard, (key.scan_code, key.is_extended), _KB, "Default",
        is_pressed=pressed,
    )


def _record(*names: str) -> list[keyboard.Key]:
    """Presses the keys in order on the real recorder, then lets go of the first."""
    from gremlin.ui.util import InputListenerModel

    model = InputListenerModel()
    _KEEP.append(model)
    done: list[list] = []
    model.listeningTerminated.connect(lambda inputs: done.append(list(inputs)))
    model.setProperty("eventTypes", [InputType.to_string(InputType.Keyboard)])
    model.setProperty("multipleInputs", True)
    model.setProperty("enabled", True)
    for name in names:
        model._kb_event_cb(_key(name))
    model._kb_event_cb(_key(names[0], pressed=False))
    assert len(done) == 1
    return [keyboard.key_from_code(*e.identifier) for e in done[0]]


def _saved(events_of: list[str]) -> Any:  # noqa: ANN401
    """Records the keys and hands them to a Map to Keyboard, as the editor does."""
    from action_plugins.map_to_keyboard import MapToKeyboardData, MapToKeyboardModel
    from gremlin.ui.util import InputListenerModel

    listener = InputListenerModel()
    _KEEP.append(listener)
    data = MapToKeyboardData(InputType.JoystickButton)
    binding = _Binding()
    model = MapToKeyboardModel(data, cast(Any, binding), cast(Any, None),
                               cast(Any, None), cast(Any, None))
    listener.listeningTerminated.connect(model.updateInputs)
    listener.setProperty("eventTypes", [InputType.to_string(InputType.Keyboard)])
    listener.setProperty("multipleInputs", True)
    listener.setProperty("enabled", True)
    try:
        for name in events_of:
            listener._kb_event_cb(_key(name))
        listener._kb_event_cb(_key(events_of[0], pressed=False))
    finally:
        model.dispose()
        model.deleteLater()
        binding.deleteLater()
    return data


def _k(*names: str) -> list[keyboard.Key]:
    return [keyboard.key_from_name(n) for n in names]


def test_recorder_keeps_press_order() -> None:
    """05 S119: A then B gives [A, B]; B then A gives [B, A]."""
    assert _record("a", "b") == _k("a", "b")
    assert _record("b", "a") == _k("b", "a")
    assert _record("c", "a", "b", "d") == _k("c", "a", "b", "d")


def test_recorder_lists_a_key_once() -> None:
    assert _record("a", "b", "a") == _k("a", "b")


def test_map_to_keyboard_keeps_press_order_with_modifier_first() -> None:
    """05 S119 + S85: the modifier goes first, the rest keep press order."""
    assert _saved(["b", "leftshift", "a"]).keys == _k("leftshift", "b", "a")
    assert _saved(["a", "leftshift", "b"]).keys == _k("leftshift", "a", "b")


def test_win_is_a_modifier_and_survives_save_and_load() -> None:
    """05 S85: recording [D, Left Win] saves [Left Win, D], kept through XML."""
    from action_plugins.map_to_keyboard import MapToKeyboardData

    data = _saved(["d", "leftwin"])
    assert data.keys == _k("leftwin", "d")
    assert _saved(["d", "rightwin"]).keys == _k("rightwin", "d")

    loaded = MapToKeyboardData(InputType.JoystickButton)
    loaded._from_xml(data._to_xml(), cast(Any, None))
    assert loaded.keys == _k("leftwin", "d")
