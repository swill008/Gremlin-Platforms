# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Input Tester link: the device-change hook flag is checked and set as one
step (AUD-THREADS-09). start_watch runs on the main thread and the watch
timer's stop_watch on a timer thread; both at once must hook the device
change signal once, never twice. Stopping when nothing is hooked doesn't
make the event listener on the calling thread."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from types import SimpleNamespace

import pytest

from gremlin import event_handler
from gremlin import input_tester_link as link


class _Signal:
    """connect() waits (bounded) for a second caller, so two unguarded
    check-then-connect calls both get through."""

    def __init__(self) -> None:
        self.connects = 0
        self.disconnects = 0
        self._count = threading.Lock()
        self._second = threading.Event()

    def connect(self, _slot: object) -> None:
        with self._count:
            self.connects += 1
            if self.connects >= 2:
                self._second.set()
        self._second.wait(0.5)

    def disconnect(self, _slot: object) -> None:
        self.disconnects += 1


@pytest.fixture
def signal(monkeypatch: pytest.MonkeyPatch) -> Iterator[_Signal]:
    sig = _Signal()
    made: list[int] = []

    def listener() -> SimpleNamespace:
        made.append(1)
        return SimpleNamespace(device_change_event=sig)

    monkeypatch.setattr(event_handler, "EventListener", listener)
    monkeypatch.setattr(link, "_connected", False)
    sig.made = made  # type: ignore[attr-defined]
    yield sig
    monkeypatch.setattr(link, "_connected", False)


def test_two_threads_hook_once(signal: _Signal) -> None:
    threads = [
        threading.Thread(target=link._connect, args=(True,)) for _ in range(2)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(5)
    assert signal.connects == 1
    assert link._connected is True


def test_unhook_when_not_hooked_leaves_listener_alone(signal: _Signal) -> None:
    link._connect(False)
    assert signal.disconnects == 0
    assert signal.made == []  # type: ignore[attr-defined]


def test_hook_then_unhook(signal: _Signal) -> None:
    link._connect(True)
    link._connect(False)
    assert (signal.connects, signal.disconnects) == (1, 1)
    assert link._connected is False
