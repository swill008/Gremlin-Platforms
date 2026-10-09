# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""01 S138 (D-01-HELP-LIST): the Help window's topic list. A handle beside
it resizes it (180 px to half the window), the width is kept the next time
Help opens and a double-click puts the default back; topics are single
spaced; chapters fold (only the open topic's chapter unfolded in the whole
book, a heading click toggles, Expand all / Collapse all in the whole book,
opening a topic unfolds its chapter, a search shows matches in folded
chapters and clearing it restores the folds). Opening Help and searching
log no "Overwriting binding". Runs the program off-screen in its own
process (help_list_smoke.py).
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SMOKE = _ROOT / "test" / "unit" / "help_list_smoke.py"


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    env = dict(
        os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1", PYTHONIOENCODING="utf-8",
        QT_LOGGING_RULES="qt.qml.binding.removal.info=true",
    )
    result = subprocess.run(
        [sys.executable, str(_SMOKE)], cwd=_ROOT, env=env,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=150,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, f"No RESULT (exit {result.returncode}).\n{result.stderr[-3000:]}"
    out = json.loads(lines[-1][len("RESULT "):])
    out["stderr"] = result.stderr
    return out


def _part(run: dict, name: str) -> dict:
    errors = [e for e in run["errors"] if e.startswith(name + ":")]
    assert not errors, errors
    return run[name]


def _shown_chapters(state: dict) -> set[str]:
    return {chapter for _, chapter in state["topics"]}


def test_handle_drag_resizes_the_list_within_limits(run: dict) -> None:
    res = _part(run, "resize")
    assert res["dragged"], "no helpListHandle"
    start, plus = res["start"], res["plus100"]
    assert start["pane"] == start["list"]
    assert plus["list"] == pytest.approx(start["list"] + 100, abs=3)
    assert plus["pane"] == plus["list"]
    assert res["max"]["list"] == res["max"]["half"]
    assert res["max"]["pane"] == res["max"]["list"]
    assert res["min"]["list"] == run["dp180"]
    assert res["min"]["pane"] == res["min"]["list"]


def test_width_is_kept_on_reopen_and_double_click_resets(run: dict) -> None:
    kept = _part(run, "resize")["kept_before"]["list"]
    res = _part(run, "reopen")
    assert kept != run["dp290"]
    assert res["after"]["list"] == kept
    assert res["after"]["pane"] == kept
    assert res["reset"]["list"] == run["dp290"]
    assert res["reset"]["pane"] == run["dp290"]


def test_topic_rows_are_single_spaced(run: dict) -> None:
    heights = _part(run, "rows")["heights"]
    assert heights, "no helpTopicRow"
    assert max(heights) <= run["dp26"], heights


def test_whole_book_opens_with_only_the_open_topics_chapter_unfolded(run: dict) -> None:
    opened = _part(run, "folding")["opened"]
    current = opened["current"]
    assert current
    assert len(opened["chapters"]) == 9
    assert {c for c, f in opened["folded"].items() if not f} == {current}
    assert _shown_chapters(opened) == {current}


def test_expand_all_and_collapse_all(run: dict) -> None:
    res = _part(run, "folding")
    assert res["buttons_whole_book"] == [True, True]
    assert not any(res["expanded"]["folded"].values())
    assert len(res["expanded"]["topics"]) == run["book"]
    assert all(res["collapsed"]["folded"].values())
    assert res["collapsed"]["topics"] == []
    assert len(res["collapsed"]["chapters"]) == 9
    assert res["buttons_area"] == [False, False]


def test_clicking_a_chapter_heading_toggles_it(run: dict) -> None:
    res = _part(run, "folding")
    assert res["heads"] == 9
    cid = res["clicked_chapter"]
    assert res["toggled_open"]["folded"][cid] is False
    assert _shown_chapters(res["toggled_open"]) == {cid}
    assert res["toggled_shut"]["folded"][cid] is True
    assert res["toggled_shut"]["topics"] == []


def test_opening_a_topic_unfolds_its_chapter(run: dict) -> None:
    res = _part(run, "folding")
    shown = res["shown"]
    assert shown["currentId"] == res["show_id"]
    assert shown["folded"][res["show_chapter"]] is False
    assert res["show_id"] in [t for t, _ in shown["topics"]]


def test_search_shows_matches_in_folded_chapters_and_clearing_restores(
    run: dict,
) -> None:
    res = _part(run, "search")
    before, during, after = res["before"], res["during"], res["after"]
    assert all(before["folded"].values())
    assert during["searching"]
    matched = {c for _, c in res["results"]}
    assert len(matched) > 1, res["results"]
    # Every match is listed, though its chapter is folded.
    assert sorted(during["topics"]) == sorted(res["results"])
    # The folds themselves stay, but for the chapter of a topic the search
    # opened (opening a topic unfolds its chapter).
    for chapter, folded in before["folded"].items():
        if chapter != during["current"]:
            assert during["folded"][chapter] == folded, chapter
    assert not after["searching"]
    # Back to the folds before the search (the open topic's chapter may
    # have been unfolded by opening it).
    for chapter, folded in before["folded"].items():
        if chapter != after["current"]:
            assert after["folded"][chapter] == folded, chapter
    assert _shown_chapters(after) <= {after["current"]}


def test_a_pasted_search_lists_its_matches(run: dict) -> None:
    """The whole search arriving in one change (a paste into the empty box)
    lists the matching topics (the list came up empty)."""
    res = _part(run, "paste")
    assert res["empty_before"]
    assert res["text"] == "memory"
    assert res["results"], "no results for a pasted search"
    assert sorted(t for t, _ in res["listed"]) == sorted(res["results"])


def test_no_overwriting_binding_on_opening_and_searching(run: dict) -> None:
    assert "search" in run, run["errors"]
    assert run["binding_warnings"] == []
    assert "Overwriting binding" not in run["stderr"], run["stderr"][-2000:]
    assert not run["qml_errors"], run["qml_errors"]
