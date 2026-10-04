# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Button Map editor fixes (3 Oct review, BM4, BM10, BM14, BM19).

- Shape in the multi-select menu reshaped every selected item (a picture
  would lose its image); Arrange > Lock/Hide acted on one item (BM4).
- Layers > Delete on an open group removed only its selected member (BM10).
- Hide Selected made one undo step per item; each nudge was its own step
  (BM14).
- After a Layers-row click the arrow keys stopped nudging (BM19).

The window-level ones (BM9, BM11, BM15) are in test_button_map_window.py.
Runs the editor off-screen in its own process.
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
        [sys.executable, str(_HERE / "button_map_fixes_smoke.py")],
        capture_output=True, text=True, timeout=120,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, done.stdout[-1500:] + done.stderr[-1500:]
    return json.loads(lines[0][len("RESULT "):])


def test_shape_changes_plain_shapes_only(results: dict) -> None:
    assert results["shapes"] == ["ellipse", "text", "line"]


def test_arrange_hide_hides_the_selection_in_one_step(results: dict) -> None:
    assert results["arrange-hide"] == [True, True, True]
    assert results["arrange-hide-steps"] == 1


def test_a_mixed_selection_gets_only_shared_rows(results: dict) -> None:
    menu = results["mixed-menu"]
    assert "Align and Distribute" in menu and "Arrange" in menu
    assert "Shape" not in menu and "Fill and Outline" not in menu


def test_hide_selected_is_one_step(results: dict) -> None:
    assert results["hide-selected-steps"] == 1


def test_nudges_in_a_row_are_one_step(results: dict) -> None:
    assert results["nudge-steps"] == 1
    # Undo right after more nudges takes back exactly those.
    assert results["undo-after-nudges"] == 0.05


def test_deleting_an_open_group_removes_the_group(results: dict) -> None:
    assert results["group-deleted"] is True


def test_arrow_keys_work_after_a_layers_click(results: dict) -> None:
    assert results["layers-then-arrow"] is True


def test_a_right_click_on_a_layers_row_picks_it(results: dict) -> None:
    selected, menu_open, text = results["layers-right-click"]
    assert selected == [text] and menu_open is True
    assert results["layers-right-click-in-selection"] is True


def test_a_drag_redraws_the_dragged_chip_and_keeps_the_rest(results: dict) -> None:
    mid = results["mid-drag"]
    assert mid["dragged-follows"] and mid["still-in-place"] and mid["live-leaders"]
    assert results["after-drag"] is True


def test_no_qml_warnings(results: dict) -> None:
    assert results["warnings"] == []
