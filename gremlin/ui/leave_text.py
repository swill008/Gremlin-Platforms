# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Leaving a text box (01 S134, D-01-LEAVE-TEXT).

One owner for every window: a text box being typed in is left by Esc or
by a press anywhere outside it, and what was typed is kept (the box saves
as it does whenever it loses the focus). A box's own Esc handling (an
inline Rename's cancel) runs first. Esc taken by a text box never reaches
the window's shortcuts, so where Esc closes the window the first Esc only
leaves the box. A window (or an item around the box) with
``leaveTextOnEscape: false`` keeps Esc doing nothing there (Module Setup,
03 S50); a press outside still leaves the box.
"""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtQuick

_OPT_OUT = "leaveTextOnEscape"


def _editor(window: QtQuick.QQuickWindow) -> QtQuick.QQuickItem | None:
    """The writable text box being typed in, if any."""
    item = window.activeFocusItem()
    if item is None or not (
        item.inherits("QQuickTextInput") or item.inherits("QQuickTextEdit")
    ):
        return None
    if item.property("readOnly") or not item.isEnabled() or not item.isVisible():
        return None
    return item


def _is_within(item: QtQuick.QQuickItem | None, ancestor: QtQuick.QQuickItem) -> bool:
    while item is not None:
        if item is ancestor:
            return True
        item = item.parentItem()
    return False


def _area(editor: QtQuick.QQuickItem) -> QtQuick.QQuickItem:
    """What counts as inside the box: the box, with its own scroll area
    (scroll bars) or its spin box / combo box."""
    parent = editor.parentItem()
    if parent is not None and (
        parent.inherits("QQuickSpinBox") or parent.inherits("QQuickComboBox")
    ):
        return parent
    # A TextArea alone in a Flickable or ScrollView: that is its scrolling.
    if parent is not None and editor.inherits("QQuickTextArea"):
        flickable = parent.parentItem()
        if (
            flickable is not None
            and flickable.inherits("QQuickFlickable")
            and len(parent.childItems()) == 1
        ):
            view = flickable.parentItem()
            if view is not None and view.inherits("QQuickScrollView"):
                return view
            return flickable
    return editor


def _contains(item: QtQuick.QQuickItem, scene_pos: QtCore.QPointF) -> bool:
    return item.contains(item.mapFromScene(scene_pos))


def _on_popup(
    window: QtQuick.QQuickWindow, editor: QtQuick.QQuickItem, scene_pos: QtCore.QPointF
) -> bool:
    """True when the press lands on an open popup or menu the box isn't
    in (the box's own right-click menu acts on the box). A modal popup's
    dimmer isn't a popup: a press there leaves the box, as does a press
    elsewhere in the popup the box is in."""
    root = window.contentItem()
    if root is None:
        return False
    for overlay in root.childItems():
        if not overlay.inherits("QQuickOverlay") or not overlay.isVisible():
            continue
        for popup in overlay.childItems():
            if (
                popup.inherits("QQuickPopupItem")
                and popup.isVisible()
                and not _is_within(editor, popup)
                and _contains(popup, scene_pos)
            ):
                return True
    return False


def _escape_opted_out(
    window: QtQuick.QQuickWindow, editor: QtQuick.QQuickItem
) -> bool:
    if window.property(_OPT_OUT) is False:
        return True
    item: QtQuick.QQuickItem | None = editor
    while item is not None:
        if item.property(_OPT_OUT) is False:
            return True
        item = item.parentItem()
    return False


def _leave(window: QtQuick.QQuickWindow, editor: QtQuick.QQuickItem) -> None:
    """Takes the focus off the box; it saves as on any loss of focus."""
    editor.setFocus(False)
    if editor.hasActiveFocus():
        root = window.contentItem()
        if root is not None:
            root.forceActiveFocus(QtCore.Qt.FocusReason.OtherFocusReason)


def _is_plain_escape(event: QtGui.QKeyEvent) -> bool:
    modifiers = event.modifiers() & ~QtCore.Qt.KeyboardModifier.KeypadModifier
    return (
        event.key() == QtCore.Qt.Key.Key_Escape
        and modifiers == QtCore.Qt.KeyboardModifier.NoModifier
    )


class LeaveTextFilter(QtCore.QObject):
    """Application-wide event filter; install once on the application."""

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        kind = event.type()
        if kind == QtCore.QEvent.Type.MouseButtonPress:
            if isinstance(watched, QtQuick.QQuickWindow):
                self._press(watched, event)  # type: ignore[arg-type]
            return False
        if kind == QtCore.QEvent.Type.ShortcutOverride:
            return self._shortcut_override(watched, event)  # type: ignore[arg-type]
        if kind == QtCore.QEvent.Type.KeyPress and isinstance(
            watched, QtQuick.QQuickWindow
        ):
            return self._escape(watched, event)  # type: ignore[arg-type]
        return False

    def _press(self, window: QtQuick.QQuickWindow, event: QtGui.QMouseEvent) -> None:
        editor = _editor(window)
        if editor is None:
            return
        pos = event.scenePosition()
        if _contains(_area(editor), pos) or _on_popup(window, editor, pos):
            return
        # Before the press is delivered: the box saves first, then the
        # pressed control acts. The press itself is never taken.
        _leave(window, editor)

    def _shortcut_override(
        self, watched: QtCore.QObject, event: QtGui.QKeyEvent
    ) -> bool:
        # Esc in a text box is the box's key, not a window shortcut's.
        if not isinstance(watched, QtQuick.QQuickItem) or not _is_plain_escape(event):
            return False
        # Not watched.window(): PySide6 then drops its wrapper of the window.
        window = QtGui.QGuiApplication.focusWindow()
        if not isinstance(window, QtQuick.QQuickWindow):
            return False
        if _editor(window) is not watched:
            return False
        if _escape_opted_out(window, watched):
            return False
        event.accept()
        return True

    def _escape(self, window: QtQuick.QQuickWindow, event: QtGui.QKeyEvent) -> bool:
        if not _is_plain_escape(event):
            return False
        editor = _editor(window)
        if editor is None or _escape_opted_out(window, editor):
            return False
        # The box gets the Esc (its own Keys.onEscapePressed, e.g. a Rename
        # cancel) and it goes no further: nothing around the box acts on it.
        QtCore.QCoreApplication.sendEvent(editor, event)
        if editor.hasActiveFocus():
            _leave(window, editor)
        return True


def install(app: QtGui.QGuiApplication) -> LeaveTextFilter:
    """Installs the filter on the application; keep the returned object."""
    leave = LeaveTextFilter(app)
    app.installEventFilter(leave)
    return leave
