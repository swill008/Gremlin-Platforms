# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""What one Run holds, and the Stop that lets go of it (map 3).

The one owner of the Run number, of the timers and loops a Run starts, of
the keys and mouse buttons it holds down and of the work Stop must do.
Only CodeRunner calls begin() and stop(); everything else registers here:

- number() / alive(run): the one Run number (macros, script timers and the
  relative axis loops read it; there is no other Run counter).
- timer(): a main-thread timer (Tempo, Double Tap, Smart Toggle, pulse
  releases). At Stop it is cancelled, or fired at once (at_stop="fire").
  It never runs after its Run has stopped.
- loop(): a thread that gets its Run's number and ends once alive(run) is
  False (the relative axis loops).
- hold() / let_go(): a key or mouse button that is down / up again. Only
  output pressed during a Run is tracked (decision R4). Stop releases
  whatever is still down, last pressed first; release_owner() lets go of
  what one macro or script still holds. owning() names the owner of what
  the current thread presses meanwhile.
- on_stop(): anything else, in one of the Stage steps below. Registrations
  are for the current Run only: Stop runs each once and forgets it.

stop() runs the stages in order, each one's work in the order it was
registered; an error in one step is logged and the rest go on. Calling it
twice (the Stop button, then quitting) is safe: the second finds nothing
left to do.

Stop stages (Stage), in order:
1. CUT_INPUT: new Run number, input disconnected, mode listening off,
   runtime_active False, last modes saved.
2. CANCEL: Run timers cancelled, waiting release actions dropped (R2),
   script timers and OSC stopped.
3. FIRE_PENDING: the at_stop="fire" timers run now (pulse releases).
4. END_WORK: macros and mouse motion end; loops end through alive().
5. RELEASE_HELD: keys and mouse buttons still down are released, last
   pressed first.
6. NEUTRAL: Logical Device values back to neutral (R1), mode stack reset
   (R3), sound and speech stopped.
7. DRIVERS: output.reset_drivers() (vJoy released, Xbox pads unplugged).
"""

from __future__ import annotations

import contextlib
import enum
import logging
import threading
from collections.abc import Callable, Hashable, Iterator
from dataclasses import dataclass
from typing import Any, Literal

from gremlin import clock, threads

__all__ = [
    "Handle",
    "STAGE_LIMIT_S",
    "Stage",
    "Timer",
    "alive",
    "begin",
    "current_owner",
    "hold",
    "held",
    "let_go",
    "loop",
    "number",
    "on_stop",
    "owning",
    "pending_timers",
    "release_held",
    "release_owner",
    "running",
    "stop",
    "stopping",
    "timer",
]


class Stage(enum.IntEnum):
    """The steps of Stop, in the order they run."""

    CUT_INPUT = 1
    CANCEL = 2
    FIRE_PENDING = 3
    END_WORK = 4
    RELEASE_HELD = 5
    NEUTRAL = 6
    DRIVERS = 7


# A stage taking longer than this is logged (each step bounds its own waits).
STAGE_LIMIT_S = 3.0

# Held only for short bookkeeping, never while calling out (bounded).
_LOCK = threading.Lock()
_number = 0
_running = False
_stopping = False
_on_stop: dict[Stage, list[Handle]] = {stage: [] for stage in Stage}
_timers: list[Timer] = []
# (kind, ident) -> what holds it; in press order, so the last is released first.
_held: dict[tuple[str, Hashable], _Held] = {}
_owner = threading.local()


def _log() -> logging.Logger:
    return logging.getLogger("system")


# --- the Run number ------------------------------------------------------------


def number() -> int:
    """The current Run's number. It changes at every Run and every Stop."""
    return _number


def running() -> bool:
    """True between begin() and stop()."""
    return _running


def stopping() -> bool:
    """True while stop() is running its stages."""
    return _stopping


def alive(run: int) -> bool:
    """False once the Run numbered run has stopped (or another began).

    The number changes at every begin() and stop(), so a number taken
    outside a Run (an editor test) stays alive only until the next Run.
    """
    return run == _number


def begin() -> int:
    """A new Run starts (CodeRunner only); returns its number.

    Whatever an earlier Run left registered is let go of first (as if it
    had been stopped), so nothing carries over.
    """
    global _number, _running
    if _running:
        stop()
    with _LOCK:
        _number += 1
        _running = True
        return _number


# --- work done at Stop ---------------------------------------------------------


class Handle:
    """One piece of work registered for Stop; drop() takes it back."""

    def __init__(self, stage: Stage, name: str, fn: Callable[[], Any]) -> None:
        self.stage = stage
        self.name = name
        self.fn = fn

    def drop(self) -> None:
        """It won't run at Stop."""
        with _LOCK:
            entries = _on_stop[self.stage]
            if self in entries:
                entries.remove(self)


def on_stop(stage: Stage, name: str, fn: Callable[[], Any]) -> Handle:
    """fn() runs at the next Stop, in stage (once: Stop forgets it)."""
    handle = Handle(stage, name, fn)
    with _LOCK:
        _on_stop[stage].append(handle)
    return handle


def _run_step(name: str, fn: Callable[[], Any]) -> None:
    try:
        fn()
    except Exception:
        _log().exception(f"Stop: {name} failed")


def stop() -> None:
    """Ends the Run (CodeRunner only): every stage in order. Safe twice.

    The Run number changes first, so loops, macros and timers of this Run
    see alive(run) False before anything is released. A stop() called from
    inside a stage (a step that asks for Stop again) returns at once.
    """
    global _number, _running, _stopping
    with _LOCK:
        if _stopping:
            return
        if _running:
            _number += 1
        _running = False
        _stopping = True
        registered = {stage: list(_on_stop[stage]) for stage in Stage}
        for entries in _on_stop.values():
            entries.clear()
        pending = list(_timers)
        _timers.clear()
    try:
        for stage in Stage:
            started = clock.monotonic()
            if stage == Stage.CANCEL:
                for t in pending:
                    if t.at_stop == "cancel":
                        _run_step(f"cancel {t.name}", t.cancel)
            elif stage == Stage.FIRE_PENDING:
                for t in pending:
                    if t.at_stop == "fire":
                        _run_step(t.name, t.fire_now)
            elif stage == Stage.RELEASE_HELD:
                release_held()
            for handle in registered[stage]:
                _run_step(handle.name, handle.fn)
            took = clock.monotonic() - started
            if took > STAGE_LIMIT_S:
                _log().warning(f"Stop: {stage.name} took {took:.1f} s")
    finally:
        with _LOCK:
            _stopping = False


# --- timers ----------------------------------------------------------------------


class Timer:
    """A one-shot timer a Run owns (cancel() / is_alive() like a Timer).

    Its function runs once at most: from the timer while its Run is on, or
    from Stop (at once, with at_stop="fire"); never after cancel(), never
    after its Run stopped.
    """

    def __init__(
        self,
        name: str,
        seconds: float,
        fn: Callable[..., Any],
        args: tuple,
        at_stop: Literal["cancel", "fire"],
    ) -> None:
        self.name = name
        self.at_stop = at_stop
        self.run = _number
        self._fn = fn
        self._args = args
        self._done = False
        self._lock = threading.Lock()
        self._inner: Any = None
        with _LOCK:
            _timers.append(self)
        self._inner = threads.main_timer(name, seconds, self._timeout)

    def _claim(self) -> bool:
        with self._lock:
            if self._done:
                return False
            self._done = True
        with _LOCK:
            if self in _timers:
                _timers.remove(self)
        return True

    def _timeout(self) -> None:
        if not self._claim():
            return
        # A timer made outside a Run (an editor test) runs until a Run
        # begins; one made in a Run runs only while that Run is on.
        if self.run != _number:
            return
        self._fn(*self._args)

    def _stop_inner(self) -> None:
        if self._inner is not None:
            self._inner.cancel()

    def cancel(self) -> None:
        """It won't run."""
        if self._claim():
            self._stop_inner()

    def fire_now(self) -> None:
        """It runs now instead of later (once)."""
        if self._claim():
            self._stop_inner()
            self._fn(*self._args)

    def is_alive(self) -> bool:
        """True until it has run or been cancelled."""
        return not self._done


def timer(
    name: str,
    seconds: float,
    fn: Callable[..., Any],
    *args: object,
    at_stop: Literal["cancel", "fire"] = "cancel",
) -> Timer:
    """Calls fn(*args) on the main thread after seconds (see Timer).

    at_stop="cancel": Stop cancels it (Tempo, Double Tap, Smart Toggle).
    at_stop="fire": Stop runs it at once, before keys are released and the
    drivers reset (a pulse's release).
    """
    return Timer(name, seconds, fn, args, at_stop)


def pending_timers() -> list[Timer]:
    """Timers that have neither run nor been cancelled (for rule checks)."""
    with _LOCK:
        return list(_timers)


# --- loops -----------------------------------------------------------------------


def loop(
    name: str,
    fn: Callable[..., Any],
    *args: object,
    stop: Callable[[], None] | None = None,
) -> threading.Thread:
    """Starts fn(run, *args) on a named thread (gremlin.threads).

    fn gets the current Run's number and must end once alive(run) is False;
    stop is the quick request that asks it to end sooner (threads.start).
    """
    return threads.start(name, fn, _number, *args, stop=stop)


# --- held keys and mouse buttons -------------------------------------------------


@dataclass
class _Held:
    owner: object
    release: Callable[[], Any]


@contextlib.contextmanager
def owning(owner: object) -> Iterator[None]:
    """Output this thread holds down meanwhile belongs to owner (a macro)."""
    before = getattr(_owner, "value", None)
    _owner.value = owner
    try:
        yield
    finally:
        _owner.value = before


def current_owner() -> object:
    """Who holds what this thread presses now (None: no one in particular)."""
    return getattr(_owner, "value", None)


def hold(
    owner: object, kind: str, ident: Hashable, release_fn: Callable[[], Any]
) -> None:
    """An output is down now; release_fn() lets go of it at Stop.

    kind is "key" or "mouse"; ident tells outputs of one kind apart (a scan
    code and extended flag, a mouse button). Outside a Run nothing is
    tracked (decision R4), except that an output an owner (a macro) presses
    after its Run stopped (a step stuck in a driver through Stop) is let go
    of at once instead of staying down.
    """
    if not _running:
        if owner is not None:
            _release([_Held(owner, release_fn)])
        return
    with _LOCK:
        _held.pop((kind, ident), None)  # to the end: released first
        _held[(kind, ident)] = _Held(owner, release_fn)


def let_go(owner: object, kind: str, ident: Hashable) -> None:
    """The output was released normally (by owner or anyone else)."""
    del owner  # whoever lets go, it is up now
    with _LOCK:
        _held.pop((kind, ident), None)


def _release(entries: list[_Held]) -> None:
    for entry in reversed(entries):
        # One failing release must not keep the others (or the rest of Stop)
        # from running.
        try:
            entry.release()
        except Exception:
            _log().exception("Could not release a held key or mouse button")


def release_owner(owner: object) -> None:
    """Lets go of what owner still holds (a macro that ended early)."""
    with _LOCK:
        keys = [key for key, entry in _held.items() if entry.owner is owner]
        entries = [_held.pop(key) for key in keys]
    _release(entries)


def release_held() -> None:
    """Lets go of everything still held, last pressed first."""
    with _LOCK:
        entries = list(_held.values())
        _held.clear()
    _release(entries)


def held() -> list[tuple[str, Hashable]]:
    """(kind, ident) of every output still held, in press order."""
    with _LOCK:
        return list(_held)


def _reset_for_tests() -> None:
    """Forgets everything (test isolation only; not part of a Stop)."""
    global _running, _stopping
    with _LOCK:
        _running = False
        _stopping = False
        for entries in _on_stop.values():
            entries.clear()
        timers_left = list(_timers)
        _timers.clear()
        _held.clear()
    for t in timers_left:
        with contextlib.suppress(Exception):
            t.cancel()
