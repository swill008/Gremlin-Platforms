"""Quick test for Screen Saver Mode's "keep the displays off" idea (1a).

Turns the displays off once. Whenever Windows turns them back on WITHOUT
real keyboard or mouse input (devices that never go quiet do that), it
turns them off again, at most once a second. The first keyboard or mouse
input ends the test and leaves the displays on.

Run:  python tools/monitor_keep_off_test.py [minutes]   (default 30)
Each event is printed and written to monitor_keep_off_test.log beside it.
Sends no keyboard or mouse input; changes no settings.
"""

from __future__ import annotations

import ctypes
import sys
import time
from ctypes import wintypes
from pathlib import Path

u = ctypes.WinDLL("user32", use_last_error=True)
k = ctypes.WinDLL("kernel32")
LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(
    LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
)
u.DefWindowProcW.restype = LRESULT
u.DefWindowProcW.argtypes = (
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
)
u.PostMessageW.argtypes = (
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
)
u.CreateWindowExW.restype = wintypes.HWND

WM_INPUT, WM_POWERBROADCAST, PBT_POWERSETTINGCHANGE = 0x00FF, 0x0218, 0x8013
WM_SYSCOMMAND, SC_MONITORPOWER, MONITOR_OFF = 0x0112, 0xF170, 2
MIN_GAP_S = 1.0
LOG = Path(__file__).with_suffix(".log")


class GUID(ctypes.Structure):
    _fields_ = [
        ("a", ctypes.c_uint32),
        ("b", ctypes.c_uint16),
        ("c", ctypes.c_uint16),
        ("d", ctypes.c_ubyte * 8),
    ]


DISPLAY_STATE = GUID(
    0x6FE69556,
    0x704A,
    0x47A0,
    (ctypes.c_ubyte * 8)(0x8F, 0x24, 0xC2, 0x8D, 0x93, 0x6F, 0xDA, 0x47),
)


class POWERBROADCAST_SETTING(ctypes.Structure):
    _fields_ = [("g", GUID), ("n", wintypes.DWORD), ("d", ctypes.c_ubyte * 4)]


class RAWINPUTHEADER(ctypes.Structure):
    _fields_ = [
        ("dwType", wintypes.DWORD),
        ("dwSize", wintypes.DWORD),
        ("hDevice", wintypes.HANDLE),
        ("wParam", wintypes.WPARAM),
    ]


class RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [
        ("usUsagePage", wintypes.USHORT),
        ("usUsage", wintypes.USHORT),
        ("dwFlags", wintypes.DWORD),
        ("hwndTarget", wintypes.HWND),
    ]


class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
        ("hIconSm", wintypes.HICON),
    ]


state = {"stop": False, "want_off": True, "last_send": 0.0, "resends": 0, "hwnd": None}


def log(text: str) -> None:
    t = time.time()
    line = (
        time.strftime("%H:%M:%S", time.localtime(t))
        + f".{int(t % 1 * 1000):03d} {text}"
    )
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def power_off(why: str) -> None:
    now = time.monotonic()
    if now - state["last_send"] < MIN_GAP_S:
        return
    state["last_send"] = now
    u.PostMessageW(state["hwnd"], WM_SYSCOMMAND, SC_MONITORPOWER, MONITOR_OFF)
    log(f"power off sent ({why})")


def proc(hwnd: int, msg: int, wp: int, lp: int) -> int:
    if msg == WM_INPUT and state["want_off"]:
        hdr = RAWINPUTHEADER()
        size = wintypes.UINT(ctypes.sizeof(hdr))
        u.GetRawInputData(
            wintypes.HANDLE(lp),
            0x10000005,
            ctypes.byref(hdr),
            ctypes.byref(size),
            ctypes.sizeof(hdr),
        )
        kind = {0: "mouse", 1: "keyboard"}.get(hdr.dwType, "other")
        log(f"real input ({kind}): stopping, displays stay on")
        state["want_off"] = False
        state["stop"] = True
    elif msg == WM_POWERBROADCAST and wp == PBT_POWERSETTINGCHANGE:
        s = ctypes.cast(lp, ctypes.POINTER(POWERBROADCAST_SETTING))[0]
        on = s.d[0] != 0
        log(f"Windows: display {'ON' if on else 'OFF'}")
        if on and state["want_off"]:
            state["resends"] += 1
            power_off(f"Windows woke them without input, #{state['resends']}")
    return u.DefWindowProcW(hwnd, msg, wp, lp)


def main() -> None:
    minutes = float(sys.argv[1]) if len(sys.argv) > 1 else 30.0
    wndproc = WNDPROC(proc)
    wc = WNDCLASSEXW()
    wc.cbSize = ctypes.sizeof(wc)
    wc.lpfnWndProc = wndproc
    wc.hInstance = k.GetModuleHandleW(None)
    wc.lpszClassName = "MonitorKeepOffTest"
    u.RegisterClassExW(ctypes.byref(wc))
    hwnd = u.CreateWindowExW(
        0, "MonitorKeepOffTest", "", 0, 0, 0, 0, 0, None, None, wc.hInstance, None
    )
    state["hwnd"] = hwnd
    u.RegisterPowerSettingNotification(hwnd, ctypes.byref(DISPLAY_STATE), 0)
    log(
        f"monitor keep-off test, up to {minutes:g} min; "
        "touch the keyboard or mouse to end it"
    )
    msg = wintypes.MSG()
    # Let the display-state message for "now" arrive, then a short grace so
    # the key press that started the test doesn't end it.
    end = time.monotonic() + 3.0
    while time.monotonic() < end:
        while u.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
            u.DispatchMessageW(ctypes.byref(msg))
        time.sleep(0.02)
    devices = (RAWINPUTDEVICE * 2)(
        RAWINPUTDEVICE(1, 2, 0x100, hwnd), RAWINPUTDEVICE(1, 6, 0x100, hwnd)
    )
    u.RegisterRawInputDevices(devices, 2, ctypes.sizeof(RAWINPUTDEVICE))
    power_off("start")
    end = time.monotonic() + minutes * 60
    while not state["stop"] and time.monotonic() < end:
        while u.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
            u.DispatchMessageW(ctypes.byref(msg))
        u.MsgWaitForMultipleObjects(0, None, False, 100, 0x04FF)
    log(f"done: Windows woke the displays {state['resends']} times without input")


if __name__ == "__main__":
    main()
