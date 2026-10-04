# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""No error goes unrecorded: in a thread, at the top level, or a crash.

An error inside a program thread used to go to the console only, which the
installed program doesn't have, so it was lost. Now it goes to system.log
with the thread's name. Errors at the top level keep their own hook (log
plus error dialog) and are also passed on here, so a console, when there is
one (tests, scripts), shows them too. A hard crash in native code (Qt,
vJoy, ViGEm, the joystick driver) writes every thread's stack to crash.log
in the logs folder.
"""

from __future__ import annotations

import faulthandler
import logging
import sys
import threading
import traceback
import types
from pathlib import Path
from typing import TextIO

CRASH_LOG = "crash.log"

_crash_file: TextIO | None = None


def thread_exception_hook(args: threading.ExceptHookArgs) -> None:
    """Logs an error that ended a thread (threading.excepthook)."""
    if issubclass(args.exc_type, SystemExit):
        return
    name = args.thread.name if args.thread is not None else "a thread"
    text = "".join(
        traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback)
    )
    logging.getLogger("system").error(f"Error in {name}:\n{text}")
    if sys.stderr is not None:
        threading.__excepthook__(args)


def pass_on(
    exception_type: type[BaseException],
    value: BaseException,
    trace: types.TracebackType | None,
) -> None:
    """Shows a top-level error on the console, when there is one."""
    if sys.stderr is not None:
        sys.__excepthook__(exception_type, value, trace)


def enable_crash_log(folder: Path) -> Path | None:
    """Writes every thread's stack to crash.log in folder on a hard crash.

    Appends, so an earlier crash is kept. Does nothing (returns None) when
    crashes are already reported elsewhere (pytest does that).
    """
    global _crash_file
    if faulthandler.is_enabled():
        return None
    path = folder / CRASH_LOG
    _crash_file = path.open("a", encoding="utf-8")
    faulthandler.enable(file=_crash_file, all_threads=True)
    return path


def install(logs_folder: Path) -> None:
    """Records errors in threads and hard crashes (see the module notes)."""
    threading.excepthook = thread_exception_hook
    try:
        enable_crash_log(logs_folder)
    except OSError:
        logging.getLogger("system").exception("Could not open the crash log")
