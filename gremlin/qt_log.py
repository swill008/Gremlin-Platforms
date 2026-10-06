# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Qt's own messages in logs/qt.log.

Qt reports QML warnings, binding notices (the program turns on
qt.qml.binding.removal) and plugin errors itself, outside Python's logging.
Started from a console they showed there; started any other way they went
to the Windows debugger, where nobody saw them, and none reached the logs.

Not qInstallMessageHandler: a Python handler deadlocks while QML compiles
on Qt's loader thread. Instead Qt always writes to the error stream
(QT_FORCE_STDERR_LOGGING), and the error stream goes into a pipe; a thread
copies each line to qt.log with the time, and to the console when there is
one. No Python code runs inside Qt's call. Anything else written to the
error stream (a Python traceback) is kept the same way.

qt.log is moved to qt.log.1 at start-up once it is over MAX_BYTES, and one
session writes at most CAP_BYTES to it (the console still gets the rest).
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from gremlin import threads

MAX_BYTES = 1_000_000
CAP_BYTES = 5_000_000
NAME = "qt.log"

# The error stream as it was (the console, or None), while installed.
_saved_fd: int | None = None
_installed = False


def _rotate(path: Path, limit: int) -> None:
    try:
        if path.stat().st_size > limit:
            os.replace(path, path.with_name(path.name + ".1"))
    except OSError:
        pass


def _copy(read_fd: int, path: Path, console: int | None, cap: int) -> None:
    """Copies the pipe to the file (each line with the time) and the console
    until the pipe closes."""
    first_console = console
    written = 0
    partial = b""
    full = False
    try:
        out = open(path, "ab", buffering=0)
    except OSError:
        out = None
    try:
        while True:
            try:
                chunk = os.read(read_fd, 65536)
            except OSError:
                break
            if not chunk:
                break
            if console is not None:
                try:
                    os.write(console, chunk)
                except OSError:
                    console = None
            if out is None or full:
                continue
            lines = (partial + chunk).split(b"\n")
            partial = lines.pop()
            stamp = time.strftime("%Y-%m-%d %H:%M:%S ").encode()
            text = b"".join(stamp + line.rstrip(b"\r") + b"\n" for line in lines)
            if written + len(text) > cap:
                text = stamp + b"[qt.log is full for this session]\n"
                full = True
            try:
                out.write(text)
                written += len(text)
            except OSError:
                out = None
        if out is not None and partial and not full:
            stamp = time.strftime("%Y-%m-%d %H:%M:%S ").encode()
            out.write(stamp + partial.rstrip(b"\r") + b"\n")
    finally:
        if out is not None:
            out.close()
        os.close(read_fd)
        if first_console is not None:
            os.close(first_console)


def _stop() -> None:
    """Gives the error stream back (the pipe closes, the copying ends)."""
    global _installed, _saved_fd
    if not _installed:
        return
    _installed = False
    try:
        sys.stderr.flush()
    except Exception:
        pass
    if _saved_fd is not None:
        os.dup2(_saved_fd, 2)
        os.close(_saved_fd)
        _saved_fd = None
    else:
        null = os.open(os.devnull, os.O_WRONLY)
        os.dup2(null, 2)
        os.close(null)


def install(folder: Path, cap: int = CAP_BYTES, limit: int = MAX_BYTES) -> bool:
    """Sends Qt's messages (and the error stream) to folder/qt.log as well
    as the console; call before the Qt application is made. False when the
    error stream can't be redirected (nothing changes then)."""
    global _installed, _saved_fd
    if _installed:
        return True
    os.environ["QT_FORCE_STDERR_LOGGING"] = "1"
    path = Path(folder) / NAME
    _rotate(path, limit)
    try:
        console: int | None = os.dup(2)
    except OSError:
        console = None
    try:
        read_fd, write_fd = os.pipe()
        os.dup2(write_fd, 2)
        os.close(write_fd)
    except OSError:
        if console is not None:
            os.close(console)
        return False
    # A program without a console has no sys.stderr: give it the pipe.
    if sys.stderr is None:
        sys.stderr = open(
            2,
            "w",
            buffering=1,
            closefd=False,
            encoding="utf-8",
            errors="backslashreplace",
        )
    _saved_fd = os.dup(console) if console is not None else None
    _installed = True
    threads.start("Qt log", _copy, read_fd, path, console, cap, stop=_stop)
    return True
