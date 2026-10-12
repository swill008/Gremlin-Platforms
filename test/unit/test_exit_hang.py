# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A test run must end within 20 s of pytest's summary (to-do 43).

test/run_tests.py reports a part that doesn't as an EXIT HANG, with its
files, and ends it; test/conftest.py's deadman prints the stacks of a
process stuck after its session and ends it. Each case runs a tiny pytest
whose session passes but whose process stays (atexit), with the 20 s cut to
about 2 s. The inner runs collect only their own folder (to-do 47).
"""

from __future__ import annotations

import importlib.util
import io
import os
import pathlib
import subprocess
import sys
import time
from types import ModuleType

import child_env  # pyright: ignore[reportMissingImports]  (test/)
import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest

_ROOT = pathlib.Path(__file__).parents[2]

_LINGERS = '''
import atexit, time

def _linger():
    time.sleep({seconds})

atexit.register(_linger)

def test_passes():
    pass
'''


def _run_tests() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "run_tests_exit_hang", _ROOT / "test" / "run_tests.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # its dataclasses look themselves up
    spec.loader.exec_module(module)
    return module


def _sample(folder: pathlib.Path, seconds: float) -> pathlib.Path:
    """A test file that passes, then keeps its process for seconds, in a
    folder of its own with its own ini (so nothing else is collected)."""
    (folder / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    sample = folder / "test_lingers.py"
    sample.write_text(_LINGERS.format(seconds=seconds), encoding="utf-8")
    return sample


def _own_folder(folder: pathlib.Path) -> tuple[str, ...]:
    return ("-c", str(folder / "pytest.ini"), "--rootdir", str(folder),
            "--confcutdir", str(folder))


def test_a_part_that_outlives_its_summary_is_an_exit_hang(
    tmp_path: pathlib.Path,
) -> None:
    run_tests = _run_tests()
    sample = _sample(tmp_path, 120)
    part = run_tests.Part("hangs", str(tmp_path), [str(sample)])
    log = io.StringIO()
    start = time.monotonic()
    run_tests.run([part], False, log, _own_folder(tmp_path),
                  exit_hang_s=2.0, stacks_s=1.0)
    took = time.monotonic() - start
    out = log.getvalue()
    assert "1 passed" in part.summary, out
    assert part.exit_hang and part.finished, out
    assert took < 40, out  # not the 120 s the process wanted
    line = next(t for t in out.splitlines() if "EXIT HANG:" in t)
    assert "after pytest's summary" in line and sample.as_posix() in line, out
    assert "EXIT HANG: ending it" in out
    assert "+ EXIT HANG" in out
    assert part.took < 30  # the time after the summary is no test's


def test_the_summary_names_the_hang_and_it_fails_the_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_tests = _run_tests()
    part = run_tests.Part("unit-3", "test/unit", ["test/unit/test_a.py",
                                                  "test/unit/test_b.py::test_x"])
    part.summary = "5 passed in 3.00s"
    part.exit_hang_at = 1.0
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    lines = run_tests.exit_hang_report([part])
    assert lines[0].startswith("EXIT HANG (1), FAILURE:"), lines
    assert "  EXIT HANG unit-3: test/unit/test_a.py test/unit/test_b.py" in lines
    assert any(t.startswith("::error title=EXIT HANG unit-3::") for t in lines)
    assert not run_tests.passed([part], [])  # a failure since to-do 42's fix
    part.exit_hang_at = 0.0
    assert run_tests.exit_hang_report([part]) == []
    assert run_tests.passed([part], [])


def test_a_real_vjoy_part_is_reported_but_never_ended(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_tests = _run_tests()
    ended: list[object] = []
    monkeypatch.setattr(run_tests, "_end", ended.append)
    sample = _sample(tmp_path, 4)
    part = run_tests.Part("integration", str(tmp_path), [str(sample)],
                          real_vjoy=True)
    log = io.StringIO()
    run_tests.run([part], False, log, _own_folder(tmp_path),
                  exit_hang_s=1.0, stacks_s=0.5)
    assert part.exit_hang and ended == [], log.getvalue()
    assert "not ending it" in log.getvalue()


def test_only_the_real_vjoy_run_gets_the_real_vjoy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_tests = _run_tests()
    monkeypatch.setenv(run_tests.REAL_VJOY_ENV, "1")  # left set in the shell
    normal = run_tests.Part("unit-1", "test/unit", ["test/unit/test_a.py"])
    assert run_tests.REAL_VJOY_ENV not in run_tests._child_env(normal)
    (real,) = run_tests.real_vjoy_parts()
    assert real.targets == ["test/integration"] and real.real_vjoy
    assert run_tests._child_env(real)[run_tests.REAL_VJOY_ENV] == "1"


def _inner_pytest(
    folder: pathlib.Path, sample: pathlib.Path, deadman: str
) -> tuple[float, int | None, str]:
    """Runs sample in a pytest of its own with test/conftest.py as a plugin
    and the exit deadman cut to deadman seconds: (took, exit code, output)."""
    env = dict(
        os.environ,
        PYTHONPATH=child_env.python_path(_ROOT / "test", _ROOT),
        GREMLIN_TEST_EXIT_DEADMAN=deadman,
        GREMLIN_TEST_HANG_LIMIT="",
        USERPROFILE=str(folder),
        QT_QPA_PLATFORM="offscreen",
    )
    out_file = folder / "out.txt"
    start = time.monotonic()
    with out_file.open("w", encoding="utf-8") as out:
        tree = proc_tree.popen(
            [sys.executable, "-m", "pytest", "-p", "conftest", "-q",
             "-p", "no:cacheprovider", *_own_folder(folder), str(sample)],
            cwd=_ROOT, env=env, stdout=out, stderr=subprocess.STDOUT,
        )
        process = tree.process
        try:
            process.wait(timeout=90)
        except subprocess.TimeoutExpired:
            tree.kill()
            process.wait()
        finally:
            tree.close()
    took = time.monotonic() - start
    return took, process.returncode, out_file.read_text(
        encoding="utf-8", errors="replace"
    )


def test_the_conftest_deadman_ends_a_process_stuck_after_its_session(
    tmp_path: pathlib.Path,
) -> None:
    sample = _sample(tmp_path, 120)
    took, code, out = _inner_pytest(tmp_path, sample, "2")
    assert "1 passed" in out, out[-3000:]
    assert "Timeout (" in out and "_linger" in out, out[-3000:]  # the stacks
    assert took < 45 and code != 0, (took, out[-3000:])


# | To-do 42's native cause (cdb on the stuck process, 2026-10-12): the app's
# | QML engine outlived the session. Py_FinalizeEx -> PySide's
# | destroyQCoreApplication deleted it as the app's child, after the app
# | itself was gone, and its picture loader (QQuickPixmapReader, started when
# | the window first loads a picture) waited in QThread::wait for a reader
# | thread that never left its event loop. The session's end must delete the
# | app's engines while the app is alive, as the program's own release_qt
# | does. These two tests in one process were the to-do's case (each alone
# | ends at once: the second loads a stick's picture into the first's window).
_ENGINE_CASE = (
    "test/unit/test_data_safety.py::"
    "test_a_profile_with_an_unknown_action_type_opens_and_keeps_it",
    "test/unit/test_stage1_history_pack.py::"
    "test_delete_device_keeps_an_autosave_that_can_be_imported_back",
)


def test_a_session_whose_window_loaded_a_picture_ends_at_once(
    tmp_path: pathlib.Path,
) -> None:
    env = child_env.child_env(
        _ROOT,
        GREMLIN_TEST_EXIT_DEADMAN="10",
        USERPROFILE=str(tmp_path),
        QT_QPA_PLATFORM="offscreen",
    )
    out_file = tmp_path / "out.txt"
    with out_file.open("w", encoding="utf-8") as out:
        tree = proc_tree.popen(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:randomly",
             "-p", "no:cacheprovider", *_ENGINE_CASE],
            cwd=_ROOT, env=env, stdout=out, stderr=subprocess.STDOUT,
        )
        process = tree.process
        try:
            process.wait(timeout=90)
        except subprocess.TimeoutExpired:
            tree.kill()
            process.wait()
        finally:
            tree.close()
    text = out_file.read_text(encoding="utf-8", errors="replace")
    assert "2 passed" in text, text[-3000:]
    # The deadman's "Timeout (0:00:10)!": the process stood still at exit
    # (the QQuickPixmapReader wait) and was ended.
    assert "Timeout (" not in text and process.returncode == 0, (
        process.returncode, text[-3000:]
    )
