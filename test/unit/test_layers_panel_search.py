# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Button Map's Layers panel: search box and kind toggles (07 S102,
D-07-LAYERS-SEARCH), checked in the running program off-screen
(layers_panel_search_smoke.py, its own process and user folder), at UI
scale 100 % and 175 %.

- One toggle per kind; any number on; none on lights All and shows every
  row; All turns them all off.
- Typing filters as you type; Esc and the box's × clear it; Enter selects
  every match on the map.
- While a filter is on, "N of M" or "No layers match".
- A row shown only for a matching child is a dimmed heading.
- The kinds and the search stay when another map's editor is shown.
- At the pane's smallest width nothing in the header, box or toggles is cut
  off (the toggles wrap).
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

_ROOT = pathlib.Path(__file__).parents[2]
_ALL = ["> Fire", "> Gear", "Throttle group", "Rectangle", "Line", "Logo", "Title",
        "Table", "Background photo"]


def _run(tmp_path_factory: pytest.TempPathFactory, scale: int) -> dict:
    home = tmp_path_factory.mktemp(f"home{scale}")
    (home / "Gremlin Platforms").mkdir()
    env = dict(os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen")
    fonts = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    env.setdefault("QT_QPA_FONTDIR", fonts)
    shot = home / f"layers_{scale}.png"
    done = subprocess.run(
        [sys.executable, str(_ROOT / "test" / "unit" / "layers_panel_search_smoke.py"),
         str(scale), str(shot)],
        cwd=_ROOT, env=env, capture_output=True, text=True, timeout=120,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, done.stdout[-1500:] + done.stderr[-1500:]
    return json.loads(lines[0][len("RESULT "):])


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return _run(tmp_path_factory, 100)


@pytest.fixture(scope="module")
def run175(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return _run(tmp_path_factory, 175)


def test_panel_has_the_filter_properties(run: dict) -> None:
    assert run["props"] == {"kinds": [], "searchText": "",
                            "state": {"kinds": [], "query": ""}, "focus": "function"}
    assert run["warnings"] == []


def test_with_no_filter_every_row_shows_and_no_count_line(run: dict) -> None:
    assert run["real-rows"] >= 1
    assert run["real-count-line"] == ""
    assert run["0-all"] == _ALL
    assert run["0-lit"] == ["all"]
    assert run["0-count"] == ""


def test_toggles_combine(run: dict) -> None:
    assert run["1-kinds"] == ["chip", "shape"]
    assert run["1-lit"] == ["chip", "shape"]
    assert run["1-state"] == {"kinds": ["chip", "shape"], "query": ""}
    assert run["1-rows"] == ["> Fire", "> Gear", "Rectangle"]
    assert run["1-count"] == "3 of 12"
    assert run["2-kinds"] == ["chip"]


def test_a_chip_shown_for_its_hotspot_is_a_dimmed_heading(run: dict) -> None:
    # Only Hotspots on: Fire shows (dimmed, no match look) for its hotspot.
    assert run["3-rows"] == ["> Fire", "  Hotspot"]
    heading, match = run["3-heading"], run["3-match"]
    assert heading["heading"] is True and match["heading"] is False
    assert heading["opacity"] < match["opacity"]
    assert heading["color"] != match["color"]
    assert heading["bold"] is False and match["bold"] is False


def test_all_turns_the_kinds_off(run: dict) -> None:
    assert run["4-kinds"] == []
    assert run["4-lit"] == ["all"]
    assert run["4-count"] == ""


def test_typing_filters_any_case(run: dict) -> None:
    assert run["5-search"] == "BUTTON 1"
    assert run["5-rows"] == ["> Fire"]
    assert run["5-count"] == "1 of 12"


def test_esc_and_x_clear_the_search(run: dict) -> None:
    assert run["6-esc"] == ["", len(_ALL), ""]
    assert run["6-still-open"] is True
    assert run["7-none"] == "No layers match"
    assert run["8-cleared"] == ["", ""]


def test_enter_selects_the_matches(run: dict) -> None:
    assert run["9-enter"] == [1, {"kinds": [], "query": "gear"}]


def test_eye_works_on_a_shown_row(run: dict) -> None:
    assert run["10-eye"] == ["c2//hidden"]


def test_focus_search_selects_the_text(run: dict) -> None:
    assert run["11-focus"] == [True, "gear"]


def test_a_group_member_shows_under_its_group_without_eye_or_lock(run: dict) -> None:
    assert run["13-member"] == ["Throttle group", "  Button 3"]
    assert run["13-member-look"] == [True, False, False]
    assert run["13-member-flags"] == ["c2//hidden"]


def test_kinds_and_search_stay_when_the_editor_changes(run: dict) -> None:
    assert run["12-kept"] == [["text"], "gear", {"kinds": ["text"], "query": "gear"}]


@pytest.mark.parametrize("scale", [100, 175])
def test_nothing_is_cut_off_at_the_smallest_width(
    run: dict, run175: dict, scale: int
) -> None:
    r = run if scale == 100 else run175
    assert abs(r["pane-w"][0] - r["pane-w"][1]) < 1, r["pane-w"]
    assert r["fit"] == [], r["fit"]
    assert r["fit-lit"] == [], r["fit-lit"]
