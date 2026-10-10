# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Child processes that take everything they start with them when they end.

A process a test (or test/run_tests.py) starts can start its own: the venv's
python.exe is a launcher that starts the real interpreter, and a program may
start helpers. Killing the direct child leaves those running, and once it
has ended taskkill /T can no longer find them (ORPHAN-PROCS: a final01_app.py
child was still running hours after a full run). On Windows each child goes
into a Job Object, started suspended so nothing it starts escapes; ending the
job ends every process in it, and closing it (also when this process dies)
does too. Elsewhere the child leads a new session and its process group is
killed.
"""

from __future__ import annotations

import os
import signal
import subprocess
from typing import Any

_WINDOWS = os.name == "nt"

if _WINDOWS:
    import ctypes
    from ctypes import wintypes

    _CREATE_SUSPENDED = 0x00000004
    _KILL_ON_JOB_CLOSE = 0x00002000
    _EXTENDED_LIMIT_INFORMATION = 9

    class _IoCounters(ctypes.Structure):
        _fields_ = [(n, ctypes.c_ulonglong) for n in (
            "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
            "ReadTransferCount", "WriteTransferCount", "OtherTransferCount",
        )]

    class _BasicLimits(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class _ExtendedLimits(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", _BasicLimits),
            ("IoInfo", _IoCounters),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    _kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    _kernel32.SetInformationJobObject.argtypes = [
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    _kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    _kernel32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    _kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    _ntdll = ctypes.WinDLL("ntdll")
    _ntdll.NtResumeProcess.argtypes = [wintypes.HANDLE]


class Tree:
    """A started process and everything it starts."""

    def __init__(self, process: subprocess.Popen, job: Any = None) -> None:  # noqa: ANN401
        self.process = process
        self._job = job

    def kill(self) -> None:
        """Ends the process and every process it started (again: no-op)."""
        if _WINDOWS:
            if self._job:
                _kernel32.TerminateJobObject(self._job, 1)
            elif self.process.poll() is None:
                self.process.kill()
            return
        try:
            os.killpg(self.process.pid, signal.SIGKILL)  # pyright: ignore[reportAttributeAccessIssue]
        except (ProcessLookupError, PermissionError):
            pass

    def close(self) -> None:
        """Kills the tree and lets the job go."""
        self.kill()
        if _WINDOWS and self._job:
            _kernel32.CloseHandle(self._job)
            self._job = None


def _new_job() -> Any:  # noqa: ANN401
    job = _kernel32.CreateJobObjectW(None, None)
    if not job:
        raise ctypes.WinError(ctypes.get_last_error())
    limits = _ExtendedLimits()
    limits.BasicLimitInformation.LimitFlags = _KILL_ON_JOB_CLOSE
    if not _kernel32.SetInformationJobObject(
        job, _EXTENDED_LIMIT_INFORMATION, ctypes.byref(limits),
        ctypes.sizeof(limits),
    ):
        error = ctypes.get_last_error()
        _kernel32.CloseHandle(job)
        raise ctypes.WinError(error)
    return job


def popen(command: list[str], **kwargs: Any) -> Tree:  # noqa: ANN401
    """subprocess.Popen, its whole tree killed by Tree.kill/close."""
    if not _WINDOWS:
        return Tree(subprocess.Popen(command, start_new_session=True, **kwargs))
    job = _new_job()
    flags = kwargs.pop("creationflags", 0) | _CREATE_SUSPENDED
    try:
        process = subprocess.Popen(command, creationflags=flags, **kwargs)
    except BaseException:
        _kernel32.CloseHandle(job)
        raise
    handle = int(process._handle)  # type: ignore[attr-defined]  # noqa: SLF001
    if not _kernel32.AssignProcessToJobObject(job, handle):
        error = ctypes.get_last_error()
        process.kill()
        _kernel32.CloseHandle(job)
        raise ctypes.WinError(error)
    _ntdll.NtResumeProcess(handle)
    return Tree(process, job)


def run(
    command: list[str], *, timeout: float, input: str | bytes | None = None,  # noqa: A002
    **kwargs: Any,  # noqa: ANN401
) -> subprocess.CompletedProcess:
    """subprocess.run(capture_output=True) whose child and everything it
    started are always ended: at its end, on timeout, on any error."""
    tree = popen(command, stdin=subprocess.PIPE if input is not None else None,
                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
    try:
        try:
            stdout, stderr = tree.process.communicate(input, timeout=timeout)
        except subprocess.TimeoutExpired as timed_out:
            tree.kill()
            stdout, stderr = tree.process.communicate()
            timed_out.output, timed_out.stderr = stdout, stderr
            raise
    finally:
        tree.close()
    return subprocess.CompletedProcess(
        command, tree.process.returncode, stdout, stderr)
