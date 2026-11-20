# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Screen Saver Mode (program map 12): Gremlin's own idle clock from the
keyboard and mouse only, and two timers (screen saver, displays off) that
run from it.

Some devices send reports all the time, so Windows' idle clock never runs.
This clock listens to keyboard and mouse Raw Input only (InputClock, on its
own thread with a hidden window), and a one-second main-thread timer
(ScreenSaverMode.tick) fires each timer once per idle period, unless a hold
(locked, full screen, a program keeping the display on) or a problem stops
it. After the power-off fires, the same hidden window hears Windows' display
state and answers each display-ON report with one power-off, at most once a
second, until real input (keeping the displays off, S6). WindowsApi is the
only part that calls Windows; tests pass a fake.
"""

from __future__ import annotations

import ctypes
import logging
import os
import re
import subprocess
import threading
from collections import deque
from collections.abc import Callable, Iterable
from ctypes import wintypes
from dataclasses import dataclass, field, replace
from typing import Any

from gremlin import clock, threads, trace, windows_event_hook

HOLD_LOCKED = "locked"
HOLD_FULLSCREEN = "fullscreen"
HOLD_DISPLAY_REQUEST = "display_request"
# S31: Wake PC has nothing ticked; both timers wait.
HOLD_NO_WAKE_DEVICE = "no_wake_device"

RESET_KEYBOARD = "keyboard"
RESET_MOUSE = "mouse"
RESET_PROGRAM = "program"

PROBLEM_NO_SCREEN_SAVER = "no_screen_saver"
PROBLEM_WINDOWS_NEVER = "windows_never"
PROBLEM_NOT_LISTENING = "not_listening"

TICK_S = 1.0
# How often presses noted while the mode is off reach the main thread (S30).
PRESS_DRAIN_S = 0.25
# A device's key or button presses are reported at most once a second each.
PRESS_GAP_S = 1.0
# Any input from a device is reported at most this often per device (S33).
ACTIVITY_GAP_S = 0.5
# A power-off (the timer's or a keep-off re-send) is never sent sooner than
# this after the last one.
POWER_OFF_GAP_S = 1.0


def _log() -> logging.Logger:
    return logging.getLogger("system")


def _trace(text: str, ring: bool = True, t: float | None = None) -> None:
    """One Screen Saver Mode trace line (S16); a no-op unless tracing and
    its tick are on. Never per input event. With ring the line also goes
    to the recent-events ring (01 S177); per-press lines pass ring=False.
    t is the wall time the thing happened (a line written later)."""
    write = getattr(trace, "screen_saver", None)
    if write is None:
        return
    try:
        if t is None:
            write(text, ring=ring)
        else:
            write(text, ring=ring, t=t)
    except Exception:
        _log().exception("Screen Saver Mode: trace failed")


def _error(text: str) -> None:
    """A failure: the normal log always, the trace too."""
    _log().warning(f"Screen Saver Mode: {text}")
    _trace(text)


@dataclass
class Settings:
    enabled: bool = False
    screen_saver_on: bool = True
    screen_saver_wait_s: int = 0  # 0 = use Windows' screen saver wait
    power_off_on: bool = True
    power_off_wait_s: int = 0  # 0 = use the power plan's display-off time
    hold_fullscreen: bool = True


@dataclass
class Status:
    enabled: bool = False
    listening: bool = False  # raw input registered and alive
    idle_s: float = 0.0  # Gremlin's idle time
    windows_idle_s: float = 0.0  # GetLastInputInfo
    # Screen saver timer.
    saver_wait_s: int = 0  # the wait in use (0 = none)
    saver_windows_wait_s: int = 0  # Windows' screen saver wait (0 = none/never)
    saver_from_windows: bool = True  # no time typed
    saver_fired: bool = False  # started in this idle period
    saver_remaining_s: float = 0.0  # until it fires, 0 when it won't
    saver_problem: str = ""  # "" | "no_screen_saver" | "windows_never"
    # Power off timer.
    off_wait_s: int = 0
    off_windows_wait_s: int = 0  # the power plan's display-off time (0 = never)
    off_from_windows: bool = True
    off_fired: bool = False
    off_remaining_s: float = 0.0
    off_problem: str = ""  # "" | "windows_never"
    keeping_off: bool = False  # answering Windows' display-ON reports (S6)
    wakes: int = 0  # re-sends in the current or last idle period (S20)
    # "" | "locked" | "no_wake_device" | "fullscreen" | "display_request"
    hold: str = ""
    hold_program: str = ""  # the full-screen program's file name, "" when unknown
    problem: str = ""  # "" | "not_listening" (both timers)
    last_reset_by: str = ""  # the device's name, "" for program input or none
    last_reset_kind: str = ""  # "keyboard" | "mouse" | "program" | ""
    last_reset_age_s: float = 0.0  # since the last counted input
    program_input_per_min: int = 0  # inputs sent by programs in the last 60 s


# ---------------------------------------------------------------- Windows

# SUB_VIDEO and VIDEOIDLE (powercfg /aliases).
_GUID_VIDEO_SUBGROUP = "7516b95f-f776-4464-8c53-06167f40cc99"
_GUID_VIDEO_IDLE = "3c0bc021-c8a8-4e07-a973-6b14cbcb2b7e"

_SYSTEM_EXECUTION_STATE = 16
_ES_DISPLAY_REQUIRED = 0x00000002

# SHQueryUserNotificationState: busy (full screen), D3D full screen,
# presentation mode.
_QUNS_FULLSCREEN = (2, 3, 4)
_SPI_GETSCREENSAVERRUNNING = 0x0072

# The input listener's hidden window while it runs: the one window the
# power-off request is posted to (WindowsApi.power_off_displays).
_power_window: int = 0
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


@dataclass(frozen=True)
class InputDevice:
    """One physical keyboard or mouse for Wake PC (S28)."""

    physical_id: str  # physical_device() of its raw input parts
    name: str  # the name of one of its parts ("" when none)
    kinds: tuple[str, ...]  # sorted subset of ("keyboard", "mouse")


class _LASTINPUTINFO(ctypes.Structure):
    _fields_ = (("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD))


def _spi_screen_saver_running() -> bool:
    """Windows' own flag: a screen saver Windows started is running."""
    user32 = ctypes.WinDLL("user32")
    running = wintypes.BOOL(0)
    if not user32.SystemParametersInfoW(
        _SPI_GETSCREENSAVERRUNNING, 0, ctypes.byref(running), 0
    ):
        return False
    return bool(running.value)


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

    # The screen saver this program started (start_screen_saver), kept to
    # tell whether it still runs.
    _saver_process: subprocess.Popen | None = None

    def screen_saver_running(self) -> bool:
        """A screen saver runs: the one this program started is still
        running, or Windows says one runs (SPI_GETSCREENSAVERRUNNING).
        Asked directly, because the screen saver need not be the window in
        front: with a second display the program in front stays in front
        (found on the user's PC 2026-11-16, a TV as the second display).
        Windows' flag alone is not enough: it is only set for a screen saver
        Windows started itself, and stayed 0 while the one this program
        started ran (same PC, same night)."""
        process = self._saver_process
        if process is not None:
            if process.poll() is None:
                return True
            self._saver_process = None
        return _spi_screen_saver_running()

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
            self._saver_process = subprocess.Popen(
                [path, "/s"], shell=False, close_fds=True
            )
        except OSError:
            _log().exception(f"Screen Saver Mode: could not start {path}")
            return False
        return True

    def power_off_displays(self) -> None:
        """Powers the displays off with ONE request, posted to the input
        listener's own hidden window, whose thread hands it to Windows.
        Not broadcast: a broadcast reaches every window of every program,
        this program's own Qt windows included, and each asks Windows to
        power off again, some of them later, after the user has woken the
        screens (found on the user's PC 2026-11-15: the main thread was
        stuck 35 s and the screens kept going off)."""
        hwnd = _power_window
        if not hwnd:
            raise RuntimeError("no listener window to send the power-off to")
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.PostMessageW.argtypes = (
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )
        user32.PostMessageW.restype = wintypes.BOOL
        if not user32.PostMessageW(
            hwnd, _WM_SYSCOMMAND, _SC_MONITORPOWER, _MONITOR_OFF
        ):
            raise ctypes.WinError(ctypes.get_last_error())

    def foreground_program(self) -> str:
        """The file name of the program in front ("" on any failure)."""
        try:
            return _foreground_program()
        except Exception:
            return ""

    def device_name(self, handle: int) -> str:
        """A raw input device's name for people ("" when none is found).
        Slow-ish: called once per device handle, never per event."""
        try:
            return _device_name(handle)
        except Exception:
            _log().exception("Screen Saver Mode: device name lookup failed")
            return ""

    def device_physical_id(self, handle: int) -> str:
        """The physical device a raw input handle belongs to ("" when
        unknown). Slow-ish: once per handle, on the listener thread."""
        try:
            return physical_device(instance_id_from_path(raw_device_path(handle)))
        except Exception:
            _log().exception("Screen Saver Mode: physical device lookup failed")
            return ""

    def input_devices(self) -> list[InputDevice]:
        """Every keyboard and mouse Windows reports, one per physical device
        (S28); [] on any failure. Slow: never on the main thread."""
        try:
            parts = []
            for handle, kind in _raw_input_device_list():
                path = raw_device_path(handle)
                if not path:
                    continue
                physical = physical_device(instance_id_from_path(path))
                if not physical:
                    continue
                try:
                    name = _device_name(handle)
                except Exception:
                    name = ""
                parts.append((physical, name, kind))
            return group_input_devices(parts)
        except Exception:
            _log().exception("Screen Saver Mode: listing keyboards and mice failed")
            return []


_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def _foreground_program() -> str:
    user32 = ctypes.WinDLL("user32")
    kernel32 = ctypes.WinDLL("kernel32")
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = (
        wintypes.HWND,
        ctypes.POINTER(wintypes.DWORD),
    )
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel32.QueryFullProcessImageNameW.argtypes = (
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    )
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return ""
    pid = wintypes.DWORD(0)
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        return ""
    process = kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if not process:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(len(buf))
        if not kernel32.QueryFullProcessImageNameW(process, 0, buf, ctypes.byref(size)):
            return ""
        return os.path.basename(buf.value)
    finally:
        kernel32.CloseHandle(process)


_RIDI_DEVICENAME = 0x20000007
_CM_DRP_DEVICEDESC = 0x01
_CM_DRP_FRIENDLYNAME = 0x0D
_DEVPROP_TYPE_STRING = 0x12
_OPEN_EXISTING = 3
_FILE_SHARE_READ_WRITE = 0x3
_INVALID_HANDLE = ctypes.c_void_p(-1).value


class _DEVPROPKEY(ctypes.Structure):
    _fields_ = (("fmtid", _GUID), ("pid", wintypes.ULONG))


# DEVPKEY_Device_BusReportedDeviceDesc
_BUS_REPORTED_DESC = ("540b947e-8b40-45bc-a8a2-6a0b894cbda2", 4)


def raw_device_path(handle: int) -> str:
    """GetRawInputDeviceInfoW(RIDI_DEVICENAME): the device's path."""
    u = ctypes.WinDLL("user32")
    u.GetRawInputDeviceInfoW.restype = wintypes.UINT
    u.GetRawInputDeviceInfoW.argtypes = (
        wintypes.HANDLE,
        wintypes.UINT,
        wintypes.LPVOID,
        ctypes.POINTER(wintypes.UINT),
    )
    size = wintypes.UINT(0)
    u.GetRawInputDeviceInfoW(handle, _RIDI_DEVICENAME, None, ctypes.byref(size))
    if not size.value or size.value > 4096:
        return ""
    buf = ctypes.create_unicode_buffer(size.value + 1)
    got = u.GetRawInputDeviceInfoW(handle, _RIDI_DEVICENAME, buf, ctypes.byref(size))
    if got == 0xFFFFFFFF or got == 0:
        return ""
    return buf.value


class _RAWINPUTDEVICELIST(ctypes.Structure):
    _fields_ = (("hDevice", wintypes.HANDLE), ("dwType", wintypes.DWORD))


_ERROR_INSUFFICIENT_BUFFER = 122


def _raw_input_device_list() -> list[tuple[int, str]]:
    """GetRawInputDeviceList: (handle, "keyboard" | "mouse") of each
    keyboard and mouse part."""
    u = ctypes.WinDLL("user32", use_last_error=True)
    u.GetRawInputDeviceList.restype = wintypes.UINT
    u.GetRawInputDeviceList.argtypes = (
        ctypes.POINTER(_RAWINPUTDEVICELIST),
        ctypes.POINTER(wintypes.UINT),
        wintypes.UINT,
    )
    size = ctypes.sizeof(_RAWINPUTDEVICELIST)
    count = wintypes.UINT(0)
    if u.GetRawInputDeviceList(None, ctypes.byref(count), size) == 0xFFFFFFFF:
        raise ctypes.WinError(ctypes.get_last_error())
    # A device plugged in between the two calls: ask again (three tries).
    for _ in range(3):
        items = (_RAWINPUTDEVICELIST * max(1, count.value))()
        count = wintypes.UINT(len(items))
        got = u.GetRawInputDeviceList(items, ctypes.byref(count), size)
        if got != 0xFFFFFFFF:
            kinds = {_RIM_TYPEKEYBOARD: RESET_KEYBOARD, _RIM_TYPEMOUSE: RESET_MOUSE}
            return [
                (int(items[i].hDevice or 0), kinds[items[i].dwType])
                for i in range(got)
                if items[i].dwType in kinds and items[i].hDevice
            ]
        code = ctypes.get_last_error()
        if code != _ERROR_INSUFFICIENT_BUFFER:
            raise ctypes.WinError(code)
    raise ctypes.WinError(_ERROR_INSUFFICIENT_BUFFER)


def group_input_devices(parts: Iterable[tuple[str, str, str]]) -> list[InputDevice]:
    """(physical id, name, kind) per raw input part -> one InputDevice per
    physical id, in the order first seen; the first non-empty name wins."""
    names: dict[str, str] = {}
    kinds: dict[str, set[str]] = {}
    for physical, name, kind in parts:
        if not physical:
            continue
        if not names.get(physical):
            names[physical] = name
        kinds.setdefault(physical, set()).add(kind)
    return [
        InputDevice(physical, names[physical], tuple(sorted(kinds[physical])))
        for physical in names
    ]


def instance_id_from_path(path: str) -> str:
    r"""\\?\HID#VID_1&PID_2#7&abc#{guid} -> HID\VID_1&PID_2\7&abc."""
    text = path
    for prefix in ("\\\\?\\", "\\??\\", "\\\\.\\"):
        if text.startswith(prefix):
            text = text[len(prefix) :]
            break
    if "#{" in text:
        text = text[: text.rindex("#{")]
    return text.replace("#", "\\")


def vid_pid_text(path: str) -> str:
    """ "VID_046D PID_C52B" from a device path, "" when it has none."""
    m = re.search(r"VID_([0-9A-Fa-f]{4}).*?PID_([0-9A-Fa-f]{4})", path)
    if not m:
        m = re.search(r"VID&([0-9A-Fa-f]{4,8})_PID&([0-9A-Fa-f]{4})", path)
    if not m:
        return ""
    return f"VID_{m.group(1).upper()} PID_{m.group(2).upper()}"


# Windows' generic descriptions: worth less than the VID/PID on their own.
_GENERIC_DESC = (
    "hid keyboard device",
    "hid-compliant mouse",
    "hid-compliant device",
    "usb input device",
    "hid-compliant consumer control device",
    "hid-compliant system controller",
    "hid-compliant vendor-defined device",
)


def _device_name(handle: int) -> str:
    path = raw_device_path(handle)
    if not path:
        return ""
    if "HID#" in path.upper():
        name = _hid_product(path)
        if name:
            return name
    name, generic = _devnode_name(instance_id_from_path(path))
    vid_pid = vid_pid_text(path)
    if name and not generic:
        return name
    if name and vid_pid:
        return f"{name} ({vid_pid})"
    return name or vid_pid or instance_id_from_path(path)


def _hid_product(path: str) -> str:
    kernel32 = ctypes.WinDLL("kernel32")
    hid = ctypes.WinDLL("hid")
    kernel32.CreateFileW.restype = wintypes.HANDLE
    kernel32.CreateFileW.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    )
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    hid.HidD_GetProductString.argtypes = (
        wintypes.HANDLE,
        wintypes.LPVOID,
        wintypes.ULONG,
    )
    # No access rights asked: enough for the product string, and keyboards
    # and mice open this way.
    handle = kernel32.CreateFileW(
        path, 0, _FILE_SHARE_READ_WRITE, None, _OPEN_EXISTING, 0, None
    )
    if not handle or handle == _INVALID_HANDLE:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(127)
        if not hid.HidD_GetProductString(handle, buf, ctypes.sizeof(buf)):
            return ""
        return buf.value.strip()
    finally:
        kernel32.CloseHandle(handle)


def _devnode_name(instance_id: str) -> tuple[str, bool]:
    """(name, generic): the bus-reported name of the device or its parent,
    else its friendly name or description."""
    cfg = ctypes.WinDLL("cfgmgr32")
    cfg.CM_Locate_DevNodeW.argtypes = (
        ctypes.POINTER(wintypes.DWORD),
        wintypes.LPCWSTR,
        wintypes.ULONG,
    )
    cfg.CM_Get_Parent.argtypes = (
        ctypes.POINTER(wintypes.DWORD),
        wintypes.DWORD,
        wintypes.ULONG,
    )
    cfg.CM_Get_DevNode_PropertyW.argtypes = (
        wintypes.DWORD,
        ctypes.POINTER(_DEVPROPKEY),
        ctypes.POINTER(wintypes.ULONG),
        wintypes.LPVOID,
        ctypes.POINTER(wintypes.ULONG),
        wintypes.ULONG,
    )
    cfg.CM_Get_DevNode_Registry_PropertyW.argtypes = (
        wintypes.DWORD,
        wintypes.ULONG,
        ctypes.POINTER(wintypes.ULONG),
        wintypes.LPVOID,
        ctypes.POINTER(wintypes.ULONG),
        wintypes.ULONG,
    )
    node = wintypes.DWORD(0)
    if cfg.CM_Locate_DevNodeW(ctypes.byref(node), instance_id, 0) != 0:
        return "", False

    def bus_desc(devinst: int) -> str:
        key = _DEVPROPKEY(_GUID.parse(_BUS_REPORTED_DESC[0]), _BUS_REPORTED_DESC[1])
        kind = wintypes.ULONG(0)
        buf = ctypes.create_unicode_buffer(256)
        size = wintypes.ULONG(ctypes.sizeof(buf))
        if (
            cfg.CM_Get_DevNode_PropertyW(
                devinst,
                ctypes.byref(key),
                ctypes.byref(kind),
                buf,
                ctypes.byref(size),
                0,
            )
            != 0
            or kind.value != _DEVPROP_TYPE_STRING
        ):
            return ""
        return buf.value.strip()

    def registry(devinst: int, prop: int) -> str:
        buf = ctypes.create_unicode_buffer(256)
        size = wintypes.ULONG(ctypes.sizeof(buf))
        if (
            cfg.CM_Get_DevNode_Registry_PropertyW(
                devinst, prop, None, buf, ctypes.byref(size), 0
            )
            != 0
        ):
            return ""
        return buf.value.strip()

    # The HID collection's parent is usually the USB/Bluetooth device, which
    # carries the name the device reports itself.
    parent = wintypes.DWORD(0)
    nodes = [node.value]
    if cfg.CM_Get_Parent(ctypes.byref(parent), node.value, 0) == 0:
        nodes.append(parent.value)
    for devinst in nodes:
        name = bus_desc(devinst)
        if name and name.lower() not in _GENERIC_DESC:
            return name, False
    name = registry(node.value, _CM_DRP_FRIENDLYNAME) or registry(
        node.value, _CM_DRP_DEVICEDESC
    )
    return name, name.lower() in _GENERIC_DESC or not name


def physical_device(instance_id: str) -> str:
    """The physical device a device belongs to (S3): the first device above
    it that is neither a HID collection nor a USB interface (MI_), as an
    upper-case instance id; "" when Windows doesn't know it. The Steam
    Controller's mouse (Col01), keyboard (Col02) and streaming part (Col03)
    all give its USB device (found on the user's PC 2026-11-16)."""
    if not instance_id:
        return ""
    cfg = ctypes.WinDLL("cfgmgr32")
    cfg.CM_Locate_DevNodeW.argtypes = (
        ctypes.POINTER(wintypes.DWORD),
        wintypes.LPCWSTR,
        wintypes.ULONG,
    )
    cfg.CM_Get_Parent.argtypes = (
        ctypes.POINTER(wintypes.DWORD),
        wintypes.DWORD,
        wintypes.ULONG,
    )
    cfg.CM_Get_Device_IDW.argtypes = (
        wintypes.DWORD,
        wintypes.LPWSTR,
        wintypes.ULONG,
        wintypes.ULONG,
    )
    node = wintypes.DWORD(0)
    if cfg.CM_Locate_DevNodeW(ctypes.byref(node), instance_id, 0) != 0:
        return ""
    current = instance_id.upper()
    for _ in range(8):
        if not _is_part(current):
            return current
        parent = wintypes.DWORD(0)
        if cfg.CM_Get_Parent(ctypes.byref(parent), node.value, 0) != 0:
            return current
        buf = ctypes.create_unicode_buffer(512)
        if cfg.CM_Get_Device_IDW(parent.value, buf, len(buf), 0) != 0:
            return current
        node = parent
        current = buf.value.upper()
    return current


def _is_part(instance_id: str) -> bool:
    """A HID collection or a USB interface: part of a physical device."""
    enumerator, _, rest = instance_id.upper().partition("\\")
    hardware_id = rest.split("\\", 1)[0]
    return enumerator == "HID" or "&MI_" in hardware_id


# -------------------------------------------------------------- Raw Input

_WM_INPUT = 0x00FF
_WM_QUIT = 0x0012
_WM_TIMER = 0x0113
_RETRY_TIMER_ID = 1  # the keep-off re-send held back by the gap (S6)
_RID_INPUT = 0x10000003
_RIDEV_REMOVE = 0x00000001
_RIDEV_INPUTSINK = 0x00000100
_RIM_TYPEMOUSE = 0
_RIM_TYPEKEYBOARD = 1
_USAGE_PAGE_GENERIC = 0x01
_RI_KEY_BREAK = 0x01
# RI_MOUSE_LEFT/RIGHT/MIDDLE/BUTTON_4/BUTTON_5 _DOWN; not move, not wheel.
_RI_MOUSE_BUTTONS_DOWN = 0x0001 | 0x0004 | 0x0010 | 0x0040 | 0x0100
_USAGE_MOUSE = 0x02
_USAGE_KEYBOARD = 0x06
_ERROR_CLASS_ALREADY_EXISTS = 1410
_WM_POWERBROADCAST = 0x0218
_PBT_POWERSETTINGCHANGE = 0x8013
_DEVICE_NOTIFY_WINDOW_HANDLE = 0
# GUID_CONSOLE_DISPLAY_STATE: Data 0 off, 1 on, 2 dimmed.
_GUID_CONSOLE_DISPLAY_STATE = "6fe69556-704a-47a0-8f24-c28d936fda47"
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


class POWERBROADCAST_SETTING(ctypes.Structure):
    _fields_ = (
        ("PowerSetting", _GUID),
        ("DataLength", wintypes.DWORD),
        ("Data", ctypes.c_ubyte * 4),
    )


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


def raw_input_press(raw: RAWINPUT) -> bool:
    """A key down or a mouse button down (S30); key up, movement and the
    wheel are not presses."""
    if raw.header.dwType == _RIM_TYPEKEYBOARD:
        return not raw.data.keyboard.Flags & _RI_KEY_BREAK
    if raw.header.dwType == _RIM_TYPEMOUSE:
        return bool(raw.data.mouse.u.buttons.usButtonFlags & _RI_MOUSE_BUTTONS_DOWN)
    return False


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
    u.RegisterPowerSettingNotification.restype = wintypes.HANDLE
    u.RegisterPowerSettingNotification.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(_GUID),
        wintypes.DWORD,
    )
    u.UnregisterPowerSettingNotification.argtypes = (wintypes.HANDLE,)
    u.SetTimer.restype = ctypes.c_size_t
    u.SetTimer.argtypes = (
        wintypes.HWND,
        ctypes.c_size_t,
        wintypes.UINT,
        ctypes.c_void_p,
    )
    u.KillTimer.argtypes = (wintypes.HWND, ctypes.c_size_t)
    return u


def display_state_on(l_param: int) -> bool | None:
    """The display state in a PBT_POWERSETTINGCHANGE message: True on (or
    dimmed), False off, None when it is another setting."""
    if not l_param:
        return None
    setting = POWERBROADCAST_SETTING.from_address(l_param)
    if bytes(setting.PowerSetting) != bytes(_GUID.parse(_GUID_CONSOLE_DISPLAY_STATE)):
        return None
    return setting.Data[0] != 0


class InputClock:
    """The time of the last keyboard or mouse input Gremlin counts.

    Raw Input (RIDEV_INPUTSINK, so input reaches it whatever window is in
    front) on a hidden top-level window, on its own program thread with its
    own message loop; WM_QUIT posted to the thread ends it. The window
    procedure only notes the time, the device handle and the kind; names
    are looked up later (ScreenSaverMode, once per handle). With a Wake PC
    list (S28), a press listener (S30) or an activity listener (S33) it
    also looks up each handle's
    physical device, once per handle on this thread (`physical_id_of`);
    input from a device not on the list doesn't count, and presses and
    uncounted devices go to `event_sink` for the main thread. The same window
    gets Windows' display state (GUID_CONSOLE_DISPLAY_STATE) and hands each
    report to `display_state_handler` (ScreenSaverMode.on_display_state),
    on this thread. Tests call note_input() only.
    """

    _NAME = "screen saver mode input"
    _START_WAIT_S = 2.0
    _STOP_WAIT_S = 2.0
    _PROGRAM_SECONDS = 60

    def __init__(self) -> None:
        self._last = clock.monotonic()
        self._thread: threading.Thread | None = None
        self._running = False
        self._registered = False
        self._ready = threading.Event()
        self._wndproc: Any = None
        self._user32: Any = None
        self.error = ""  # why the last start() failed, "" when it didn't
        # Why the display-state notification could not be registered ("" ok).
        self.notify_error = ""
        # Called on the listener thread with each display state (True on).
        self.display_state_handler: Callable[[bool], None] | None = None
        # Called on the listener thread when the re-send timer fires; returns
        # the seconds still to wait, or None when it is done (S6).
        self.timer_handler: Callable[[], float | None] | None = None
        self._hwnd: Any = None
        # The last counted input's source: (device handle or None, kind).
        self._source: tuple[int | None, str] = (None, "")
        # Program input per second: [second, count], the last minute only.
        self._program: deque[list[int]] = deque(maxlen=self._PROGRAM_SECONDS + 1)
        self._program_lock = threading.Lock()
        # Wake PC (S28): the ticked physical ids; None = every device counts.
        self._wake: frozenset[str] | None = None
        # Physical ids already reported as not counted, until the list changes.
        self._not_counted: set[str] = set()
        # Handle -> physical id, filled on the listener thread.
        self.physical_id_of: Callable[[int], str] | None = None
        self._physical: dict[int, str] = {}
        # Presses (S30) are reported while this is True.
        self.report_presses = False
        self._pressed_at: dict[tuple[str, str], float] = {}
        # Any device input (S33) is reported while this is True.
        self.report_activity = False
        self._active_at: dict[str, float] = {}
        # (event, handle, physical id, kind) to the main thread; never Qt.
        self.event_sink: Callable[[str, int, str, str], None] | None = None

    def set_wake_ids(self, ids: frozenset[str] | None) -> None:
        """The ticked physical ids (None: every device counts)."""
        self._wake = ids
        self._not_counted = set()

    def physical_id(self, handle: int) -> str:
        """The handle's physical id, looked up once per handle."""
        known = self._physical.get(handle)
        if known is not None:
            return known
        lookup = self.physical_id_of
        physical = ""
        if lookup is not None:
            try:
                physical = str(lookup(handle) or "").upper()
            except Exception:
                _log().exception("Screen Saver Mode: physical device lookup failed")
        self._physical[handle] = physical
        return physical

    def _send(self, event: str, handle: int, physical: str, kind: str) -> None:
        sink = self.event_sink
        if sink is not None:
            try:
                sink(event, handle, physical, kind)
            except Exception:
                _log().exception("Screen Saver Mode: input event failed")

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

    def note_input(
        self,
        own: bool = False,
        source: int | None = None,
        kind: str = "",
        press: bool = False,
    ) -> None:
        """One input. `source` is the device's raw input handle, None (or
        0) for input sent by a program; `kind` "keyboard" or "mouse";
        `press` a key or button down. Gremlin's own input (own) doesn't
        count; with a Wake PC list, neither does a device not on it."""
        if own:
            return
        now = clock.monotonic()
        wake = self._wake
        if source and (wake is not None or self.report_presses or self.report_activity):
            physical = self.physical_id(source)
            if self.report_activity:
                last = self._active_at.get(physical)
                if last is None or now - last >= ACTIVITY_GAP_S:
                    self._active_at[physical] = now
                    self._send("activity", source, physical, kind)
            if press and self.report_presses:
                last = self._pressed_at.get((physical, kind))
                if last is None or now - last >= PRESS_GAP_S:
                    self._pressed_at[(physical, kind)] = now
                    self._send("press", source, physical, kind)
            if wake is not None and physical not in wake:
                if physical not in self._not_counted:
                    self._not_counted.add(physical)
                    self._send("not_counted", source, physical, kind)
                return
        if not source:
            self._source = (None, RESET_PROGRAM)
            second = int(now)
            with self._program_lock:
                if self._program and self._program[-1][0] == second:
                    self._program[-1][1] += 1
                else:
                    self._program.append([second, 1])
        else:
            self._source = (source, kind)
        self._last = now

    def last_source(self) -> tuple[int | None, str]:
        """(device handle or None, "keyboard" | "mouse" | "program" | "")
        of the last counted input."""
        return self._source

    def program_input_per_min(self, now: float | None = None) -> int:
        """Inputs sent by programs (not Gremlin) in the last 60 s."""
        now = clock.monotonic() if now is None else now
        since = int(now) - self._PROGRAM_SECONDS
        with self._program_lock:
            return sum(n for second, n in self._program if second > since)

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
                        self.note_input(
                            own=kind == "own",
                            source=raw.header.hDevice or None,
                            kind=RESET_MOUSE
                            if raw.header.dwType == _RIM_TYPEMOUSE
                            else RESET_KEYBOARD,
                            press=raw_input_press(raw),
                        )
            except Exception:
                _log().exception("Screen Saver Mode raw input failed")
        elif msg == _WM_TIMER and w_param == _RETRY_TIMER_ID:
            # The timer is one-shot: killed here (this thread owns the
            # window), armed again only when the handler wants more time.
            try:
                self._user32.KillTimer(hwnd, _RETRY_TIMER_ID)
                handler = self.timer_handler
                again = handler() if handler is not None else None
                if again is not None:
                    self.arm_timer(again)
            except Exception:
                _log().exception("Screen Saver Mode keep-off timer failed")
            return 0
        elif msg == _WM_POWERBROADCAST and w_param == _PBT_POWERSETTINGCHANGE:
            try:
                on = display_state_on(l_param)
                handler = self.display_state_handler
                if on is not None and handler is not None:
                    handler(on)
            except Exception:
                _log().exception("Screen Saver Mode display state failed")
        return self._user32.DefWindowProcW(hwnd, msg, w_param, l_param)

    def arm_timer(self, delay_s: float) -> bool:
        """Arms the one-shot re-send timer on the listener's own window, so
        the re-send needs no main thread. Only the listener thread may call
        it (SetTimer needs the window's thread); False when it can't."""
        hwnd, u = self._hwnd, self._user32
        if not hwnd or u is None:
            return False
        ms = max(10, int(delay_s * 1000) + 1)
        try:
            return bool(u.SetTimer(hwnd, _RETRY_TIMER_ID, ms, None))
        except Exception:
            return False

    def _listen(self) -> None:
        global _power_window
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
        notify = None
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
            # Windows' display state, for keeping the displays off (S6).
            # Without it the timers still work; the reason is reported.
            self.notify_error = ""
            notify = u.RegisterPowerSettingNotification(
                hwnd,
                ctypes.byref(_GUID.parse(_GUID_CONSOLE_DISPLAY_STATE)),
                _DEVICE_NOTIFY_WINDOW_HANDLE,
            )
            if not notify:
                self.notify_error = (
                    "display state notification not registered "
                    f"(Windows error {ctypes.get_last_error()})"
                )
            _power_window = hwnd
            self._hwnd = hwnd
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
            if _power_window == hwnd:
                _power_window = 0
            self._hwnd = None
            self._registered = False
            self._ready.set()
            try:
                if notify:
                    u.UnregisterPowerSettingNotification(notify)
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
class _Timer:
    """One timer's wait and whether it fired in this idle period."""

    wait_s: int = 0
    windows_wait_s: int = 0
    fired: bool = False


@dataclass
class _Period:
    """One idle period: from the last counted input (or the end of a hold)."""

    input_at: float = 0.0
    start: float = 0.0
    held: bool = False
    screen_saver: str = ""
    saver: _Timer = field(default_factory=_Timer)
    off: _Timer = field(default_factory=_Timer)


def _typed(seconds: int | None) -> int:
    return max(0, int(seconds or 0))


def _row_problems(path: str, saver_wait_s: int, off_wait_s: int) -> tuple[str, str]:
    """(screen saver row, power off row) problems for the waits in use."""
    if not path:
        saver = PROBLEM_NO_SCREEN_SAVER
    elif saver_wait_s <= 0:
        saver = PROBLEM_WINDOWS_NEVER
    else:
        saver = ""
    off = PROBLEM_WINDOWS_NEVER if off_wait_s <= 0 else ""
    return saver, off


class ScreenSaverMode:
    """The two timers and keeping the displays off (S2-S11, S15, S16, S20)."""

    # status() while off reads Windows at most this often.
    _OFF_READ_S = 1.0
    POWER_OFF_GAP_S = POWER_OFF_GAP_S

    def __init__(
        self, api: WindowsApi | None = None, clock_: InputClock | None = None
    ) -> None:
        self._api = api if api is not None else WindowsApi()
        self._clock = clock_ if clock_ is not None else InputClock()
        self._clock.display_state_handler = self.on_display_state
        self._clock.timer_handler = self.on_retry_timer
        self._clock.physical_id_of = self._api.device_physical_id
        self._clock.event_sink = self._note_device_event
        self._settings = Settings()
        self._running = False
        self._listening = False
        self._timer: Any = None
        self._period = _Period()
        self._status = Status()
        self._status_live = False  # _status was filled while running
        # (read at, screen saver path, its wait, display-off wait) while off.
        self._off_read: tuple[float, str, int, int] | None = None
        self._last_hold = ""
        self._last_problems = ("", "", "")
        self._hold_program = ""
        # Device names by raw input handle, looked up once each.
        self._names: dict[int, str] = {}
        self._last_reset_traced: tuple[str, str] | None = None
        # Keeping the displays off (S6): shared with the listener thread,
        # whose window procedure only notes and posts under this lock.
        self._keep_lock = threading.Lock()
        self._keeping_off = False
        self._keep_input_at = 0.0  # the counted input keep-off started after
        self._last_power_off = -1e9
        self._retry_at = 0.0  # a re-send waiting for the gap (0 = none)
        self._display_on = True  # Windows' last report
        self._wakes = 0  # re-sends in this (or the last) idle period
        self._wakes_total = 0  # since the mode was switched on
        # (kind, number, text, wall time it happened) for the main thread to
        # trace: never traced on the listener thread.
        self._events: deque[tuple[str, int, str, float]] = deque(maxlen=1000)
        # Device hooks (S21, S23), main thread only.
        self._before_power_off: Callable[[], None] | None = None
        self._after_input: Callable[[], None] | None = None
        self._hooked = False  # before_power_off ran, after_input not yet
        # Wake PC (S28-S31): None until set_wake_devices() is called.
        self._wake: frozenset[str] | None = None
        self._press_listener: Callable[[str, str], None] | None = None
        self._activity_listener: Callable[[str], None] | None = None
        self._detecting = False  # start_detection() without the mode on
        self._drain_timer: Any = None

    def set_device_hooks(
        self,
        before_power_off: Callable[[], None] | None,
        after_input: Callable[[], None] | None,
    ) -> None:
        """before_power_off: just before the Power off displays timer's
        first power-off of an idle period (S21; must return fast).
        after_input: once at the first counted input after it (S23).
        Both on the main thread; never while the mode is off."""
        self._before_power_off = before_power_off
        self._after_input = after_input

    # ----- Wake PC (S28-S31)

    def set_wake_devices(self, physical_ids: Iterable[str]) -> None:
        """The ticked devices (S28): keyboard and mouse input from any other
        device doesn't count; program input always does. None ticked holds
        both timers (S31). Main thread; may come before apply()."""
        ids = frozenset(str(i).upper() for i in physical_ids if i)
        self._wake = ids
        self._clock.set_wake_ids(ids)
        _trace(f"wake devices: {len(ids)} ticked")

    def set_press_listener(self, listener: Callable[[str, str], None] | None) -> None:
        """While set, each key or button press from any device reaches
        listener(physical_id, "keyboard" | "mouse") on the main thread, at
        most once a second per device and kind (S30)."""
        self._press_listener = listener
        self._clock.report_presses = listener is not None
        self._arm_drain()

    def set_activity_listener(self, listener: Callable[[str], None] | None) -> None:
        """While set, any keyboard or mouse input from a device, ticked or
        not, reaches listener(physical_id) on the main thread, at most once
        per device every ACTIVITY_GAP_S (S33). Not traced."""
        self._activity_listener = listener
        self._clock.report_activity = listener is not None
        self._arm_drain()

    def start_detection(self) -> bool:
        """Listens for presses while the mode is off too (no timers run);
        False when the listener could not start."""
        if self._detecting or self._running:
            self._detecting = True
            return self._clock.listening()
        self._detecting = True
        ok = self._clock.start()
        if ok:
            _trace("listener started for Wake PC")
        else:
            reason = getattr(self._clock, "error", "") or "unknown reason"
            _trace(f"listener for Wake PC not started: {reason}")
        self._arm_drain()
        return ok

    def stop_detection(self) -> None:
        """Ends start_detection(); the listener keeps running while the mode
        is on."""
        if not self._detecting:
            return
        self._detecting = False
        if not self._running:
            self._clock.stop()
            _trace("listener for Wake PC stopped")

    def _arm_drain(self) -> None:
        """While the mode is off, presses reach the main thread on a short
        timer (the tick drains them while it is on)."""
        if (
            self._drain_timer is None
            and (
                self._press_listener is not None or self._activity_listener is not None
            )
            and not self._running
        ):
            self._drain_timer = threads.main_timer(
                "screen saver mode presses", PRESS_DRAIN_S, self._on_drain_timer
            )

    def _on_drain_timer(self) -> None:
        self._drain_timer = None
        try:
            self._drain_events()
        except Exception:
            _log().exception("Screen Saver Mode: press drain failed")
        self._arm_drain()

    def _note_device_event(
        self, event: str, handle: int, physical: str, kind: str
    ) -> None:
        """Listener thread: queues a press, activity or an uncounted device."""
        self._events.append((event, handle, f"{kind}	{physical}", 0.0))

    def _call_hook(self, name: str, hook: Callable[[], None] | None) -> None:
        if hook is None:
            return
        _trace(f"device hook: {name}")
        try:
            hook()
        except Exception:
            _log().exception(f"Screen Saver Mode: device hook {name} failed")
            _trace(f"device hook {name} failed (see the log)")

    # ----- settings

    def settings(self) -> Settings:
        return replace(self._settings)

    def apply(self, settings: Settings) -> None:
        """Takes the settings; on/off starts or stops the clock and timer."""
        self._settings = replace(settings)
        self._off_read = None
        saver = _timer_text(settings.screen_saver_on, settings.screen_saver_wait_s)
        off = _timer_text(settings.power_off_on, settings.power_off_wait_s)
        _trace(
            f"settings applied: {'on' if settings.enabled else 'off'}, "
            f"screen saver {saver}, power off displays {off}, "
            f"hold full screen {'on' if settings.hold_fullscreen else 'off'}"
        )
        if settings.enabled and not self._running:
            self._running = True
            self._last_hold = ""
            self._last_problems = ("", "", "")
            with self._keep_lock:
                self._wakes = 0
                self._wakes_total = 0
                self._events.clear()
            self._listening = self._clock.start()
            if self._listening:
                _trace("listener started")
                notify_error = getattr(self._clock, "notify_error", "")
                if notify_error:
                    _error(f"{notify_error}: the displays can't be kept off")
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
            if not settings.power_off_on:
                self._end_keep_off("power off displays switched off")
            # A changed switch or wait: the countdowns read their waits again.
            self._read_waits()
            self._trace_countdown()
        self._update_status()
        if self._running:
            self._note_problems(*self._problems())

    def shutdown(self) -> None:
        if self._running:
            self._stop()
        self._update_status()

    def _stop(self) -> None:
        self._end_keep_off("Screen Saver Mode switched off")
        self._hooked = False
        self._running = False
        if self._timer is not None:
            try:
                self._timer.cancel()
            except Exception:
                pass
            self._timer = None
        if self._detecting:
            _trace("listener kept for Wake PC")
        else:
            self._clock.stop()
        self._listening = False
        self._last_hold = ""
        self._last_problems = ("", "", "")
        self._hold_program = ""
        self._last_reset_traced = None
        _trace("listener stopped")
        self._arm_drain()

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

    def _windows_waits(self) -> tuple[str, int, int]:
        """(screen saver path, its wait, display-off wait) from Windows;
        a wait of 0 = none/never."""
        path, saver = "", 0
        try:
            path = str(self._api.screen_saver_path() or "")
            saver = max(0, int(self._api.screen_saver_wait_s())) if path else 0
        except Exception:
            _log().exception("Screen Saver Mode: reading the screen saver wait failed")
            _trace("reading Windows' screen saver wait failed (see the log)")
        try:
            off = max(0, int(self._api.display_off_wait_s()))
        except Exception:
            _log().exception("Screen Saver Mode: reading the display-off time failed")
            _trace("reading Windows' display-off time failed (see the log)")
            off = 0
        return path, saver, off

    def _read_waits(self) -> None:
        """Each timer's wait, Windows' read each time the countdown starts
        (S5); a typed time replaces it."""
        p = self._period
        s = self._settings
        p.screen_saver, p.saver.windows_wait_s, p.off.windows_wait_s = (
            self._windows_waits()
        )
        p.saver.wait_s = _typed(s.screen_saver_wait_s) or p.saver.windows_wait_s
        p.off.wait_s = _typed(s.power_off_wait_s) or p.off.windows_wait_s

    def _trace_countdown(self) -> None:
        p = self._period
        s = self._settings

        def row(on: bool, typed: int, t: _Timer) -> str:
            if not on:
                return "off"
            source = "typed" if _typed(typed) else "from Windows"
            return (
                f"{_wait_text(t.wait_s)} ({source}; "
                f"Windows {_wait_text(t.windows_wait_s)})"
            )

        _trace(
            "countdown started: screen saver "
            f"{row(s.screen_saver_on, s.screen_saver_wait_s, p.saver)}, "
            "power off displays "
            f"{row(s.power_off_on, s.power_off_wait_s, p.off)}"
        )

    def _new_period(self, input_at: float, start: float, quiet: bool = False) -> None:
        self._period = _Period(input_at=input_at, start=start)
        self._read_waits()
        if not quiet:
            self._trace_countdown()

    def _problems(self) -> tuple[str, str, str]:
        """(both timers, screen saver row, power off row)."""
        both = (
            PROBLEM_NOT_LISTENING
            if not self._listening or not self._clock.listening()
            else ""
        )
        p = self._period
        saver, off = _row_problems(p.screen_saver, p.saver.wait_s, p.off.wait_s)
        return both, saver, off

    def _note_problems(self, both: str, saver: str, off: str) -> None:
        old = self._last_problems
        names = ("", "screen saver ", "power off displays ")
        for name, before, now in zip(names, old, (both, saver, off), strict=True):
            if before != now:
                _trace(f"{name}problem: {now}" if now else f"{name}problem cleared")
        self._last_problems = (both, saver, off)

    def _hold(self) -> str:
        if self._api.locked():
            return HOLD_LOCKED
        if self._wake is not None and not self._wake:
            return HOLD_NO_WAKE_DEVICE
        if (
            self._settings.hold_fullscreen
            and self._api.fullscreen_busy()
            and not self._screen_saver_running()
        ):
            # A screen saver in front is not a full-screen program: Windows
            # reports it as busy, which would hold the power-off timer behind
            # the screen saver this mode started (found on the user's PC
            # 2026-11-15).
            return HOLD_FULLSCREEN
        if self._api.display_required():
            return HOLD_DISPLAY_REQUEST
        return ""

    def tick(self) -> None:
        """Once a second on the main thread: fires each timer once per idle
        period when idle >= its wait, with no hold and no problem; ends
        keeping the displays off on counted input; retries a held-back
        re-send; traces what the listener thread noted."""
        if not self._running:
            return
        now = clock.monotonic()
        last = self._clock.last_input()
        if last != self._period.input_at:
            # Input: a new idle period (S6), the countdowns start again.
            # Traced only for the first input after an action, not per input.
            after_action = self._period.saver.fired or self._period.off.fired
            if after_action:
                _trace("input after action: countdown restarts")
            self._end_keep_off("keyboard or mouse input")
            if self._hooked:
                self._hooked = False
                self._call_hook("after input", self._after_input)
            self._new_period(last, last, quiet=not after_action)
        p = self._period
        hold = ""
        try:
            hold = self._hold()
        except Exception:
            _log().exception("Screen Saver Mode: hold check failed")
            _trace("hold check failed (see the log)")
        program = self._foreground() if hold == HOLD_FULLSCREEN else ""
        if hold != self._last_hold:
            if self._last_hold:
                _trace(f"hold ended: {self._last_hold}")
            if hold:
                who = f" ({program})" if program else ""
                _trace(f"hold began: {hold}{who}")
            self._last_hold = hold
        elif hold == HOLD_FULLSCREEN and program and program != self._hold_program:
            _trace(f"hold program: {program}")
        self._hold_program = program
        self._trace_reset()
        if hold:
            # Held: both countdowns start again when the hold ends (S7,
            # S11, S15).
            p.held = True
            p.start = now
        elif p.held:
            # Counted from the last held moment: the waits are read again.
            p.held = False
            self._read_waits()
            self._trace_countdown()
        problems = self._problems()
        both, saver_problem, off_problem = problems
        self._note_problems(*problems)
        s = self._settings
        if not hold and not both:
            elapsed = now - p.start
            if (
                s.screen_saver_on
                and not saver_problem
                and not p.saver.fired
                and elapsed >= p.saver.wait_s
            ):
                self._fire_screen_saver()
                p.saver.fired = True
            if (
                s.power_off_on
                and not off_problem
                and not p.off.fired
                and elapsed >= p.off.wait_s
            ):
                # A power-off held back by the gap is tried again next tick.
                p.off.fired = self._fire_power_off()
        self._retry_keep_off(now)
        self._drain_events()
        self._update_status(now=now, hold=hold, problems=problems)

    def _screen_saver_running(self) -> bool:
        """A screen saver runs: Windows says so, or one is the window in front."""
        try:
            if self._api.screen_saver_running():
                return True
        except Exception:
            pass
        return self._foreground().lower().endswith(".scr")

    def _foreground(self) -> str:
        try:
            return str(self._api.foreground_program() or "")
        except Exception:
            return ""

    def _device_name(self, handle: int) -> str:
        """The device's name, looked up once per handle and kept."""
        if handle in self._names:
            return self._names[handle]
        try:
            name = str(self._api.device_name(handle) or "")
        except Exception:
            _log().exception("Screen Saver Mode: device name lookup failed")
            name = ""
        self._names[handle] = name
        return name

    def _reset_source(self) -> tuple[str, str]:
        """(device name, kind) of the last counted input."""
        try:
            handle, kind = self._clock.last_source()
        except Exception:
            return "", ""
        if kind == RESET_PROGRAM or not handle:
            return "", kind
        return self._device_name(handle), kind

    def _trace_reset(self) -> None:
        """Traces the input source when it changes (never per input)."""
        name, kind = self._reset_source()
        if not kind or (name, kind) == self._last_reset_traced:
            return
        self._last_reset_traced = (name, kind)
        if kind == RESET_PROGRAM:
            _trace("last reset by: input sent by a program")
        else:
            _trace(f"last reset by: {name or 'a device'} ({kind})")

    def _fire_screen_saver(self) -> None:
        path = self._period.screen_saver
        try:
            if self._api.start_screen_saver(path):
                _log().info(f"Screen Saver Mode: screen saver started ({path})")
                _trace(f"action fired: screen saver {path}: started")
            else:
                _error(f"action fired: screen saver {path}: could not start")
        except Exception as e:
            _log().exception("Screen Saver Mode action failed")
            _trace(f"action fired: screen saver: failed ({e})")

    def _fire_power_off(self) -> bool:
        """Powers the displays off and starts keeping them off; False only
        when held back by POWER_OFF_GAP_S (tried again next tick)."""
        now = clock.monotonic()
        with self._keep_lock:
            if now - self._last_power_off < self.POWER_OFF_GAP_S:
                held = True
            else:
                held = False
                self._last_power_off = now
                self._keeping_off = True
                self._keep_input_at = self._period.input_at
                self._retry_at = 0.0
                self._wakes = 0
        if held:
            _trace(
                "action waits: power off displays was sent less than "
                f"{self.POWER_OFF_GAP_S:g} s ago"
            )
            return False
        self._hooked = True
        self._call_hook("before power off", self._before_power_off)
        try:
            self._api.power_off_displays()
            _log().info("Screen Saver Mode: displays powered off")
            _trace("action fired: power off displays: sent")
            _trace("keep off started")
        except Exception as e:
            with self._keep_lock:
                self._keeping_off = False
            _log().exception("Screen Saver Mode action failed")
            _trace(f"action fired: power off displays: failed ({e})")
        return True

    # ----- keeping the displays off (S6, S20)

    def on_display_state(self, on: bool) -> None:
        """Windows reported the display state (the listener thread's window
        procedure; tests call it). Cheap: notes, and while keeping the
        displays off answers an ON report with one power-off, at most once
        per POWER_OFF_GAP_S (inside the gap one re-send waits for its end)."""
        now = clock.monotonic()
        with self._keep_lock:
            self._display_on = on
            if not on:
                self._retry_at = 0.0
                return
            # Counted input since keep-off started: the tick ends it; never
            # power off the displays a person just woke.
            if not self._keeping_off or self._clock.last_input() != self._keep_input_at:
                return
            if now - self._last_power_off < self.POWER_OFF_GAP_S:
                if self._retry_at:
                    return
                self._retry_at = self._last_power_off + self.POWER_OFF_GAP_S
                self._events.append(("wait", self._wakes, "", clock.now()))
                delay = self._retry_at - now
            else:
                self._note_resend(now)
                delay = None
        if delay is None:
            self._post_resend()
            return
        # The held-back re-send goes out from a timer on this (listener)
        # thread, so it never waits for the main thread. If the timer can't
        # be armed, the tick still sends it (_retry_keep_off).
        arm = getattr(self._clock, "arm_timer", None)
        if arm is not None:
            arm(delay)

    def on_retry_timer(self) -> float | None:
        """The re-send timer fired (the listener thread's window procedure;
        tests call it): sends the held-back re-send if it is still due.
        Returns the seconds still to wait, None when nothing is pending."""
        return self._retry_keep_off(clock.monotonic())

    def _note_resend(self, now: float) -> None:
        """Under the lock: one re-send counted."""
        self._retry_at = 0.0
        self._last_power_off = now
        self._wakes += 1
        self._wakes_total += 1
        self._events.append(("resend", self._wakes, "", clock.now()))

    def _post_resend(self) -> None:
        try:
            self._api.power_off_displays()
        except Exception as e:
            self._events.append(("failed", self._wakes, str(e), clock.now()))

    def _retry_keep_off(self, now: float) -> float | None:
        """A re-send held back by the gap, sent once the gap has ended and
        the displays are still on (any thread, under the lock: the timer on
        the listener thread normally, the tick as a fallback). Returns the
        seconds still to wait, None when nothing is pending."""
        with self._keep_lock:
            if not self._retry_at:
                return None
            if (
                not self._keeping_off
                or not self._display_on
                or self._clock.last_input() != self._keep_input_at
            ):
                self._retry_at = 0.0
                return None
            if now < self._retry_at:
                return self._retry_at - now
            self._note_resend(now)
        self._post_resend()
        return None

    def _end_keep_off(self, reason: str) -> None:
        with self._keep_lock:
            if not self._keeping_off:
                return
            self._keeping_off = False
            self._retry_at = 0.0
            wakes, total = self._wakes, self._wakes_total
        self._drain_events()
        _log().info(
            f"Screen Saver Mode: stopped keeping the displays off ({reason}): "
            f"Windows turned them back on {wakes} times in this idle period "
            f"({total} since switched on)"
        )
        _trace(f"keep off ended: {reason}; {wakes} wakes")

    def _drain_events(self) -> None:
        """Traces what the listener thread noted (main thread)."""
        while True:
            try:
                kind, n, text, at = self._events.popleft()
            except IndexError:
                return
            if kind == "resend":
                _trace(
                    "keep off: Windows turned the displays back on, "
                    f"power off sent again (#{n})",
                    t=at,
                )
            elif kind == "wait":
                _trace(
                    "keep off: Windows turned the displays back on within "
                    f"{self.POWER_OFF_GAP_S:g} s of the last power off: "
                    "sent again when the gap ends",
                    t=at,
                )
            elif kind == "failed":
                _log().warning(
                    f"Screen Saver Mode: keep off power off #{n} failed ({text})"
                )
                _trace(f"keep off: power off #{n} failed ({text})", t=at)
            elif kind == "activity":
                listener = self._activity_listener
                if listener is not None:
                    try:
                        listener(text.partition("	")[2])
                    except Exception:
                        _log().exception("Screen Saver Mode: activity listener failed")
            elif kind in ("press", "not_counted"):
                device_kind, _, physical = text.partition("	")
                name = self._device_name(n) or "a device"
                if kind == "not_counted":
                    _trace(
                        f"not counted: {name} ({device_kind}) is not ticked",
                        ring=False,
                    )
                    continue
                _trace(f"press: {name} ({device_kind})", ring=False)
                listener = self._press_listener
                if listener is not None:
                    try:
                        listener(physical, device_kind)
                    except Exception:
                        _log().exception("Screen Saver Mode: press listener failed")

    # ----- status

    def _off_windows_waits(self) -> tuple[str, int, int]:
        """Windows' waits while off, read at most once a second (S5: the
        window shows them while off too)."""
        now = clock.monotonic()
        cached = self._off_read
        if cached is not None and now - cached[0] < self._OFF_READ_S:
            return cached[1], cached[2], cached[3]
        path, saver, off = self._windows_waits()
        self._off_read = (now, path, saver, off)
        return path, saver, off

    def _off_status(self) -> Status:
        path, saver_windows, off_windows = self._off_windows_waits()
        s = self._settings
        saver_wait = _typed(s.screen_saver_wait_s) or saver_windows
        off_wait = _typed(s.power_off_wait_s) or off_windows
        saver_problem, off_problem = _row_problems(path, saver_wait, off_wait)
        with self._keep_lock:
            wakes = self._wakes
        return Status(
            enabled=s.enabled,
            saver_wait_s=saver_wait,
            saver_windows_wait_s=saver_windows,
            saver_from_windows=_typed(s.screen_saver_wait_s) == 0,
            saver_problem=saver_problem,
            off_wait_s=off_wait,
            off_windows_wait_s=off_windows,
            off_from_windows=_typed(s.power_off_wait_s) == 0,
            off_problem=off_problem,
            wakes=wakes,
        )

    def _update_status(
        self,
        now: float | None = None,
        hold: str = "",
        problems: tuple[str, str, str] | None = None,
    ) -> None:
        if not self._running:
            self._status_live = False
            return
        now = clock.monotonic() if now is None else now
        p = self._period
        s = self._settings
        both, saver_problem, off_problem = (
            self._problems() if problems is None else problems
        )
        try:
            windows_idle = float(self._api.windows_idle_s())
        except Exception:
            windows_idle = 0.0

        def remaining(t: _Timer, on: bool, row_problem: str) -> float:
            if hold or both or row_problem or not on or t.fired:
                return 0.0
            return max(0.0, t.wait_s - (now - p.start))

        reset_by, reset_kind = self._reset_source()
        try:
            per_min = int(self._clock.program_input_per_min(now))
        except Exception:
            per_min = 0
        with self._keep_lock:
            keeping_off, wakes = self._keeping_off, self._wakes
        self._status = Status(
            enabled=True,
            listening=self._clock.listening(),
            idle_s=max(0.0, now - p.input_at),
            windows_idle_s=windows_idle,
            saver_wait_s=p.saver.wait_s,
            saver_windows_wait_s=p.saver.windows_wait_s,
            saver_from_windows=_typed(s.screen_saver_wait_s) == 0,
            saver_fired=p.saver.fired,
            saver_remaining_s=remaining(p.saver, s.screen_saver_on, saver_problem),
            saver_problem=saver_problem,
            off_wait_s=p.off.wait_s,
            off_windows_wait_s=p.off.windows_wait_s,
            off_from_windows=_typed(s.power_off_wait_s) == 0,
            off_fired=p.off.fired,
            off_remaining_s=remaining(p.off, s.power_off_on, off_problem),
            off_problem=off_problem,
            keeping_off=keeping_off,
            wakes=wakes,
            hold=hold,
            hold_program=self._hold_program if hold == HOLD_FULLSCREEN else "",
            problem=both,
            last_reset_by=reset_by,
            last_reset_kind=reset_kind,
            last_reset_age_s=max(0.0, now - self._clock.last_input())
            if reset_kind
            else 0.0,
            program_input_per_min=per_min,
        )
        self._status_live = True

    def status(self) -> Status:
        """The status as of the last tick (cheap; the UI polls it). While
        off it carries Windows' waits for both timers."""
        if not self._running or not self._status_live:
            return self._off_status()
        st = replace(self._status)
        # Keep-off can end or count between ticks (listener thread).
        with self._keep_lock:
            st.keeping_off, st.wakes = self._keeping_off, self._wakes
        return st


def _wait_text(seconds: int | float) -> str:
    seconds = int(seconds or 0)
    return f"{seconds} s" if seconds > 0 else "none"


def _timer_text(on: bool, typed: int) -> str:
    if not on:
        return "off"
    wait = _wait_text(typed) if _typed(typed) else "from Windows"
    return f"on (wait {wait})"


_manager: ScreenSaverMode | None = None
_manager_lock = threading.Lock()


def manager() -> ScreenSaverMode:
    """The one Screen Saver Mode."""
    global _manager
    with _manager_lock:
        if _manager is None:
            _manager = ScreenSaverMode()
        return _manager
