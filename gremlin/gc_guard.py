# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Python's cycle collector runs on the main thread only.

Left automatic, the collector runs on whichever thread happens to allocate
when its threshold is reached: the History writer, a device poller, any
worker. Objects it frees there are freed on that thread. A main-thread
QObject held in a reference cycle (a HardwareProfile with its labels timer,
CI run 38205139995) was freed on the History thread: Qt printed "Timers
cannot be stopped from another thread", the timer stayed registered on the
main thread and its next tick reached the freed object, an access violation.

install(app) turns the automatic collector off and collects from one
QTimer the application owns, so on the main thread, in the same steps the
automatic collector takes: the young generation each tick, the middle one
every THRESHOLD ticks, everything every THRESHOLD * THRESHOLD ticks. And
once when the application is about to quit, before the tear-down. Garbage
without a cycle is freed at once as always (reference counting), on the
thread that drops it; only cycles wait for the main thread.
"""

from __future__ import annotations

import gc

import shiboken6
from PySide6 import QtCore

# Milliseconds between collections.
INTERVAL_MS = 1000
# Collections of one generation before the next older one is collected.
THRESHOLD = 10

_timer: QtCore.QTimer | None = None
_app: QtCore.QCoreApplication | None = None
# Whether the automatic collector was on before install (None: not installed).
_was_enabled: bool | None = None


def collect() -> None:
    """One step, on the main thread: the oldest generation that is due."""
    _count0, count1, count2 = gc.get_count()
    if count2 >= THRESHOLD:
        gc.collect(2)
    elif count1 >= THRESHOLD:
        gc.collect(1)
    else:
        gc.collect(0)


def _about_to_quit() -> None:
    gc.collect()


def installed() -> bool:
    _forget_dead()
    return _timer is not None


def _forget_dead() -> None:
    """The application, and the timer with it, was deleted (tests make
    more than one): install again for the next one."""
    global _timer, _app
    if _timer is not None and not shiboken6.isValid(_timer):
        _timer = None
        _app = None


def install(app: QtCore.QCoreApplication) -> None:
    """Collects on app's (the main) thread from now on. Again: nothing,
    except that a collector someone turned back on is turned off again."""
    global _timer, _app, _was_enabled
    _forget_dead()
    if _timer is not None:
        gc.disable()
        return
    if _was_enabled is None:
        _was_enabled = gc.isenabled()
    gc.disable()
    # An app-owned QTimer, not threads.main_timer: this belongs to the
    # application, not to a Run (test_run_scope_only.py).
    timer = QtCore.QTimer(app)
    timer.setObjectName("gc_guard")
    timer.setInterval(INTERVAL_MS)
    timer.timeout.connect(collect)
    timer.start()
    app.aboutToQuit.connect(_about_to_quit)
    _timer = timer
    _app = app


def uninstall() -> None:
    """Back to the automatic collector (tests)."""
    global _timer, _app, _was_enabled
    _forget_dead()
    if _was_enabled:
        gc.enable()
    _was_enabled = None
    if _timer is None:
        return
    timer, app = _timer, _app
    _timer = None
    _app = None
    try:
        timer.stop()
        timer.deleteLater()
    except RuntimeError:  # the application, and the timer with it, is gone
        pass
    if app is not None:
        try:
            app.aboutToQuit.disconnect(_about_to_quit)
        except (RuntimeError, TypeError):
            pass
