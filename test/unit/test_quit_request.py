"""01 S173: the installer's quit request reaches the tray window, which
answers it and then quits the way the tray's Exit (File > Exit) does."""

from __future__ import annotations

from unittest import mock

import pytest
import win32gui
from PySide6 import QtCore

from gremlin.ui import system_tray


@pytest.fixture
def app() -> QtCore.QCoreApplication:
    return QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])


def _bare_tray() -> system_tray.SystemTrayIcon:
    # No real tray icon, window or backend: only the parts the request uses.
    tray = system_tray.SystemTrayIcon.__new__(system_tray.SystemTrayIcon)
    QtCore.QObject.__init__(tray)
    tray._hwnd = 0
    tray._quit_request = 0
    tray._taskbar_created = 0
    return tray


def _wndproc_map(tray: system_tray.SystemTrayIcon) -> dict:
    seen: dict = {}

    def register_class(wc: object) -> int:
        seen.update(wc.lpfnWndProc)
        return 1

    with (
        mock.patch.object(tray, "_create_icon", return_value=0),
        mock.patch.object(tray, "_add_icon"),
        mock.patch.object(win32gui, "RegisterClass", register_class),
        mock.patch.object(win32gui, "CreateWindowEx", return_value=0),
    ):
        tray._create_resources()
    return seen


def test_the_tray_window_handles_the_registered_quit_request() -> None:
    tray = _bare_tray()
    handlers = _wndproc_map(tray)
    request = win32gui.RegisterWindowMessage("GremlinPlatformsQuitRequest")
    assert request in handlers
    assert handlers[request] == tray._quit_request_cb


def test_the_request_is_answered_then_quits_from_the_event_loop(
    app: QtCore.QCoreApplication,
) -> None:
    tray = _bare_tray()
    handlers = _wndproc_map(tray)
    request = win32gui.RegisterWindowMessage("GremlinPlatformsQuitRequest")
    with mock.patch.object(tray, "_quit_gremlin") as quit_gremlin:
        # The installer waits on the answer: nothing quits inside it.
        assert handlers[request](0, request, 0, 0) == 1
        quit_gremlin.assert_not_called()
        deadline = QtCore.QDeadlineTimer(2000)
        while not quit_gremlin.called and not deadline.hasExpired():
            app.processEvents()
        quit_gremlin.assert_called_once_with()


def test_the_quit_is_the_tray_exit_path() -> None:
    # Shows the window, then the same signal File > Exit's quitGremlin uses.
    tray = _bare_tray()
    tray._backend = mock.Mock()
    with mock.patch.object(tray, "restore_window") as restore:
        tray._quit_gremlin()
    restore.assert_called_once_with("quit")  # the cause for the Window trace
    tray._backend.quitRequested.emit.assert_called_once_with()
