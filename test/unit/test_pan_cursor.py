# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The pan cursor (07 S14; D-07-PAN-CURSOR): while a pan drag is under way
the pointer is a closed hand; with Space held before the drag, an open hand.

Runs the real Device Mapping Editor window off-screen (pan_cursor_smoke.py) in its own
process.
"""

from __future__ import annotations

import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

_HERE = pathlib.Path(__file__).parent


def test_pan_cursor_in_the_window(tmp_path: pathlib.Path) -> None:
    result = proc_tree.run(
        [sys.executable, str(_HERE / "pan_cursor_smoke.py"), str(tmp_path)],
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=150,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "PYTHONIOENCODING": "utf-8"},
    )
    lines = result.stdout.splitlines()
    assert "done" in lines, smoke_report.explain(result)
    assert [line for line in lines if line.startswith("ERROR")] == []
    mine = [
        line for line in lines if line.startswith("WARN") and "VkbRigFace.qml" in line
    ]
    assert mine == []
    r = {
        line.split(" ", 2)[1]: (line.split(" ", 2) + [""])[2]
        for line in lines
        if line.startswith("RESULT ")
    }
    # before / during / after the drag, and whether the view panned.
    closed = "ClosedHandCursor"
    for name in ("left-view", "middle-view", "middle-edit"):
        before, during, after, panned = r[name].split(" ")
        assert panned == "True", (name, r[name])
        assert during == closed, (name, r[name])
        assert before != closed and after != closed, (name, r[name])
    # Space held: an open hand, a closed hand while dragging.
    assert r["space-held"] == "OpenHandCursor"
    before, during, after, panned = r["space-drag"].split(" ")
    assert (before, during, after, panned) == (
        "OpenHandCursor",
        closed,
        "OpenHandCursor",
        "True",
    )
    assert r["space-released"] not in ("OpenHandCursor", closed)
