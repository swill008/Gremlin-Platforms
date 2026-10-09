# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""01 S134 (D-01-LEAVE-TEXT) end to end: the real program off-screen
(leave_text_windows_smoke.py, started as joystick_gremlin.py starts it, so
the program-wide leave-text owner is in place) with real key and mouse
events in real windows. A text box is left by Esc or a click on a blank
spot and what was typed is kept and saved (the Device Library description);
an inline Rename's Esc still cancels; where Esc closes the window (Options)
the first Esc only leaves the box and a second closes; Module Setup keeps
Esc doing nothing (03 S50) and a click away still leaves the box."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

_HERE = pathlib.Path(__file__).parent


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("leave_text_home")
    (home / "Gremlin Platforms").mkdir()
    proc = subprocess.run(
        [sys.executable, str(_HERE / "leave_text_windows_smoke.py")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=150,
        cwd=str(_HERE.parents[1]),
        env={
            **os.environ,
            "USERPROFILE": str(home),
            "QT_QPA_PLATFORM": "offscreen",
            "PYTHONUNBUFFERED": "1",
        },
    )
    results: dict = {"errors": [], "calls": None}
    for line in proc.stdout.splitlines():
        if line.startswith("RESULT "):
            _tag, name, value = line.split(" ", 2)
            results[name] = json.loads(value)
        elif line.startswith("ERROR"):
            results["errors"].append(line)
        elif line.startswith("CALLS "):
            results["calls"] = json.loads(line[6:])
    assert "done" in proc.stdout, proc.stdout[-3000:] + proc.stderr[-3000:]
    return results


def test_runs_without_errors(run: dict) -> None:
    assert run["errors"] == []


def test_library_description_click_away_leaves_and_saves(run: dict) -> None:
    res = run["library-click-away"]
    assert res["focused"], "the click did not put the cursor in the description"
    assert res["focus"] is False
    assert res["text"].endswith("click")
    assert res["saved"] == res["text"]
    assert res["visible"] is True
    key = run["library-open"]["key"]
    assert [key, res["text"]] in run["calls"]


def test_library_description_esc_leaves_saves_and_keeps_window(run: dict) -> None:
    res = run["library-esc"]
    assert res["focused"]
    assert res["focus"] is False
    assert res["text"].endswith("click esc")
    assert res["saved"] == res["text"]
    assert res["visible"] is True
    key = run["library-open"]["key"]
    assert run["calls"][-1] == [key, res["text"]]


def test_library_rename_esc_still_cancels(run: dict) -> None:
    res = run["library-rename-esc"]
    assert res["started"]
    assert res["renaming"] is False
    assert res["after"] == res["before"]
    assert res["visible"] is True


def test_options_click_away_leaves_search(run: dict) -> None:
    res = run["options-click-away"]
    assert res["focused"]
    assert res["focus"] is False
    assert res["text"] == "scale"
    assert res["visible"] is True


def test_options_first_esc_leaves_box_second_closes(run: dict) -> None:
    res = run["options-esc"]
    assert res["focused"]
    # First Esc: out of the box, typing kept, window still open.
    assert res["focus"] is False
    assert res["visible"] is True
    assert res["text"] == "scalex"
    # Second Esc: the window closes (EscapeCloses).
    assert res["visible-after-second"] is False


def test_module_setup_esc_does_nothing(run: dict) -> None:
    assert run["module-open"]["dirty"] is False
    res = run["module-esc"]
    assert res["focused"]
    assert res["focus"] is True
    assert res["text"] == "trigger"
    assert res["visible"] is True


def test_module_setup_click_away_leaves_and_saves(run: dict) -> None:
    res = run["module-click-away"]
    assert res["focus"] is False
    assert res["text"] == "trigger"
    assert res["visible"] is True
    # The box's onEditingFinished ran (it marks the claims changed).
    assert res["saved"] is True
