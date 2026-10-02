# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Gives memory back while the main window is hidden to the tray.

While Gremlin runs a profile from the tray nobody sees its pages, so:
the main window unloads them (Main.qml enterTray: Home, Scripts, Profile
Settings, and Configuration unless it holds unsaved edits), Qt drops the
hidden window's graphics, unused compiled QML and garbage, and Windows is
told it may take back the memory pages nothing is using. Showing the window
again (leaveTray) loads the pages afresh. The profile keeps running
throughout: none of this touches the input or output side.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import gc
import logging

from PySide6 import QtCore, QtGui, QtQml

# Let the pages finish unloading before the clean-up.
_SETTLE_MS = 400


def enter_tray(window: QtGui.QWindow, engine: QtQml.QQmlEngine | None) -> None:
    """The window was hidden to the tray: unload its pages, then clean up."""
    if window.isVisible():
        return
    QtCore.QMetaObject.invokeMethod(window, "enterTray")
    QtCore.QTimer.singleShot(_SETTLE_MS, lambda: release(window, engine))


def leave_tray(window: QtGui.QWindow) -> None:
    """The window is shown again: load its pages."""
    QtCore.QMetaObject.invokeMethod(window, "leaveTray")


def release(window: QtGui.QWindow, engine: QtQml.QQmlEngine | None) -> None:
    """Drops what a hidden window does not need. Does nothing once the
    window is visible again or the program is closing."""
    if window.isVisible() or QtCore.QCoreApplication.closingDown():
        return
    if engine is not None:
        engine.collectGarbage()
    gc.collect()
    if isinstance(window, QtGui.QWindow) and hasattr(window, "releaseResources"):
        window.releaseResources()
    if engine is not None:
        engine.trimComponentCache()
    trim_working_set()


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
