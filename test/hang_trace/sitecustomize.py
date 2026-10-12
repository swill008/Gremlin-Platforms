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


def _guard_vjoy() -> None:
    """The programs the tests start get the stand-in vJoy too (test/vjoy_guard.py)."""
    import importlib.util

    test_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(test_folder, "vjoy_guard.py")
    try:
        guard = sys.modules.get("vjoy_guard")
        if guard is None:
            spec = importlib.util.spec_from_file_location("vjoy_guard", path)
            assert spec is not None and spec.loader is not None
            guard = importlib.util.module_from_spec(spec)
            sys.modules["vjoy_guard"] = guard
            spec.loader.exec_module(guard)
        guard.install()
    except Exception as e:
        sys.stderr.write(f"vjoy guard not installed: {e!r}\n")


_NO_REAL_DILL = (
    "tests must use test/fake_hardware: the real dill.dll was about to load "
    "({path})"
)


def _refuse_real_dill(path: str) -> None:
    raise RuntimeError(_NO_REAL_DILL.format(path=path))


class _DillGuard:
    """Import hook: once dill is imported, its loader refuses the real
    dill.dll (it loads on first use, never at import). A program the tests
    start must install test/fake_hardware before it reads devices."""

    def find_spec(self, name, path=None, target=None):  # noqa: ANN001, ANN202
        if name != "dill":
            return None
        import importlib.machinery

        spec = importlib.machinery.PathFinder.find_spec(name, path)
        if spec is None or spec.loader is None:
            return spec
        exec_module = spec.loader.exec_module

        def guarded(module):  # noqa: ANN001, ANN202
            exec_module(module)
            setattr(module, "_load_dll", _refuse_real_dill)

        spec.loader.exec_module = guarded  # type: ignore[method-assign]
        return spec


def _guard_dill() -> None:
    """The programs the tests start never load the real dill.dll."""
    dill = sys.modules.get("dill")
    if dill is not None:
        setattr(dill, "_load_dll", _refuse_real_dill)
    else:
        sys.meta_path.insert(0, _DillGuard())


if _LIMIT:
    _guard_vjoy()
    _guard_dill()
    import stall_watch

    threading.Thread(
        target=_end_when_the_main_code_ends, name="hang-trace", daemon=True
    ).start()
    # Start-up, until the event loop first runs, gets the longer allowance
    # (to-do 128: the Main.qml load stands still for seconds on a busy PC).
    _watch = stall_watch.StallWatch(
        _stalled,
        sys.stderr,
        limit=float(_LIMIT),
        start_up=stall_watch.STARTUP_BLOCKED_AFTER,
    )
    _watch.watch("this program")
    _watch.start()
    stall_watch.PROGRAM_WATCH = _watch
