# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Deferred Qt work stays with the test that left it (to-do 133).

test/conftest.py deletes a test's deleteLater objects at that test's own
end (a later test's event loop deleted them, and a crash there named the
wrong test), and notes a test that left more gremlin.signal connections
than it found (not one that started a once-per-process hook). Each case
runs a tiny pytest of its own, in a fixed order, with test/conftest.py as
a plugin.
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys

import child_env  # pyright: ignore[reportMissingImports]  (test/)
import proc_tree  # pyright: ignore[reportMissingImports]  (test/)

_ROOT = pathlib.Path(__file__).parents[2]

_SAMPLE = '''
import shiboken6
from PySide6 import QtCore

import gremlin.signal

APP = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
LEFT = []
KEPT = []


def test_leaves_a_deferred_delete():
    thing = QtCore.QObject()
    thing.deleteLater()
    LEFT.append(thing)


def test_the_object_went_at_the_end_of_the_test_that_left_it():
    assert not shiboken6.isValid(LEFT[0])


def test_starts_a_once_per_process_hook():
    import gremlin.osc_feedback

    hub = gremlin.signal.signal
    before = hub.receivers("2oscServerSettingsChanged()")
    gremlin.osc_feedback._hook()
    assert hub.receivers("2oscServerSettingsChanged()") > before


def test_leaves_a_connection():
    slot = lambda: None
    KEPT.append(slot)
    gremlin.signal.signal.profileChanged.connect(slot)


def test_cleans_up_after_itself():
    slot = lambda: None
    gremlin.signal.signal.profileChanged.connect(slot)
    gremlin.signal.signal.profileChanged.disconnect(slot)
'''


def _inner_pytest(folder: pathlib.Path) -> tuple[int | None, str, str]:
    """Runs the sample in a pytest of its own: (exit code, output, the rule
    check report)."""
    (folder / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    sample = folder / "test_sample_deferred.py"
    sample.write_text(_SAMPLE, encoding="utf-8")
    report = folder / "validate.txt"
    profile = folder / "profile"
    profile.mkdir()
    env = dict(
        os.environ,
        PYTHONPATH=child_env.python_path(_ROOT / "test", _ROOT),
        GREMLIN_VALIDATE_REPORT=str(report),
        GREMLIN_TEST_HANG_LIMIT="",
        USERPROFILE=str(profile),
        QT_QPA_PLATFORM="offscreen",
    )
    out_file = folder / "out.txt"
    with out_file.open("w", encoding="utf-8") as out:
        tree = proc_tree.popen(
            [sys.executable, "-m", "pytest", "-p", "conftest", "-v",
             "-p", "no:cacheprovider", "-p", "no:randomly",
             "-c", str(folder / "pytest.ini"), "--rootdir", str(folder),
             "--confcutdir", str(folder), str(sample)],
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
    text = report.read_text(encoding="utf-8") if report.is_file() else ""
    return process.returncode, out_file.read_text(
        encoding="utf-8", errors="replace"
    ), text


def test_deferred_deletes_and_kept_connections_stay_with_their_test(
    tmp_path: pathlib.Path,
) -> None:
    code, out, report = _inner_pytest(tmp_path)
    assert code == 0 and "5 passed" in out, out[-3000:]
    # The connection left behind is a warning naming its test, not a failure.
    named = [line for line in report.splitlines() if "RECEIVERS-GREW" in line]
    assert len(named) == 1 and "profileChanged +1" in named[0], report
    block = report.split("test_leaves_a_connection", 1)
    assert len(block) == 2 and "RECEIVERS-GREW" in block[1].splitlines()[1], report
    assert "test_cleans_up_after_itself" not in report, report
    # The first test to start a once-per-process hook isn't named.
    assert "test_starts_a_once_per_process_hook" not in report, report
    assert "test_leaves_a_deferred_delete" not in report, report
