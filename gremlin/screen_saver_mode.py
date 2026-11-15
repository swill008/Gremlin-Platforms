# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Screen Saver Mode (program map 12): Gremlin's own idle clock from the
keyboard and mouse only, and the action (screen saver or displays off) when
it runs out.

Some devices send reports all the time, so Windows' idle clock never runs.
This clock listens to keyboard and mouse Raw Input only (InputClock, on its
own thread with a hidden window), and a one-second main-thread timer
(ScreenSaverMode.tick) does the action once per idle period, unless a hold
(locked, full screen, a program keeping the display on) or a problem stops
it. WindowsApi is the only part that calls Windows; tests pass a fake.
"""

from __future__ import annotations

import ctypes
import logging
import os
import subprocess
import threading
from ctypes import wintypes
from dataclasses import dataclass, replace
from typing import Any

from gremlin import clock, threads, trace, windows_event_hook

ACTION_SCREEN_SAVER = "screen_saver"
ACTION_POWER_OFF = "power_off"

HOLD_LOCKED = "locked"
HOLD_FULLSCREEN = "fullscreen"
HOLD_DISPLAY_REQUEST = "display_request"

PROBLEM_NO_SCREEN_SAVER = "no_screen_saver"
PROBLEM_WINDOWS_NEVER = "windows_never"
PROBLEM_NOT_LISTENING = "not_listening"

TICK_S = 1.0


def _log() -> logging.Logger:
    return logging.getLogger("system")


def _trace(text: str) -> None:
    """One Screen Saver Mode trace line (S16); a no-op unless tracing and
    its tick are on. Never per input event."""
    write = getattr(trace, "screen_saver", None)
    if write is None:
        return
    try:
        write(text)
    except Exception:
        _log().exception("Screen Saver Mode: trace failed")


def _error(text: str) -> None:
    """A failure: the normal log always, the trace too."""
    _log().warning(f"Screen Saver Mode: {text}")
    _trace(text)


_ACTION_TEXT = {
    ACTION_SCREEN_SAVER: "screen saver",
    ACTION_POWER_OFF: "power off displays",
}


@dataclass
class Settings:
    enabled: bool = False
    action: str = ACTION_POWER_OFF
    wait_override_s: int = 0  # 0 = use Windows' time
    hold_fullscreen: bool = True


@dataclass
class Status:
    enabled: bool = False
    listening: bool = False  # raw input registered and alive
    idle_s: float = 0.0  # Gremlin's idle time
    windows_idle_s: float = 0.0  # GetLastInputInfo
    wait_s: int = 0  # the wait in use (0 = none)
    windows_wait_s: int = 0  # Windows' value for the chosen action (0 = never/none)
    wait_from_windows: bool = True
    hold: str = ""  # "" | "locked" | "fullscreen" | "display_request"
    hold_program: str = ""  # the combined flag doesn't name programs
    fired: bool = False  # action done in this idle period
    problem: str = ""  # "" | "no_screen_saver" | "windows_never" | "not_listening"
    remaining_s: float = 0.0  # until the action, 0 when none


# ---------------------------------------------------------------- Windows

# SUB_VIDEO and VIDEOIDLE (powercfg /aliases).
_GUID_VIDEO_SUBGROUP = "7516b95f-f776-4464-8c53-06167f40cc99"
_GUID_VIDEO_IDLE = "3c0bc021-c8a8-4e07-a973-6b14cbcb2b7e"

_SYSTEM_EXECUTION_STATE = 16
_ES_DISPLAY_REQUIRED = 0x00000002

# SHQueryUserNotificationState: busy (full screen), D3D full screen,
# presentation mode.
_QUNS_FULLSCREEN = (2, 3, 4)

_HWND_BROADCAST = 0xFFFF
_WM_SYSCOMMAND = 0x0112
_SC_MONITORPOWER = 0xF170
_MONITOR_OFF = 2


class _GUID(ctypes.Structure):
    _fields_ = (
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    )

    @classmethod
    def parse(cls, text: str) -> _GUID:
        import uuid

        raw = uuid.UUID(text).bytes_le
        return cls.from_buffer_copy(raw)


class _SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = (
        ("ACLineStatus", ctypes.c_ubyte),
        ("BatteryFlag", ctypes.c_ubyte),
        ("BatteryLifePercent", ctypes.c_ubyte),
        ("SystemStatusFlag", ctypes.c_ubyte),
        ("BatteryLifeTime", wintypes.DWORD),
        ("BatteryFullLifeTime", wintypes.DWORD),
    )


class _LASTINPUTINFO(ctypes.Structure):
    _fields_ = (("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD))


class WindowsApi:
    """Every Windows call Screen Saver Mode makes. Tests pass a fake."""

    def screen_saver_path(self) -> str:
        """The screen saver chosen in Windows, "" when none."""
        import winreg

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop"
            ) as key:
                value, _kind = winreg.QueryValueEx(key, "SCRNSAVE.EXE")
        except OSError:
            return ""
        return os.path.expandvars(str(value or "")).strip()

    def screen_saver_wait_s(self) -> int:
        """Windows' screen saver wait (0 when no screen saver is chosen)."""
        import winreg

        if not self.screen_saver_path():
            return 0
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop"
            ) as key:
                value, _kind = winreg.QueryValueEx(key, "ScreenSaveTimeOut")
            return max(0, int(value))
        except (OSError, ValueError, TypeError):
            return 0

    def display_off_wait_s(self) -> int:
        """The active power plan's display-off time (AC or DC by the power
        source now), 0 = never."""
        powrprof = ctypes.WinDLL("powrprof")
        kernel32 = ctypes.WinDLL("kernel32")
        scheme = ctypes.POINTER(_GUID)()
        if powrprof.PowerGetActiveScheme(None, ctypes.byref(scheme)) != 0:
            return 0
        try:
            power = _SYSTEM_POWER_STATUS()
            on_battery = (
                kernel32.GetSystemPowerStatus(ctypes.byref(power))
                and power.ACLineStatus == 0
            )
            read = (
                powrprof.PowerReadDCValueIndex
                if on_battery
                else powrprof.PowerReadACValueIndex
            )
            sub = _GUID.parse(_GUID_VIDEO_SUBGROUP)
            setting = _GUID.parse(_GUID_VIDEO_IDLE)
            value = wintypes.DWORD(0)
            if (
                read(
                    None,
                    scheme,
                    ctypes.byref(sub),
                    ctypes.byref(setting),
                    ctypes.byref(value),
                )
                != 0
            ):
                return 0
            return int(value.value)
        finally:
            kernel32.LocalFree.argtypes = (ctypes.c_void_p,)
            kernel32.LocalFree(ctypes.cast(scheme, ctypes.c_void_p))

    def windows_idle_s(self) -> float:
        user32 = ctypes.WinDLL("user32")
        kernel32 = ctypes.WinDLL("kernel32")
        info = _LASTINPUTINFO(ctypes.sizeof(_LASTINPUTINFO), 0)
        if not user32.GetLastInputInfo(ctypes.byref(info)):
            return 0.0
        kernel32.GetTickCount.restype = wintypes.DWORD
        return ((kernel32.GetTickCount() - info.dwTime) & 0xFFFFFFFF) / 1000.0

    def display_required(self) -> bool:
        """Windows' combined display flag: some program asks to keep the
        display on (no administrator rights needed)."""
        powrprof = ctypes.WinDLL("powrprof")
        state = wintypes.ULONG(0)
        status = powrprof.CallNtPowerInformation(
            _SYSTEM_EXECUTION_STATE,
            None,
            0,
            ctypes.byref(state),
            ctypes.sizeof(state),
        )
        return status == 0 and bool(state.value & _ES_DISPLAY_REQUIRED)

    def fullscreen_busy(self) -> bool:
        shell32 = ctypes.WinDLL("shell32")
        state = ctypes.c_int(0)
        if shell32.SHQueryUserNotificationState(ctypes.byref(state)) != 0:
            return False
        return state.value in _QUNS_FULLSCREEN

    def locked(self) -> bool:
        """The workstation is locked (the input desktop is not "Default")."""
        user32 = ctypes.WinDLL("user32")
        user32.OpenInputDesktop.restype = wintypes.HANDLE
        user32.OpenInputDesktop.argtypes = (
            wintypes.DWORD,
            wintypes.BOOL,
            wintypes.DWORD,
        )
        user32.CloseDesktop.argtypes = (wintypes.HANDLE,)
        user32.GetUserObjectInformationW.argtypes = (
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
        )
        desktop = user32.OpenInputDesktop(0, False, 0x0001)  # DESKTOP_READOBJECTS
        if not desktop:
            return True
        try:
            name = ctypes.create_unicode_buffer(256)
            needed = wintypes.DWORD(0)
            if not user32.GetUserObjectInformationW(
                desktop, 2, name, ctypes.sizeof(name), ctypes.byref(needed)
            ):
                return False
            return name.value.lower() != "default"
        finally:
            user32.CloseDesktop(desktop)

    def start_screen_saver(self, path: str) -> bool:
        try:
            subprocess.Popen([path, "/s"], shell=False, close_fds=True)
        except OSError:
            _log().exception(f"Screen Saver Mode: could not start {path}")
            return False
        return True

    def power_off_displays(self) -> None:
        user32 = ctypes.WinDLL("user32")
        user32.PostMessageW.argtypes = (
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )
        user32.PostMessageW(
            _HWND_BROADCAST, _WM_SYSCOMMAND, _SC_MONITORPOWER, _MONITOR_OFF
        )


# -------------------------------------------------------------- Raw Input

_WM_INPUT = 0x00FF
_WM_QUIT = 0x0012
_RID_INPUT = 0x10000003
_RIDEV_REMOVE = 0x00000001
_RIDEV_INPUTSINK = 0x00000100
_RIM_TYPEMOUSE = 0
_RIM_TYPEKEYBOARD = 1
_USAGE_PAGE_GENERIC = 0x01
_USAGE_MOUSE = 0x02
_USAGE_KEYBOARD = 0x06
_ERROR_CLASS_ALREADY_EXISTS = 1410
_CLASS_NAME = "GremlinPlatformsScreenSaverModeInput"


class RAWINPUTHEADER(ctypes.Structure):
    _fields_ = (
        ("dwType", wintypes.DWORD),
        ("dwSize", wintypes.DWORD),
        ("hDevice", wintypes.HANDLE),
        ("wParam", wintypes.WPARAM),
    )


class _RAWMOUSE_BUTTONS(ctypes.Structure):
    _fields_ = (("usButtonFlags", wintypes.USHORT), ("usButtonData", wintypes.USHORT))


class _RAWMOUSE_UNION(ctypes.Union):
    _fields_ = (("ulButtons", wintypes.ULONG), ("buttons", _RAWMOUSE_BUTTONS))


class RAWMOUSE(ctypes.Structure):
    _fields_ = (
        ("usFlags", wintypes.USHORT),
        ("u", _RAWMOUSE_UNION),
        ("ulRawButtons", wintypes.ULONG),
        ("lLastX", wintypes.LONG),
        ("lLastY", wintypes.LONG),
        ("ulExtraInformation", wintypes.ULONG),
    )


class RAWKEYBOARD(ctypes.Structure):
    _fields_ = (
        ("MakeCode", wintypes.USHORT),
        ("Flags", wintypes.USHORT),
        ("Reserved", wintypes.USHORT),
        ("VKey", wintypes.USHORT),
        ("Message", wintypes.UINT),
        ("ExtraInformation", wintypes.ULONG),
    )


class _RAWINPUT_DATA(ctypes.Union):
    _fields_ = (("mouse", RAWMOUSE), ("keyboard", RAWKEYBOARD))


class RAWINPUT(ctypes.Structure):
    _fields_ = (("header", RAWINPUTHEADER), ("data", _RAWINPUT_DATA))


class _RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = (
        ("usUsagePage", wintypes.USHORT),
        ("usUsage", wintypes.USHORT),
        ("dwFlags", wintypes.DWORD),
        ("hwndTarget", wintypes.HWND),
    )


_LRESULT = wintypes.LPARAM
_WNDPROC = ctypes.WINFUNCTYPE(
    _LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
)


class _WNDCLASSEXW(ctypes.Structure):
    _fields_ = (
        ("cbSize", wintypes.UINT),
        ("style", wintypes.UINT),
        ("lpfnWndProc", _WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
        ("hIconSm", wintypes.HICON),
    )


def raw_input_kind(raw: RAWINPUT) -> str:
    """ "input" for keyboard or mouse input that counts (S3), "own" for
    input Gremlin sent itself (marked OWN_KEY_MARK), "" for anything else."""
    mark = windows_event_hook.OWN_KEY_MARK
    if raw.header.dwType == _RIM_TYPEMOUSE:
        return "own" if raw.data.mouse.ulExtraInformation == mark else "input"
    if raw.header.dwType == _RIM_TYPEKEYBOARD:
        return "own" if raw.data.keyboard.ExtraInformation == mark else "input"
    return ""


def _user32() -> ctypes.WinDLL:
    """A user32 of this module's own, so its argtypes don't touch others'."""
    u = ctypes.WinDLL("user32", use_last_error=True)
    u.DefWindowProcW.restype = _LRESULT
    u.DefWindowProcW.argtypes = (
        wintypes.HWND,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPARAM,
    )
    u.RegisterClassExW.restype = wintypes.ATOM
    u.RegisterClassExW.argtypes = (ctypes.POINTER(_WNDCLASSEXW),)
    u.UnregisterClassW.argtypes = (wintypes.LPCWSTR, wintypes.HINSTANCE)
    u.CreateWindowExW.restype = wintypes.HWND
    u.CreateWindowExW.argtypes = (
        wintypes.DWORD,
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.DWORD,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.HWND,
        wintypes.HMENU,
        wintypes.HINSTANCE,
        wintypes.LPVOID,
    )
    u.DestroyWindow.argtypes = (wintypes.HWND,)
    u.RegisterRawInputDevices.argtypes = (
        ctypes.POINTER(_RAWINPUTDEVICE),
        wintypes.UINT,
        wintypes.UINT,
    )
    u.GetRawInputData.restype = wintypes.UINT
    u.GetRawInputData.argtypes = (
        wintypes.HANDLE,
        wintypes.UINT,
        wintypes.LPVOID,
        ctypes.POINTER(wintypes.UINT),
        wintypes.UINT,
    )
    u.GetMessageW.argtypes = (
        wintypes.LPMSG,
        wintypes.HWND,
        wintypes.UINT,
        wintypes.UINT,
    )
    u.TranslateMessage.argtypes = (wintypes.LPMSG,)
    u.DispatchMessageW.argtypes = (wintypes.LPMSG,)
    u.PostThreadMessageW.argtypes = (
        wintypes.DWORD,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPARAM,
    )
    return u


class InputClock:
    """The time of the last keyboard or mouse input Gremlin counts.

    Raw Input (RIDEV_INPUTSINK, so input reaches it whatever window is in
    front) on a hidden top-level window, on its own program thread with its
    own message loop; WM_QUIT posted to the thread ends it. The window
    procedure only notes the time. Tests call note_input() only.
    """

    _NAME = "screen saver mode input"
    _START_WAIT_S = 2.0
    _STOP_WAIT_S = 2.0

    def __init__(self) -> None:
        self._last = clock.monotonic()
        self._thread: threading.Thread | None = None
        self._running = False
        self._registered = False
        self._ready = threading.Event()
        self._wndproc: Any = None
        self._user32: Any = None
        self.error = ""  # why the last start() failed, "" when it didn't

    def start(self) -> bool:
        """Registers raw input on its thread; False when it could not
        (the reason in `error`)."""
        self._last = clock.monotonic()
        if self._running:
            return self.listening()
        self.error = ""
        # Tests turn the hooks off: no raw input is registered on their PC.
        if not windows_event_hook.enabled:
            self.error = "input hooks are off"
            return False
        self._running = True
        self._registered = False
        self._ready.clear()
        self._thread = threads.start(self._NAME, self._listen, stop=self._ask_to_stop)
        self._ready.wait(self._START_WAIT_S)
        if not self._registered:
            if not self.error:
                self.error = f"no answer within {self._START_WAIT_S:g} s"
            self.stop()
            return False
        return True

    def stop(self) -> None:
        if not self._running and self._thread is None:
            return
        self._running = False
        thread = self._thread
        self._thread = None
        if thread is None:
            return
        # Posted again until the thread ends: one posted before the thread
        # has its message queue would be lost.
        deadline = clock.monotonic() + self._STOP_WAIT_S
        while thread.is_alive() and clock.monotonic() < deadline:
            self._post_quit(thread)
            thread.join(0.05)
        if thread.is_alive():
            _log().warning(f"{thread.name} did not stop")
        self._registered = False

    def listening(self) -> bool:
        thread = self._thread
        return bool(
            self._running
            and self._registered
            and thread is not None
            and thread.is_alive()
        )

    def last_input(self) -> float:
        return self._last

    def note_input(self, own: bool = False) -> None:
        if not own:
            self._last = clock.monotonic()

    def _ask_to_stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._post_quit(self._thread)

    def _post_quit(self, thread: threading.Thread) -> None:
        if thread.ident is not None and self._user32 is not None:
            self._user32.PostThreadMessageW(thread.ident, _WM_QUIT, 0, 0)

    def _window_proc(self, hwnd: int, msg: int, w_param: int, l_param: int) -> int:
        if msg == _WM_INPUT:
            try:
                raw = RAWINPUT()
                size = wintypes.UINT(ctypes.sizeof(raw))
                got = self._user32.GetRawInputData(
                    l_param,
                    _RID_INPUT,
                    ctypes.byref(raw),
                    ctypes.byref(size),
                    ctypes.sizeof(RAWINPUTHEADER),
                )
                if got != 0xFFFFFFFF and got > 0:
                    kind = raw_input_kind(raw)
                    if kind:
                        self.note_input(own=kind == "own")
            except Exception:
                _log().exception("Screen Saver Mode raw input failed")
        return self._user32.DefWindowProcW(hwnd, msg, w_param, l_param)

    def _listen(self) -> None:
        u = self._user32 = _user32()
        kernel32 = ctypes.WinDLL("kernel32")
        kernel32.GetModuleHandleW.restype = wintypes.HMODULE
        instance = kernel32.GetModuleHandleW(None)
        self._wndproc = _WNDPROC(self._window_proc)
        wc = _WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(_WNDCLASSEXW)
        wc.lpfnWndProc = self._wndproc
        wc.hInstance = instance
        wc.lpszClassName = _CLASS_NAME
        hwnd = None
        class_made = False
        try:
            if u.RegisterClassExW(ctypes.byref(wc)):
                class_made = True
            elif (code := ctypes.get_last_error()) != _ERROR_CLASS_ALREADY_EXISTS:
                self.error = f"window class not registered (Windows error {code})"
                return
            # A hidden top-level window (RIDEV_INPUTSINK needs one, not a
            # message-only window).
            hwnd = u.CreateWindowExW(
                0, _CLASS_NAME, "", 0, 0, 0, 0, 0, None, None, instance, None
            )
            if not hwnd:
                self.error = (
                    f"input window not made (Windows error {ctypes.get_last_error()})"
                )
                return
            devices = (_RAWINPUTDEVICE * 2)(
                _RAWINPUTDEVICE(
                    _USAGE_PAGE_GENERIC, _USAGE_MOUSE, _RIDEV_INPUTSINK, hwnd
                ),
                _RAWINPUTDEVICE(
                    _USAGE_PAGE_GENERIC, _USAGE_KEYBOARD, _RIDEV_INPUTSINK, hwnd
                ),
            )
            if not u.RegisterRawInputDevices(
                devices, 2, ctypes.sizeof(_RAWINPUTDEVICE)
            ):
                self.error = (
                    f"raw input not registered "
                    f"(Windows error {ctypes.get_last_error()})"
                )
                return
            self._registered = True
            self._ready.set()
            msg = wintypes.MSG()
            while self._running:
                result = u.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if result == 0 or result == -1:
                    break
                u.TranslateMessage(ctypes.byref(msg))
                u.DispatchMessageW(ctypes.byref(msg))
        finally:
            self._registered = False
            self._ready.set()
            try:
                if hwnd:
                    remove = (_RAWINPUTDEVICE * 2)(
                        _RAWINPUTDEVICE(
                            _USAGE_PAGE_GENERIC, _USAGE_MOUSE, _RIDEV_REMOVE, None
                        ),
                        _RAWINPUTDEVICE(
                            _USAGE_PAGE_GENERIC, _USAGE_KEYBOARD, _RIDEV_REMOVE, None
                        ),
                    )
                    u.RegisterRawInputDevices(remove, 2, ctypes.sizeof(_RAWINPUTDEVICE))
                    u.DestroyWindow(hwnd)
                if class_made:
                    u.UnregisterClassW(_CLASS_NAME, instance)
            except Exception:
                pass


# ---------------------------------------------------------------- manager


@dataclass
class _Period:
    """One idle period: from the last counted input (or the end of a hold)."""

    input_at: float = 0.0
    start: float = 0.0
    fired: bool = False
    held: bool = False
    wait_s: int = 0
    windows_wait_s: int = 0
    screen_saver: str = ""


class ScreenSaverMode:
    """The countdown and the action (S2-S11, S15, S16 tracing)."""

    # status() while off reads Windows at most this often.
    _OFF_READ_S = 1.0

    def __init__(
        self, api: WindowsApi | None = None, clock_: InputClock | None = None
    ) -> None:
        self._api = api if api is not None else WindowsApi()
        self._clock = clock_ if clock_ is not None else InputClock()
        self._settings = Settings()
        self._running = False
        self._listening = False
        self._timer: Any = None
        self._period = _Period()
        self._status = Status()
        self._status_live = False  # _status was filled while running
        # (read at, action, Windows' wait) for status() while off.
        self._off_read: tuple[float, str, int] | None = None
        self._last_hold = ""
        self._last_problem = ""

    # ----- settings

    def settings(self) -> Settings:
        return replace(self._settings)

    def apply(self, settings: Settings) -> None:
        """Takes the settings; on/off starts or stops the clock and timer."""
        self._settings = replace(settings)
        self._off_read = None
        wait = (
            _wait_text(settings.wait_override_s)
            if settings.wait_override_s
            else "from Windows"
        )
        _trace(
            f"settings applied: {'on' if settings.enabled else 'off'}, "
            f"{_ACTION_TEXT.get(settings.action, settings.action)}, wait {wait}"
            f", hold full screen "
            f"{'on' if settings.hold_fullscreen else 'off'}"
        )
        if settings.enabled and not self._running:
            self._running = True
            self._last_hold = ""
            self._last_problem = ""
            self._listening = self._clock.start()
            if self._listening:
                _trace("listener started")
            else:
                reason = getattr(self._clock, "error", "") or "unknown reason"
                if windows_event_hook.enabled:
                    _error(f"listener failed: {reason}")
                else:
                    _trace(f"listener not started: {reason}")
            self._new_period(self._clock.last_input(), clock.monotonic())
            self._arm()
        elif not settings.enabled and self._running:
            self._stop()
        elif self._running:
            # A changed action or wait: the countdown reads its wait again.
            self._read_wait()
            self._trace_countdown()
        self._update_status()
        if self._running:
            self._note_problem(self._status.problem)

    def shutdown(self) -> None:
        if self._running:
            self._stop()
        self._update_status()

    def _stop(self) -> None:
        self._running = False
        if self._timer is not None:
            try:
                self._timer.cancel()
            except Exception:
                pass
            self._timer = None
        self._clock.stop()
        self._listening = False
        self._last_hold = ""
        self._last_problem = ""
        _trace("listener stopped")

    # ----- timer

    def _arm(self) -> None:
        self._timer = threads.main_timer("screen saver mode", TICK_S, self._on_timer)

    def _on_timer(self) -> None:
        self._timer = None
        if not self._running:
            return
        try:
            self.tick()
        except Exception:
            _log().exception("Screen Saver Mode tick failed")
            _trace("tick failed (see the log)")
        if self._running:
            self._arm()

    # ----- countdown

    def _windows_wait(self, action: str) -> tuple[str, int]:
        """(screen saver path, Windows' wait) for the action; 0 = never."""
        try:
            if action == ACTION_SCREEN_SAVER:
                path = self._api.screen_saver_path()
                wait = self._api.screen_saver_wait_s() if path else 0
            else:
                path = ""
                wait = self._api.display_off_wait_s()
            return path, max(0, int(wait))
        except Exception:
            _log().exception("Screen Saver Mode: reading Windows' wait failed")
            _trace("reading Windows' wait failed (see the log)")
            return "", 0

    def _read_wait(self) -> None:
        """The wait for the chosen action, read from Windows each time the
        countdown starts (S5)."""
        p = self._period
        s = self._settings
        p.screen_saver, p.windows_wait_s = self._windows_wait(s.action)
        override = max(0, int(s.wait_override_s or 0))
        p.wait_s = override if override > 0 else p.windows_wait_s

    def _trace_countdown(self) -> None:
        p = self._period
        typed = (self._settings.wait_override_s or 0) > 0
        source = "typed" if typed else "from Windows"
        _trace(
            f"countdown started: wait {_wait_text(p.wait_s)} ({source}; "
            f"Windows {_wait_text(p.windows_wait_s)})"
        )

    def _new_period(self, input_at: float, start: float, quiet: bool = False) -> None:
        self._period = _Period(input_at=input_at, start=start)
        self._read_wait()
        if not quiet:
            self._trace_countdown()

    def _problem(self) -> str:
        if not self._listening or not self._clock.listening():
            return PROBLEM_NOT_LISTENING
        if (
            self._settings.action == ACTION_SCREEN_SAVER
            and not self._period.screen_saver
        ):
            return PROBLEM_NO_SCREEN_SAVER
        if self._period.wait_s <= 0:
            return PROBLEM_WINDOWS_NEVER
        return ""

    def _note_problem(self, problem: str) -> None:
        if problem != self._last_problem:
            self._last_problem = problem
            _trace(f"problem: {problem}" if problem else "problem cleared")

    def _hold(self) -> str:
        if self._api.locked():
            return HOLD_LOCKED
        if self._settings.hold_fullscreen and self._api.fullscreen_busy():
            return HOLD_FULLSCREEN
        if self._api.display_required():
            return HOLD_DISPLAY_REQUEST
        return ""

    def tick(self) -> None:
        """Once a second on the main thread: does the action once per idle
        period when idle >= wait, with no hold and no problem."""
        if not self._running:
            return
        now = clock.monotonic()
        last = self._clock.last_input()
        if last != self._period.input_at:
            # Input: a new idle period (S6), the countdown starts again.
            # Traced only for the first input after the action, not per input.
            after_action = self._period.fired
            if after_action:
                _trace("input after action: countdown restarts")
            self._new_period(last, last, quiet=not after_action)
        p = self._period
        hold = ""
        try:
            hold = self._hold()
        except Exception:
            _log().exception("Screen Saver Mode: hold check failed")
            _trace("hold check failed (see the log)")
        if hold != self._last_hold:
            if self._last_hold:
                _trace(f"hold ended: {self._last_hold}")
            if hold:
                _trace(f"hold began: {hold}")
            self._last_hold = hold
        if hold:
            # Held: the countdown starts again when the hold ends (S7,
            # S11, S15).
            p.held = True
            p.start = now
        elif p.held:
            # Counted from the last held moment: the wait is read again.
            p.held = False
            self._read_wait()
            self._trace_countdown()
        problem = self._problem()
        self._note_problem(problem)
        if not hold and not problem and not p.fired and now - p.start >= p.wait_s:
            p.fired = True
            self._fire()
        self._update_status(now=now, hold=hold, problem=problem)

    def _fire(self) -> None:
        action = self._settings.action
        try:
            if action == ACTION_SCREEN_SAVER:
                path = self._period.screen_saver
                if self._api.start_screen_saver(path):
                    _trace(f"action fired: screen saver {path}: started")
                else:
                    _error(f"action fired: screen saver {path}: could not start")
            else:
                self._api.power_off_displays()
                _trace("action fired: power off displays: sent")
        except Exception as e:
            _log().exception("Screen Saver Mode action failed")
            _trace(f"action fired: {_ACTION_TEXT.get(action, action)}: failed ({e})")

    # ----- status

    def _off_windows_wait(self) -> int:
        """Windows' wait for the chosen action while off, read at most once
        a second (S5: the window shows it while off too)."""
        now = clock.monotonic()
        action = self._settings.action
        cached = self._off_read
        if (
            cached is not None
            and cached[1] == action
            and now - cached[0] < self._OFF_READ_S
        ):
            return cached[2]
        _path, wait = self._windows_wait(action)
        self._off_read = (now, action, wait)
        return wait

    def _off_status(self) -> Status:
        windows_wait = self._off_windows_wait()
        override = max(0, int(self._settings.wait_override_s or 0))
        return Status(
            enabled=self._settings.enabled,
            wait_s=override if override > 0 else windows_wait,
            windows_wait_s=windows_wait,
            wait_from_windows=override == 0,
        )

    def _update_status(
        self, now: float | None = None, hold: str = "", problem: str | None = None
    ) -> None:
        if not self._running:
            self._status_live = False
            return
        now = clock.monotonic() if now is None else now
        p = self._period
        if problem is None:
            problem = self._problem()
        try:
            windows_idle = float(self._api.windows_idle_s())
        except Exception:
            windows_idle = 0.0
        remaining = 0.0
        if not hold and not problem and not p.fired:
            remaining = max(0.0, p.wait_s - (now - p.start))
        self._status = Status(
            enabled=True,
            listening=self._clock.listening(),
            idle_s=max(0.0, now - p.input_at),
            windows_idle_s=windows_idle,
            wait_s=p.wait_s,
            windows_wait_s=p.windows_wait_s,
            wait_from_windows=not (self._settings.wait_override_s or 0) > 0,
            hold=hold,
            hold_program="",
            fired=p.fired,
            problem=problem,
            remaining_s=remaining,
        )
        self._status_live = True

    def status(self) -> Status:
        """The status as of the last tick (cheap; the UI polls it). While
        off it carries Windows' wait for the chosen action."""
        if not self._running or not self._status_live:
            return self._off_status()
        return replace(self._status)


def _wait_text(seconds: int | float) -> str:
    seconds = int(seconds or 0)
    return f"{seconds} s" if seconds > 0 else "none"


_manager: ScreenSaverMode | None = None
_manager_lock = threading.Lock()


def manager() -> ScreenSaverMode:
    """The one Screen Saver Mode."""
    global _manager
    with _manager_lock:
        if _manager is None:
            _manager = ScreenSaverMode()
        return _manager
