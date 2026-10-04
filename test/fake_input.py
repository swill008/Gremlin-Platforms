# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Keys and mouse input the program sends stay inside the test process.

The program sends keys with keybd_event and mouse input with SendInput.
In a test those went to the real PC: tests typed into whichever window had
focus, and read the keys back through a real keyboard hook. install()
replaces both: a key is recorded in sent and handed straight to the
program's keyboard callbacks, as the hook would have; mouse input is
recorded only. test/conftest.py installs it before anything starts.
"""

from __future__ import annotations

import win32api
import win32con

from gremlin import sendinput, windows_event_hook

# ("key", scan_code, is_extended, is_pressed) or ("input", count).
sent: list[tuple] = []


def _keybd_event(
    virtual_code: int, scan_code: int, flags: int, extra: int = 0
) -> None:
    is_pressed = not flags & win32con.KEYEVENTF_KEYUP
    is_extended = bool(flags & win32con.KEYEVENTF_EXTENDEDKEY)
    sent.append(("key", scan_code, is_extended, is_pressed))
    event = windows_event_hook.KeyEvent(
        scan_code & 0xFF, is_extended, bool(is_pressed), True
    )
    for callback in list(windows_event_hook.g_keyboard_callbacks):
        callback(event)


def _send_input(*inputs: object) -> int:
    sent.append(("input", len(inputs)))
    return len(inputs)


def install() -> None:
    """Keeps the program's key and mouse output inside the test process."""
    win32api.keybd_event = _keybd_event
    sendinput._send_input = _send_input
