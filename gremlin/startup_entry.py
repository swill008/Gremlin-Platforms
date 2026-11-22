# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Start with Windows (01 S194): the program's value in the user's own
Windows sign-in list, HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run.
Windows' list is the truth; nothing else stores whether it is on."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Protocol

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "Gremlin-Platforms"
# Windows' own Startup Apps switch is recorded here (read, never written).
APPROVED_KEY = (
    r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
)
NOTE_OFF_IN_WINDOWS = "Turned off in Windows' Startup Apps"
SETTINGS_URI = "ms-settings:startupapps"

_log = logging.getLogger("system")


class RealRegistryBlocked(RuntimeError):
    """The real Windows registry used from a test."""


class Store(Protocol):
    def get(self, name: str) -> str | None: ...
    def set(self, name: str, value: str) -> None: ...
    def delete(self, name: str) -> None: ...


class ApprovedStore(Protocol):
    """Read-only: the StartupApproved record, whose first byte is odd when the
    user turned the entry off in Windows' Startup Apps."""

    def get(self, name: str) -> bytes | None: ...


def _under_test() -> bool:
    return bool(os.environ.get("PYTEST_CURRENT_TEST")) or "pytest" in sys.modules


class _RealStore:
    """The HKCU Run key (no administrator permission needed)."""

    def __init__(self) -> None:
        if _under_test():
            raise RealRegistryBlocked(
                "startup_entry used the real registry from a test"
            )

    def get(self, name: str) -> str | None:
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
                value, _kind = winreg.QueryValueEx(key, name)
        except FileNotFoundError:
            return None
        return str(value)

    def set(self, name: str, value: str) -> None:
        import winreg

        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)

    def delete(self, name: str) -> None:
        import winreg

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
            ) as key:
                winreg.DeleteValue(key, name)
        except FileNotFoundError:
            pass


class _RealApprovedStore:
    def __init__(self) -> None:
        if _under_test():
            raise RealRegistryBlocked(
                "startup_entry used the real registry from a test"
            )

    def get(self, name: str) -> bytes | None:
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, APPROVED_KEY) as key:
                value, _kind = winreg.QueryValueEx(key, name)
        except OSError:
            return None
        return bytes(value) if isinstance(value, (bytes, bytearray)) else None


def _store(store: Store | None) -> Store:
    return store if store is not None else _RealStore()


def command(exe: str | None = None) -> str:
    """The sign-in command: the installed exe with --start-minimized. Run from
    source, pythonw (no console) with joystick_gremlin.py, which moves to its
    own folder when it starts."""
    if exe is not None or getattr(sys, "frozen", False):
        return f'"{exe or sys.executable}" --start-minimized'
    python = Path(sys.executable)
    pythonw = python.with_name("pythonw.exe")
    if pythonw.is_file():
        python = pythonw
    script = Path(__file__).resolve().parent.parent / "joystick_gremlin.py"
    return f'"{python}" "{script}" --start-minimized'


def state(
    store: Store | None = None, approved: ApprovedStore | None = None
) -> str:
    """"off" (no entry), "off_in_windows" (entry present, switched off in
    Windows' Startup Apps) or "on". An unreadable record counts as absent."""
    if _store(store).get(VALUE_NAME) is None:
        return "off"
    record = approved if approved is not None else _RealApprovedStore()
    try:
        data = record.get(VALUE_NAME)
    except OSError:
        data = None
    if isinstance(data, (bytes, bytearray)) and data and data[0] % 2 == 1:
        return "off_in_windows"
    return "on"


def is_enabled(
    store: Store | None = None, approved: ApprovedStore | None = None
) -> bool:
    """True when the entry is there and Windows lets it run."""
    return state(store, approved) == "on"


def open_windows_startup_settings() -> bool:
    """Opens Windows' Startup Apps page; True when asked. Refused in tests."""
    if _under_test():
        raise RealRegistryBlocked("startup_entry opened Windows settings from a test")
    try:
        os.startfile(SETTINGS_URI)  # type: ignore[attr-defined]  # noqa: S606
    except OSError as exc:
        _log.warning(f"Start with Windows: could not open Windows settings: {exc}")
        return False
    return True


def set_enabled(on: bool, store: Store | None = None) -> bool:
    """Adds (on) or removes the value; True when done, False (logged) when
    Windows refused."""
    target = _store(store)
    try:
        if on:
            target.set(VALUE_NAME, command())
        else:
            target.delete(VALUE_NAME)
    except OSError as exc:
        verb = "added to" if on else "removed from"
        _log.warning(
            f"Start with Windows: the entry could not be {verb} the Windows "
            f"sign-in list: {exc}"
        )
        return False
    _log.info(f"Start with Windows: {'on' if on else 'off'}")
    return True
