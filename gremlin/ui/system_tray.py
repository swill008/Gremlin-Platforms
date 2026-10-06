# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import contextlib
import ctypes
import logging

import win32api
import win32con
import win32gui
from PySide6 import (
    QtCore,
    QtGui,
)

import gremlin.util
from gremlin.config import Configuration
from gremlin.ui import tray_memory, window_placement
from gremlin.ui.backend import Backend

# Private message the tray icon uses to report activity to the helper window.
_WM_TRAY = win32con.WM_USER + 20

# Shell_NotifyIcon values pywin32 does not expose.
# https://learn.microsoft.com/en-us/windows/win32/api/shellapi/ns-shellapi-notifyicondataw
_NOTIFYICON_VERSION_4 = 4
_NIF_SHOWTIP = 0x00000080

# Tray menu command identifiers.
_ID_SHOW = 1023
_ID_TOGGLE = 1024
_ID_QUIT = 1025


def _extract_screen_coordinates(wparam: int) -> tuple[int, int]:
    """Returns the screen position packed into a message parameter."""
    return (ctypes.c_short(wparam).value, ctypes.c_short(wparam >> 16).value)


class SystemTrayIcon(QtCore.QObject):
    """Tray icon for Gremlin, implemented using Win32 functionality.

    Supports hiding the Gremlin UI to the system tray on minimize and close. The
    context menu exposes basic UI functionality. The icon reflects Gremlin's
    activation state.
    """

    def __init__(self, window: QtGui.QWindow) -> None:
        super().__init__()

        self._window = window
        self._backend = Backend()
        self._icon_present = False
        self._last_window_mode = QtGui.QWindow.Visibility.Windowed
        self._taskbar_created = 0
        self._instance = 0
        self._class_atom = None
        self._hwnd = 0
        self._idle_icon = 0
        self._active_icon = 0
        # Hidden to the tray, with its pages unloaded (tray_memory).
        self._trayed = False

        try:
            self._create_resources()
        except win32gui.error as e:
            logging.getLogger("system").warning(
                f"Failed to create the system tray icon: {e.strerror}"
            )
            return

        self._window.visibilityChanged.connect(self._window_mode_changed_cb)
        tray_memory.let_hidden_window_release_graphics(self._window)
        self._backend.activityChanged.connect(self._gremlin_status_change_cb)
        self._window.installEventFilter(self)
        self._window_mode_changed_cb(self._window.visibility())

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        # Minimize to tray covers the X too: the window hides, the profile
        # keeps running, and Exit (File menu or tray menu) quits. Only the
        # X (a close from Windows: spontaneous) hides; the close a quit
        # makes passes, or Exit would only hide the window (01 Q2).
        if (
            event.type() == QtCore.QEvent.Type.Close
            and event.spontaneous()
            and self._icon_present
            and Configuration().exists("global", "general", "minimize-to-tray")
            and Configuration().value("global", "general", "minimize-to-tray")
        ):
            event.ignore()
            # onClosing (which saves it) does not run: save the place here
            # (01 Q3).
            window_placement.save_window(self._window)
            self._window.hide()
            self._tell_once_still_running()
            return True
        return super().eventFilter(watched, event)

    def release_resources(self) -> None:
        if self._hwnd:
            with contextlib.suppress(win32gui.error):
                win32gui.DestroyWindow(self._hwnd)
            self._hwnd = 0
        if self._class_atom is not None:
            with contextlib.suppress(win32gui.error):
                win32gui.UnregisterClass(self._class_atom, self._instance)
            self._class_atom = None
        for icon in (self._idle_icon, self._active_icon):
            if icon:
                with contextlib.suppress(win32gui.error):
                    win32gui.DestroyIcon(icon)
        self._idle_icon = 0
        self._active_icon = 0

    def restore_window(self) -> None:
        self._window.setVisibility(self._last_window_mode)
        self._window.raise_()
        self._window.requestActivate()

    def _create_resources(self) -> None:
        self._idle_icon = self._create_icon("gfx/icon.ico")
        self._active_icon = self._create_icon("gfx/icon_active.ico")

        self._taskbar_created = win32gui.RegisterWindowMessage("TaskbarCreated")
        self._instance = win32api.GetModuleHandle(None)
        wc = win32gui.WNDCLASS()
        wc.hInstance = self._instance
        wc.lpszClassName = "JoystickGremlinSystemTray"
        wc.lpfnWndProc = {
            _WM_TRAY: self._system_tray_event_cb,
            win32con.WM_COMMAND: self._handle_context_menu_cb,
            win32con.WM_DESTROY: self._destroy_system_tray_cb,
            self._taskbar_created: self._taskbar_created_cb,
        }
        self._class_atom = win32gui.RegisterClass(wc)
        self._hwnd = win32gui.CreateWindowEx(
            win32con.WS_EX_TOOLWINDOW | win32con.WS_EX_NOACTIVATE,
            self._class_atom,
            "Gremlin-Platforms",
            win32con.WS_OVERLAPPED,
            0,
            0,
            0,
            0,
            0,
            0,
            wc.hInstance,
            None,
        )
        self._add_icon()

    def _create_icon(self, relative_path: str) -> int:
        size = win32api.GetSystemMetrics(win32con.SM_CXSMICON)
        return win32gui.LoadImage(
            0,
            gremlin.util.resource_path(relative_path),
            win32con.IMAGE_ICON,
            size,
            size,
            win32con.LR_LOADFROMFILE,
        )

    def _current_icon(self) -> int:
        return self._active_icon if self._backend.gremlinActive else self._idle_icon

    def _add_icon(self) -> None:
        try:
            win32gui.Shell_NotifyIcon(
                win32gui.NIM_ADD,
                (
                    self._hwnd,
                    0,
                    win32gui.NIF_ICON
                    | win32gui.NIF_MESSAGE
                    | win32gui.NIF_TIP
                    | _NIF_SHOWTIP,
                    _WM_TRAY,
                    self._current_icon(),
                    "Gremlin-Platforms",
                ),
            )
            win32gui.Shell_NotifyIcon(
                win32gui.NIM_SETVERSION,
                (self._hwnd, 0, 0, 0, 0, "", "", _NOTIFYICON_VERSION_4),
            )
            self._icon_present = True
        except win32gui.error:
            self._icon_present = False
            logging.getLogger("system").warning(
                "Failed to add the system tray icon", exc_info=True
            )

    def _tell_once_still_running(self) -> None:
        """The first time the X hides the window, say the program is still
        running (a tray balloon); never again after that."""
        cfg = Configuration()
        if not cfg.exists("global", "internal", "tray-notice-shown"):
            return
        if cfg.value("global", "internal", "tray-notice-shown"):
            return
        self.show_balloon(
            "Gremlin-Platforms is still running",
            "It is in the system tray. Exit from the tray icon's menu.",
        )
        cfg.set("global", "internal", "tray-notice-shown", True)

    def show_balloon(self, title: str, text: str) -> None:
        """A Windows notification from the tray icon."""
        with contextlib.suppress(win32gui.error):
            win32gui.Shell_NotifyIcon(
                win32gui.NIM_MODIFY,
                (
                    self._hwnd,
                    0,
                    win32gui.NIF_INFO,
                    _WM_TRAY,
                    self._current_icon(),
                    "Gremlin-Platforms",
                    text,
                    10000,
                    title,
                    win32gui.NIIF_INFO,
                ),
            )

    def _gremlin_status_change_cb(self) -> None:
        with contextlib.suppress(win32gui.error):
            win32gui.Shell_NotifyIcon(
                win32gui.NIM_MODIFY,
                (self._hwnd, 0, win32gui.NIF_ICON, _WM_TRAY, self._current_icon()),
            )

    def _window_mode_changed_cb(self, mode: QtGui.QWindow.Visibility) -> None:
        if mode in (
            QtGui.QWindow.Visibility.Windowed,
            QtGui.QWindow.Visibility.Maximized,
            QtGui.QWindow.Visibility.FullScreen,
        ):
            self._last_window_mode = mode

        # In the tray nobody sees the pages: give their memory back while
        # hidden, load them again when shown.
        if mode == QtGui.QWindow.Visibility.Hidden and self._icon_present:
            if not self._trayed:
                self._trayed = True
                tray_memory.enter_tray(self._window, self._backend.engine)
        elif mode != QtGui.QWindow.Visibility.Hidden and self._trayed:
            self._trayed = False
            tray_memory.leave_tray(self._window)

        if (
            mode == QtGui.QWindow.Visibility.Minimized
            and self._icon_present
            and Configuration().exists("global", "general", "minimize-to-tray")
            and Configuration().value("global", "general", "minimize-to-tray")
        ):
            self._window.hide()

    def _system_tray_event_cb(
        self, hwnd: int, msg: int, wparam: int, lparam: int
    ) -> int:
        match win32api.LOWORD(lparam):
            case win32con.WM_LBUTTONUP:
                self.restore_window()
            case win32con.WM_RBUTTONUP:
                self._show_menu(*_extract_screen_coordinates(wparam))
        return 0

    def _handle_context_menu_cb(
        self, hwnd: int, msg: int, wparam: int, lparam: int
    ) -> int:
        command = win32api.LOWORD(wparam)
        if command == _ID_SHOW:
            self._toggle_visibility()
        elif command == _ID_TOGGLE:
            self._toggle_run()
        elif command == _ID_QUIT:
            self._quit_gremlin()
        return 0

    def _toggle_run(self) -> None:
        """Run/Stop the same way as the toolbar (Main.qml toggleRun asks
        about an open action pane with changes first, 06 Q6)."""
        if not QtCore.QMetaObject.invokeMethod(self._window, "toggleRun"):
            self._backend.toggleActiveState()

    def _toggle_visibility(self) -> None:
        self._window.hide() if self._window.isVisible() else self.restore_window()

    def _taskbar_created_cb(
        self, hwnd: int, msg: int, wparam: int, lparam: int
    ) -> int:
        if self._icon_present:
            self._delete_icon()
        self._add_icon()
        return 0

    def _destroy_system_tray_cb(
        self, hwnd: int, msg: int, wparam: int, lparam: int
    ) -> int:
        self._delete_icon()
        return 0

    def _delete_icon(self) -> None:
        with contextlib.suppress(win32gui.error):
            win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, (self._hwnd, 0))
        self._icon_present = False

    def _show_menu(self, x: int, y: int) -> None:
        menu = win32gui.CreatePopupMenu()
        try:
            show_hide = (
                "Hide Gremlin-Platforms"
                if self._window.isVisible()
                else "Show Gremlin-Platforms"
            )
            win32gui.AppendMenu(menu, win32con.MF_STRING, _ID_SHOW, show_hide)
            win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, "")
            label = "Stop Profile" if self._backend.gremlinActive else "Run Profile"
            win32gui.AppendMenu(menu, win32con.MF_STRING, _ID_TOGGLE, label)
            win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, "")
            win32gui.AppendMenu(
                menu, win32con.MF_STRING, _ID_QUIT, "Exit Gremlin-Platforms"
            )
            with contextlib.suppress(win32gui.error):
                win32gui.SetForegroundWindow(self._hwnd)
            win32gui.TrackPopupMenu(
                menu,
                win32con.TPM_LEFTALIGN | win32con.TPM_RIGHTBUTTON,
                x,
                y,
                0,
                self._hwnd,
                None,
            )
            win32gui.PostMessage(self._hwnd, win32con.WM_NULL, 0, 0)
        finally:
            win32gui.DestroyMenu(menu)

    def _quit_gremlin(self) -> None:
        self.restore_window()
        self._backend.quitRequested.emit()
