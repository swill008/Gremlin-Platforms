# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Every thread the program starts: named, tracked, and stopped on exit.

Threads used to be started anonymously ("Thread-12") and nothing could stop
them all: the program ended through os._exit, and a script or test that
ended any other way waited for them forever. Start every thread through
start(), timer() or thread_timer() instead. Each one gets a readable name
and is listed while it runs, with the request that stops it, so shutdown()
can stop them all and say which didn't stop.

A stop request only asks: it sets a flag, wakes a wait or cancels a timer,
and returns at once. shutdown() does the waiting, within one time limit.
"""

from __future__ import annotations

import logging
import sys
import threading
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, cast

if TYPE_CHECKING:
    from PySide6 import QtCore

PREFIX = "Gremlin-Platforms: "

_R = TypeVar("_R")


class _Thread(Protocol):
    """What shutdown() needs of a listed thread (a threading.Thread or a
    _QtThread)."""

    name: str

    def is_alive(self) -> bool: ...

    def join(self, timeout: float | None = None) -> None: ...


_LOCK = threading.Lock()
# Live threads and the request that stops each (None: it ends by itself).
_live: dict[_Thread, Callable[[], None] | None] = {}


def _forget(thread: _Thread) -> None:
    with _LOCK:
        _live.pop(thread, None)


def start(
    name: str,
    target: Callable[..., Any],
    *args: object,
    stop: Callable[[], None] | None = None,
) -> threading.Thread:
    """Starts target(*args) on a new thread called name.

    stop asks the thread to end (see the module notes); leave it out for a
    thread that ends by itself soon.
    """

    def run() -> None:
        try:
            target(*args)
        finally:
            _forget(thread)

    thread = threading.Thread(target=run, name=PREFIX + name)
    with _LOCK:
        _live[thread] = stop
    try:
        thread.start()
    except BaseException:
        _forget(thread)
        raise
    return thread


class _Timer(threading.Timer):
    """A threading.Timer that leaves the list when it is done or cancelled."""

    def run(self) -> None:
        try:
            super().run()
        finally:
            _forget(self)


def timer(
    name: str, seconds: float, function: Callable[..., Any], *args: object
) -> threading.Timer:
    """Calls function(*args) on a new thread after seconds (cancel() stops it)."""
    t = _Timer(seconds, function, args)
    t.name = PREFIX + name
    with _LOCK:
        _live[t] = t.cancel
    try:
        t.start()
    except BaseException:
        _forget(t)
        raise
    return t


# Qt timers still waiting (listed by running(), cancelled by shutdown());
# they are timers of a thread with an event loop, not threads.
_qt_timers: set[QtTimer] = set()


def has_event_loop() -> bool:
    """True when the calling thread has a Qt event loop to run timers (the
    main thread once the Qt application exists, the input thread); False on
    a plain thread (a macro, a loop, a timer thread)."""
    if "PySide6.QtCore" not in sys.modules:
        return False
    from PySide6 import QtCore

    return QtCore.QThread.currentThread().eventDispatcher() is not None


class _Poster(Protocol):
    """A QObject that runs a job posted from any thread on its own thread."""

    posted: Any  # a Signal(object): posted.emit(job)

    def moveToThread(self, thread: QtCore.QThread, /) -> bool: ...  # noqa: N802


def _make_poster() -> _Poster:
    from PySide6 import QtCore

    class _QtPoster(QtCore.QObject):
        """Runs what is posted to it on the thread it lives on."""

        posted = QtCore.Signal(object)

        def __init__(self) -> None:
            super().__init__()
            self.posted.connect(self._run, QtCore.Qt.ConnectionType.QueuedConnection)

        @QtCore.Slot(object)
        def _run(self, job: Callable[[], None]) -> None:
            try:
                job()
            except Exception:
                logging.getLogger("system").exception(
                    "A call posted to a thread failed"
                )

    return _QtPoster()


# One poster per thread that has made a Qt timer (made on that thread, so
# it lives there), and one on the main thread for main_call().
_posters = threading.local()
_main_poster: _Poster | None = None


def _poster_here() -> _Poster:
    poster = getattr(_posters, "value", None)
    if poster is None:
        poster = _make_poster()
        _posters.value = poster
    return poster


class QtTimer:
    """A one-shot Qt timer of the thread that made it (that thread runs the
    function), with the same cancel() / is_alive() as threading.Timer.

    Listed while it waits, like a thread, so shutdown() cancels it and a
    check can name it. cancel() may be called from any thread: the timer is
    stopped on its own thread (Qt allows nothing else) and never runs after.
    """

    def __init__(
        self, name: str, seconds: float, function: Callable[..., Any], args: tuple
    ) -> None:
        from PySide6 import QtCore

        self.name = PREFIX + name
        self._function = function
        self._args = args
        self._ident = threading.get_ident()
        self._poster = _poster_here()
        self._alive = True
        # A child of this thread's poster: Qt owns it, so dropping it from
        # Python (on any thread) never deletes it; deleteLater() does, on
        # this thread (also when the thread ends).
        self._timer: QtCore.QTimer | None = QtCore.QTimer(
            cast("QtCore.QObject", self._poster)
        )
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fire)
        with _LOCK:
            _qt_timers.add(self)
        self._timer.start(max(0, round(seconds * 1000)))

    def _take(self) -> bool:
        """True once: for the one that fires or cancels it."""
        with _LOCK:
            if not self._alive:
                return False
            self._alive = False
            _qt_timers.discard(self)
            return True

    def _fire(self) -> None:
        if self._take():
            # Not deleted inside its own signal: deleteLater waits for it.
            timer, self._timer = self._timer, None
            if timer is not None:
                timer.deleteLater()
            self._function(*self._args)

    def _stop_here(self) -> None:
        timer, self._timer = self._timer, None
        if timer is not None:
            timer.stop()
            timer.deleteLater()

    def cancel(self) -> None:
        if not self._take():
            return
        if threading.get_ident() == self._ident:
            self._stop_here()
        else:
            # Queued to its own thread; this object holds the timer until
            # then, so it is not deleted from the wrong thread either.
            self._poster.posted.emit(self._stop_here)

    def is_alive(self) -> bool:
        return self._alive


# The handle main_timer() returns on the main thread.
MainTimer = QtTimer


def thread_timer(
    name: str, seconds: float, function: Callable[..., Any], *args: object
) -> QtTimer | threading.Timer:
    """Calls function(*args) after seconds on the calling thread, when that
    thread has a Qt event loop (the input thread for a Run's timers, the
    main thread); from any other thread on a named timer thread (timer()).

    cancel() works from any thread.
    """
    if has_event_loop():
        return QtTimer(name, seconds, function, args)
    return timer(name, seconds, function, *args)


def main_timer(
    name: str, seconds: float, function: Callable[..., Any], *args: object
) -> QtTimer | threading.Timer:
    """Calls function(*args) on the main thread after seconds.

    For timers of the window (UI only; a Run's timers use thread_timer
    through run_scope.timer). Made from another thread (no event loop there
    to run it), it falls back to timer().
    """
    if threading.current_thread() is not threading.main_thread():
        return timer(name, seconds, function, *args)
    return QtTimer(name, seconds, function, args)


def main_call(fn: Callable[..., Any], *args: object) -> None:
    """Runs fn(*args) on the main thread and returns at once: inline when
    already there (or with no Qt application, so no loop to queue to),
    otherwise queued to the main thread's event loop. An exception there is
    logged."""
    poster = _main_poster_or_none()
    if poster is None:
        fn(*args)
        return
    poster.posted.emit(lambda: fn(*args))


def _main_poster_or_none() -> _Poster | None:
    """The main thread's poster; None on the main thread itself or with no
    Qt application (then the caller runs fn inline)."""
    global _main_poster
    if threading.current_thread() is threading.main_thread():
        return None
    if "PySide6.QtCore" not in sys.modules:
        return None
    from PySide6 import QtCore

    app = QtCore.QCoreApplication.instance()
    if app is None:
        return None
    with _LOCK:
        poster = _main_poster
        if poster is None:
            poster = _make_poster()
            poster.moveToThread(app.thread())
            _main_poster = poster
    return poster


def main_call_wait(fn: Callable[..., _R], *args: object, timeout: float) -> _R:
    """Runs fn(*args) on the main thread and returns its result, waiting at
    most timeout seconds (inline when already there or with no Qt
    application); fn's own exception is raised here. Past the limit
    TimeoutError is raised and logged, with .started saying which case it
    is: a job that hadn't started is dropped and never runs; one already
    running may still finish (its result is dropped). A queued call, never
    a blocking Qt connection: a main thread that is waiting on the caller
    only delays this up to timeout."""
    poster = _main_poster_or_none()
    if poster is None:
        return fn(*args)
    done = threading.Event()
    lock = threading.Lock()
    outcome: dict[str, Any] = {}
    flags = {"started": False, "gave_up": False}

    def job() -> None:
        with lock:
            if flags["gave_up"]:
                return  # the caller has gone: never run late
            flags["started"] = True
        try:
            outcome["result"] = fn(*args)
        except BaseException as error:
            outcome["error"] = error
        finally:
            done.set()

    poster.posted.emit(job)
    if not done.wait(timeout):
        with lock:
            started = flags["started"]
            flags["gave_up"] = True
        if not (started and done.is_set()):
            name = getattr(fn, "__qualname__", repr(fn))
            if started:
                text = (
                    f"Main thread call {name} took over {timeout:.1f} s; "
                    "it may still finish."
                )
            else:
                text = (
                    f"Main thread call {name} didn't start within "
                    f"{timeout:.1f} s; it was dropped."
                )
            logging.getLogger("system").warning(text)
            error = TimeoutError(text)
            error.started = started  # type: ignore[attr-defined]
            raise error
    if "error" in outcome:
        raise outcome["error"]
    return outcome["result"]


class _QtThread:
    """A QThread as shutdown() sees it: listed by name, stopped by quitting
    its event loop, waited for within the limit."""

    def __init__(self, name: str, qthread: QtCore.QThread) -> None:
        self.name = name
        self.qthread = qthread

    def is_alive(self) -> bool:
        return self.qthread.isRunning()

    def join(self, timeout: float | None = None) -> None:
        from PySide6 import QtCore

        # Waiting for itself would never end.
        if QtCore.QThread.currentThread() is self.qthread:
            return
        if timeout is None:
            self.qthread.wait()
        else:
            self.qthread.wait(max(0, round(timeout * 1000)))


def start_qt(name: str, qthread: QtCore.QThread) -> None:
    """Starts qthread (a Qt thread with its own event loop) called name.

    Listed by running() like a thread; shutdown() asks it to stop with
    quit() and waits for it within its limit.
    """
    from PySide6 import QtCore

    qthread.setObjectName(PREFIX + name)
    entry = _QtThread(PREFIX + name, qthread)
    # finished is emitted on qthread itself; the list has its own lock.
    qthread.finished.connect(
        lambda: _forget(entry), QtCore.Qt.ConnectionType.DirectConnection
    )
    with _LOCK:
        _live[entry] = qthread.quit
    try:
        qthread.start()
    except BaseException:
        _forget(entry)
        raise


# | Wrong-thread guards (debug helpers). Qt objects belong to one thread:
# | the window's to the main thread, the input path's to the input thread
# | (gremlin/input_thread.py). A function that must run on one of them
# | calls assert_main(what) / assert_input(what) first. With
# | guards_raise on (tests) a wrong thread raises WrongThread; otherwise
# | it is logged once per what to the system log.

guards_raise = False
_guard_logged: set[str] = set()


class WrongThread(AssertionError):
    """A function that belongs to one thread was called on another."""


def _wrong_thread(what: str, wanted: str) -> None:
    text = f"{what} must run on the {wanted}, not on {threading.current_thread().name}"
    if guards_raise:
        raise WrongThread(text)
    with _LOCK:
        if what in _guard_logged:
            return
        _guard_logged.add(what)
    logging.getLogger("system").warning(text)


def assert_main(what: str) -> None:
    """Checks that the caller is on the main (window) thread."""
    if threading.current_thread() is not threading.main_thread():
        _wrong_thread(what, "main thread")


def assert_input(what: str) -> None:
    """Checks that the caller is on the input thread (or that the input
    thread runs inline on the caller, see input_thread.set_inline)."""
    from gremlin import input_thread

    if not (input_thread.is_inline() or input_thread.is_input_thread()):
        _wrong_thread(what, "input thread")


def running() -> list[str]:
    """The names of the program's threads (and Qt timers) that are still
    running."""
    with _LOCK:
        names = [t.name for t in _live if t.is_alive()]
        names += [t.name for t in _qt_timers if t.is_alive()]
    return sorted(names)


def shutdown(timeout: float = 2.0) -> list[str]:
    """Asks every thread to stop and waits up to timeout seconds in all.

    Returns the names of those still running (they are logged too).
    """
    with _LOCK:
        threads = list(_live.items())
        qt_timers = list(_qt_timers)
    # Each is stopped on its own thread (queued there before that thread is
    # asked to stop below, so it is stopped first).
    for qt_timer in qt_timers:
        try:
            qt_timer.cancel()
        except Exception:
            logging.getLogger("system").exception(f"Could not cancel {qt_timer.name}")
    for thread, stop in threads:
        if stop is None:
            continue
        try:
            stop()
        except Exception:
            logging.getLogger("system").exception(
                f"Could not ask {thread.name} to stop"
            )
    deadline = time.monotonic() + timeout
    for thread, _ in threads:
        if thread is not threading.current_thread():
            thread.join(max(0.0, deadline - time.monotonic()))
    left = sorted(t.name for t, _ in threads if t.is_alive())
    if left:
        logging.getLogger("system").warning(
            f"Still running after {timeout:.0f} s: {', '.join(left)}"
        )
    return left
