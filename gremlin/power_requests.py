# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""Refresh Programs and Ignore this program (Screen Saver Mode S13, S14).

Windows shows which programs ask it to keep the display or the PC awake
(`powercfg /requests`) and which are ignored (`powercfg /requestsoverride`)
only to administrators, so every call here is ONE elevated cmd.exe that runs
the powercfg commands into temp files; Gremlin itself never runs elevated.
The ignored programs are Windows' own setting.

The elevated run goes through a runner(commands) -> outputs seam; tests pass
a fake and the real one refuses to run under pytest."""

from __future__ import annotations

import ctypes
import ntpath
import os
import re
import shutil
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field

ERROR_CANCELLED = 1223
RUN_TIMEOUT_S = 60.0

REFUSED_TEXT = "Administrator rights were refused."
TIMEOUT_TEXT = "Windows did not answer in time."
NOT_CHANGED_TEXT = "Windows did not change the setting."

# powercfg /requests section -> kind shown; the other sections (PERFBOOST,
# ACTIVELOCKSCREEN) don't keep the display or the PC awake and are skipped.
_KINDS = {
    "DISPLAY": "Display",
    "SYSTEM": "System",
    "AWAYMODE": "Awaymode",
    "EXECUTION": "Execution",
}
_ALL_SECTIONS = (*_KINDS, "PERFBOOST", "ACTIVELOCKSCREEN")
_OVERRIDE_TYPES = ("DISPLAY", "SYSTEM", "AWAYMODE", "EXECUTION", "PERFBOOST")
_ENTRY = re.compile(r"^\[(PROCESS|DRIVER|SERVICE)\]\s+(.+)$")
_NAME_OK = re.compile(r"^[A-Za-z0-9 _.\-+#@$~,'\[\]{}]+\.exe$", re.IGNORECASE)

Runner = Callable[[list[str]], list[str]]


class Refused(Exception):
    """The administrator rights prompt was refused."""


class RealRunnerBlocked(RuntimeError):
    """The real runner was called from a test."""


@dataclass
class ProgramRequest:
    name: str
    path: str
    kinds: list[str] = field(default_factory=list)
    ignored: bool = False


@dataclass
class RequestsResult:
    ok: bool
    error: str
    programs: list[ProgramRequest] = field(default_factory=list)


_LIST_REQUESTS = "powercfg /requests"
_LIST_OVERRIDES = "powercfg /requestsoverride"


def list_requests(runner: Runner | None = None) -> RequestsResult:
    """The programs asking Windows to keep the display or PC awake, plus the
    ignored ones (listed even when not asking now)."""
    run = runner or _real_runner
    try:
        requests_text, overrides_text = run([_LIST_REQUESTS, _LIST_OVERRIDES])
    except Refused:
        return RequestsResult(False, REFUSED_TEXT)
    except TimeoutError:
        return RequestsResult(False, TIMEOUT_TEXT)
    except (OSError, ValueError) as error:
        return RequestsResult(False, f"Windows could not list the programs ({error}).")
    return RequestsResult(
        True, "", merge(parse_requests(requests_text), parse_overrides(overrides_text))
    )


def set_ignored(
    name: str, ignored: bool, runner: Runner | None = None
) -> tuple[bool, str]:
    """Adds (ignored) or removes Windows' override for the program's display
    and PC requests. (ok, error text)."""
    if not valid_name(name):
        return False, f'"{name}" is not a program file name.'
    run = runner or _real_runner
    command = f'powercfg /requestsoverride PROCESS "{name}"'
    if ignored:
        command += " DISPLAY SYSTEM AWAYMODE"
    try:
        _set_text, overrides_text = run([command, _LIST_OVERRIDES])
    except Refused:
        return False, REFUSED_TEXT
    except TimeoutError:
        return False, TIMEOUT_TEXT
    except (OSError, ValueError) as error:
        return False, f"Windows could not change the setting ({error})."
    now_ignored = name.lower() in {n.lower() for n in parse_overrides(overrides_text)}
    if now_ignored != ignored:
        return False, NOT_CHANGED_TEXT
    return True, ""


def valid_name(name: str) -> bool:
    """A bare program file name (no folder, quotes or command characters)."""
    return (
        isinstance(name, str)
        and 0 < len(name) <= 255
        and name == name.strip()
        and bool(_NAME_OK.match(name))
    )


# Parsing ------------------------------------------------------------------


def parse_requests(text: str) -> list[ProgramRequest]:
    """`powercfg /requests` output -> one entry per program, with each kind
    it asks for. Lines under an entry (its reason) are skipped."""
    programs: dict[str, ProgramRequest] = {}
    section = ""
    for raw in text.splitlines():
        line = raw.strip()
        if line.endswith(":") and line[:-1].upper() in _ALL_SECTIONS:
            section = line[:-1].upper()
            continue
        match = _ENTRY.match(line)
        if not match or section not in _KINDS:
            continue
        tag, rest = match.group(1), match.group(2).strip()
        if tag == "PROCESS":
            name, path = ntpath.basename(rest), rest
        else:
            name, path = rest, ""
        key = name.lower()
        entry = programs.setdefault(key, ProgramRequest(name, path))
        kind = _KINDS[section]
        if kind not in entry.kinds:
            entry.kinds.append(kind)
    return list(programs.values())


def parse_overrides(text: str) -> list[str]:
    """`powercfg /requestsoverride` output -> names under [PROCESS]."""
    names: list[str] = []
    section = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].upper()
            continue
        if section != "PROCESS":
            continue
        words = line.split()
        while words and words[-1].upper() in _OVERRIDE_TYPES:
            words.pop()
        name = " ".join(words).strip('"')
        if name and name.lower() not in {n.lower() for n in names}:
            names.append(name)
    return names


def merge(programs: list[ProgramRequest], ignored: list[str]) -> list[ProgramRequest]:
    """Marks ignored programs and adds the ignored ones not asking now."""
    out = list(programs)
    by_name = {p.name.lower(): p for p in out}
    for name in ignored:
        found = by_name.get(name.lower())
        if found is not None:
            found.ignored = True
        else:
            out.append(ProgramRequest(name, "", [], True))
    return out


# The elevated run ----------------------------------------------------------


def _under_test() -> bool:
    return bool(os.environ.get("PYTEST_CURRENT_TEST")) or "pytest" in sys.modules


def command_line(commands: list[str], outputs: list[str]) -> str:
    """cmd.exe parameters running each command into its output file."""
    parts = [f'{c} >> "{o}" 2>&1' for c, o in zip(commands, outputs, strict=True)]
    return '/d /c "' + " & ".join(parts) + '"'


def _real_runner(commands: list[str]) -> list[str]:
    if _under_test():
        raise RealRunnerBlocked("power_requests real runner called from a test")
    if os.name != "nt":
        raise OSError("needs Windows")
    folder = tempfile.mkdtemp(prefix="gremlin_power_")
    outputs = [ntpath.join(folder, f"out{i}.txt") for i in range(len(commands))]
    # The folder only lets this user and Administrators in; a file the
    # elevated cmd made would be Administrators' and unreadable here, so make
    # them now and let cmd append.
    for path in outputs:
        open(path, "w", encoding="mbcs").close()
    try:
        _elevated_cmd(command_line(commands, outputs), folder)
        texts = []
        for path in outputs:
            with open(path, encoding="oem", errors="replace") as fh:
                texts.append(fh.read())
        return texts
    finally:
        shutil.rmtree(folder, ignore_errors=True)


if os.name == "nt":
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


def _elevated_cmd(parameters: str, folder: str) -> None:
    """One elevated, hidden cmd.exe; waits (bounded) for it to end."""
    if _under_test():
        raise RealRunnerBlocked("power_requests elevated run called from a test")
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
    info.lpParameters = parameters
    info.lpDirectory = folder
    info.nShow = SW_HIDE
    if not shell.ShellExecuteExW(ctypes.byref(info)):
        err = ctypes.get_last_error()
        if err == ERROR_CANCELLED:
            raise Refused()
        raise OSError(err, "ShellExecuteExW failed")
    try:
        if info.hProcess:
            waited = k32.WaitForSingleObject(info.hProcess, int(RUN_TIMEOUT_S * 1000))
            if waited != WAIT_OBJECT_0:
                raise TimeoutError("powercfg did not finish in time")
    finally:
        if info.hProcess:
            k32.CloseHandle(info.hProcess)
