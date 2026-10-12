# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Python's cycle collector runs on the main thread only (gremlin/gc_guard.py),
and a test in which Qt says a timer was stopped from another thread fails
(test/conftest.py, CROSS-THREAD-TIMER).

The crash it guards against (CI run 38205139995): the collector ran on the
History thread and freed a main-thread HardwareProfile held in a cycle; its
timer stayed registered on the main thread and the next tick reached freed
memory."""

from __future__ import annotations

import gc
import os
import pathlib
import subprocess
import sys
import threading
import weakref

import child_env  # pyright: ignore[reportMissingImports]  (test/)
import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest
from PySide6 import QtCore

_ROOT = pathlib.Path(__file__).parents[2]


class _Holder(QtCore.QObject):
    """A main-thread QObject with a running timer, held in a cycle."""

    def __init__(self) -> None:
        super().__init__()
        self.timer = QtCore.QTimer(self)
        self.timer.start(60_000)
        self.me = self


def _allocate_on_worker() -> None:
    """Allocates far past the collector's threshold on a worker thread: an
    automatic collector would run there."""

    def churn() -> None:
        keep = [[i] for i in range(50_000)]
        del keep

    worker = threading.Thread(target=churn, name="gc-guard-churn")
    worker.start()
    worker.join(10.0)
    assert not worker.is_alive()


def test_collector_runs_on_the_main_thread_only(
    qapp: QtCore.QCoreApplication, capfd: pytest.CaptureFixture[str]
) -> None:
    freed_on: list[str] = []
    holder = _Holder()
    alive = weakref.ref(
        holder, lambda _ref: freed_on.append(threading.current_thread().name)
    )
    del holder

    _allocate_on_worker()
    assert alive() is not None, f"freed on {freed_on}"

    # The guard's own timer frees it, on the main thread.
    deadline = QtCore.QDeadlineTimer(5000)
    while alive() is not None and not deadline.hasExpired():
        qapp.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 50)
        QtCore.QThread.msleep(20)
    assert alive() is None
    assert freed_on == [threading.main_thread().name]
    err = capfd.readouterr().err
    assert "from another thread" not in err

    from gremlin import gc_guard

    assert gc_guard.installed()
    assert not gc.isenabled()


def test_install_is_idempotent_and_uninstall_restores(
    qapp: QtCore.QCoreApplication,
) -> None:
    from gremlin import gc_guard

    gc_guard.install(qapp)
    gc_guard.install(qapp)
    timers = [
        t
        for t in qapp.findChildren(QtCore.QTimer)
        if t.objectName() == "gc_guard" and t.isActive()
    ]
    assert len(timers) == 1
    gc.enable()  # someone turned it back on: install turns it off again
    gc_guard.install(qapp)
    assert not gc.isenabled()
    try:
        gc_guard.uninstall()
        assert gc.isenabled()
        assert not gc_guard.installed()
    finally:
        gc_guard.install(qapp)
    assert not gc.isenabled()


_SAMPLE = """
import gc
import threading

from PySide6 import QtCore


class Holder(QtCore.QObject):
    def __init__(self):
        super().__init__()
        self.timer = QtCore.QTimer(self)
        self.timer.start(600_000)
        self.me = self


def _app():
    return QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])


def test_freed_on_the_main_thread_passes():
    _app()
    holder = Holder()
    del holder
    gc.collect()


def test_freed_on_a_worker_fails():
    _app()
    holder = Holder()
    del holder
    worker = threading.Thread(target=gc.collect, name="collector")
    worker.start()
    worker.join(10.0)
"""


@pytest.fixture(scope="module")
def inner_run(tmp_path_factory: pytest.TempPathFactory) -> str:
    folder = tmp_path_factory.mktemp("gc_guard")
    sample = folder / "test_sample.py"
    sample.write_text(_SAMPLE, encoding="utf-8")
    (folder / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    env = dict(
        os.environ,
        PYTHONPATH=child_env.python_path(_ROOT / "test", _ROOT),
        GREMLIN_TEST_HANG_LIMIT="",
        USERPROFILE=str(folder),
    )
    log = folder / "out.txt"
    # To a file, not a pipe (a full pipe would block the run); its own
    # folder, ini and rootdir (as test_rules_fail_on_damage).
    with log.open("w", encoding="utf-8") as out:
        tree = proc_tree.popen(
            [
                sys.executable,
                "-m",
                "pytest",
                "-p",
                "conftest",
                "-v",
                "-rA",
                "-p",
                "no:cacheprovider",
                "-p",
                "no:randomly",
                "-c",
                str(folder / "pytest.ini"),
                "--rootdir",
                str(folder),
                "--confcutdir",
                str(folder),
                str(sample),
            ],
            cwd=_ROOT,
            env=env,
            stdout=out,
            stderr=subprocess.STDOUT,
        )
        try:
            tree.process.wait(timeout=120)
        finally:
            tree.close()
    return log.read_text(encoding="utf-8", errors="replace")


def _lines(out: str, name: str) -> list[str]:
    lines = [line for line in out.splitlines() if f"::{name} " in line]
    assert lines, out[-3000:]
    return lines


def test_check_passes_a_main_thread_free(inner_run: str) -> None:
    lines = _lines(inner_run, "test_freed_on_the_main_thread_passes")
    assert any("PASSED" in line for line in lines), inner_run[-3000:]
    assert not any("ERROR" in line for line in lines), inner_run[-3000:]


def test_check_fails_a_cross_thread_free(inner_run: str) -> None:
    lines = _lines(inner_run, "test_freed_on_a_worker_fails")
    assert any("ERROR" in line or "FAILED" in line for line in lines), inner_run[-3000:]
    assert "CROSS-THREAD-TIMER in" in inner_run, inner_run[-3000:]
    assert "test_freed_on_a_worker_fails" in inner_run
    assert "Timers cannot be stopped from another thread" in inner_run
