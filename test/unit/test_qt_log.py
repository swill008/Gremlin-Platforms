# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""qt.log: Qt's own messages (and anything on the error stream) kept in
logs/qt.log, each line with the time, and still shown on the console. Run
in a process of its own: it takes over the error stream."""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys

_ROOT = pathlib.Path(__file__).parents[2]

_SCRIPT = r"""
import sys
sys.path.insert(0, ".")
from pathlib import Path
folder = Path(sys.argv[1])
cap = int(sys.argv[2])
from gremlin import qt_log, threads
assert qt_log.install(folder, cap=cap, limit=100)
from PySide6 import QtCore
app = QtCore.QCoreApplication([])
QtCore.qWarning("a Qt warning from the test")
print("a line on the error stream", file=sys.stderr, flush=True)
for i in range(int(sys.argv[3])):
    QtCore.qWarning(f"filler {i:04d} " + "x" * 60)
left = threads.shutdown(timeout=3.0)
print("LEFT", left, flush=True)
"""


def _run(
    folder: pathlib.Path, cap: int = 5_000_000, filler: int = 0
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", _SCRIPT, str(folder), str(cap), str(filler)],
        cwd=_ROOT, capture_output=True, text=True, timeout=60,
    )


def test_qt_messages_go_to_the_file_and_the_console(tmp_path: pathlib.Path) -> None:
    done = _run(tmp_path)
    assert "LEFT []" in done.stdout, done.stdout + done.stderr
    text = (tmp_path / "qt.log").read_text(encoding="utf-8")
    stamp = r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d "
    assert re.search(stamp + r".*a Qt warning from the test$", text, re.M), text
    assert re.search(stamp + r"a line on the error stream$", text, re.M), text
    # Still on the console (here: the captured error stream).
    assert "a Qt warning from the test" in done.stderr
    assert "a line on the error stream" in done.stderr


def test_a_big_log_moves_aside_at_start(tmp_path: pathlib.Path) -> None:
    (tmp_path / "qt.log").write_text("old\n" * 100, encoding="utf-8")
    done = _run(tmp_path)
    assert "LEFT []" in done.stdout, done.stderr
    assert (tmp_path / "qt.log.1").read_text(encoding="utf-8").startswith("old")
    assert "old" not in (tmp_path / "qt.log").read_text(encoding="utf-8")


def test_the_debug_page_shows_it() -> None:
    from gremlin.ui.live_debug import DEBUG_FILES

    assert DEBUG_FILES["qt"] == "qt.log"
    page = (_ROOT / "qml" / "DialogLiveLog.qml").read_text(encoding="utf-8")
    assert '{ text: "Qt", value: "qt" }' in page


def test_one_session_writes_no_more_than_the_cap(tmp_path: pathlib.Path) -> None:
    done = _run(tmp_path, cap=4000, filler=200)
    assert "LEFT []" in done.stdout, done.stderr
    text = (tmp_path / "qt.log").read_text(encoding="utf-8")
    assert len(text.encode()) <= 4000 + 80
    assert text.rstrip().endswith("[qt.log is full for this session]")
    # The console still gets everything.
    assert "filler 0199" in done.stderr
