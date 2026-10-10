# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""Reset Devices: restart physical USB game controllers so every program
opens them again (HidHide only checks a device when a program opens it).

Listing and the presence checks are read only (SetupAPI / cfgmgr32). The
restart itself is one elevated cmd.exe running `pnputil /restart-device`
per device; Gremlin never runs elevated. Tests replace the runner with
set_runner(); the real one refuses to run under pytest."""

from __future__ import annotations

import ntpath
import os
import shutil
import sys
import tempfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from gremlin import clock

RESET_TIMEOUT = 60.0
BACK_TIMEOUT = 10.0
_POLL = 0.1

ERROR_CANCELLED = 1223
ERROR_SUCCESS_REBOOT_REQUIRED = 3010

_VJOY = (0x1234, 0xBEAD)
_VIGEM_MARKS = ("VIGEM", "VIRTUAL GAMEPAD EMULATION")


class Cancelled(Exception):
    """The user declined Windows' administrator prompt; nothing was reset."""


class RealRunnerBlocked(RuntimeError):
    """The real runner was called from a test."""


@dataclass
class ResetDevice:
    usb_id: str
    hid_ids: list[str] = field(default_factory=list)
    name: str = ""
    windows_name: str = ""
    vid: int = 0
    pid: int = 0
    plugged: bool = True
    hidden: bool = False
    in_profile: bool = False

    @property
    def vid_pid_text(self) -> str:
        return f"VID {self.vid:04X} · PID {self.pid:04X}"


@dataclass
class ResetResult:
    usb_id: str
    # ok | restart | not_found (absent before the reset) | declined | failed
    outcome: str
    code: int | None = None
    back_after: float | None = None
    detail: str = ""

    @property
    def text(self) -> str:
        if self.outcome == "ok":
            if self.back_after is None:
                return f"reset ✓ · not back after {BACK_TIMEOUT:.0f} s"
            return f"reset ✓ · back after {self.back_after:.1f} s"
        if self.outcome == "restart":
            return "needs a Windows restart, or unplug it and plug it back in"
        if self.outcome == "not_found":
            return "not found"
        if self.outcome == "declined":
            return "permission declined"
        if self.code is None:
            return f"failed: {self.detail or 'no result'}"
        return f"failed: {self.code} (0x{self.code & 0xFFFFFFFF:08X})"


# Test seams ---------------------------------------------------------------

Runner = Callable[[list[str]], dict[str, int]]
_runner: Runner | None = None
_enumerator: Callable[[], list[dict]] | None = None
_presence: Callable[[str], bool] | None = None


def set_runner(fn: Runner | None) -> None:
    """fn(usb_ids) -> {usb_id: exit code}, raising Cancelled when declined.
    None restores the real runner."""
    global _runner
    _runner = fn


def set_enumerator(fn: Callable[[], list[dict]] | None) -> None:
    """fn() -> raw HID rows (see _real_enumerate). None restores the real one."""
    global _enumerator
    _enumerator = fn


def set_presence(fn: Callable[[str], bool] | None) -> None:
    """fn(instance_id) -> present now. None restores the real check."""
    global _presence
    _presence = fn


# Listing ------------------------------------------------------------------


def _is_virtual(row: dict) -> bool:
    if (int(row.get("vid") or 0), int(row.get("pid") or 0)) == _VJOY:
        return True
    text = f"{row.get('bus_id', '')} {row.get('bus_desc', '')}".upper()
    return any(mark in text for mark in _VIGEM_MARKS)


def _lookup(names: dict[str, str], keys: Iterable[str]) -> str:
    for key in keys:
        hit = names.get(key.upper())
        if hit:
            return hit
    return ""


def list_devices(
    hidden_ids: Iterable[str],
    profile_device_names: Iterable[str] = (),
    known: Iterable[dict] = (),
    gremlin_names: dict[str, str] | None = None,
) -> list[ResetDevice]:
    """Plugged-in physical USB game controllers, one per USB device, plus the
    known ones that aren't plugged in (plugged=False)."""
    hidden = {h.upper() for h in hidden_ids if h}
    profile = {n.casefold() for n in profile_device_names if n}
    aliases = {k.upper(): v for k, v in (gremlin_names or {}).items() if v}
    rows = (_enumerator or _real_enumerate)()
    by_usb: dict[str, ResetDevice] = {}
    for row in rows:
        usb = str(row.get("usb_id") or "")
        if not usb.upper().startswith("USB\\") or _is_virtual(row):
            continue
        key = usb.upper()
        dev = by_usb.get(key)
        if dev is None:
            dev = by_usb[key] = ResetDevice(
                usb_id=usb,
                name=str(row.get("name") or ""),
                windows_name=str(row.get("windows_name") or ""),
                vid=int(row.get("vid") or 0),
                pid=int(row.get("pid") or 0),
            )
        hid = str(row.get("hid_id") or "")
        if hid and hid not in dev.hid_ids:
            dev.hid_ids.append(hid)
        if not dev.name and row.get("name"):
            dev.name = str(row["name"])
    out = list(by_usb.values())
    for dev in out:
        dev.hidden = any(h.upper() in hidden for h in dev.hid_ids)
        dev.name = _lookup(aliases, [dev.usb_id, *dev.hid_ids]) or dev.name
    for item in known:
        usb = str(item.get("usb_id") or "")
        if not usb or usb.upper() in by_usb:
            continue
        by_usb[usb.upper()] = dev = ResetDevice(
            usb_id=usb,
            name=_lookup(aliases, [usb]) or str(item.get("name") or ""),
            vid=int(item.get("vid") or 0),
            pid=int(item.get("pid") or 0),
            plugged=False,
        )
        out.append(dev)
    for dev in out:
        dev.in_profile = bool(
            profile and {dev.name.casefold(), dev.windows_name.casefold()} & profile
        )
    out.sort(key=lambda d: (not d.plugged, (d.name or d.usb_id).casefold()))
    return out


def _real_enumerate() -> list[dict]:
    if os.name != "nt":
        return []
    from gremlin import hidhide_driver as hh

    rows: list[dict] = []
    for group in hh.list_hid_devices(True):
        for hid in group.get("instanceIds") or []:
            usb = hh._parent_instance(hid)
            if not usb:
                continue
            # A composite device's HID parent is an interface (MI_xx); look two
            # levels up for the ViGEm bus.
            up1 = hh._parent_instance(usb)
            up2 = hh._parent_instance(up1) if up1 else ""
            vid, pid = hh._vid_pid(usb)
            rows.append(
                {
                    "hid_id": hid,
                    "usb_id": usb,
                    "bus_id": f"{up1} {up2}",
                    "bus_desc": f"{hh._device_description(up1)} "
                    f"{hh._device_description(up2)}",
                    "name": group.get("name") or "",
                    "windows_name": hh._device_description(usb),
                    "vid": vid or 0,
                    "pid": pid or 0,
                }
            )
    return rows


# Reset --------------------------------------------------------------------


def _outcome(code: int | None) -> str:
    if code is None:
        return "failed"
    if code == 0:
        return "ok"
    if code == ERROR_SUCCESS_REBOOT_REQUIRED:
        return "restart"
    return "failed"


def _present(instance: str) -> bool:
    if _presence is not None:
        return _presence(instance)
    if os.name != "nt":
        return False
    import ctypes
    from ctypes import wintypes

    cfg = ctypes.WinDLL("cfgmgr32", use_last_error=True)
    devinst = wintypes.DWORD(0)
    # CM_LOCATE_DEVNODE_NORMAL: only devices that are present now.
    return cfg.CM_Locate_DevNodeW(ctypes.byref(devinst), instance, 0) == 0


def reset(
    devices: Iterable[str | ResetDevice], runner: Runner | None = None
) -> list[ResetResult]:
    """Restarts every device in one elevated process (one prompt), then waits
    up to BACK_TIMEOUT per device for it to be present again. Blocks: run it
    off the UI thread. A device that isn't present before the reset is
    "not_found" and isn't sent to pnputil."""
    items = list(devices)
    ids = [d.usb_id if isinstance(d, ResetDevice) else str(d) for d in items]
    if not ids:
        return []
    absent = {usb.upper() for usb in ids if not _present(usb)}
    send = [usb for usb in ids if usb.upper() not in absent]
    codes: dict[str, int] = {}
    if send:
        run = runner or _runner or _real_runner
        try:
            codes = run(send) or {}
        except Cancelled:
            return [
                ResetResult(i, "not_found" if i.upper() in absent else "declined")
                for i in ids
            ]
        except TimeoutError:
            return [
                ResetResult(i, "not_found")
                if i.upper() in absent
                else ResetResult(i, "failed", detail="timed out")
                for i in ids
            ]
    upper = {k.upper(): v for k, v in codes.items()}
    started = clock.monotonic()
    results: list[ResetResult] = []
    for item, usb in zip(items, ids, strict=True):
        if usb.upper() in absent:
            results.append(ResetResult(usb, "not_found"))
            continue
        code = upper.get(usb.upper())
        result = ResetResult(usb, _outcome(code), code)
        if result.outcome == "ok":
            watch = [usb]
            if isinstance(item, ResetDevice):
                watch += item.hid_ids
            result.back_after = _wait_back(watch, started)
        results.append(result)
    return results


def _wait_back(ids: list[str], started: float) -> float | None:
    deadline = started + BACK_TIMEOUT
    while True:
        if all(_present(i) for i in ids):
            return max(0.0, clock.monotonic() - started)
        if clock.monotonic() >= deadline:
            return None
        clock.sleep(_POLL)


def _under_test() -> bool:
    return bool(os.environ.get("PYTEST_CURRENT_TEST")) or "pytest" in sys.modules


_RESTART = "pnputil /restart-device"


def _batch_text(ids: list[str], result_path: str, command: str = _RESTART) -> str:
    """One pnputil line per device, then `<index>|<exit code>` to the result
    file (indexes, so ids with & need no escaping in echo)."""
    lines = ["@echo off"]
    for n, usb in enumerate(ids):
        safe = usb.replace("%", "%%").replace('"', "")
        lines.append(f'{command} "{safe}" >nul 2>&1')
        lines.append(f'>>"{result_path}" echo {n}^|%errorlevel%')
    return "\r\n".join(lines) + "\r\n"


def _parse_results(text: str, ids: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for line in text.splitlines():
        index, _, code = line.strip().partition("|")
        try:
            out[ids[int(index)]] = int(code)
        except (ValueError, IndexError):
            continue
    return out


def _run_batch(
    ids: list[str],
    launch: Callable[[str, str], None],
    command: str = _RESTART,
) -> dict[str, int]:
    """Writes reset.cmd, has launch(script, folder) run it to the end, then
    reads the exit codes back."""
    folder = tempfile.mkdtemp(prefix="gremlin_reset_")
    script = ntpath.join(folder, "reset.cmd")
    result_path = ntpath.join(folder, "result.txt")
    with open(script, "w", encoding="mbcs", newline="") as fh:
        fh.write(_batch_text(ids, result_path, command))
    # mkdtemp's folder only lets SYSTEM, Administrators and the file's owner
    # in. A result file made by the elevated cmd is owned by Administrators,
    # which this (unelevated) process can't read, so make it here first and
    # let the batch append to it.
    open(result_path, "w", encoding="mbcs").close()
    try:
        launch(script, folder)
        try:
            with open(result_path, encoding="mbcs", errors="replace") as fh:
                return _parse_results(fh.read(), ids)
        except OSError:
            return {}
    finally:
        # Best effort: a file the elevated cmd left (owned by Administrators)
        # may not go; that's fine.
        shutil.rmtree(folder, ignore_errors=True)


def _real_runner(ids: list[str]) -> dict[str, int]:
    if _under_test():
        raise RealRunnerBlocked("device_reset real runner called from a test")
    if os.name != "nt":
        raise OSError("device reset needs Windows")
    return _run_batch(ids, _elevated_launch)


def _elevated_launch(script: str, folder: str) -> None:
    """Runs script in one elevated cmd.exe and waits for it."""
    if _under_test():
        raise RealRunnerBlocked("device_reset elevated launch called from a test")
    import ctypes
    from ctypes import wintypes

    class SHELLEXECUTEINFOW(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("fMask", ctypes.c_ulong),
            ("hwnd", wintypes.HWND),
            ("lpVerb", wintypes.LPCWSTR),
            ("lpFile", wintypes.LPCWSTR),
            ("lpParameters", wintypes.LPCWSTR),
            ("lpDirectory", wintypes.LPCWSTR),
            ("nShow", ctypes.c_int),
            ("hInstApp", wintypes.HINSTANCE),
            ("lpIDList", ctypes.c_void_p),
            ("lpClass", wintypes.LPCWSTR),
            ("hkeyClass", wintypes.HKEY),
            ("dwHotKey", wintypes.DWORD),
            ("hIconOrMonitor", wintypes.HANDLE),
            ("hProcess", wintypes.HANDLE),
        ]

    SEE_MASK_NOCLOSEPROCESS = 0x00000040
    SEE_MASK_NO_CONSOLE = 0x00008000
    SW_HIDE = 0
    WAIT_OBJECT_0 = 0
    shell = ctypes.WinDLL("shell32", use_last_error=True)
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    shell.ShellExecuteExW.argtypes = [ctypes.POINTER(SHELLEXECUTEINFOW)]
    shell.ShellExecuteExW.restype = wintypes.BOOL
    k32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    k32.WaitForSingleObject.restype = wintypes.DWORD
    k32.CloseHandle.argtypes = [wintypes.HANDLE]

    info = SHELLEXECUTEINFOW()
    info.cbSize = ctypes.sizeof(SHELLEXECUTEINFOW)
    info.fMask = SEE_MASK_NOCLOSEPROCESS | SEE_MASK_NO_CONSOLE
    info.lpVerb = "runas"
    info.lpFile = "cmd.exe"
    info.lpParameters = f'/d /c ""{script}""'
    info.lpDirectory = folder
    info.nShow = SW_HIDE
    if not shell.ShellExecuteExW(ctypes.byref(info)):
        err = ctypes.get_last_error()
        if err == ERROR_CANCELLED:
            raise Cancelled()
        raise OSError(err, "ShellExecuteExW failed")
    try:
        if info.hProcess:
            waited = k32.WaitForSingleObject(info.hProcess, int(RESET_TIMEOUT * 1000))
            if waited != WAIT_OBJECT_0:
                raise TimeoutError("pnputil did not finish in time")
    finally:
        if info.hProcess:
            k32.CloseHandle(info.hProcess)


# Running games ------------------------------------------------------------


def running_listed_games(games: Iterable[str | dict]) -> list[str]:
    """Exe names of the listed programs (paths or {"path": ...}) running now."""
    from gremlin import process_paths

    paths = [g.get("path", "") if isinstance(g, dict) else g for g in games]
    listed = {process_paths._key(str(p)) for p in paths if p}
    if not listed:
        return []
    names = [ntpath.basename(p) for p in listed]
    out: list[str] = []
    for image, _start in process_paths.running_programs(names):
        name = ntpath.basename(image)
        if process_paths._key(image) in listed and name not in out:
            out.append(name)
    return out
