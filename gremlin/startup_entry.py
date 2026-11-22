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

_log = logging.getLogger("system")


class RealRegistryBlocked(RuntimeError):
    """The real Windows registry used from a test."""


class Store(Protocol):
    def get(self, name: str) -> str | None: ...
    def set(self, name: str, value: str) -> None: ...
    def delete(self, name: str) -> None: ...


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


def is_enabled(store: Store | None = None) -> bool:
    """True when the value is in the list (whatever its command)."""
    return _store(store).get(VALUE_NAME) is not None


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
