# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Hang tracing for the programs the tests start.

Python loads this at start-up because test/conftest.py puts this folder on
PYTHONPATH for the programs the tests start (only when
GREMLIN_TEST_HANG_LIMIT is set, so it does nothing anywhere else).

Why such a program could sit until its test's timeout without a word:

* JoystickGremlinApp replaces sys.excepthook with one that only logs to
  system.log and shows an error dialog (invisible off-screen), so an
  uncaught error printed nothing.
* The program's own threads (process monitor, event handler, Windows event
  hook) are not daemon threads. The program ends through os._exit, but a
  script that ends any other way, an uncaught error included, waits for
  them forever.

So here: when the main code ends while other threads still run, the error
(if any) is printed and the program ends at once; a program whose main
thread stops making progress prints every thread's stack and ends
(stall_watch.py), as does one that runs longer than the limit.
"""

from __future__ import annotations

import os
import sys
import threading
import traceback

_LIMIT = os.environ.get("GREMLIN_TEST_HANG_LIMIT", "")


def _end_when_the_main_code_ends() -> None:
    main = threading.main_thread()
    main.join()  # returns once the main code has ended
    error = getattr(sys, "last_exc", None)
    others = [
        t.name for t in threading.enumerate()
        if t is not threading.current_thread() and t is not main and not t.daemon
    ]
    if not others:
        return  # nothing to wait for: Python ends as usual
    if error is not None and sys.excepthook is not sys.__excepthook__:
        # Python's own hook would have printed it; the program's doesn't.
        sys.stderr.write("".join(traceback.format_exception(error)))
    sys.stderr.write(
        "hang trace: the main code ended; not waiting for the threads "
        f"still running ({', '.join(others)})\n"
    )
    sys.stdout.flush()
    sys.stderr.flush()
    # A program that ended with sys.exit(n) ends with 0 here: that code
    # isn't visible to Python at this point. Tests' programs end through
    # os._exit or with an error.
    os._exit(1 if error is not None else 0)


def _stalled(report: str) -> None:
    import stall_watch

    stall_watch.write(sys.stderr, f"program: {' '.join(sys.argv)}{report}")
    stall_watch.end_process(3)


if _LIMIT:
    import stall_watch

    threading.Thread(
        target=_end_when_the_main_code_ends, name="hang-trace", daemon=True
    ).start()
    _watch = stall_watch.StallWatch(_stalled, sys.stderr, limit=float(_LIMIT))
    _watch.watch("this program")
    _watch.start()
    stall_watch.PROGRAM_WATCH = _watch
