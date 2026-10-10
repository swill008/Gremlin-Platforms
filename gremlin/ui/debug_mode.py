# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Red debug mode: while Diagnostic logs is ALL, the Live log feed runs or
tracing is on (Live Log Reader › Trace),
every window shows a subtle red frame with a DEBUG badge (DebugFrame.qml).

The frame is added to each program window by install(): new windows are
picked up when they get focus and by a slow check. It sits at the window
root, so Button Map exports and prints (which grab the page, not the
window) never include it; the eyedropper hides it while it samples
(hidden_frames)."""

from __future__ import annotations

import contextlib
from collections.abc import Iterator

from PySide6 import QtCore, QtGui, QtQml, QtQuick

import gremlin.ui.type_aliases as ta
from gremlin import log_feed, trace

QML_IMPORT_NAME = "Gremlin.UI"
QML_IMPORT_MAJOR_VERSION = 1

FRAME_NAME = "gremlinDebugFrame"


class _Signals(QtCore.QObject):
    changed = QtCore.Signal()


_SIGNALS: _Signals | None = None


def _signals() -> _Signals:
    global _SIGNALS
    if _SIGNALS is None:
        _SIGNALS = _Signals()
        from gremlin.ui.log_option import _notifier

        _notifier().changed.connect(_SIGNALS.changed)
        log_feed.add_listener(_SIGNALS.changed.emit)
        trace.on_change(_SIGNALS.changed.emit)
    return _SIGNALS


def is_active() -> bool:
    """Diagnostic logs is ALL, the Live log feed is running, or tracing is on."""
    if log_feed.active() or trace.enabled():
        return True
    from gremlin.config import Configuration
    from gremlin.ui.log_option import (
        DEFAULT_LEVEL,
        LOG_GROUP,
        LOG_NAME,
        LOG_SECTION,
        normalize_level,
    )

    cfg = Configuration()
    value = (
        cfg.value(LOG_SECTION, LOG_GROUP, LOG_NAME)
        if cfg.exists(LOG_SECTION, LOG_GROUP, LOG_NAME) else DEFAULT_LEVEL
    )
    return normalize_level(value) == "ALL"


@ta.QmlElement
class DebugMode(QtCore.QObject):
    """For QML: whether red debug mode is on."""

    activeChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        _signals().changed.connect(self.activeChanged)

    @QtCore.Property(bool, notify=activeChanged)
    def active(self) -> bool:
        return is_active()


class _Installer(QtCore.QObject):
    """Adds DebugFrame.qml to every program window."""

    def __init__(self, app: QtGui.QGuiApplication) -> None:
        super().__init__(app)
        self._component: QtQml.QQmlComponent | None = None
        app.focusWindowChanged.connect(lambda _w: self.scan())
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(1500)
        self._timer.timeout.connect(self.scan)
        self._timer.start()

    def scan(self) -> None:
        for window in QtGui.QGuiApplication.topLevelWindows():
            if isinstance(window, QtQuick.QQuickWindow):
                self._add(window)

    def _add(self, window: QtQuick.QQuickWindow) -> None:
        root = window.contentItem()
        if root is None or root.findChild(QtQuick.QQuickItem, FRAME_NAME):
            return
        engine = QtQml.qmlEngine(window)
        if engine is None:
            return
        if self._component is None or self._component.engine() is not engine:
            from gremlin.util import resource_path

            path = resource_path("qml/DebugFrame.qml")
            self._component = QtQml.QQmlComponent(
                engine, QtCore.QUrl.fromLocalFile(path)
            )
        frame = self._component.create(QtQml.qmlContext(window))
        if not isinstance(frame, QtQuick.QQuickItem):
            return
        frame.setObjectName(FRAME_NAME)
        # Owned by the window from now on.
        QtQml.QQmlEngine.setObjectOwnership(
            frame, QtQml.QQmlEngine.ObjectOwnership.CppOwnership
        )
        frame.setParent(root)
        frame.setParentItem(root)


_INSTALLER: _Installer | None = None


def install(app: QtGui.QGuiApplication) -> None:
    global _INSTALLER
    if _INSTALLER is None:
        _INSTALLER = _Installer(app)
        _INSTALLER.scan()


@contextlib.contextmanager
def hidden_frames(window: object) -> Iterator[None]:
    """Hide the window's debug frame (e.g. while the eyedropper samples)."""
    if not isinstance(window, QtQuick.QQuickWindow):
        yield
        return
    root = window.contentItem()
    frame = root.findChild(QtQuick.QQuickItem, FRAME_NAME) if root else None
    if frame is None:
        yield
        return
    before = frame.opacity()
    frame.setOpacity(0.0)
    try:
        yield
    finally:
        frame.setOpacity(before)
