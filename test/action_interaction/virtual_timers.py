# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Timers on a clock the test steps, for timing actions (Double Tap, Tempo,
Smart Toggle and a pulse's release).

Those actions wait through run_scope.timer, which starts a
threads.main_timer. VirtualTimers stands in for threads.main_timer: a timer
runs only when the test calls advance() past its time, in time order, on
the test's own (main) thread. A slow PC then can't turn two quick taps into
two single taps, or let a release overtake a timer.
"""

from __future__ import annotations

import itertools
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any
from unittest import mock


class VirtualTimer:
    """One waiting timer (cancel() / is_alive() like threads.MainTimer)."""

    def __init__(
        self, due: float, order: int, function: Callable[..., Any], args: tuple
    ) -> None:
        self.due = due
        self.order = order
        self._function = function
        self._args = args
        self._alive = True

    def cancel(self) -> None:
        self._alive = False

    def is_alive(self) -> bool:
        return self._alive

    def fire(self) -> None:
        self._alive = False
        self._function(*self._args)


class VirtualTimers:
    """threads.main_timer on a clock that moves only by advance()."""

    def __init__(self) -> None:
        self.now = 0.0
        self._timers: list[VirtualTimer] = []
        self._order = itertools.count()

    def main_timer(
        self, _name: str, seconds: float, function: Callable[..., Any], *args: object
    ) -> VirtualTimer:
        timer = VirtualTimer(self.now + seconds, next(self._order), function, args)
        self._timers.append(timer)
        return timer

    def pending(self) -> list[VirtualTimer]:
        return [t for t in self._timers if t.is_alive()]

    def advance(self, seconds: float) -> None:
        """Moves the clock on by seconds, running each timer that comes due
        (the earliest first; a timer one of them starts runs too if it comes
        due in time)."""
        end = self.now + seconds
        while True:
            self._timers = self.pending()
            due = [t for t in self._timers if t.due <= end]
            if not due:
                break
            timer = min(due, key=lambda t: (t.due, t.order))
            self.now = max(self.now, timer.due)
            timer.fire()
        self.now = end


@contextmanager
def virtual_timers() -> Iterator[VirtualTimers]:
    """threads.main_timer replaced by a VirtualTimers while inside."""
    from gremlin import threads

    clock = VirtualTimers()
    with mock.patch.object(threads, "main_timer", clock.main_timer):
        yield clock
