# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import os
import pathlib
import sys
import tempfile
import threading
import time
from collections.abc import Iterator
from typing import IO

# Tests never put a window on the user's screen: the Gremlin app some tests
# build (pytest-qt's qapp) and every window it opens stay off-screen.
os.environ["QT_QPA_PLATFORM"] = "offscreen"
# Nor reach the network (the programs tests start inherit it): the update
# check is off. HTTPS_PROXY doesn't stop Qt's network calls.
os.environ["GREMLIN_OFFLINE"] = "1"
os.environ.setdefault(
    "QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
)

# Mock before any imports happen
from unittest.mock import Mock

import pytest

import gremlin.util

gremlin.util.userprofile_path = Mock(return_value=tempfile.mkdtemp())

import gremlin.ui.backend  # noqa: E402
import gremlin.windows_event_hook  # noqa: E402
import joystick_gremlin  # noqa: E402

# By its folder: as a plain module (pytest -p conftest), "test" is Python's own.
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import fake_input  # noqa: E402  # pyright: ignore[reportMissingImports]

# Tests never hook the keyboard and mouse of the PC they run on, and never
# send keys or mouse input to it (test/fake_input.py).
gremlin.windows_event_hook.enabled = False
fake_input.install()

# Hang tracing for the programs tests start (test/hang_trace/sitecustomize.py):
# one that stalls or runs longer than this prints every thread's stack and
# ends, and one whose main code has ended doesn't wait for its threads. Below the
# shortest timeout a test gives such a program (60 s), so the stacks arrive
# before the test gives up. Tests in this process: stall detection below.
os.environ.setdefault("GREMLIN_TEST_HANG_LIMIT", "50")
_HANG_TRACE = str(pathlib.Path(__file__).parent / "hang_trace")
if _HANG_TRACE not in os.environ.get("PYTHONPATH", "").split(os.pathsep):
    os.environ["PYTHONPATH"] = os.pathsep.join(
        p for p in (_HANG_TRACE, os.environ.get("PYTHONPATH", "")) if p
    )
sys.path.insert(0, _HANG_TRACE)
import stall_watch  # noqa: E402  # pyright: ignore[reportMissingImports]


def pytest_collection_modifyitems(
    session: pytest.Session, config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Stops a run that mixes test/unit with the folders needing the Gremlin app.

    The unit tests run on a plain QCoreApplication; test/integration and
    test/action_interaction need JoystickGremlinApp. One process has one
    application, so mixed runs fail in hundreds of confusing ways.
    """
    root = pathlib.Path(__file__).parent
    folders = set()
    for item in items:
        try:
            folders.add(pathlib.Path(str(item.path)).relative_to(root).parts[0])
        except ValueError:
            continue
    if "unit" in folders and folders & {"integration", "action_interaction"}:
        raise pytest.UsageError(
            "Run each test folder in its own pytest run: "
            "pytest test/unit, pytest test/integration, pytest test/action_interaction."
        )


@pytest.fixture(autouse=True)
def _no_message_boxes(monkeypatch: pytest.MonkeyPatch) -> list[tuple]:
    """No test shows a real Windows message box (they appear on screen even
    off-screen, and wait for a click): they are recorded instead."""
    shown: list[tuple] = []
    monkeypatch.setattr(
        joystick_gremlin, "_message_box", lambda *a: shown.append(a) or 1
    )
    return shown


@pytest.fixture(scope="session")
def qapp_cls() -> type[joystick_gremlin.JoystickGremlinApp]:
    return joystick_gremlin.JoystickGremlinApp


@pytest.fixture(scope="session")
def test_root_dir() -> pathlib.Path:
    return pathlib.Path(__file__).parent


# | Stall detection (test/hang_trace/stall_watch.py): a test whose main thread
# | stops making progress fails within seconds with the stack of every thread,
# | and the run goes on. A test may run 120 s at most.


class _Stalls:
    watch: stall_watch.StallWatch | None = None
    out: IO[str] = sys.stderr
    reports: dict[str, str] = {}
    finished = 0
    exit_status = 0


@pytest.hookimpl(trylast=True)  # after pytest's faulthandler kept the real stderr
def pytest_configure(config: pytest.Config) -> None:
    try:
        from _pytest.faulthandler import fault_handler_stderr_fd_key

        _Stalls.out = os.fdopen(
            os.dup(config.stash[fault_handler_stderr_fd_key]), "w", encoding="utf-8"
        )
    except Exception:
        _Stalls.out = sys.__stderr__ or sys.stderr
    if stall_watch.PROGRAM_WATCH is not None:  # pytest started by a test
        stall_watch.PROGRAM_WATCH.stop()
    watch = stall_watch.StallWatch(_test_stalled, _Stalls.out, limit=120.0)
    watch.start()
    _Stalls.watch = watch


def _test_stalled(report: str) -> None:
    """From the watchdog thread: fail the stalled test, or end the run when
    it can't be stopped (stuck inside C code)."""
    watch = _Stalls.watch
    nodeid = report.split("\n", 2)[1].removeprefix("=== STALLED: ")
    _Stalls.reports[nodeid] = report
    finished = _Stalls.finished
    stall_watch.write(_Stalls.out, report + "Failing this test.\n")
    stall_watch.raise_in_main_thread(stall_watch.TestStalled)
    deadline = time.monotonic() + stall_watch.STOP_GRACE
    while time.monotonic() < deadline:
        moved_on = watch is not None and watch.label not in (None, nodeid)
        if _Stalls.finished != finished or moved_on:
            return
        time.sleep(0.1)
    stall_watch.write(
        _Stalls.out,
        f"The test didn't stop within {stall_watch.STOP_GRACE:.0f} s (stuck inside "
        "C code): ending the run.\n" + stall_watch.describe_threads(),
    )
    stall_watch.end_process(3)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item: pytest.Item, nextitem: pytest.Item | None):  # noqa: ANN201
    if _Stalls.watch is not None:
        _Stalls.watch.watch(item.nodeid)
    try:
        yield
    finally:
        if _Stalls.watch is not None:
            _Stalls.watch.watch(None)
        if item.nodeid in _Stalls.reports:
            stall_watch.raise_in_main_thread(None)  # not raised yet: take it back
        _Stalls.finished += 1


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    _Stalls.exit_status = int(exitstatus)


@pytest.hookimpl(trylast=True)
def pytest_unconfigure(config: pytest.Config) -> None:
    """The run is over: stop the program's threads, so none keeps the
    process open. Any that still won't stop is named, with its stack, and
    the process ends with pytest's own result instead of waiting."""
    import gremlin.threads

    gremlin.threads.shutdown(timeout=2.0)
    main = threading.main_thread()
    left = [
        t for t in threading.enumerate()
        if t is not main and not t.daemon and t.is_alive()
    ]
    if left:
        stall_watch.write(
            _Stalls.out,
            "\n=== These threads would keep the test run from ending: "
            f"{', '.join(t.name for t in left)}\n"
            + stall_watch.describe_threads()
            + "=== Ending the run.\n",
        )
        stall_watch.end_process(_Stalls.exit_status)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):  # noqa: ANN201
    outcome = yield
    report = _Stalls.reports.get(item.nodeid)
    if report is not None and call.excinfo is not None:
        outcome.get_result().sections.append(("stall report", report))


@pytest.fixture(autouse=True)
def _no_threads_left_running() -> Iterator[None]:
    """A test may not leave threads running (a program thread left behind
    keeps the process from ending, see test/hang_trace/sitecustomize.py)."""
    before = set(threading.enumerate())
    yield
    new = [t for t in threading.enumerate() if t not in before and not t.daemon]
    watch = _Stalls.watch
    label = watch.label if watch is not None else None
    if watch is not None:
        watch.watch(None)  # a short wait on purpose, not a stall
    deadline = time.monotonic() + 2.0
    for thread in new:
        thread.join(max(0.0, deadline - time.monotonic()))
    if watch is not None and label is not None:
        watch.watch(label)
    left = [thread.name for thread in new if thread.is_alive()]
    if left:
        pytest.fail(f"The test left threads running: {', '.join(left)}")
