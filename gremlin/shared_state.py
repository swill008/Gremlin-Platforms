# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from gremlin import threads

if TYPE_CHECKING:
    from gremlin import profile


"""Stores global state that needs to be shared between various
parts of the program.

This is ugly but the only sane way to do this at the moment.
"""

# Who holds input highlighting off (Run, Listen, macro Record, Calibration,
# OSC Add). It is suspended while any of them does (03 S114, 09 S33).
_highlight_holders: set[str] = set()

# Delayed releases still waiting, by holder (Listen lets go after 2 s).
_release_timers: dict[str, threading.Timer] = {}

# Guards the two above: a delayed release runs on a timer thread.
_highlight_lock = threading.Lock()

# True while a profile is running (Gremlin toggled on)
_runtime_active = False

# Holds the currently active profile
current_profile: None | profile.Profile = None


def suspend_input_highlighting() -> bool:
    """Returns whether or not input highlighting is suspended.

    :return True if input's are not automatically selected, False otherwise
    """
    return bool(_highlight_holders)


def input_highlighting_holders() -> set[str]:
    """Who holds input highlighting off right now."""
    with _highlight_lock:
        return set(_highlight_holders)


def _cancel_release(holder: str) -> None:
    timer = _release_timers.pop(holder, None)
    if timer is not None:
        timer.cancel()


def hold_input_highlighting(holder: str) -> None:
    """Suspends input highlighting until holder releases it (a pending
    delayed release by the same holder is cancelled)."""
    with _highlight_lock:
        _cancel_release(holder)
        _highlight_holders.add(holder)


def release_input_highlighting(holder: str, delay: float = 0) -> None:
    """Lets go of holder's hold, after delay seconds when given; highlighting
    returns only when no one else holds it."""
    with _highlight_lock:
        _cancel_release(holder)
        if delay <= 0 or holder not in _highlight_holders:
            _highlight_holders.discard(holder)
            return
        timer: threading.Timer | None = None

        def release() -> None:
            with _highlight_lock:
                # Not if a newer hold or release replaced this one.
                if _release_timers.get(holder) is timer:
                    del _release_timers[holder]
                    _highlight_holders.discard(holder)

        timer = threads.timer("input highlighting", delay, release)
        _release_timers[holder] = timer


def set_suspend_input_highlighting(value: bool) -> None:
    """Clears every hold (and pending release), then holds highlighting off
    under "set" if value. For tests putting the state back; the program
    holds and releases by name."""
    with _highlight_lock:
        for holder in list(_release_timers):
            _cancel_release(holder)
        _highlight_holders.clear()
        if value:
            _highlight_holders.add("set")


def runtime_active() -> bool:
    """Returns whether Gremlin is currently running a profile."""
    return _runtime_active


def set_runtime_active(value: bool) -> None:
    """Records whether a profile is running."""
    global _runtime_active
    _runtime_active = bool(value)
