# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import contextlib
import ctypes
import ctypes.wintypes
import logging
import typing
import uuid

if typing.TYPE_CHECKING:
    from gremlin import startup_entry

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

# The installer's request to quit (01 S173, installer/gremlin_platforms.iss
# AskToClose); the answer tells it the request was taken.
QUIT_REQUEST_NAME = "GremlinPlatformsQuitRequest"
QUIT_REQUEST_HANDLED = 1

# Tray menu command identifiers.
_ID_SHOW = 1023
_ID_TOGGLE = 1024
_ID_QUIT = 1025
_ID_SSM = 1026
_ID_DISPLAYS_OFF = 1027
_ID_START_WITH_WINDOWS = 1028

# Messages that say Windows showed the main window (01 S174).
_WM_SHOWWINDOW = 0x0018
_WM_WINDOWPOSCHANGED = 0x0047
_SWP_SHOWWINDOW = 0x0040

# Power messages to the tray's own window (records only, 01 S176).
_WM_POWERBROADCAST = 0x0218
_PBT_APMSUSPEND = 0x0004
_PBT_APMRESUMEAUTOMATIC = 0x0012
_PBT_POWERSETTINGCHANGE = 0x8013
_DEVICE_NOTIFY_WINDOW_HANDLE = 0
_GUID_CONSOLE_DISPLAY_STATE = uuid.UUID("6fe69556-704a-47a0-8f24-c28d936fda47")

_MAIN_WINDOW = "Main window"


class _WINDOWPOS(ctypes.Structure):
    _fields_ = (
        ("hwnd", ctypes.wintypes.HWND),
        ("hwndInsertAfter", ctypes.wintypes.HWND),
        ("x", ctypes.c_int),
        ("y", ctypes.c_int),
        ("cx", ctypes.c_int),
        ("cy", ctypes.c_int),
        ("flags", ctypes.wintypes.UINT),
    )


def _extract_screen_coordinates(wparam: int) -> tuple[int, int]:
    """Returns the screen position packed into a message parameter."""
    return (ctypes.c_short(wparam).value, ctypes.c_short(wparam >> 16).value)


def _note(text: str) -> None:
    """A Window trace step; tracing can never break the tray."""
    with contextlib.suppress(Exception):
        from gremlin.ui import window_trace

        window_trace.note(_MAIN_WINDOW, text)


def _warn(text: str) -> None:
    """A "Window:" warning in system.log (01 S175)."""
    with contextlib.suppress(Exception):
        from gremlin.ui import window_trace

        window_trace.warn(text)


def _register_display_notify(hwnd: int) -> int:
    """Asks Windows to tell the tray's window about display power changes
    (GUID_CONSOLE_DISPLAY_STATE); the handle to unregister, 0 on failure."""
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        register = user32.RegisterPowerSettingNotification
        register.restype = ctypes.wintypes.HANDLE
        register.argtypes = (
            ctypes.wintypes.HANDLE,
            ctypes.c_void_p,
            ctypes.wintypes.DWORD,
        )
        guid = (ctypes.c_ubyte * 16).from_buffer_copy(
            _GUID_CONSOLE_DISPLAY_STATE.bytes_le
        )
        return int(
            register(hwnd, ctypes.byref(guid), _DEVICE_NOTIFY_WINDOW_HANDLE) or 0
        )
    except (AttributeError, OSError):
        return 0


def _unregister_display_notify(handle: int) -> None:
    with contextlib.suppress(AttributeError, OSError):
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        unregister = user32.UnregisterPowerSettingNotification
        unregister.argtypes = (ctypes.wintypes.HANDLE,)
        unregister(handle)


def _display_state(l_param: int) -> str | None:
    """ "off", "on" or "dimmed" from a PBT_POWERSETTINGCHANGE message; None
    for another setting."""
    from gremlin import screen_saver_mode

    on = screen_saver_mode.display_state_on(l_param)
    if on is None:
        return None
    if not on:
        return "off"
    data = screen_saver_mode.POWERBROADCAST_SETTING.from_address(l_param).Data[0]
    return "dimmed" if data == 2 else "on"


class NativeShowFilter(QtCore.QAbstractNativeEventFilter):
    """Watches the main window's own Windows messages for a show Qt did not
    make (01 S174): WM_SHOWWINDOW with wParam 1, or WM_WINDOWPOSCHANGED with
    SWP_SHOWWINDOW. Sees every message of the process, so it checks the
    window handle first and only queues the follow-up, never acts inside
    the message."""

    def __init__(self, tray: SystemTrayIcon) -> None:
        super().__init__()
        self._tray = tray

    def nativeEventFilter(
        self, event_type: QtCore.QByteArray | bytes, message: object
    ) -> tuple[bool, int]:
        try:
            hwnd = self._tray.main_hwnd
            # message is a shiboken VoidPtr, whose bool() is always False:
            # test its address, not the object.
            address = int(message)  # type: ignore[call-overload]
            if not hwnd or not address:
                return False, 0
            msg = ctypes.wintypes.MSG.from_address(address)
            if (msg.hWnd or 0) != hwnd:
                return False, 0
            if msg.message == _WM_SHOWWINDOW:
                shown = bool(msg.wParam)
            elif msg.message == _WM_WINDOWPOSCHANGED and msg.lParam:
                pos = _WINDOWPOS.from_address(msg.lParam)
                shown = bool(pos.flags & _SWP_SHOWWINDOW)
            else:
                return False, 0
            if shown:
                self._tray.native_shown()
        except Exception:
            logging.getLogger("system").debug("Tray show filter failed", exc_info=True)
        return False, 0


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
        self._quit_request = 0
        self._instance = 0
        self._class_atom = None
        self._hwnd = 0
        self._idle_icon = 0
        self._active_icon = 0
        self._display_notify = 0
        # Hidden to the tray, with its pages unloaded (tray_memory). Set
        # only by _sync_tray, and only once the window took the call.
        self._trayed = False
        # Why the window is about to hide or show, for the trace note, and
        # whether Gremlin asked for a hide (for "enter skipped").
        self._cause = ""
        self._hide_asked = False
        # The main window's handle, for the native filter (0: not Windows).
        self.main_hwnd = 0
        self._native_filter: NativeShowFilter | None = None
        self._adopt_queued = False

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
        self._install_native_filter()
        with contextlib.suppress(Exception):
            from gremlin.ui import window_trace

            window_trace.set_tray_state_reader(lambda: self._trayed)
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
            self._ask_hide("X")
            self._tell_once_still_running()
            return True
        # Backstop for a show Windows made without Qt (01 S174): the native
        # filter is the main hook; whether an expose comes then is unverified.
        if event.type() == QtCore.QEvent.Type.Expose and self._trayed:
            QtCore.QTimer.singleShot(0, self, lambda: self._sync_tray("expose"))
        return super().eventFilter(watched, event)

    def release_resources(self) -> None:
        if self._native_filter is not None:
            app = QtCore.QCoreApplication.instance()
            if app is not None:
                with contextlib.suppress(RuntimeError):
                    app.removeNativeEventFilter(self._native_filter)
            self._native_filter = None
        if self._display_notify:
            _unregister_display_notify(self._display_notify)
            self._display_notify = 0
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

    def restore_window(self, cause: str = "shown") -> None:
        self._cause = cause
        self._hide_asked = False
        self._window.setVisibility(self._last_window_mode)
        self._window.raise_()
        self._window.requestActivate()

    def _create_resources(self) -> None:
        self._idle_icon = self._create_icon("gfx/icon.ico")
        self._active_icon = self._create_icon("gfx/icon_active.ico")

        self._taskbar_created = win32gui.RegisterWindowMessage("TaskbarCreated")
        self._quit_request = win32gui.RegisterWindowMessage(QUIT_REQUEST_NAME)
        self._instance = win32api.GetModuleHandle(None)
        wc = win32gui.WNDCLASS()
        wc.hInstance = self._instance
        wc.lpszClassName = "JoystickGremlinSystemTray"
        wc.lpfnWndProc = {
            _WM_TRAY: self._system_tray_event_cb,
            win32con.WM_COMMAND: self._handle_context_menu_cb,
            win32con.WM_DESTROY: self._destroy_system_tray_cb,
            self._taskbar_created: self._taskbar_created_cb,
            self._quit_request: self._quit_request_cb,
            _WM_POWERBROADCAST: self._power_broadcast_cb,
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
        self._display_notify = _register_display_notify(self._hwnd)
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

        # Qt emits this before Windows applies the change: decide once the
        # current show or hide has finished (D-01-TRAY-TRUTH).
        QtCore.QTimer.singleShot(0, self, lambda: self._sync_tray("visibility"))

        # Never hide inside this signal: it may come from inside Qt's own
        # show, which would then show the native window anyway (01 S85).
        if mode == QtGui.QWindow.Visibility.Minimized and self._minimize_to_tray():
            QtCore.QTimer.singleShot(0, self, self._hide_if_still_minimized)

    def _minimize_to_tray(self) -> bool:
        return bool(
            self._icon_present
            and Configuration().exists("global", "general", "minimize-to-tray")
            and Configuration().value("global", "general", "minimize-to-tray")
        )

    def _hide_if_still_minimized(self) -> None:
        if (
            self._window.visibility() == QtGui.QWindow.Visibility.Minimized
            and self._minimize_to_tray()
        ):
            self._ask_hide("minimize")

    def _ask_hide(self, cause: str) -> None:
        self._cause = cause
        self._hide_asked = True
        self._window.hide()

    def _install_native_filter(self) -> None:
        app = QtCore.QCoreApplication.instance()
        if app is None:
            return
        self._refresh_main_hwnd()
        self._native_filter = NativeShowFilter(self)
        app.installNativeEventFilter(self._native_filter)

    def _refresh_main_hwnd(self) -> int:
        """The main window's Windows handle, 0 off Windows (tests use the
        offscreen platform and stand-in windows)."""
        hwnd = 0
        if QtGui.QGuiApplication.platformName() == "windows":
            win_id = getattr(self._window, "winId", None)
            if win_id is not None:
                with contextlib.suppress(Exception):
                    hwnd = int(win_id())
        self.main_hwnd = hwnd
        return hwnd

    def _native_state(self) -> tuple[bool, bool]:
        """(shown, minimized) as Windows has it; Qt's own state when there
        is no Windows handle."""
        hwnd = self._refresh_main_hwnd()
        if hwnd:
            with contextlib.suppress(win32gui.error, AttributeError):
                return (
                    bool(win32gui.IsWindowVisible(hwnd)),
                    bool(win32gui.IsIconic(hwnd)),
                )
        mode = self._window.visibility()
        return (
            mode != QtGui.QWindow.Visibility.Hidden,
            mode == QtGui.QWindow.Visibility.Minimized,
        )

    def _qt_shown(self) -> bool:
        return self._window.visibility() != QtGui.QWindow.Visibility.Hidden

    def native_shown(self) -> None:
        """The native filter saw Windows show the main window: check it once
        the message is done (queued, never inside the message)."""
        if self._adopt_queued or self._qt_shown():
            return
        self._adopt_queued = True
        QtCore.QTimer.singleShot(0, self, self._adopt_native_show)

    def _adopt_native_show(self) -> None:
        """Windows shows the window while Qt has it hidden: bring Qt in line
        so its visibility signal fires and the pages load (01 S174, 1a)."""
        self._adopt_queued = False
        shown, minimized = self._native_state()
        if not shown or self._qt_shown():
            return
        _warn(
            "shown by Windows while hidden to the tray; "
            "showing it and loading its pages"
        )
        self._cause = "Windows showed it"
        self._window.setVisibility(
            QtGui.QWindow.Visibility.Minimized if minimized else self._last_window_mode
        )

    def _sync_tray(self, reason: str) -> None:
        """The one place that decides "in the tray" (D-01-TRAY-TRUTH): the
        native window is not shown and the tray icon is there. Pages unload
        on entering and load on leaving; _trayed changes only when the
        window took the call."""
        shown, _minimized = self._native_state()
        if shown and not self._qt_shown():
            self.native_shown()
            return
        cause = self._cause or reason
        hide_asked = self._hide_asked
        self._cause = ""
        self._hide_asked = False
        want = self._icon_present and not shown
        if want and not self._trayed:
            if tray_memory.enter_tray(self._window, self._backend.engine):
                self._trayed = True
                _note(f"tray: entered ({cause})")
            else:
                _warn(f"hiding to the tray failed ({cause}): its pages stay loaded")
        elif not want and self._trayed:
            if tray_memory.leave_tray(self._window):
                self._trayed = False
                _note(f"tray: left ({cause})")
            else:
                _warn(f"leaving the tray failed ({cause}): its pages did not load")
        elif hide_asked and shown and not self._trayed:
            # Gremlin asked for a hide, but the window is shown again.
            _note("tray: enter skipped (window visible)")

    def _power_broadcast_cb(self, hwnd: int, msg: int, wparam: int, lparam: int) -> int:
        # Records only (01 S176): nothing in the tray changes here.
        with contextlib.suppress(Exception):
            if wparam == _PBT_POWERSETTINGCHANGE:
                state = _display_state(lparam)
                if state is not None:
                    _note(f"displays {state}")
            elif wparam == _PBT_APMSUSPEND:
                _note("sleeping")
            elif wparam == _PBT_APMRESUMEAUTOMATIC:
                _note("resumed")
        return 1

    def _system_tray_event_cb(
        self, hwnd: int, msg: int, wparam: int, lparam: int
    ) -> int:
        match win32api.LOWORD(lparam):
            case win32con.WM_LBUTTONUP:
                self.restore_window("tray click")
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
        elif command == _ID_SSM:
            self._toggle_screen_saver_mode()
        elif command == _ID_DISPLAYS_OFF:
            self._turn_displays_off_now()
        elif command == _ID_START_WITH_WINDOWS:
            self._toggle_start_with_windows()
        elif command == _ID_QUIT:
            self._quit_gremlin()
        return 0

    @staticmethod
    def _start_with_windows_state(store: startup_entry.Store | None = None) -> str:
        """"on", "off" or "off_in_windows" (Windows' Startup Apps has it
        turned off); "off" when the start-up module fails (the tray must not
        break)."""
        try:
            from gremlin import startup_entry

            return str(startup_entry.state(store=store))
        except Exception:
            logging.getLogger("system").warning(
                "Tray: reading the start-with-Windows entry failed", exc_info=True
            )
            return "off"

    @staticmethod
    def _start_with_windows_on(store: startup_entry.Store | None = None) -> bool:
        """Whether the tick shows: only when the entry is really on."""
        return SystemTrayIcon._start_with_windows_state(store) == "on"

    def _toggle_start_with_windows(
        self, store: startup_entry.Store | None = None
    ) -> None:
        try:
            from gremlin import startup_entry

            log = logging.getLogger("system")
            state = self._start_with_windows_state(store)
            if state == "off_in_windows":
                log.info("Tray: Start with Windows is off in Windows, opening settings")
                if not startup_entry.open_windows_startup_settings():
                    log.warning("Tray: could not open Windows Startup Apps settings")
                return
            on = state != "on"
            log.info("Tray: Start with Windows %s", "on" if on else "off")
            if not startup_entry.set_enabled(on, store=store):
                log.warning("Tray: Start with Windows change was not applied")
        except Exception:
            logging.getLogger("system").warning(
                "Tray: Start with Windows toggle failed", exc_info=True
            )

    @staticmethod
    def _ssm_functions() -> tuple | None:
        """(ssm_enabled, set_ssm_enabled, turn_displays_off_now) from the
        Screen Saver Mode model, None when it is not there."""
        try:
            from gremlin.ui import screen_saver_mode_model as model

            return (
                model.ssm_enabled,
                model.set_ssm_enabled,
                model.turn_displays_off_now,
            )
        except (ImportError, AttributeError):
            return None

    @staticmethod
    def _ssm_trace(text: str) -> None:
        with contextlib.suppress(Exception):
            from gremlin import trace

            trace.screen_saver(text)

    def _toggle_screen_saver_mode(self) -> None:
        functions = self._ssm_functions()
        if functions is None:
            return
        enabled, set_enabled, _off = functions
        try:
            on = not enabled()
            self._ssm_trace(f"Tray: Screen Saver Mode {'on' if on else 'off'}")
            set_enabled(on)
        except Exception:
            logging.getLogger("system").warning(
                "Tray: Screen Saver Mode toggle failed", exc_info=True
            )

    def _turn_displays_off_now(self) -> None:
        functions = self._ssm_functions()
        if functions is None:
            return
        try:
            self._ssm_trace("Tray: turn displays off now")
            functions[2]()
        except Exception:
            logging.getLogger("system").warning(
                "Tray: turn displays off now failed", exc_info=True
            )

    def _toggle_run(self) -> None:
        """Run/Stop the same way as the toolbar (Main.qml toggleRun asks
        about an open action pane with changes first, 06 Q6)."""
        if not QtCore.QMetaObject.invokeMethod(self._window, "toggleRun"):
            self._backend.toggleActiveState()

    def _toggle_visibility(self) -> None:
        if self._window.isVisible():
            self._ask_hide("tray menu")
        else:
            self.restore_window("tray menu")

    def _taskbar_created_cb(self, hwnd: int, msg: int, wparam: int, lparam: int) -> int:
        if self._icon_present:
            self._delete_icon()
        self._add_icon()
        return 0

    def _quit_request_cb(self, hwnd: int, msg: int, wparam: int, lparam: int) -> int:
        # The installer is waiting on this answer: quit from the event loop,
        # not inside its message.
        QtCore.QTimer.singleShot(0, self, self._quit_gremlin)
        return QUIT_REQUEST_HANDLED

    def _destroy_system_tray_cb(
        self, hwnd: int, msg: int, wparam: int, lparam: int
    ) -> int:
        if self._display_notify:
            _unregister_display_notify(self._display_notify)
            self._display_notify = 0
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
            functions = self._ssm_functions()
            ssm_on = False
            if functions is not None:
                with contextlib.suppress(Exception):
                    ssm_on = bool(functions[0]())
            ssm_flags = win32con.MF_STRING | (
                win32con.MF_CHECKED if ssm_on else win32con.MF_UNCHECKED
            )
            off_flags = win32con.MF_STRING
            if functions is None:
                ssm_flags |= win32con.MF_GRAYED
                off_flags |= win32con.MF_GRAYED
            win32gui.AppendMenu(menu, ssm_flags, _ID_SSM, "Screen Saver Mode")  # pyright: ignore[reportCallIssue]  (pywin32 stub)
            win32gui.AppendMenu(
                menu, off_flags, _ID_DISPLAYS_OFF, "Turn displays off now"  # pyright: ignore[reportCallIssue]
            )
            win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, "")
            label = "Stop Profile" if self._backend.gremlinActive else "Run Profile"
            win32gui.AppendMenu(menu, win32con.MF_STRING, _ID_TOGGLE, label)
            start_flags = win32con.MF_STRING | (
                win32con.MF_CHECKED
                if SystemTrayIcon._start_with_windows_on()
                else win32con.MF_UNCHECKED
            )
            win32gui.AppendMenu(
                menu, start_flags, _ID_START_WITH_WINDOWS, "Start with Windows"  # pyright: ignore[reportCallIssue]
            )
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
        self.restore_window("quit")
        self._backend.quitRequested.emit()
