# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Keys are never sent on the input thread (gap B4-KBD-INPUT-THREAD,
05 S85, S100, S147-S150; 01 S180-S182).

In the installed program, real key presses stopped reaching the program
once Map to Keyboard had sent a key on the input thread. Keys sent there
go through gremlin.keyboard's one key sender thread, in order; Stop waits
for it, so a key queued down is released and nothing is sent after Stop.

The real input thread runs Map to Keyboard's functor; keys are recorded at
win32api.keybd_event (no real key reaches the PC).
"""

from __future__ import annotations

import sys
import threading
from collections.abc import Iterator
from types import SimpleNamespace

sys.path.append(".")

import pytest
import win32api
import win32con

from action_plugins.map_to_keyboard import MapToKeyboardData, MapToKeyboardFunctor
from gremlin import clock, input_thread, keyboard, macro, run_scope
from gremlin.base_classes import Value
from gremlin.types import Event, InputType

_LIMIT = 3.0


@pytest.fixture
def rig(qapp: object, monkeypatch: pytest.MonkeyPatch) -> Iterator[SimpleNamespace]:
    """The real input thread; key output as (scan, pressed, thread name)."""
    sent: list[tuple[int, bool, str]] = []
    gate = threading.Event()
    gate.set()

    def record(vk: int, scan: int, flags: int, extra: int = 0) -> None:
        gate.wait(_LIMIT)
        sent.append(
            (
                scan,
                not flags & win32con.KEYEVENTF_KEYUP,
                threading.current_thread().name,
            )
        )

    monkeypatch.setattr(win32api, "keybd_event", record)
    was_inline = input_thread.is_inline()
    input_thread.set_inline(False)
    input_thread.start()
    run_scope.stop()
    run_scope._reset_for_tests()
    run_scope.begin()
    try:
        yield SimpleNamespace(sent=sent, gate=gate)
    finally:
        gate.set()
        run_scope.stop()
        run_scope._reset_for_tests()
        assert input_thread.stop(2.0)
        input_thread.set_inline(was_inline)


def _functor(*names: str) -> tuple[MapToKeyboardFunctor, list[int]]:
    data = MapToKeyboardData()
    data.keys = [keyboard.key_from_name(n) for n in names]
    return MapToKeyboardFunctor(data), [k.scan_code for k in data.keys]


def _press(functor: MapToKeyboardFunctor, pressed: bool) -> None:
    event = Event(InputType.JoystickButton, 1, None, "Default", is_pressed=pressed)
    input_thread.call_wait(functor, event, Value(pressed), timeout=_LIMIT)


def _until_sent(sent: list[object], count: int) -> None:
    deadline = clock.monotonic() + _LIMIT
    while len(sent) < count and clock.monotonic() < deadline:
        clock.sleep(0.01)
    clock.sleep(0.05)  # and nothing more after it


def _input_thread_name() -> str:
    return input_thread.call_wait(
        lambda: threading.current_thread().name, timeout=_LIMIT
    )


def test_a_press_on_the_input_thread_never_sends_there(rig: SimpleNamespace) -> None:
    functor, scans = _functor("leftcontrol", "a")
    _press(functor, True)
    _press(functor, False)
    _until_sent(rig.sent, 4)
    on_input = _input_thread_name()
    assert len(rig.sent) == 4
    assert all(name != on_input for _, _, name in rig.sent), rig.sent
    assert [(s, p) for s, p, _ in rig.sent] == [
        (scans[0], True), (scans[1], True), (scans[1], False), (scans[0], False),
    ]
    assert run_scope.held() == []


def test_order_is_kept_for_several_keys_and_presses(rig: SimpleNamespace) -> None:
    functor, scans = _functor("leftshift", "leftalt", "b", "c")
    rig.gate.clear()  # the sender waits: everything queues up behind it
    for _ in range(3):
        _press(functor, True)
        _press(functor, False)
    rig.gate.set()
    _until_sent(rig.sent, 24)
    one = [(s, True) for s in scans] + [(s, False) for s in reversed(scans)]
    assert [(s, p) for s, p, _ in rig.sent] == one * 3


def test_a_send_from_another_thread_follows_queued_keys(rig: SimpleNamespace) -> None:
    functor, scans = _functor("d")
    other = keyboard.key_from_name("e")
    rig.gate.clear()
    _press(functor, True)
    keyboard.send_key_down(other)  # the test's own thread (like a macro)
    keyboard.send_key_up(other)
    rig.gate.set()
    _until_sent(rig.sent, 3)
    assert [(s, p) for s, p, _ in rig.sent] == [
        (scans[0], True), (other.scan_code, True), (other.scan_code, False),
    ]


def test_stop_releases_a_key_whose_down_was_still_queued(
    rig: SimpleNamespace,
) -> None:
    functor, scans = _functor("f", "g")
    rig.gate.clear()
    _press(functor, True)  # both downs still queued
    assert len(rig.sent) == 0
    stopper = threading.Thread(target=run_scope.stop)
    stopper.start()
    rig.gate.set()
    stopper.join(_LIMIT)
    assert not stopper.is_alive()
    # Down first, then released last pressed first; all sent before Stop
    # returned, and nothing after.
    assert [(s, p) for s, p, _ in rig.sent] == [
        (scans[0], True), (scans[1], True), (scans[1], False), (scans[0], False),
    ]
    assert run_scope.held() == []
    _until_sent(rig.sent, 5)  # waits: nothing more may come
    assert len(rig.sent) == 4


def test_stop_on_the_input_thread_releases_queued_keys(
    rig: SimpleNamespace,
) -> None:
    functor, scans = _functor("h")
    rig.gate.clear()
    _press(functor, True)
    threading.Timer(0.2, rig.gate.set).start()
    input_thread.call_wait(run_scope.stop, timeout=_LIMIT)
    assert [(s, p) for s, p, _ in rig.sent] == [(scans[0], True), (scans[0], False)]


def test_keys_go_while_an_exclusive_macro_holds_the_queue(
    rig: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    used: list[str] = []

    class Busy:
        def __getattr__(self, name: str) -> object:
            used.append(name)
            return lambda *a, **k: None

    monkeypatch.setattr(macro, "MacroManager", Busy)
    functor, scans = _functor("j")
    _press(functor, True)
    _until_sent(rig.sent, 1)
    assert [(s, p) for s, p, _ in rig.sent] == [(scans[0], True)]
    assert used == []
