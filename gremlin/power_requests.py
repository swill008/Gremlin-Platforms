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
import logging
import ntpath
import os
import re
import shutil
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field

from gremlin import trace

ERROR_CANCELLED = 1223
RUN_TIMEOUT_S = 60.0
TRACE_OUTPUT_LIMIT = 4096  # characters of each raw output put in the trace

REFUSED_TEXT = "Administrator rights were refused."
TIMEOUT_TEXT = "Windows did not answer in time."
NOT_CHANGED_TEXT = "Windows did not change the setting."

PROCESS, DRIVER, SERVICE = "PROCESS", "DRIVER", "SERVICE"
CALLER_KINDS = (PROCESS, DRIVER, SERVICE)

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
_MAX_CALLER_NAME = 260
_IGNORE_TYPES = "DISPLAY SYSTEM AWAYMODE"

Runner = Callable[[list[str]], list[str]]

_log = logging.getLogger("system")


class Refused(Exception):
    """The administrator rights prompt was refused."""


class RealRunnerBlocked(RuntimeError):
    """The real runner was called from a test."""


class Outputs(list):
    """What the real runner gives back: each command's output, plus the
    elevated cmd.exe's line and exit code for the trace."""

    def __init__(
        self, texts: list[str], line: str = "", exit_code: int | None = None
    ) -> None:
        super().__init__(texts)
        self.line = line
        self.exit_code = exit_code


@dataclass
class ProgramRequest:
    name: str
    path: str
    kinds: list[str] = field(default_factory=list)
    ignored: bool = False
    kind: str = PROCESS  # who asks: PROCESS, DRIVER or SERVICE
    detail: str = ""  # Windows' line under the request, e.g. "Electron"


@dataclass
class RequestsResult:
    ok: bool
    error: str
    programs: list[ProgramRequest] = field(default_factory=list)


_LIST_REQUESTS = "powercfg /requests"
_LIST_OVERRIDES = "powercfg /requestsoverride"


def list_requests(runner: Runner | None = None) -> RequestsResult:
    """The programs, drivers and services asking Windows to keep the display
    or PC awake, plus the ignored ones (listed even when not asking now)."""
    commands = [_LIST_REQUESTS, _LIST_OVERRIDES]
    outputs, error = _run("Refresh Programs", commands, runner)
    if outputs is None:
        return RequestsResult(False, error)
    requests_text, overrides_text = (list(outputs) + ["", ""])[:2]
    programs = merge(parse_requests(requests_text), parse_overrides(overrides_text))
    _trace(f"Refresh Programs: {len(programs)} rows")
    for row in programs:
        _trace("  " + _row_text(row))
    return RequestsResult(True, "", programs)


def set_ignored(
    name: str, ignored: bool, kind: str = PROCESS, runner: Runner | None = None
) -> tuple[bool, str]:
    """Adds (ignored) or removes Windows' override for the caller's display
    and PC requests. (ok, error text)."""
    what = f'Ignore {kind} "{name}" {"on" if ignored else "off"}'
    if kind not in CALLER_KINDS:
        return _refuse(what, f'"{kind}" is not a kind Windows can ignore.')
    if kind == PROCESS and not valid_name(name):
        return _refuse(what, f'"{name}" is not a program file name.')
    if kind != PROCESS and not valid_caller_name(name):
        return _refuse(what, f'"{name}" is not a name Windows can ignore.')
    command = f'powercfg /requestsoverride {kind} "{name}"'
    if ignored:
        command += " " + _IGNORE_TYPES
    outputs, error = _run(what, [command, _LIST_OVERRIDES], runner)
    if outputs is None:
        return False, error
    overrides_text = (list(outputs) + ["", ""])[1]
    now = {(k, n.lower()) for k, n in parse_overrides(overrides_text)}
    now_ignored = (kind, name.lower()) in now
    if now_ignored != ignored:
        state = "lacks" if ignored else "still has"
        _trace(f"{what}: check failed, Windows' list {state} it")
        _log.warning("Screen Saver Mode: %s: %s", what, NOT_CHANGED_TEXT)
        return False, NOT_CHANGED_TEXT
    _trace(f"{what}: check ok")
    return True, ""


def valid_name(name: str) -> bool:
    """A bare program file name (no folder, quotes or command characters)."""
    return (
        isinstance(name, str)
        and 0 < len(name) <= 255
        and name == name.strip()
        and bool(_NAME_OK.match(name))
    )


def valid_caller_name(name: str) -> bool:
    """A driver or service name as /requests shows it: may hold spaces,
    brackets, backslashes and &, which are safe inside the double quotes;
    no quote, line break or other control character, and no % (cmd.exe
    would expand it)."""
    return (
        isinstance(name, str)
        and 0 < len(name) <= _MAX_CALLER_NAME
        and name == name.strip()
        and '"' not in name
        and "%" not in name
        and not any(ord(c) < 0x20 or ord(c) == 0x7F for c in name)
    )


# Running and tracing --------------------------------------------------------


def _trace(text: str) -> None:
    """One Screen Saver Mode trace line; a no-op until trace has the tick."""
    try:
        write = getattr(trace, "screen_saver", None)
        if write is not None:
            write(text)
    except Exception:
        pass


def _refuse(what: str, error: str) -> tuple[bool, str]:
    _trace(f"{what}: refused, {error}")
    _log.warning("Screen Saver Mode: %s: %s", what, error)
    return False, error


def _trimmed(text: str) -> str:
    if len(text) <= TRACE_OUTPUT_LIMIT:
        return text
    return (
        text[:TRACE_OUTPUT_LIMIT]
        + f"\n... ({len(text) - TRACE_OUTPUT_LIMIT} more characters)"
    )


def _row_text(row: ProgramRequest) -> str:
    text = f"[{row.kind}] {row.name}: {', '.join(row.kinds) or 'not asking'}"
    if row.ignored:
        text += ", ignored"
    if row.detail:
        text += f' ("{row.detail}")'
    return text


def _run(
    what: str, commands: list[str], runner: Runner | None
) -> tuple[list[str] | None, str]:
    """One elevated run, traced; (outputs, "") or (None, error text)."""
    run = runner or _real_runner
    for command in commands:
        _trace(f"{what}: command: {command}")
    try:
        outputs = run(commands)
    except Refused:
        return None, _failed(what, "refused", REFUSED_TEXT)
    except TimeoutError:
        return None, _failed(what, "timeout", TIMEOUT_TEXT)
    except (OSError, ValueError) as error:
        return None, _failed(
            what, "error", f"Windows could not run powercfg ({error})."
        )
    line = getattr(outputs, "line", "")
    if line:
        _trace(f"{what}: cmd.exe {line}")
    exit_code = getattr(outputs, "exit_code", None)
    _trace(f"{what}: exit code {'unknown' if exit_code is None else exit_code}")
    if exit_code not in (None, 0):
        _log.warning("Screen Saver Mode: %s: cmd.exe exit code %s", what, exit_code)
    for command, text in zip(commands, outputs, strict=False):
        _trace(f"{what}: output of {command}:\n{_trimmed(text)}")
    return list(outputs), ""


def _failed(what: str, state: str, error: str) -> str:
    _trace(f"{what}: {state}, {error}")
    _log.warning("Screen Saver Mode: %s: %s", what, error)
    return error


# Parsing ------------------------------------------------------------------


def parse_requests(text: str) -> list[ProgramRequest]:
    """`powercfg /requests` output -> one entry per caller (kind and name),
    with each kind of request it makes and Windows' line under it."""
    programs: dict[tuple[str, str], ProgramRequest] = {}
    section = ""
    current: ProgramRequest | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            current = None
            continue
        if line.endswith(":") and line[:-1].upper() in _ALL_SECTIONS:
            section = line[:-1].upper()
            current = None
            continue
        match = _ENTRY.match(line)
        if not match:
            if current is not None and line != "None.":
                if not current.detail:
                    current.detail = line
                elif line not in current.detail.split("; "):
                    current.detail += "; " + line
            continue
        current = None
        if section not in _KINDS:
            continue
        tag, rest = match.group(1), match.group(2).strip()
        if tag == PROCESS:
            name, path = ntpath.basename(rest), rest
        else:
            name, path = rest, ""
        key = (tag, name.lower())
        entry = programs.setdefault(key, ProgramRequest(name, path, kind=tag))
        kind = _KINDS[section]
        if kind not in entry.kinds:
            entry.kinds.append(kind)
        current = entry
    return list(programs.values())


def parse_overrides(text: str) -> list[tuple[str, str]]:
    """`powercfg /requestsoverride` output -> (kind, name) per ignored
    caller; the types are the trailing upper-case words."""
    found: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    section = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if (
            line.startswith("[")
            and line.endswith("]")
            and line[1:-1].upper() in CALLER_KINDS
        ):
            section = line[1:-1].upper()
            continue
        if section not in CALLER_KINDS:
            continue
        words = line.split()
        while words and words[-1] in _OVERRIDE_TYPES:
            words.pop()
        name = " ".join(words).strip('"')
        if name and (section, name.lower()) not in seen:
            seen.add((section, name.lower()))
            found.append((section, name))
    return found


def merge(
    programs: list[ProgramRequest], ignored: list[tuple[str, str]]
) -> list[ProgramRequest]:
    """Marks ignored callers (matched by kind and name) and adds the ignored
    ones not asking now."""
    out = list(programs)
    by_key = {(p.kind, p.name.lower()): p for p in out}
    for kind, name in ignored:
        found = by_key.get((kind, name.lower()))
        if found is not None:
            found.ignored = True
        else:
            out.append(ProgramRequest(name, "", [], True, kind))
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
        line = command_line(commands, outputs)
        exit_code = _elevated_cmd(line, folder)
        texts = []
        for path in outputs:
            with open(path, encoding="oem", errors="replace") as fh:
                texts.append(fh.read())
        return Outputs(texts, line, exit_code)
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


def _elevated_cmd(parameters: str, folder: str) -> int | None:
    """One elevated, hidden cmd.exe; waits (bounded) for it to end and
    gives its exit code (None when Windows doesn't say)."""
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
    k32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    k32.GetExitCodeProcess.restype = wintypes.BOOL

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
        if not info.hProcess:
            return None
        waited = k32.WaitForSingleObject(info.hProcess, int(RUN_TIMEOUT_S * 1000))
        if waited != WAIT_OBJECT_0:
            raise TimeoutError("powercfg did not finish in time")
        code = wintypes.DWORD()
        if not k32.GetExitCodeProcess(info.hProcess, ctypes.byref(code)):
            return None
        return int(code.value)
    finally:
        if info.hProcess:
            k32.CloseHandle(info.hProcess)
