# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import ctypes
import logging
import threading
from ctypes import wintypes
from dataclasses import dataclass
from typing import Callable

from gremlin import clock, threads
from gremlin.common import SingletonMetaclass
from gremlin.types import MouseButton

user32 = ctypes.WinDLL("user32")


g_keyboard_callbacks = []
g_mouse_callbacks = []

# False: start() installs no hook. Tests turn it off, so they never hook
# the keyboard and mouse of the PC they run on; the program never does.
enabled = True


# The following pages are references to the various functions used:
#
# SetWindowsHookEx
#     https://msdn.microsoft.com/en-us/library/windows/desktop/ms644990(v=vs.85).aspx
# LowLevelMouseProc
#     https://msdn.microsoft.com/de-de/library/windows/desktop/ms644986(v=vs.85).aspx
# MSLLHOOKSTRUCT
#     https://msdn.microsoft.com/en-us/library/ms644970(v=vs.85).aspx
# LowLevelKeyboardProc
#     https://msdn.microsoft.com/en-us/library/ms644985(v=vs.85).aspx
# KBDLLHOOKSTRUCT
#     https://msdn.microsoft.com/en-us/library/windows/desktop/ms644967(v=vs.85).aspx

# Signature of a hook callback function which can be used as a decorator
HOOKPROC = ctypes.WINFUNCTYPE(
    wintypes.LPARAM, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
)

# fmt: off
# Function to hook into an event stream
user32.SetWindowsHookExW.restype = wintypes.HHOOK
user32.SetWindowsHookExW.argtypes = (
    ctypes.c_int,           # _In_ idHook
    HOOKPROC,               # _In_ lpfn
    wintypes.HINSTANCE,     # _In_ hMod
    wintypes.DWORD          # _In_ dwThreadId
)

# Function to call next hook in the chain
user32.CallNextHookEx.restype = wintypes.LPARAM
user32.CallNextHookEx.argtypes = (
    wintypes.HHOOK,         # _In_opt_ hhk
    ctypes.c_int,           # _In_     nCode
    wintypes.WPARAM,        # _In_     wParam
    wintypes.LPARAM         # _In_     lParam
)

# Retrieve a single message from a stream
user32.GetMessageW.argtypes = (
    wintypes.LPMSG,         # _Out_    lpMsg
    wintypes.HWND,          # _In_opt_ hWnd
    wintypes.UINT,          # _In_     wMsgFilterMin
    wintypes.UINT           # _In_     wMsgFilterMax
)
# fmt: on

# Convert message content
user32.TranslateMessage.argtypes = (wintypes.LPMSG,)

# Dispatch message to hooked processes
user32.DispatchMessageW.argtypes = (wintypes.LPMSG,)

# fmt: off
# Action definitions
HC_ACTION       = 0
WH_KEYBOARD_LL  = 13
WH_MOUSE_LL     = 14

WM_QUIT         = 0x0012
WM_MOUSEMOVE    = 0x0200
WM_LBUTTONDOWN  = 0x0201
WM_LBUTTONUP    = 0x0202
WM_RBUTTONDOWN  = 0x0204
WM_RBUTTONUP    = 0x0205
WM_MBUTTONDOWN  = 0x0207
WM_MBUTTONUP    = 0x0208
WM_MOUSEWHEEL   = 0x020A
WM_XBUTTONDOWN  = 0x020B
WM_XBUTTONUP    = 0x020C
WM_MOUSEHWHEEL  = 0x020E
WM_TIMER        = 0x0113
# Asks a hook's thread to put its hook back (rehook_soon).
WM_REHOOK       = 0x8000 + 1
# fmt: on

# The extra info (dwExtraInfo) on every key the program sends itself
# (keyboard.send_key_down/up), so the hook can tell them from real keys.
OWN_KEY_MARK = 0x47524D4C

# A key that reaches the hook this late (ms) may have cost us the hook.
SLOW_KEY_MS = 200
# The hooks are put back this often (ms) in any case: Windows says
# nothing when it removes one.
REHOOK_EVERY_MS = 10_000

_tick_count = ctypes.windll.kernel32.GetTickCount
_tick_count.restype = wintypes.DWORD
_tick_count.argtypes = ()

user32.SetTimer.restype = ctypes.c_size_t
user32.SetTimer.argtypes = (
    wintypes.HWND, ctypes.c_size_t, wintypes.UINT, ctypes.c_void_p
)
user32.KillTimer.argtypes = (wintypes.HWND, ctypes.c_size_t)
user32.UnhookWindowsHookEx.argtypes = (wintypes.HHOOK,)


class KBDLLHOOKSTRUCT(ctypes.Structure):
    """Data structure used with keuboard callbacks."""

    _fields_ = (
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", wintypes.WPARAM),
    )


LPKBDLLHOOKSTRUCT = ctypes.POINTER(KBDLLHOOKSTRUCT)


class MSLLHOOKSTRUCT(ctypes.Structure):
    """Data structure used with mouse callbacks."""

    _fields_ = (
        ("pt", wintypes.POINT),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", wintypes.WPARAM),
    )


LPMSLLHOOKSTRUCT = ctypes.POINTER(MSLLHOOKSTRUCT)


@HOOKPROC
def process_keyboard_event(n_code: int, w_param: int, l_param: int) -> int:
    """Process a single keyboard event.

    :param n_code code detailing how to process the event
    :param w_param message type identifier
    :param l_param message content
    """
    # Whatever happens here, the key goes on to the other programs' hooks.
    try:
        _keyboard_event(n_code, w_param, l_param)
    except Exception:
        logging.getLogger("system").exception("Keyboard hook callback failed")
    return user32.CallNextHookEx(None, n_code, w_param, l_param)


def _keyboard_event(n_code: int, w_param: int, l_param: int) -> None:
    msg = ctypes.cast(l_param, LPKBDLLHOOKSTRUCT)[0]

    # Only handle events we're supposed to, see
    # https://msdn.microsoft.com/en-us/library/windows/desktop/ms644985(v=vs.85).aspx
    if n_code >= 0 and msg.scanCode:
        # Extract data from the message
        scan_code = msg.scanCode & 0xFF
        is_extended = msg.flags is not None and bool(msg.flags & 0x0001)
        is_pressed = w_param in [0x0100, 0x0104]
        is_injected = msg.flags is not None and bool(msg.flags & 0x0010)
        is_own = is_injected and msg.dwExtraInfo == OWN_KEY_MARK

        # A scan code of 541 indicates AltGr being pressed. AltGr is sent
        # as a combination of RAlt + RCtrl to the system and as such
        # generates two key events, one for RAlt and one for RCtrl. The
        # RCtrl one is being modified due to RAlt being pressed.
        #
        # In this application we want the RAlt key press and ignore the
        # RCtrl key press.

        # Create the event and pass it to all all registered callbacks
        if msg.scanCode != 541:
            evt = KeyEvent(scan_code, is_extended, is_pressed, is_injected, is_own)
            for cb in g_keyboard_callbacks:
                cb(evt)

        # Windows silently removes a low-level hook that keeps it waiting
        # too long (LowLevelHooksTimeout, at most 1 s): a key that reached
        # us late means the hook may be gone, so it is put back.
        if (_tick_count() - msg.time) & 0xFFFFFFFF > SLOW_KEY_MS:
            KeyboardHook().rehook_soon()


@HOOKPROC
def process_mouse_event(n_code: int, w_param: int, l_param: int) -> int:
    """Process a single mouse event.

    :param n_code code detailing how to process the event
    :param w_param message type identifier
    :param l_param message content
    """
    try:
        _mouse_event(n_code, w_param, l_param)
    except Exception:
        logging.getLogger("system").exception("Mouse hook callback failed")
    return user32.CallNextHookEx(None, n_code, w_param, l_param)


def _mouse_event(n_code: int, w_param: int, l_param: int) -> None:
    if n_code == HC_ACTION and w_param != WM_MOUSEMOVE:
        msg = ctypes.cast(l_param, LPMSLLHOOKSTRUCT)[0]

        # Only handle events we're supposed to, see
        # https://msdn.microsoft.com/en-us/library/windows/desktop/ms644985(v=vs.85).aspx
        button_id = None
        is_pressed = True
        if w_param in [WM_LBUTTONDOWN, WM_LBUTTONUP]:
            button_id = MouseButton.Left
            is_pressed = w_param == WM_LBUTTONDOWN
        elif w_param in [WM_RBUTTONDOWN, WM_RBUTTONUP]:
            button_id = MouseButton.Right
            is_pressed = w_param == WM_RBUTTONDOWN
        elif w_param in [WM_MBUTTONDOWN, WM_MBUTTONUP]:
            button_id = MouseButton.Middle
            is_pressed = w_param == WM_MBUTTONDOWN
        elif w_param in [WM_XBUTTONDOWN, WM_XBUTTONUP]:
            if msg.mouseData & (0x0001 << 16):
                button_id = MouseButton.Back
            elif msg.mouseData & (0x0002 << 16):
                button_id = MouseButton.Forward
            is_pressed = w_param == WM_XBUTTONDOWN
        elif w_param == WM_MOUSEWHEEL:
            if (msg.mouseData >> 16) == 120:
                button_id = MouseButton.WheelUp
            elif (msg.mouseData >> 16) == 65416:
                button_id = MouseButton.WheelDown

        # Create the event and pass it to all all registered callbacks
        evt = MouseEvent(button_id, is_pressed)
        for cb in g_mouse_callbacks:
            cb(evt)


@dataclass
class KeyEvent:
    """Structure containing details about a key event.

    - scan_code is the hardware scan code of this event
    - is_extended indicates whether the scan code is an extended one
    - is_pressed is a flag indicating if the key is pressed
    - is_injected indicates if the event has been injected
    - is_own: injected by this program (keyboard.send_key_down/up)
    """

    scan_code: int
    is_extended: bool
    is_pressed: bool
    is_injected: bool
    is_own: bool = False

    def __str__(self) -> str:
        """Returns a string representation of the event.

        :return string representation of the event
        """
        up_or_down = "down" if self.is_pressed else "up"
        injected_str = "injected" if self.is_injected else ""
        return (
            f"({hex(self.scan_code)} {self.is_extended}) {up_or_down}, {injected_str}"
        )


@dataclass
class MouseEvent:
    """Structure containing information about a mouse event."""

    button_id: MouseButton
    is_pressed: bool


class _Hook:
    """A low-level Windows hook with its own thread and message loop.

    The hook only works while its thread runs a message loop; WM_QUIT
    posted to that thread ends the loop.
    """

    _NAME = ""
    _HOOK_TYPE = 0
    _STOP_WAIT_S = 2.0

    def __init__(self) -> None:
        self._running = False
        self._listen_thread: threading.Thread | None = None
        self._rehook_asked = False

    def _handler(self) -> Callable[[int, int, int], int]:
        raise NotImplementedError

    def start(self) -> None:
        """Starts the hook if it is not yet running."""
        if self._running or not enabled:
            return
        self._running = True
        self._listen_thread = threads.start(
            self._NAME, self._listen, stop=self._ask_to_stop
        )

    def stop(self) -> None:
        """Stops the hook and waits (briefly) for its thread to end."""
        if not self._running:
            return
        self._running = False
        thread = self._listen_thread
        if thread is None:
            return
        # Posted again until the thread ends: one posted before the thread
        # has its message queue would be lost.
        deadline = clock.monotonic() + self._STOP_WAIT_S
        while thread.is_alive() and clock.monotonic() < deadline:
            self._post_quit(thread)
            thread.join(0.05)
        if thread.is_alive():
            logging.getLogger("system").warning(f"{thread.name} did not stop")

    def _ask_to_stop(self) -> None:
        self._running = False
        if self._listen_thread is not None:
            self._post_quit(self._listen_thread)

    @staticmethod
    def _post_quit(thread: threading.Thread) -> None:
        if thread.ident is not None:
            user32.PostThreadMessageW(thread.ident, WM_QUIT, 0, 0)

    def rehook_soon(self) -> None:
        """Asks the hook's thread to put the hook back (Windows may have
        removed it). Asked once until the thread has done it."""
        thread = self._listen_thread
        if not self._running or thread is None or thread.ident is None:
            return
        if self._rehook_asked:
            return
        self._rehook_asked = True
        user32.PostThreadMessageW(thread.ident, WM_REHOOK, 0, 0)

    def _install(self) -> int:
        return user32.SetWindowsHookExW(self._HOOK_TYPE, self._handler(), None, 0)

    def _rehook(self, hook_id: int) -> int:
        """Installs the hook again, then removes the old one (which fails
        quietly if Windows already did). Runs on the hook's thread between
        messages, so no event is seen twice or missed. Returns the hook in
        use."""
        self._rehook_asked = False
        new_id = self._install()
        if not new_id:
            logging.getLogger("system").warning(f"{self._NAME} could not be put back")
            return hook_id
        try:
            user32.UnhookWindowsHookEx(hook_id)
        except Exception:
            pass
        return new_id

    def _listen(self) -> None:
        """Installs the hook and runs the message loop until WM_QUIT.

        The hook is put back every REHOOK_EVERY_MS and when a callback
        asks for it (rehook_soon): Windows removes a slow hook silently.
        """
        self._rehook_asked = False
        hook_id = self._install()
        timer_id = user32.SetTimer(None, 0, REHOOK_EVERY_MS, None)
        try:
            msg = wintypes.MSG()
            while self._running:
                result = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if not result:
                    break
                if result == -1:
                    raise ctypes.WinError(ctypes.get_last_error())
                if msg.message == WM_REHOOK or (
                    msg.message == WM_TIMER and not msg.hWnd and msg.wParam == timer_id
                ):
                    hook_id = self._rehook(hook_id)
                    continue
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            try:
                if timer_id:
                    user32.KillTimer(None, timer_id)
                user32.UnhookWindowsHookEx(hook_id)
            except Exception:
                pass


class KeyboardHook(_Hook, metaclass=SingletonMetaclass):
    """Hooks into the event stream and grabs keyboard related events
    and passes them on to registered callback functions.
    """

    _NAME = "keyboard hook"
    _HOOK_TYPE = WH_KEYBOARD_LL

    def _handler(self) -> Callable[[int, int, int], int]:
        return process_keyboard_event

    def register(self, callback: Callable[[KeyEvent], None]) -> None:
        """Registers a new message callback.

        Args:
            callback: callback to add to the list of functions to receive events
        """
        global g_keyboard_callbacks
        g_keyboard_callbacks.append(callback)


class MouseHook(_Hook, metaclass=SingletonMetaclass):
    """Hooks into the event stream and grabs mouse related events and passes
    them on to registered callback functions.
    """

    _NAME = "mouse hook"
    _HOOK_TYPE = WH_MOUSE_LL

    def __init__(self) -> None:
        super().__init__()
        # Listen and macro Record share the one hook (start/stop count).
        self._users = 0
        self._users_lock = threading.Lock()

    def _handler(self) -> Callable[[int, int, int], int]:
        return process_mouse_event

    def register(self, callback: Callable[[MouseEvent], None]) -> None:
        """Registers a new message callback.

        :param callback the new callback to register
        """
        global g_mouse_callbacks
        g_mouse_callbacks.append(callback)

    def acquire(self) -> None:
        """One more user (Listen, macro Record) wants mouse events: the hook
        runs while anyone wants it."""
        with self._users_lock:
            self._users += 1
            first = self._users == 1
        if first:
            self.start()

    def release(self) -> None:
        """A user no longer wants mouse events: the last one out stops the
        hook. A release without an acquire does nothing."""
        with self._users_lock:
            if self._users == 0:
                return
            self._users -= 1
            last = self._users == 0
        if last:
            self.stop()

    @property
    def users(self) -> int:
        return self._users
