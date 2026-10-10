# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""test/run_tests.py ends each part's whole process tree (ORPHAN-PROCS).

A test that starts a program which outlives it left that program running
for hours after the run. Each case runs a tiny pytest whose test starts a
grandchild that sleeps 60 s and writes its own process id; after the runner
returns, nothing of that tree may be left.
"""

from __future__ import annotations

import importlib.util
import io
import pathlib
import sys
import time
from types import ModuleType

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest

_ROOT = pathlib.Path(__file__).parents[2]

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows runner")

_STARTS_SLEEPER = '''
import pathlib, subprocess, sys, time

def test_starts_a_sleeper():
    pids = pathlib.Path({pids!r})
    code = ("import os, pathlib, time; "
            "pathlib.Path(%r).write_text(str(os.getpid())); time.sleep(60)"
            % str(pids))
    subprocess.Popen([sys.executable, "-c", code], stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    end = time.monotonic() + 20
    while not pids.exists() and time.monotonic() < end:
        time.sleep(0.05)
    assert pids.exists()
    {after}
'''


def _run_tests() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "run_tests_tree", _ROOT / "test" / "run_tests.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # its dataclasses look themselves up
    spec.loader.exec_module(module)
    return module


def _sample(folder: pathlib.Path, after: str = "") -> tuple[pathlib.Path, pathlib.Path]:
    (folder / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    pids = folder / "sleeper.pid"
    sample = folder / "test_sleeper.py"
    sample.write_text(_STARTS_SLEEPER.format(pids=str(pids), after=after),
                      encoding="utf-8")
    return sample, pids


def _own_folder(folder: pathlib.Path) -> tuple[str, ...]:
    return ("-c", str(folder / "pytest.ini"), "--rootdir", str(folder),
            "--confcutdir", str(folder))


def _gone(run_tests: ModuleType, pid: int, wait: float = 3.0) -> bool:
    end = time.monotonic() + wait
    while run_tests._alive(pid) and time.monotonic() < end:  # noqa: SLF001
        time.sleep(0.05)
    return not run_tests._alive(pid)  # noqa: SLF001


def test_a_grandchild_is_ended_with_its_part(tmp_path: pathlib.Path) -> None:
    run_tests = _run_tests()
    sample, pids = _sample(tmp_path)
    part = run_tests.Part("tree", str(tmp_path), [str(sample)])
    log = io.StringIO()
    run_tests.run([part], False, log, _own_folder(tmp_path))
    assert "1 passed" in part.summary, log.getvalue()
    pid = int(pids.read_text())
    assert _gone(run_tests, pid), f"sleeper {pid} outlived its part"


def test_ctrl_c_ends_every_part_tree(tmp_path: pathlib.Path) -> None:
    run_tests = _run_tests()
    # The test waits after starting its sleeper; Ctrl+C comes meanwhile.
    sample, pids = _sample(
        tmp_path, after="print('SLEEPER UP', flush=True); time.sleep(60)")

    class _Log(io.StringIO):
        def write(self, text: str) -> int:
            if "SLEEPER UP" in text:
                raise KeyboardInterrupt
            return super().write(text)

    part = run_tests.Part("tree", str(tmp_path), [str(sample)])
    start = time.monotonic()
    with pytest.raises(KeyboardInterrupt):
        run_tests.run([part], False, _Log(), (*_own_folder(tmp_path), "-s"))
    assert time.monotonic() - start < 30
    assert part.process is not None
    pid = int(pids.read_text())
    assert _gone(run_tests, pid), f"sleeper {pid} outlived Ctrl+C"
    assert _gone(run_tests, part.process.pid), "pytest outlived Ctrl+C"


def test_proc_tree_run_ends_what_its_child_started(tmp_path: pathlib.Path) -> None:
    pids = tmp_path / "sleeper.pid"
    code = (
        "import pathlib, subprocess, sys, time\n"
        f"pid_file = {str(pids)!r}\n"
        "inner = ('import os, pathlib, time; pathlib.Path(%r)'\n"
        "         '.write_text(str(os.getpid())); time.sleep(60)' % pid_file)\n"
        "subprocess.Popen([sys.executable, '-c', inner], stdin=subprocess.DEVNULL,\n"
        "                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
        f"p = pathlib.Path({str(pids)!r})\n"
        "while not p.exists(): time.sleep(0.05)\n"
        "time.sleep(60)\n"
    )
    start = time.monotonic()
    with pytest.raises(proc_tree.subprocess.TimeoutExpired):
        proc_tree.run([sys.executable, "-c", code], timeout=4, cwd=tmp_path)
    assert time.monotonic() - start < 15
    pid = int(pids.read_text())
    assert _gone(_run_tests(), pid), f"sleeper {pid} outlived the timeout"
