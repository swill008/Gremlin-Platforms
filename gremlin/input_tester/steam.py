# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Is Steam running? Process list only (read only, no process opened)."""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes

STEAM_EXE = "steam.exe"

_TH32CS_SNAPPROCESS = 0x00000002
_INVALID_HANDLE = ctypes.c_void_p(-1).value


class _PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_void_p),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


def process_names() -> list[str]:
    """Exe names of every running process (casefolded)."""
    if os.name != "nt":
        return []
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
    k32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    k32.Process32FirstW.argtypes = [ctypes.c_void_p, ctypes.POINTER(_PROCESSENTRY32W)]
    k32.Process32NextW.argtypes = [ctypes.c_void_p, ctypes.POINTER(_PROCESSENTRY32W)]
    k32.CloseHandle.argtypes = [ctypes.c_void_p]
    snap = k32.CreateToolhelp32Snapshot(_TH32CS_SNAPPROCESS, 0)
    if not snap or snap == _INVALID_HANDLE:
        return []
    names: list[str] = []
    try:
        entry = _PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(entry)
        ok = k32.Process32FirstW(snap, ctypes.byref(entry))
        while ok:
            names.append(entry.szExeFile.casefold())
            ok = k32.Process32NextW(snap, ctypes.byref(entry))
    finally:
        k32.CloseHandle(snap)
    return names


def steam_running() -> bool:
    return STEAM_EXE in process_names()
