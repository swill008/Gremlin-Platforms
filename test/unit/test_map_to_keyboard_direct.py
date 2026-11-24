# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Map to Keyboard sends its keys at once, not through the macro queue
(05 S85, D-05-MACRO-MANAGER): an exclusive macro never delays them, Stop
still releases them, and a release after a mode change lets them go.

Key output is recorded at keybd_event (the driver call under
gremlin.keyboard), so the real send and run_scope tracking run; no real key
reaches the PC.
"""

from __future__ import annotations

import sys
import uuid
from collections.abc import Iterator

sys.path.append(".")

import pytest
import win32api
import win32con

from action_plugins.map_to_keyboard import MapToKeyboardData, MapToKeyboardFunctor
from gremlin import keyboard, macro, run_scope
from gremlin.base_classes import Value
from gremlin.types import Event, InputType, ModeType

_GUID = uuid.UUID("85858585-1111-2222-3333-444444444444")


@pytest.fixture
def keys(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[tuple[int, bool]]]:
    """Key output as (scan code, is_pressed), in order."""
    sent: list[tuple[int, bool]] = []

    def record(vk: int, scan: int, flags: int, extra: int = 0) -> None:
        sent.append((scan, not flags & win32con.KEYEVENTF_KEYUP))

    monkeypatch.setattr(win32api, "keybd_event", record)
    run_scope.stop()
    run_scope._reset_for_tests()
    run_scope.begin()
    yield sent
    run_scope.stop()
    run_scope._reset_for_tests()


@pytest.fixture
def no_macro_queue(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Any use of the macro manager is noted (an exclusive macro running
    would hold a queued macro back)."""
    used: list[str] = []

    class Busy:
        def __getattr__(self, name: str) -> object:
            used.append(name)
            return lambda *a, **k: None

    monkeypatch.setattr(macro, "MacroManager", Busy)
    return used


def _functor() -> tuple[MapToKeyboardFunctor, list[int]]:
    data = MapToKeyboardData()
    data.keys = [keyboard.key_from_name("leftcontrol"), keyboard.key_from_name("a")]
    return MapToKeyboardFunctor(data), [k.scan_code for k in data.keys]


def _event(pressed: bool) -> Event:
    return Event(InputType.JoystickButton, 1, _GUID, "Default", is_pressed=pressed)


def test_keys_go_down_and_up_at_once_while_a_macro_holds_the_queue(
    keys: list[tuple[int, bool]], no_macro_queue: list[str]
) -> None:
    functor, scans = _functor()
    functor(_event(True), Value(True))
    # Sent before the call returns: no macro thread involved.
    assert keys == [(scans[0], True), (scans[1], True)]
    functor(_event(False), Value(False))
    assert keys[2:] == [(scans[1], False), (scans[0], False)]
    assert no_macro_queue == []


def test_stop_releases_held_keys(
    keys: list[tuple[int, bool]], no_macro_queue: list[str]
) -> None:
    functor, scans = _functor()
    functor(_event(True), Value(True))
    run_scope.stop()  # input still held
    assert keys == [
        (scans[0], True), (scans[1], True), (scans[1], False), (scans[0], False),
    ]
    run_scope.stop()  # a second Stop sends nothing more
    assert len(keys) == 4


def test_release_after_a_mode_change_releases_the_keys(
    keys: list[tuple[int, bool]], no_macro_queue: list[str]
) -> None:
    functor, scans = _functor()
    functor(_event(True), Value(True))
    assert functor.waits_for_end()  # the handler keeps the binding pending
    functor(_event(False), Value(False, ModeType.Foreign))
    assert keys[2:] == [(scans[1], False), (scans[0], False)]
    assert not functor.waits_for_end()
    assert run_scope.held() == []


def test_no_key_is_sent_twice(
    keys: list[tuple[int, bool]], no_macro_queue: list[str]
) -> None:
    functor, scans = _functor()
    functor(_event(True), Value(True))
    functor(_event(False), Value(False))
    run_scope.stop()  # nothing left to release
    for scan in scans:
        assert keys.count((scan, True)) == 1
        assert keys.count((scan, False)) == 1
    assert len(keys) == 4
