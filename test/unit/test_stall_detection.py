# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The stall detection catches a test that stops making progress.

(test/hang_trace/stall_watch.py, used by test/conftest.py and, for the
programs tests start, test/hang_trace/sitecustomize.py.) Each case runs a
small test file through pytest with the real conftest, with stalls caught
after 1 s instead of 10 (0.1 s for the start-up cases).
"""

from __future__ import annotations

import sys

sys.path.append(".")

import os
import pathlib
import re
import subprocess
import time

import child_env  # pyright: ignore[reportMissingImports]  (test/)
import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest

_ROOT = pathlib.Path(__file__).parents[2]

_GOES_ON = '''
import os, subprocess, sys, threading, time

def test_stuck_in_python():
    while True:
        pass

def test_runs_after_the_stalled_one():
    pass

def test_leaves_a_thread_running():
    threading.Thread(target=time.sleep, args=(4,)).start()

def test_a_program_it_starts_stalls():
    env = dict(os.environ, GREMLIN_TEST_HANG_LIMIT="50")
    result = subprocess.run(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        capture_output=True, text=True, timeout=60, env=env,
    )
    assert result.returncode == 3, result.stderr
    assert "=== STALLED: this program" in result.stderr
'''

_IDLE = '''
from PySide6 import QtCore, QtTest

app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])

def test_idle_event_loop():
    QtTest.QTest.qWait(600000)
'''

_BLOCKED_IN_C = '''
import threading

def test_blocked_in_c():
    threading.Event().wait()
'''

_HELD_GIL = '''
from PySide6 import QtCore, QtTest

def test_app_made_late_then_idle():
    # No heartbeat yet, and qWait keeps the GIL: only the deadman sees it.
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    QtTest.QTest.qWait(600000)
'''


_SAMPLES = {
    "goes_on": _GOES_ON,
    "idle": _IDLE,
    "blocked_in_c": _BLOCKED_IN_C,
    "held_gil": _HELD_GIL,
}


# Start-up (to-do 128): the first test's app start (pytest-qt's qapp: the
# Gremlin app loading Main.qml) may stand still for seconds on a busy PC. An
# exception raised into the main thread there crashed the run (access
# violation inside Qt). A slow start-up is waited out; a stuck one ends the
# run with the report, raising nothing.
_SLOW_START = """
import fake_hardware
import joystick_gremlin
import pytest

fake_hardware.install(vjoy_ids=(1,))


@pytest.fixture(scope="session")
def qapp_cls():
    return joystick_gremlin.JoystickGremlinApp


def test_app_starts(qapp):
    assert isinstance(qapp, joystick_gremlin.JoystickGremlinApp)
"""

_STUCK_START = """
import threading

import pytest
from PySide6 import QtWidgets


class _NeverStarts(QtWidgets.QApplication):
    def __init__(self, args):
        super().__init__(args)
        threading.Event().wait(60)


@pytest.fixture(scope="session")
def qapp_cls():
    return _NeverStarts


def test_app_starts(qapp):
    pass
"""

# name: (code, extra environment). Stalls are caught after 1 s (0.1 s for the
# start-up ones: the real Main.qml load always stands still that long).
_SAMPLE_ENV = {"GREMLIN_TEST_STALL_AFTER": "1"}
_START_ENV = {"GREMLIN_TEST_STALL_AFTER": "0.1"}
_SAMPLES = {
    **{name: (code, _SAMPLE_ENV) for name, code in _SAMPLES.items()},
    "slow_start": (
        _SLOW_START,
        {**_START_ENV, "GREMLIN_TEST_STARTUP_STALL_AFTER": "60"},
    ),
    "stuck_start": (
        _STUCK_START,
        {**_START_ENV, "GREMLIN_TEST_STARTUP_STALL_AFTER": "1"},
    ),
}


@pytest.fixture(scope="module")
def runs(tmp_path_factory: pytest.TempPathFactory) -> dict[str, tuple[int, str, float]]:
    """Every sample through pytest at once (each waits out real stalls)."""
    started = {}
    for name, (code, extra) in _SAMPLES.items():
        folder = tmp_path_factory.mktemp(name)
        sample = folder / "test_sample.py"
        sample.write_text(code, encoding="utf-8")
        # Its own ini and root, so collection looks only in this folder, never
        # at the shared temp folder another test may be emptying (to-do 47).
        (folder / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
        own = ["-c", str(folder / "pytest.ini"), "--rootdir", str(folder),
               "--confcutdir", str(folder)]
        env = dict(
            os.environ,
            PYTHONPATH=child_env.python_path(_ROOT / "test", _ROOT),
            GREMLIN_TEST_HANG_LIMIT="",  # this pytest watches its own tests
            USERPROFILE=str(folder),
            **extra,
        )
        # To a file, not a pipe: a pipe nobody reads yet fills up and blocks
        # the run writing its stall report.
        log = folder / "out.txt"
        with log.open("w", encoding="utf-8") as out:
            tree = proc_tree.popen(
                [sys.executable, "-m", "pytest", "-p", "conftest", "-q",
                 "-p", "no:cacheprovider", *own, "-s", str(sample)],
                cwd=_ROOT, env=env, stdout=out, stderr=subprocess.STDOUT,
            )
        started[name] = (tree, log, time.monotonic())
    results = {}
    for name, (tree, log, start) in started.items():
        process = tree.process
        try:
            process.wait(timeout=90)
        except subprocess.TimeoutExpired:
            tree.kill()
            process.wait()
        finally:
            tree.close()
        took = time.monotonic() - start
        out = log.read_text(encoding="utf-8", errors="replace")
        results[name] = (process.returncode, out, took)
    return results


def test_a_stalled_test_fails_and_the_run_goes_on(runs: dict) -> None:
    code, out, _ = runs["goes_on"]
    assert "=== STALLED: " in out and "test_stuck_in_python" in out, out[-3000:]
    assert "it is blocked" in out
    assert re.search(r'test_sample.py", line [56], in test_stuck_in_python', out)
    assert "FAILED" in out and "TestStalled" in out
    assert "The test left threads running: Thread-" in out
    assert "1 failed, 3 passed, 1 error" in out, out[-3000:]
    assert code == 1


def test_an_idle_event_loop_is_reported(runs: dict) -> None:
    code, out, took = runs["idle"]
    assert "its event loop idles" in out, out[-3000:]
    assert 'test_sample.py", line 7, in test_idle_event_loop' in out
    assert code != 0 and took < 60


def test_a_test_blocked_in_c_ends_the_run_with_the_stacks(runs: dict) -> None:
    code, out, took = runs["blocked_in_c"]
    assert "=== STALLED: " in out and "it is blocked" in out, out[-3000:]
    assert "(stuck inside C code): ending the run" in out
    assert code == 3 and took < 60


def test_the_deadman_ends_a_process_that_keeps_the_gil(runs: dict) -> None:
    code, out, took = runs["held_gil"]
    assert "Timeout (" in out, out[-3000:]  # faulthandler's stacks
    assert "test_app_made_late_then_idle" in out
    assert code != 0 and took < 60


def test_a_slow_start_up_is_waited_out(runs: dict) -> None:
    code, out, _ = runs["slow_start"]
    assert "access violation" not in out, out[-3000:]
    assert "=== STALLED: " not in out, out[-3000:]
    assert "1 passed" in out and code == 0, out[-3000:]


def test_a_stuck_start_up_ends_the_run_raising_nothing(runs: dict) -> None:
    code, out, took = runs["stuck_start"]
    assert "access violation" not in out, out[-3000:]
    assert "=== STALLED: " in out and "test_app_starts" in out, out[-3000:]
    assert "Start-up hasn't finished within 1 s" in out, out[-3000:]
    assert "Failing this test." not in out
    assert code == 3 and took < 60


# A program the tests start (to-do 128, program side): its start-up, until
# its event loop first runs, gets the same longer allowance as pytest's own
# app start-up (GREMLIN_TEST_STARTUP_STALL_AFTER), then the usual limit. CI
# run 38302618588: the Gremlin app's Main.qml load stood still 30 s and the
# program watch ended it as stalled. Here stalls are caught after 0.5 s and
# start-up gets 8 s (past the 4 s C-level deadman, which must wait too).
_PROGRAM = """
import sys, time
from PySide6 import QtCore

app = QtCore.QCoreApplication([])
time.sleep(float(sys.argv[1]))  # start-up, before the event loop runs
QtCore.QTimer.singleShot(500, app.quit)
app.exec()
time.sleep(float(sys.argv[2]))  # after start-up
"""

_PROGRAM_RUNS = {"slow": ("5", "0"), "stuck": ("60", "0"), "after": ("0", "60")}


@pytest.fixture(scope="module")
def program_runs(
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, tuple[int, str, float]]:
    folder = tmp_path_factory.mktemp("program_start")
    env = dict(
        os.environ,
        PYTHONPATH=child_env.python_path(_ROOT / "test", _ROOT),
        GREMLIN_TEST_HANG_LIMIT="50",
        GREMLIN_TEST_STALL_AFTER="0.5",
        GREMLIN_TEST_STARTUP_STALL_AFTER="8",
        USERPROFILE=str(folder),
        QT_QPA_PLATFORM="offscreen",
    )
    started = {}
    for name, args in _PROGRAM_RUNS.items():
        log = folder / f"{name}.txt"
        with log.open("w", encoding="utf-8") as out:
            tree = proc_tree.popen(
                [sys.executable, "-c", _PROGRAM, *args],
                cwd=_ROOT, env=env, stdout=out, stderr=subprocess.STDOUT,
            )
        started[name] = (tree, log, time.monotonic())
    results = {}
    for name, (tree, log, start) in started.items():
        process = tree.process
        try:
            process.wait(timeout=60)
        except subprocess.TimeoutExpired:
            tree.kill()
            process.wait()
        finally:
            tree.close()
        took = time.monotonic() - start
        results[name] = (process.returncode, log.read_text("utf-8", "replace"), took)
    return results


def test_a_programs_slow_start_up_is_waited_out(program_runs: dict) -> None:
    code, out, _ = program_runs["slow"]
    assert "=== STALLED: " not in out and "Timeout (" not in out, out[-3000:]
    assert code == 0, out[-3000:]


def test_a_programs_stuck_start_up_ends_it_with_the_report(
    program_runs: dict,
) -> None:
    code, out, took = program_runs["stuck"]
    assert "=== STALLED: this program" in out, out[-3000:]
    assert "Start-up hasn't finished within 8 s" in out, out[-3000:]
    assert code == 3 and 8 <= took < 30, (code, took)


def test_after_start_up_a_program_has_the_usual_limit(program_runs: dict) -> None:
    code, out, _ = program_runs["after"]
    assert "=== STALLED: this program" in out, out[-3000:]
    assert "Start-up hasn't finished" not in out
    # (Its run time includes waiting for the others: read the report's.)
    still = re.search(r"hasn't moved for (\d+) s", out)
    assert still and int(still[1]) < 8 and code == 3, (code, out[-3000:])
