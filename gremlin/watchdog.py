# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Log When Not Responding: where the program is stuck when it freezes.

A timer on the main loop ticks every BEAT_MS. A watchdog thread checks it
once a second: when it hasn't ticked for THRESHOLD_S, it writes "Not
responding" and the stack of every thread to system.log, once per freeze,
and "Responding again" when the ticks come back. The option is off by
default and takes effect at once.

It can only write while the stuck main thread lets other threads run: a
call that holds Python's lock (GIL) while it waits is logged once it
returns.
"""

from __future__ import annotations

import faulthandler
import logging
import tempfile
import threading

from PySide6 import QtCore

from gremlin import clock, threads

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

    def _watch(self) -> None:
        frozen_since: float | None = None
        while not self._stop.wait(min(1.0, self._threshold / 2)):
            last = self._last_beat
            silent = clock.monotonic() - last
            if frozen_since is None and silent >= self._threshold:
                frozen_since = last
                _log.warning(
                    f"Not responding for {silent:.0f} s. Where every thread is:\n"
                    + thread_stacks()
                )
            elif frozen_since is not None and silent < self._threshold:
                _log.warning(
                    f"Responding again after {last - frozen_since:.0f} s"
                )
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
