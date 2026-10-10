# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""Running process paths, and the checks that compare them with HidHide's
program list (wrong copy of a game running, old Input Tester entry).

Read only: processes are opened with query rights and nothing else."""

from __future__ import annotations

import ntpath
import sys
from collections.abc import Iterable

TESTER_EXE = "Gremlin Input Tester.exe"


def running_images() -> list[str]:
    """Full image paths of the running processes; ones that can't be opened
    are skipped."""
    if sys.platform != "win32":
        return []
    import ctypes
    from ctypes import wintypes

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * 260),
        ]

    k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    k32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    k32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    k32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    k32.OpenProcess.restype = wintypes.HANDLE
    k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)
    ]
    k32.CloseHandle.argtypes = [wintypes.HANDLE]

    TH32CS_SNAPPROCESS = 0x2
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    invalid = wintypes.HANDLE(-1).value

    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if not snap or snap == invalid:
        return []
    pids: list[int] = []
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        ok = k32.Process32FirstW(snap, ctypes.byref(entry))
        while ok:
            pids.append(int(entry.th32ProcessID))
            ok = k32.Process32NextW(snap, ctypes.byref(entry))
    finally:
        k32.CloseHandle(snap)

    images: list[str] = []
    buf = ctypes.create_unicode_buffer(32768)
    for pid in pids:
        if pid == 0:
            continue
        handle = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            continue
        try:
            size = wintypes.DWORD(len(buf))
            if k32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
                images.append(buf.value)
        finally:
            k32.CloseHandle(handle)
    return images


def _key(path: str) -> str:
    return ntpath.normcase(ntpath.normpath(path.strip()))


def _name(path: str) -> str:
    return ntpath.basename(path.strip()).casefold()


def game_path_problems(games: Iterable[dict], images: Iterable[str]) -> list[str]:
    """One message per running path whose exe name matches a listed game but
    whose full path isn't on the list."""
    listed = {_key(str(g.get("path", ""))) for g in games if g.get("path")}
    names = {_name(p) for p in listed}
    problems: list[str] = []
    seen: set[str] = set()
    for image in images:
        if not image:
            continue
        key = _key(image)
        if key in listed or key in seen or _name(image) not in names:
            continue
        seen.add(key)
        problems.append(
            f"{ntpath.basename(image)} is running from {image}, "
            "which isn't on the list"
        )
    return problems


def old_tester_entry(apps: Iterable[str], current: str) -> str:
    """The first list entry that is an Input Tester but not the current one."""
    if not current:
        return ""
    cur = _key(current)
    for app in apps:
        if _name(app) == TESTER_EXE.casefold() and _key(app) != cur:
            return app
    return ""


def tester_path_problem(apps: Iterable[str], current: str) -> str:
    """Message when the list holds an Input Tester from another folder;
    "" when it doesn't (or the current copy is also there)."""
    apps = list(apps)
    if current and any(_key(a) == _key(current) for a in apps):
        return ""
    old = old_tester_entry(apps, current)
    if not old:
        return ""
    return (
        f"The Input Tester on the list is an old copy ({old}); "
        f"the current one is {current}"
    )
