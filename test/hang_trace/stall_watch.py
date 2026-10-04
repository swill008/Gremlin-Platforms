# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Stall detection for the tests and the programs they start.

Looks for no progress instead of waiting out a long timer. A watchdog
thread checks the main thread several times a second:

* Its stack: the same frames on the same lines means it isn't moving.
* The event loop: once a Qt application exists, a timer on the main thread
  ticks every 250 ms. If it stops ticking, the main thread is blocked (a
  deadlock, a blocking call, a modal box waiting for a click).

The main thread has stalled when its stack hasn't changed for
BLOCKED_AFTER seconds and the event loop isn't ticking, or for IDLE_AFTER
seconds while the event loop idles (waiting for something that never
comes). A wait on a program the test started doesn't count: that program
is watched itself, and the test gives it a timeout. Running longer than
the limit in all counts too.

The watchdog is Python, so it only runs when the main thread lets go of
Python's lock (the GIL). Some calls keep it while they wait (PySide's
QTest.qWait does), so a C-level timer is the deadman: every sign of
progress (a stack change, an event-loop tick) sets it again, and if nothing
does for BACKSTOP_AFTER seconds it prints every thread's stack and ends the
process (see _Deadman).

On a stall the watchdog prints what the main thread is waiting in and the
stack of every thread, then calls on_stall: pytest's process fails just
that test (the run goes on), a program the tests started ends.
"""

from __future__ import annotations

import ctypes
import faulthandler
import os
import sys
import tempfile
import threading
import time
from collections.abc import Callable
from types import FrameType
from typing import IO, Any

# Seconds (GREMLIN_TEST_STALL_AFTER sets it, for the stall tests themselves).
BLOCKED_AFTER = float(os.environ.get("GREMLIN_TEST_STALL_AFTER", "10"))
IDLE_AFTER = 3 * BLOCKED_AFTER
# After failing a test, how long it may take to stop before the run ends.
STOP_GRACE = min(5.0, max(2.0, BLOCKED_AFTER / 2))
# The C-level deadman: later than the watchdog would report anything.
BACKSTOP_AFTER = IDLE_AFTER + STOP_GRACE + min(5.0, BLOCKED_AFTER)
_SAMPLE = min(0.5, BLOCKED_AFTER / 10)
_BEAT_EVERY_MS = 250

_THIS_PROCESS = ctypes.c_void_p(-1)  # Windows' handle for the current process
_NEVER = 0xFFFFFFFF
_WT_EXECUTEINTIMERTHREAD = 0x20

# The watch sitecustomize starts in a program the tests started (if that
# program is pytest, its conftest stops it and watches each test instead).
PROGRAM_WATCH: StallWatch | None = None

# Waits on another (watched) program, which aren't a stall of this one.
_WAITS_ON_A_PROGRAM = (os.sep + "subprocess.py",)


class TestStalled(BaseException):  # noqa: N818 (reads as what happened)
    """Raised in the main thread when its test has stalled.

    A BaseException so a test's `except Exception` can't swallow it."""


def _signature(frame: FrameType | None) -> tuple:
    out = []
    while frame is not None:
        out.append((id(frame.f_code), frame.f_lineno))
        frame = frame.f_back
    return tuple(out)


def _waits_on_a_program(frame: FrameType | None) -> bool:
    while frame is not None:
        if frame.f_code.co_filename.endswith(_WAITS_ON_A_PROGRAM):
            return True
        frame = frame.f_back
    return False


def describe_threads() -> str:
    """The stack of every thread, with the thread names.

    Written by faulthandler (C): while the main thread keeps the GIL (inside
    QTest.qWait, say) the watchdog only gets the odd moment to run, too few
    for Python's traceback module, which reads every source file.
    """
    names = ", ".join(
        f"{t.name} = 0x{t.ident:08x}" for t in threading.enumerate() if t.ident
    )
    with tempfile.TemporaryFile("w+", encoding="utf-8") as out:
        faulthandler.dump_traceback(file=out, all_threads=True)
        out.seek(0)
        stacks = out.read()
    return f"Threads: {names}\n{stacks}"


def _where(frame: FrameType | None) -> str:
    if frame is None:
        return "?"
    code = frame.f_code
    return f'File "{code.co_filename}", line {frame.f_lineno}, in {code.co_name}'


class _Deadman:
    """Ends the process when no progress is seen for a while, even if the
    main thread holds the GIL inside C code.

    faulthandler prints every thread's stack (it needs no GIL), and a
    Windows timer then calls TerminateProcess directly: no Python, no GIL.
    Ending the process any other way (os._exit, faulthandler's own exit)
    can hang while Qt holds the main thread: the process waits in its DLL
    shutdown.

    The exit code it leaves means nothing beyond "not 0": the timer passes
    its own "fired" flag as the code, so only the low byte (1) is set.
    """

    _KILL_AFTER_DUMP = 2.0

    def __init__(self, out: IO[str]) -> None:
        self._out = out
        self._timer: Any = None
        if sys.platform != "win32":
            return
        from ctypes import wintypes

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.CreateTimerQueueTimer.argtypes = [
            ctypes.POINTER(wintypes.HANDLE), wintypes.HANDLE, ctypes.c_void_p,
            ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.ULONG,
        ]
        k32.CreateTimerQueueTimer.restype = wintypes.BOOL
        k32.ChangeTimerQueueTimer.argtypes = [
            wintypes.HANDLE, wintypes.HANDLE, wintypes.ULONG, wintypes.ULONG
        ]
        k32.ChangeTimerQueueTimer.restype = wintypes.BOOL
        k32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
        self._k32 = k32
        timer = wintypes.HANDLE()
        # The timer calls TerminateProcess(this process, 1) itself.
        terminate = ctypes.cast(k32.TerminateProcess, ctypes.c_void_p).value
        if k32.CreateTimerQueueTimer(
            ctypes.byref(timer), None, terminate, _THIS_PROCESS,
            _NEVER, 0, _WT_EXECUTEINTIMERTHREAD,
        ):
            self._timer = timer

    def arm(self, seconds: float) -> None:
        if self._timer is None:  # not Windows: faulthandler's exit
            faulthandler.dump_traceback_later(seconds, exit=True, file=self._out)
            return
        faulthandler.dump_traceback_later(seconds, exit=False, file=self._out)
        self._k32.ChangeTimerQueueTimer(
            None, self._timer, int((seconds + self._KILL_AFTER_DUMP) * 1000), 0
        )

    def cancel(self) -> None:
        faulthandler.cancel_dump_traceback_later()
        if self._timer is not None:
            self._k32.ChangeTimerQueueTimer(None, self._timer, _NEVER, 0)


def end_process(code: int) -> None:
    """Ends this process now (see _Deadman for why not os._exit)."""
    sys.stdout.flush()
    sys.stderr.flush()
    if sys.platform == "win32":
        ctypes.windll.kernel32.TerminateProcess(_THIS_PROCESS, code)
    os._exit(code)


class StallWatch:
    """Watches the main thread; see the module notes.

    on_stall(report) is called from the watchdog thread. out is where the
    C-level deadman writes (a real file: it needs a file descriptor). limit
    is the longest anything watched may run, in seconds.
    """

    def __init__(
        self, on_stall: Callable[[str], None], out: IO[str], limit: float
    ) -> None:
        self._on_stall = on_stall
        self._deadman = _Deadman(out)
        self._limit = limit
        self._lock = threading.Lock()
        self._label: str | None = None
        self._started = 0.0
        self._since = 0.0
        self._sig: tuple = ()
        self._beat = 0.0
        self._armed = 0.0
        self._app: Any = None
        self._keep: list[Any] = []
        self._main = threading.main_thread()
        self._stopped = False

    def start(self) -> None:
        threading.Thread(target=self._run, name="stall-watch", daemon=True).start()

    def stop(self) -> None:
        """Stops watching for good (another watch takes over)."""
        self._stopped = True
        self.watch(None)

    def watch(self, label: str | None) -> None:
        """Start watching (label names what runs), or stop with None."""
        with self._lock:
            self._label = label
            self._sig = ()
            self._started = self._since = time.monotonic()
        if label is None:
            self._deadman.cancel()
        else:
            self._progress(force=True)
            if threading.current_thread() is self._main:
                self.install_heartbeat()

    @property
    def label(self) -> str | None:
        return self._label

    # The deadman: every sign of progress sets it again.
    def _progress(self, force: bool = False) -> None:
        now = time.monotonic()
        if self._label is None or (not force and now - self._armed < 1.0):
            return
        self._armed = now
        try:
            self._deadman.arm(BACKSTOP_AFTER)
        except Exception:
            pass

    def install_heartbeat(self) -> None:
        """The event-loop timer, once a Qt application exists. Best made on
        the main thread (each test does); the watchdog tries too, for the
        programs the tests start."""
        core = sys.modules.get("PySide6.QtCore")
        if core is None:
            return
        app = core.QCoreApplication.instance()
        if app is None or app is self._app:
            return
        self._app = app
        watch = self

        class _Beat(core.QObject):
            @core.Slot()
            def start(self) -> None:
                timer = core.QTimer(self)
                timer.timeout.connect(self.tick)
                timer.start(_BEAT_EVERY_MS)

            @core.Slot()
            def tick(self) -> None:
                watch._beat = time.monotonic()
                watch._progress()

        beat = _Beat()
        if threading.current_thread() is self._main:
            beat.start()
        else:  # made here, handed to the main thread, started there
            beat.moveToThread(app.thread())
            core.QMetaObject.invokeMethod(
                beat, "start", core.Qt.ConnectionType.QueuedConnection
            )
        self._keep.append(beat)  # never deleted from another thread

    def _ticking(self) -> bool:
        return time.monotonic() - self._beat < max(1.0, 8 * _BEAT_EVERY_MS / 1000)

    def _run(self) -> None:
        while self._main.is_alive() and not self._stopped:
            time.sleep(_SAMPLE)
            try:
                self.install_heartbeat()
            except Exception:
                pass
            report = self._check()
            if report is not None:
                self._on_stall(report)

    def _check(self) -> str | None:
        with self._lock:
            label = self._label
            if label is None:
                return None
            frame = sys._current_frames().get(self._main.ident or 0)
            # The heartbeat's own tick isn't the main thread's work.
            while frame is not None and frame.f_code.co_filename == __file__:
                frame = frame.f_back
            now = time.monotonic()
            sig = _signature(frame)
            if now - self._started >= self._limit:
                headline = (
                    f"It is still running after the limit ({self._limit:.0f} s)."
                )
            else:
                if sig != self._sig or _waits_on_a_program(frame):
                    self._sig = sig
                    self._since = now
                    self._progress()
                    return None
                still = now - self._since
                ticking = self._ticking()
                if still < (IDLE_AFTER if ticking else BLOCKED_AFTER):
                    return None
                state = (
                    "its event loop idles, waiting for something that never comes"
                    if ticking
                    else "it is blocked (its event loop isn't running)"
                )
                headline = f"The main thread hasn't moved for {still:.0f} s; {state}."
            self._label = None  # report once
            # Time to finish the report before the deadman ends the process.
            self._deadman.arm(BACKSTOP_AFTER)
        where = _where(frame)
        return (
            f"\n=== STALLED: {label}\n{headline}\n"
            f"The main thread is in:\n  {where}\n\n"
            f"{describe_threads()}=== end of stall report\n"
        )


def raise_in_main_thread(error: type[BaseException] | None) -> None:
    """Raises error in the main thread when it next runs Python code
    (None takes back one not raised yet)."""
    ctypes.pythonapi.PyThreadState_SetAsyncExc(
        ctypes.c_ulong(threading.main_thread().ident or 0),
        ctypes.py_object(error) if error is not None else None,
    )


def write(out: IO[str], text: str) -> None:
    try:
        out.write(text)
        out.flush()
    except Exception:
        pass
