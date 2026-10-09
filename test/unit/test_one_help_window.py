# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""01 S128, 10 S42 (D-01-ONE-HELP): one Help window. The main window's Help
(F1) shows the whole book; the Device Library's and the Button Map's show
only their chapter, with View Full Help widening to the whole book and a
way back. Links and Related topics open topics. Each menu bar has one Help
item. Runs the program off-screen in its own process.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SMOKE = _ROOT / "test" / "unit" / "one_help_window_smoke.py"


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    env = dict(
        os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1", PYTHONIOENCODING="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(_SMOKE)], cwd=_ROOT, env=env,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=150,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, f"No RESULT (exit {result.returncode}).\n{result.stderr[-3000:]}"
    out = json.loads(lines[-1][len("RESULT "):])
    assert not out["errors"], out["errors"]
    return out


def _whole_book(state: dict) -> None:
    assert state["windows"] == 1, "not one Help window"
    assert state["chapter"] == ""
    assert state["count"] == state["full"] > 0
    assert len(state["chapters"]) == 9
    assert len(state["heads"]) == 9
    assert state["title"] == "Help"


def _only(state: dict, chapter: str, title: str) -> None:
    assert state["windows"] == 1, "not one Help window"
    assert state["chapter"] == chapter
    assert state["chapters"] == [chapter]
    assert state["heads"] == [title]
    assert state["currentChapter"] == chapter, "shows a topic of another chapter"
    assert 0 < state["count"] < state["full"]
    assert state["title"] == "Help — " + title


def test_each_menu_bar_has_one_help_item(run: dict) -> None:
    for key in ("main_items", "library_items", "buttonmap_items"):
        helps = [i for i in run[key] if i["text"] == "Help"]
        assert len(helps) == 1, (key, run[key])
        assert not [i for i in run[key] if "Guide" in i["text"]], (key, run[key])
    for key in ("library_items", "buttonmap_items"):
        assert run[key] == [{"text": "Help", "hint": "F1"}], (key, run[key])


def test_main_f1_opens_the_whole_book(run: dict) -> None:
    _whole_book(run["main_f1"])


def test_links_and_related_topics_open_topics(run: dict) -> None:
    assert run["link_opened"]
    assert run["related_clicked"], "no Related topics link shown"
    assert run["related_opened"]


def test_library_f1_shows_its_chapter_and_view_full_help_widens(run: dict) -> None:
    _only(run["library_f1"], "device-library", "Device Library")
    assert run["full_clicked"], "no View Full Help button"
    # S128: on the scope row, below the search box, before Search all of Help.
    full, field, every = (run["place"][k] for k in ("full", "field", "all"))
    assert full and field and every, run["place"]
    assert full[1] >= field[1] + field[3]
    assert full[0] + full[2] <= every[0]
    assert abs((full[1] + full[3] / 2) - (every[1] + every[3] / 2)) < 12
    _whole_book(run["library_full"])
    assert run["back_clicked"], "no way back to the chapter"
    _only(run["library_back"], "device-library", "Device Library")


def test_button_map_f1_shows_its_chapter(run: dict) -> None:
    _only(run["buttonmap_f1"], "button-map", "Button Map")


def test_main_f1_after_an_area_shows_the_whole_book(run: dict) -> None:
    _whole_book(run["main_again"])
    assert not run["qml_errors"], run["qml_errors"]
