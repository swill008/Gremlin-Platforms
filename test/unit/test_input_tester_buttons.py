# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Input Tester buttons area (02 S147, S148), end to end: input_tester.py
started off-screen (input_tester_buttons_smoke.py) on fake hardware whose
stick has 128 buttons. S147: the buttons area uses the detail pane's free
height, so every row that fits shows without scrolling. S148: with Follow
input on a press outside the shown rows scrolls it into view; off, the view
stays where it is."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

_HERE = pathlib.Path(__file__).parent
# Screenshots for a person to look at (not checked).
_SHOTS = pathlib.Path(os.environ.get("INPUT_TESTER_SHOTS", ""))


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    tmp = tmp_path_factory.mktemp("tester_buttons")
    home = tmp / "home"
    gremlin_dir = home / "Gremlin Platforms"
    gremlin_dir.mkdir(parents=True)
    shot = (_SHOTS if str(_SHOTS) not in ("", ".") else tmp) / "tester_buttons.png"
    proc = subprocess.run(
        [
            sys.executable,
            str(_HERE / "input_tester_buttons_smoke.py"),
            str(gremlin_dir),
            str(shot),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=90,
        cwd=str(tmp),
        env={
            **os.environ,
            "USERPROFILE": str(home),
            "QT_QPA_PLATFORM": "offscreen",
            "PYTHONUNBUFFERED": "1",
        },
    )
    out: dict = {"errors": [], "qtlog": None}
    for line in proc.stdout.splitlines():
        if line.startswith("RESULT "):
            _tag, name, value = line.split(" ", 2)
            out[name] = json.loads(value)
        elif line.startswith("ERROR"):
            out["errors"].append(line)
        elif line.startswith("QTLOG "):
            out["qtlog"] = json.loads(line[6:])
    assert "done" in proc.stdout, proc.stdout[-3000:] + proc.stderr[-3000:]
    return out


def test_no_errors_or_qml_warnings(run: dict) -> None:
    assert run["errors"] == []
    assert run["qtlog"] == []


def test_tall_window_shows_every_row_without_scrolling(run: dict) -> None:
    """S147: all 8 rows of 128 buttons show; nothing scrolls; hats below."""
    tall = run["tall"]
    assert tall["interactive"] is False
    assert tall["view_h"] >= tall["content_h"]
    assert tall["all_cells"] is True
    assert tall["label"] == "BUTTONS (128)"
    assert tall["hats_in_view"] is True
    assert tall["detail_scrolls"] is False


def test_short_window_shows_rows_that_fit(run: dict) -> None:
    """S147: more than the old two rows fit, fewer than all; the area
    scrolls, the hats stay in view and the pane itself doesn't scroll."""
    before = run["short"]["before"]
    assert before["interactive"] is True
    assert before["content_h"] / 4 < before["view_h"] < before["content_h"]
    assert before["hats_in_view"] is True
    assert before["detail_scrolls"] is False
    assert before["label"].startswith("BUTTONS (1–")


def test_follow_input_on_scrolls_pressed_button_into_view(run: dict) -> None:
    """S148: Follow input on, button 120 pressed: it scrolls into view."""
    on = run["short"]["follow_on"]
    assert on["content_y"] > 0
    assert on["cell_120"] is True
    assert on["label"].endswith("–128 OF 128)")


def test_follow_input_off_keeps_the_view(run: dict) -> None:
    """S148: Follow input off: the press lights the cell, the view stays."""
    short = run["short"]
    assert short["switch_off"] is True
    off = short["follow_off"]
    assert off["cell_120_pressed"] is True
    assert off["content_y"] == 0
    assert off["cell_120"] is False
