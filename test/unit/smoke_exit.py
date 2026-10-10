# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Ends an off-screen smoke script: releases Qt first, then os._exit(code).

A bare os._exit while windows and the QML engine are alive leaves Qt's
clean-up to DLL unload, which can crash in Qt6Gui.dll (AUD-THREADS-01). The
same steps as joystick_gremlin.release_qt, but a stuck or failing step still
ends the process with the script's own exit code.
"""

from __future__ import annotations

import gc
import os
import sys
import threading

_LIMIT_S = 3.0


def smoke_exit(code: int = 0, limit: float = _LIMIT_S) -> None:
    """Closes the windows, deletes the QML engines, lets the application go,
    then ends the process with code. Never returns."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.flush()
        except Exception:
            pass
    guard = threading.Timer(limit, os._exit, (code,))
    guard.daemon = True
    guard.start()
    try:
        _release_qt()
    except BaseException:
        pass
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.flush()
        except Exception:
            pass
    os._exit(code)


def _release_qt() -> None:
    qt_core = sys.modules.get("PySide6.QtCore")
    if qt_core is None:
        return
    app = qt_core.QCoreApplication.instance()
    if app is None:
        return
    qt_gui = sys.modules.get("PySide6.QtGui")
    if qt_gui is not None and isinstance(app, qt_gui.QGuiApplication):
        for window in qt_gui.QGuiApplication.topLevelWindows():
            window.hide()
            window.destroy()
    qt_qml = sys.modules.get("PySide6.QtQml")
    if qt_qml is not None:
        engines = [o for o in gc.get_objects() if isinstance(o, qt_qml.QQmlEngine)]
        for engine in engines:
            try:
                engine.deleteLater()
            except RuntimeError:
                pass  # Already deleted on the C++ side.
        del engines
    qt_core.QCoreApplication.sendPostedEvents(
        None, qt_core.QEvent.Type.DeferredDelete
    )
    gc.collect()
    app.shutdown()
