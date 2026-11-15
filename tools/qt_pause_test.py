"""Does Qt's main thread pause while the displays are off?

A small Qt Quick window that changes every 200 ms, and a 100 ms main-thread
stopwatch that records the longest gap. After 5 s the displays go off and
are kept off (as Screen Saver Mode does) for 20 s, then the result is
printed. `--no-vsync` switches off "wait for the screen" (swap interval 0).
Keyboard or mouse input ends the keep-off early. Sends no input.

Run:  python tools/qt_pause_test.py [--no-vsync]
"""

from __future__ import annotations

import ctypes
import sys
import time
from ctypes import wintypes

from PySide6 import QtCore, QtGui, QtQuick

NO_VSYNC = "--no-vsync" in sys.argv
NO_WINDOW = "--no-window" in sys.argv
OTHER_THREAD = "--other-thread" in sys.argv
if NO_VSYNC:
    fmt = QtGui.QSurfaceFormat.defaultFormat()
    fmt.setSwapInterval(0)
    QtGui.QSurfaceFormat.setDefaultFormat(fmt)

app = QtGui.QGuiApplication(sys.argv)
view = QtQuick.QQuickView()
view.setResizeMode(QtQuick.QQuickView.ResizeMode.SizeRootObjectToView)
qml = b"""
import QtQuick
Rectangle { width: 240; height: 80; color: "#202020"
  property int n: 0
  Timer { interval: 200; running: true; repeat: true; onTriggered: n++ }
  Text { anchors.centerIn: parent; color: "white"; text: "frame " + n } }
"""
view.setSource(QtCore.QUrl("data:text/plain," + bytes(qml).decode()))
if not NO_WINDOW:
    view.show()
screen_events: list[str] = []
app.screenAdded.connect(
    lambda s: screen_events.append(f"{time.strftime('%H:%M:%S')} added {s.name()}")
)
app.screenRemoved.connect(
    lambda s: screen_events.append(f"{time.strftime('%H:%M:%S')} removed {s.name()}")
)

u = ctypes.WinDLL("user32")
u.PostMessageW.argtypes = (
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
)
u.GetLastInputInfo.argtypes = (ctypes.c_void_p,)


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]


def stamp() -> str:
    return time.strftime("%H:%M:%S")


state = {
    "last": time.monotonic(),
    "worst": 0.0,
    "worst_at": "",
    "phase": "before",
    "end": 0.0,
}
hwnd = int(view.winId())
if OTHER_THREAD:
    # A hidden window on its own thread with its own message loop, as
    # Screen Saver Mode's listener: the power-off is handled there.
    import threading

    _ready = threading.Event()
    _box: dict = {}

    def _own_loop() -> None:
        LRESULT = ctypes.c_ssize_t
        WNDPROC = ctypes.WINFUNCTYPE(
            LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
        )
        uu = ctypes.WinDLL("user32")
        uu.DefWindowProcW.restype = LRESULT
        uu.DefWindowProcW.argtypes = (
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )
        uu.CreateWindowExW.restype = wintypes.HWND

        class WC(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.UINT),
                ("style", wintypes.UINT),
                ("p", WNDPROC),
                ("a", ctypes.c_int),
                ("b", ctypes.c_int),
                ("i", wintypes.HINSTANCE),
                ("ic", wintypes.HICON),
                ("cu", wintypes.HANDLE),
                ("bg", wintypes.HBRUSH),
                ("mn", wintypes.LPCWSTR),
                ("cn", wintypes.LPCWSTR),
                ("sm", wintypes.HICON),
            ]

        proc = WNDPROC(lambda h, m, w, lp: uu.DefWindowProcW(h, m, w, lp))
        wc = WC()
        wc.cbSize = ctypes.sizeof(wc)
        wc.p = proc
        wc.i = ctypes.WinDLL("kernel32").GetModuleHandleW(None)
        wc.cn = "QtPauseOther"
        uu.RegisterClassExW(ctypes.byref(wc))
        _box["hwnd"] = uu.CreateWindowExW(
            0, "QtPauseOther", "", 0, 0, 0, 0, 0, None, None, wc.i, None
        )
        _ready.set()
        msg = wintypes.MSG()
        while uu.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            uu.DispatchMessageW(ctypes.byref(msg))

    threading.Thread(target=_own_loop, daemon=True).start()
    _ready.wait(5)
    hwnd = _box["hwnd"]


def beat() -> None:
    now = time.monotonic()
    gap = now - state["last"]
    state["last"] = now
    if state["phase"] == "off" and gap > state["worst"]:
        state["worst"], state["worst_at"] = gap, stamp()


def power_off() -> None:
    u.PostMessageW(hwnd, 0x0112, 0xF170, 2)


def step() -> None:
    now = time.monotonic()
    if state["phase"] == "before" and now >= state["end"]:
        state["phase"], state["end"] = "off", now + 20
        print(
            stamp(),
            "displays off for 20 s",
            "(no vsync)" if NO_VSYNC else "(vsync on)",
            "(no window)" if NO_WINDOW else "",
            "(power-off on another thread)" if OTHER_THREAD else "",
            flush=True,
        )
        power_off()
    elif state["phase"] == "off":
        if now >= state["end"]:
            state["phase"] = "done"
            print(
                stamp(),
                f"longest main-thread gap while off: {state['worst']:.2f} s "
                f"at {state['worst_at']}",
                flush=True,
            )
            print(
                stamp(),
                f"screen added/removed messages: {len(screen_events)}",
                flush=True,
            )
            for line in screen_events[:12]:
                print("   ", line, flush=True)
            app.quit()
        else:
            power_off()  # keep off, about once a second (as Screen Saver Mode)


state["end"] = time.monotonic() + 5
t1 = QtCore.QTimer()
t1.setInterval(100)
t1.timeout.connect(beat)
t1.start()
t2 = QtCore.QTimer()
t2.setInterval(1000)
t2.timeout.connect(step)
t2.start()
print(stamp(), "Qt window up; displays go off in 5 s; hands off", flush=True)
app.exec()
