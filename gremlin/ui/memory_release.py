# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Gives back the QML memory nothing uses any more (01 S199,
D-01-RELEASE-UNUSED).

Every page load leaves unused compiled component data in the engine's
cache, and the JavaScript garbage collection runs late; neither is undone
while the window is shown (claude/audits/2026-11-24-upstream-since-fork/
native-growth.md). So a short while after a main-window page unloads
(PageLoader.qml) or a tool window closes (helpers.js createComponent), and
when the window hides to the tray (tray_memory), release_unused() runs the
JavaScript collection, Python's, then the component cache trim. A burst of
unloads and closes runs it once, DELAY_MS after the last one.
"""

from __future__ import annotations

import contextlib
import gc

from PySide6 import QtCore, QtQml

# After the last unload or close; a page shown again within it is not
# rebuilt from a trimmed cache (measured 2026-11-23, see the S199 row).
DELAY_MS = 1500

_NAME = "gremlinMemoryRelease"


def _note(text: str) -> None:
    """A Window trace step; tracing can never break the release."""
    with contextlib.suppress(Exception):
        from gremlin.ui import window_trace

        window_trace.note("Main window", text)


def release_unused(engine: QtQml.QQmlEngine | None) -> bool:
    """JavaScript garbage collection, Python's, then the QML component
    cache trim. Main thread. A release waiting on the timer is dropped:
    this one covers it. False when there was nothing to do it on (no
    engine, or the program is closing)."""
    if engine is None or QtCore.QCoreApplication.closingDown():
        return False
    waiting = of(engine)
    if waiting is not None:
        waiting.cancel()
    engine.collectGarbage()
    gc.collect()
    engine.trimComponentCache()
    return True


class MemoryRelease(QtCore.QObject):
    """The QML context property memoryRelease: request() after a page
    unloads or a window closes. One per engine, a child of it, with one
    single-shot timer that each request restarts."""

    def __init__(self, engine: QtQml.QQmlEngine) -> None:
        super().__init__(engine)
        self.setObjectName(_NAME)
        self._engine = engine
        self._timer = QtCore.QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(DELAY_MS)
        self._timer.timeout.connect(self._run)

    @QtCore.Slot()
    def request(self) -> None:
        """A page unloaded or a window closed: release DELAY_MS after the
        last such request."""
        self._timer.start()

    def cancel(self) -> None:
        self._timer.stop()

    def pending(self) -> bool:
        return self._timer.isActive()

    def _run(self) -> None:
        if release_unused(self._engine):
            _note("unused QML memory released")


def of(engine: QtQml.QQmlEngine) -> MemoryRelease | None:
    """The engine's MemoryRelease, None before expose()."""
    found = engine.findChild(QtCore.QObject, _NAME)
    return found if isinstance(found, MemoryRelease) else None


def expose(engine: QtQml.QQmlEngine) -> MemoryRelease:
    """Sets the QML context property memoryRelease (before Main.qml
    loads). Main thread."""
    release = of(engine) or MemoryRelease(engine)
    engine.rootContext().setContextProperty("memoryRelease", release)
    return release
