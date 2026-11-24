# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Gives memory back while the main window is hidden to the tray.

While Gremlin runs a profile from the tray nobody sees its pages, so:
the main window unloads them (Main.qml enterTray: Home, the device pages,
and Device Bindings unless it holds unsaved edits), Qt drops the
hidden window's graphics, unused compiled QML and garbage (memory_release,
01 S199), and Windows is
told it may take back the memory pages nothing is using. Showing the window
again (leaveTray) loads the pages afresh. The profile keeps running
throughout: none of this touches the input or output side.
"""

from __future__ import annotations

import contextlib
import ctypes
import ctypes.wintypes
import logging

from PySide6 import QtCore, QtGui, QtQml

from gremlin.ui import memory_release

# Let the pages finish unloading before the clean-up.
_SETTLE_MS = 400


def _note(text: str) -> None:
    """A Window trace step; tracing can never break the tray."""
    with contextlib.suppress(Exception):
        from gremlin.ui import window_trace

        window_trace.note("Main window", text)


def enter_tray(window: QtGui.QWindow, engine: QtQml.QQmlEngine | None) -> bool:
    """The window was hidden to the tray: unload its pages, then clean up.
    False when the window could not be told (its pages stay loaded).
    Whether to enter is the caller's choice (SystemTrayIcon._sync_tray)."""
    if not QtCore.QMetaObject.invokeMethod(window, "enterTray"):
        return False
    QtCore.QTimer.singleShot(_SETTLE_MS, lambda: release(window, engine))
    return True


def leave_tray(window: QtGui.QWindow) -> bool:
    """The window is shown again: load its pages. False when the window
    could not be told."""
    return bool(QtCore.QMetaObject.invokeMethod(window, "leaveTray"))


def release(window: QtGui.QWindow, engine: QtQml.QQmlEngine | None) -> None:
    """Drops what a hidden window does not need. Does nothing once the
    window is visible again or the program is closing."""
    if window.isVisible() or QtCore.QCoreApplication.closingDown():
        _note("tray: release skipped")
        return
    memory_release.release_unused(engine)
    if isinstance(window, QtGui.QWindow) and hasattr(window, "releaseResources"):
        window.releaseResources()
    trim_working_set()
    _note("tray: release done")


def trim_working_set() -> None:
    """Lets Windows take back the memory pages nothing is using now; they
    come back from memory as they are touched again."""
    try:
        kernel32 = ctypes.windll.kernel32
        current = kernel32.GetCurrentProcess
        current.restype = ctypes.wintypes.HANDLE
        trim = kernel32.SetProcessWorkingSetSize
        trim.argtypes = [ctypes.wintypes.HANDLE, ctypes.c_size_t, ctypes.c_size_t]
        trim.restype = ctypes.wintypes.BOOL
        trim(current(), ctypes.c_size_t(-1), ctypes.c_size_t(-1))
    except (AttributeError, OSError):
        logging.getLogger("system").debug("Working set trim unavailable")


def let_hidden_window_release_graphics(window: QtGui.QWindow) -> None:
    """A hidden main window lets go of its scene graph and graphics; they
    are made again when it shows."""
    for name in ("setPersistentSceneGraph", "setPersistentGraphics"):
        setter = getattr(window, name, None)
        if setter is not None:
            setter(False)
