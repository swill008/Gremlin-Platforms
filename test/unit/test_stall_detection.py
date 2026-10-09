# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The stall detection catches a test that stops making progress.

(test/hang_trace/stall_watch.py, used by test/conftest.py and, for the
programs tests start, test/hang_trace/sitecustomize.py.) Each case runs a
small test file through pytest with the real conftest, with stalls caught
after 2 s instead of 10.
"""

from __future__ import annotations

import sys

sys.path.append(".")

import os
import pathlib
import re
import subprocess
import time

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


@pytest.fixture(scope="module")
def runs(tmp_path_factory: pytest.TempPathFactory) -> dict[str, tuple[int, str, float]]:
    """Every sample through pytest at once (each waits out real stalls)."""
    started = {}
    for name, code in _SAMPLES.items():
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
            PYTHONPATH=os.pathsep.join([str(_ROOT / "test"), str(_ROOT)]),
            GREMLIN_TEST_STALL_AFTER="1",
            GREMLIN_TEST_HANG_LIMIT="",  # this pytest watches its own tests
            USERPROFILE=str(folder),
        )
        # To a file, not a pipe: a pipe nobody reads yet fills up and blocks
        # the run writing its stall report.
        log = folder / "out.txt"
        with log.open("w", encoding="utf-8") as out:
            process = subprocess.Popen(
                [sys.executable, "-m", "pytest", "-p", "conftest", "-q",
                 "-p", "no:cacheprovider", *own, "-s", str(sample)],
                cwd=_ROOT, env=env, stdout=out, stderr=subprocess.STDOUT,
            )
        started[name] = (process, log, time.monotonic())
    results = {}
    for name, (process, log, start) in started.items():
        try:
            process.wait(timeout=90)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
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
