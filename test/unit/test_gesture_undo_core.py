# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A drag in the Device Mapping Editor is one undo step (07 S55a).

A picture's hover highlight used to save an undo step each time it changed,
so dragging a corner handle back and forth across the picture's edge made
many steps. Runs the editor off-screen in its own process
(gesture_undo_core_smoke.py).
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest

_HERE = pathlib.Path(__file__).parent

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows fonts")


@pytest.fixture(scope="module")
def results() -> dict:
    done = proc_tree.run(
        [sys.executable, str(_HERE / "gesture_undo_core_smoke.py")],
        text=True, timeout=120,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, done.stdout[-1500:] + done.stderr[-1500:]
    return json.loads(lines[0][len("RESULT "):])


def test_a_corner_drag_across_the_edge_is_one_step(results: dict) -> None:
    r = results["corner"]
    assert r["resized"] is True
    assert r["steps-mid"] == 0
    assert r["steps"] == 1
    assert r["undo-restores"] is True


def test_a_chip_dragged_over_a_picture_is_one_step(results: dict) -> None:
    assert results["chip"] == {"steps": 1, "moved": True}


def test_hovering_a_picture_makes_no_step(results: dict) -> None:
    assert results["hover-steps"] == 0


def test_esc_mid_drag_ends_it_as_one_step(results: dict) -> None:
    r = results["esc"]
    assert r["active"] is False and r["drag"] == ""
    assert r["steps"] == 1
    assert r["undo-restores"] is True


def test_undo_mid_drag_takes_the_drag_back(results: dict) -> None:
    r = results["undo-mid"]
    assert r["steps"] == 0
    assert r["restored"] is True
    assert r["active"] is False
    assert r["redo"] is True


def test_no_qml_warnings(results: dict) -> None:
    assert results["warnings"] == []
