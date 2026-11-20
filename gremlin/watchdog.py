# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Log When Not Responding: where the program is stuck when it freezes.

A timer on the main loop ticks every BEAT_MS. A watchdog thread checks it
once a second: when it hasn't ticked for THRESHOLD_S, it writes "Not
responding" and the stack of every thread to system.log, once per freeze,
and "Responding again" when the ticks come back. The option is off by
default and takes effect at once.

While the input thread runs, the same thread also reads its heartbeat
(input_thread.silent_for): past the same limit it writes "Input thread not
responding" with the stacks and recent events, and "Input thread responding
again", once per stall.

It can only write while the stuck main thread lets other threads run: a
call that holds Python's lock (GIL) while it waits is logged once it
returns.
"""

from __future__ import annotations

import ctypes
import faulthandler
import logging
import os
import sys
import tempfile
import threading

from PySide6 import QtCore

from gremlin import clock, input_thread, threads

OPTION = ("global", "general", "log-when-not-responding")
THRESHOLD_S = 5.0
BEAT_MS = 250

_log = logging.getLogger("system")


def thread_stacks() -> str:
    """Every thread's stack, with the thread names."""
    names = ", ".join(
        f"{t.name} = 0x{t.ident:08x}" for t in threading.enumerate() if t.ident
    )
    with tempfile.TemporaryFile("w+", encoding="utf-8") as out:
        faulthandler.dump_traceback(file=out, all_threads=True)
        out.seek(0)
        return f"Threads: {names}\n{out.read()}"


# Wait Chain Traversal (advapi32): what Windows says a thread is waiting on.
WCT_MAX_NODE_COUNT = 16
WCTP_GETINFO_ALL_FLAGS = 0xF
_OBJECT_TYPES = (
    "CriticalSection", "SendMessage", "Mutex", "Alpc", "Com", "ThreadWait",
    "ProcessWait", "Thread", "ComActivation", "Unknown", "SocketIo", "SmbIo",
)
_OBJECT_STATUSES = (
    "NoAccess", "Running", "Blocked", "PidOnly", "PidOnlyRpcss", "Owned",
    "NotOwned", "Abandoned", "Unknown", "Error",
)

_main_thread_id: int | None = None


class _LockObject(ctypes.Structure):
    _fields_ = [
        ("ObjectName", ctypes.c_wchar * 128),
        ("Timeout", ctypes.c_longlong),
        ("Alertable", ctypes.c_int),
    ]


class _ThreadObject(ctypes.Structure):
    _fields_ = [
        ("ProcessId", ctypes.c_uint32),
        ("ThreadId", ctypes.c_uint32),
        ("WaitTime", ctypes.c_uint32),
        ("ContextSwitches", ctypes.c_uint32),
    ]


class _NodeUnion(ctypes.Union):
    _fields_ = [("LockObject", _LockObject), ("ThreadObject", _ThreadObject)]


class WaitChainNodeInfo(ctypes.Structure):
    """WAITCHAIN_NODE_INFO."""

    _fields_ = [
        ("ObjectType", ctypes.c_uint32),
        ("ObjectStatus", ctypes.c_uint32),
        ("u", _NodeUnion),
    ]


def _enum_name(names: tuple[str, ...], value: int) -> str:
    return names[value - 1] if 1 <= value <= len(names) else f"#{value}"


def format_wait_chain(
    nodes: list[WaitChainNodeInfo],
    is_cycle: bool,
    thread_names: dict[int, str] | None = None,
) -> str:
    """The "Main thread wait chain (Windows):" block, one line per node."""
    names = thread_names or {}
    lines = ["Main thread wait chain (Windows):"]
    for n in nodes:
        kind = _enum_name(_OBJECT_TYPES, n.ObjectType)
        status = _enum_name(_OBJECT_STATUSES, n.ObjectStatus)
        text = f"  {kind}, {status}"
        if kind == "Thread":
            pid, tid = n.u.ThreadObject.ProcessId, n.u.ThreadObject.ThreadId
            if pid == os.getpid():
                name = names.get(tid)
                text += f", this process, thread {tid}" + (f" ({name})" if name else "")
            else:
                text += f", process {pid}, thread {tid}"
        else:
            obj = n.u.LockObject.ObjectName
            if obj:
                text += f", {obj}"
        lines.append(text)
    if is_cycle:
        lines.append("  deadlock cycle")
    return "\n".join(lines)


def _query_wait_chain(thread_id: int) -> tuple[list[WaitChainNodeInfo], bool]:
    """Asks Windows for the wait chain of a thread (raises on failure)."""
    from ctypes import wintypes

    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    advapi.OpenThreadWaitChainSession.restype = wintypes.HANDLE
    advapi.OpenThreadWaitChainSession.argtypes = [wintypes.DWORD, ctypes.c_void_p]
    advapi.GetThreadWaitChain.restype = wintypes.BOOL
    advapi.GetThreadWaitChain.argtypes = [
        wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p,
        ctypes.POINTER(wintypes.BOOL),
    ]
    advapi.CloseThreadWaitChainSession.argtypes = [wintypes.HANDLE]
    session = advapi.OpenThreadWaitChainSession(0, None)
    if not session:
        raise OSError(f"OpenThreadWaitChainSession failed ({ctypes.get_last_error()})")
    try:
        nodes = (WaitChainNodeInfo * WCT_MAX_NODE_COUNT)()
        count = wintypes.DWORD(WCT_MAX_NODE_COUNT)
        cycle = wintypes.BOOL(0)
        ok = advapi.GetThreadWaitChain(
            session, None, WCTP_GETINFO_ALL_FLAGS, thread_id,
            ctypes.byref(count), nodes, ctypes.byref(cycle),
        )
        if not ok:
            raise OSError(f"GetThreadWaitChain failed ({ctypes.get_last_error()})")
        return list(nodes[: min(count.value, WCT_MAX_NODE_COUNT)]), bool(cycle.value)
    finally:
        advapi.CloseThreadWaitChainSession(session)


def wait_chain_block() -> str:
    """What Windows reports the main thread is waiting on, as plain text.
    Windows only (empty elsewhere); never raises. Runs on the watchdog thread."""
    if sys.platform != "win32":
        return ""
    try:
        tid = _main_thread_id or threading.main_thread().native_id
        if not tid:
            raise RuntimeError("main thread id unknown")
        nodes, cycle = _query_wait_chain(tid)
        names = {t.native_id: t.name for t in threading.enumerate() if t.native_id}
        return format_wait_chain(nodes, cycle, names)
    except Exception as e:
        return f"Main thread wait chain: not available ({e})"


def _recent_block() -> str:
    """The recent events and the last known window state, as plain text
    (no Qt calls: this runs on the watchdog thread)."""
    parts: list[str] = []
    try:
        from gremlin import trace

        lines = trace.recent_lines()
        parts.append("Recent events:\n" + ("\n".join(lines) if lines else "(none)"))
    except Exception:
        pass
    try:
        from gremlin.ui import window_trace

        known = window_trace.last_known()
        parts.append(
            "Last known window state:\n"
            + "\n".join(f"  {k}: {v}" for k, v in dict(known).items())
        )
    except Exception:
        pass
    return "\n".join(parts)


def _note(text: str, area: str = "Main window") -> None:
    """The stall to the window events, and to trace.log while Timing is on."""
    try:
        from gremlin.ui import window_trace

        window_trace.note(area, text)
    except Exception:
        pass


def _event(text: str) -> None:
    try:
        from gremlin import trace

        if trace.timing_on():
            trace.event(text)
    except Exception:
        pass


class Watchdog(QtCore.QObject):
    """See the module notes. Made and started on the main thread."""

    def __init__(self, threshold_s: float = THRESHOLD_S) -> None:
        super().__init__()
        self._threshold = threshold_s
        self._last_beat = clock.monotonic()
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(BEAT_MS)
        self._timer.timeout.connect(self._beat)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.running:
            return
        global _main_thread_id
        _main_thread_id = threading.main_thread().native_id
        self._last_beat = clock.monotonic()
        self._timer.start()
        self._stop.clear()
        self._thread = threads.start(
            "not-responding watchdog", self._watch, stop=self._stop.set
        )

    def stop(self) -> None:
        self._timer.stop()
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _beat(self) -> None:
        self._last_beat = clock.monotonic()

    def _check_input_thread(self, stalled_since: float | None) -> float | None:
        """One check of the input thread's heartbeat; returns the new
        stalled-since beat time (None when it is responding). Never raises."""
        try:
            if not input_thread.is_running():
                return None  # not running (or stopped meanwhile): nothing to watch
            silent = input_thread.silent_for()
            if stalled_since is None and silent >= self._threshold:
                text = f"Input thread not responding for {silent:.0f} s."
                _note(f"stall began: no heartbeat for {silent:.0f} s", "Input thread")
                _event(text)
                _log.warning(
                    f"{text} Where every thread is:\n"
                    + thread_stacks()
                    + "\n"
                    + _recent_block()
                )
                return clock.monotonic() - silent
            if stalled_since is not None and silent < self._threshold:
                beat = input_thread.last_beat()
                took = (beat if beat is not None else clock.monotonic()) - stalled_since
                text = f"Input thread responding again after {took:.0f} s"
                _note(f"stall ended after {took:.0f} s", "Input thread")
                _event(text)
                _log.warning(text)
                return None
        except Exception:
            _log.debug("Input thread check failed", exc_info=True)
        return stalled_since

    def _watch(self) -> None:
        frozen_since: float | None = None
        input_stalled_since: float | None = None
        while not self._stop.wait(min(1.0, self._threshold / 2)):
            input_stalled_since = self._check_input_thread(input_stalled_since)
            last = self._last_beat
            silent = clock.monotonic() - last
            if frozen_since is None and silent >= self._threshold:
                frozen_since = last
                text = f"Not responding for {silent:.0f} s."
                _note(f"stall began: no main-loop tick for {silent:.0f} s")
                _event(text)
                _log.warning(
                    f"{text} Where every thread is:\n"
                    + thread_stacks()
                    + ("\n" + wait_chain_block()).rstrip("\n")
                    + "\n"
                    + _recent_block()
                )
            elif frozen_since is not None and silent < self._threshold:
                text = f"Responding again after {last - frozen_since:.0f} s"
                _note(f"stall ended after {last - frozen_since:.0f} s")
                _event(text)
                _log.warning(text)
                frozen_since = None


_watchdog: Watchdog | None = None


def apply() -> None:
    """Starts or stops the watchdog to match the option (main thread)."""
    global _watchdog
    from gremlin.config import Configuration

    wanted = bool(Configuration().value(*OPTION))
    if wanted:
        if _watchdog is None:
            _watchdog = Watchdog()
        _watchdog.start()
    elif _watchdog is not None:
        _watchdog.stop()
