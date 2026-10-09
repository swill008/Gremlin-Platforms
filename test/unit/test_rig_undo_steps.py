# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""One undo step per command in the Button Map editor (07 S55).

A run of nudges or color-picker moves waits for a pause before it becomes
an undo step. A command made during that wait used to take the run into its
own step (Undo took back both), and Add Callout made two steps. Runs the
editor off-screen in its own process (rig_undo_steps_smoke.py).
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

_HERE = pathlib.Path(__file__).parent

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows fonts")


@pytest.fixture(scope="module")
def results() -> dict:
    done = subprocess.run(
        [sys.executable, str(_HERE / "rig_undo_steps_smoke.py")],
        capture_output=True, text=True, timeout=120,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, done.stdout[-1500:] + done.stderr[-1500:]
    return json.loads(lines[0][len("RESULT "):])


def test_a_drawing_after_nudges_is_its_own_step(results: dict) -> None:
    r = results["nudge-draw"]
    assert r["waiting"] is True and r["moved"] is True
    assert r["steps"] == 2
    assert r["undo1"] == {"drawing-gone": True, "nudge-kept": True}
    assert r["undo2"] == {"nudge-undone": True}


def test_a_field_change_after_a_color_drag_is_its_own_step(results: dict) -> None:
    r = results["live-field"]
    assert r["steps"] == 2
    # Undo takes back the size only; the color drag stays.
    color, size = r["undo1"]
    assert color == "#300450" and size != 31
    assert r["undo2"] is True


def test_a_run_step_holds_the_state_after_the_run(results: dict) -> None:
    assert results["pause"] == {"steps": 1, "redo-state": True}


def test_add_callout_is_one_step(results: dict) -> None:
    r = results["callout"]
    assert r["added"] is True and r["tail"] == {"to": r["chip"]}
    assert r["steps"] == 1
    assert r["undo-removes"] is True


def test_undoing_a_callout_added_after_nudges_keeps_them(results: dict) -> None:
    assert results["nudge-callout"] == {"callout-gone": True, "nudge-kept": True}


def test_no_qml_warnings(results: dict) -> None:
    assert results["warnings"] == []
