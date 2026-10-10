# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""Running process paths, and the checks that compare them with HidHide's
program list (wrong copy of a game running, old Input Tester entry).

Read only: processes are opened with query rights and nothing else."""

from __future__ import annotations

import datetime
import ntpath
import sys
from collections.abc import Iterable

TESTER_EXE = "Gremlin Input Tester.exe"


def running_images() -> list[str]:
    """Full image paths of the running processes; ones that can't be opened
    are skipped."""
    return [path for path, _start in running_programs()]


def running_programs(
    names: Iterable[str] | None = None,
) -> list[tuple[str, datetime.datetime | None]]:
    """(full image path, local start time) of the running processes; ones
    that can't be opened are skipped, a start time that can't be read is
    None. names (exe file names): only processes with one of these names are
    opened (each Windows call gives up the GIL, so fewer is quicker)."""
    wanted = None if names is None else {_name(n) for n in names if n}
    if wanted is not None and not wanted:
        return []
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
    k32.GetProcessTimes.argtypes = [
        wintypes.HANDLE, *[ctypes.POINTER(wintypes.FILETIME)] * 4
    ]

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
            if wanted is None or entry.szExeFile.casefold() in wanted:
                pids.append(int(entry.th32ProcessID))
            ok = k32.Process32NextW(snap, ctypes.byref(entry))
    finally:
        k32.CloseHandle(snap)

    images: list[tuple[str, datetime.datetime | None]] = []
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
                times = [wintypes.FILETIME() for _ in range(4)]
                start = None
                if k32.GetProcessTimes(handle, *(ctypes.byref(f) for f in times)):
                    ticks = (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime
                    start = _filetime(ticks)
                images.append((buf.value, start))
        finally:
            k32.CloseHandle(handle)
    return images


def _filetime(ticks: int) -> datetime.datetime | None:
    """A FILETIME (100 ns since 1601, UTC) as a local time without zone."""
    if ticks <= 0:
        return None
    utc = datetime.datetime(1601, 1, 1, tzinfo=datetime.UTC) + datetime.timedelta(
        microseconds=ticks // 10
    )
    return utc.astimezone().replace(tzinfo=None)


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


def started_before(
    programs: Iterable[tuple[str, datetime.datetime | None]],
    listed: Iterable[str],
    when: datetime.datetime | None,
) -> list[tuple[str, datetime.datetime]]:
    """(path, start) of each running program on the listed paths that
    started before `when`; one per path (the earliest). Nothing when `when`
    is None (no change known)."""
    if when is None:
        return []
    keys = {_key(str(p)) for p in listed if p}
    if not keys:
        return []
    found: dict[str, tuple[str, datetime.datetime]] = {}
    for path, start in programs:
        if not path or start is None or start >= when:
            continue
        key = _key(path)
        if key not in keys:
            continue
        if key not in found or start < found[key][1]:
            found[key] = (path, start)
    return list(found.values())


def stale_text(
    path: str, start: datetime.datetime, change: datetime.datetime
) -> str:
    """The warning for a program started before the last HidHide change."""
    started, changed = start.strftime("%H:%M"), change.strftime("%H:%M")
    if _name(path) == TESTER_EXE.casefold():
        return (
            f"Gremlin Input Tester was started ({started}) before the last HidHide "
            f"change ({changed}): restart it so the change applies. Restart Input "
            "Tester opens a new one; close the old window."
        )
    return (
        f"{ntpath.basename(path.strip())} was started ({started}) before the last "
        f"HidHide change ({changed}): restart it so the change applies. HidHide "
        "only checks devices when a program opens them."
    )
