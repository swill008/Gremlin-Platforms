# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""D-02-INPUT-TESTER (contract 9b, 9d page part, 9e): the HidHide page's
Input Tester button, Add Input Tester to the list, Update path, the last
result line and the game path warning, in the real program off-screen
(hidhide_tester_page_smoke.py: fake HidHide driver, injected launcher, fake
process list, real mouse clicks); and gremlin.process_paths on its own."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

from gremlin import process_paths

_HERE = pathlib.Path(__file__).parent
LIVE = r"D:\StarCitizen\LIVE\Bin64\StarCitizen.exe"
PTU = r"D:\StarCitizen\PTU\Bin64\StarCitizen.exe"


# process_paths ---------------------------------------------------------------

def test_a_game_running_from_another_folder_is_named_once() -> None:
    games = [{"name": "Star Citizen", "path": LIVE}]
    images = [LIVE, PTU, PTU.lower(), r"C:\Windows\explorer.exe"]
    assert process_paths.game_path_problems(games, images) == [
        f"StarCitizen.exe is running from {PTU}, which isn't on the list"
    ]


def test_the_listed_game_itself_is_no_problem() -> None:
    games = [{"path": LIVE}]
    assert process_paths.game_path_problems(games, [LIVE.upper()]) == []
    assert process_paths.game_path_problems([], [PTU]) == []


def test_an_old_tester_entry_is_named_with_both_paths() -> None:
    old = r"C:\Old\Gremlin Input Tester.exe"
    new = r"C:\Program Files\Gremlin-Platforms\Gremlin Input Tester.exe"
    assert process_paths.tester_path_problem([LIVE, old], new) == (
        f"The Input Tester on the list is an old copy ({old}); "
        f"the current one is {new}"
    )
    assert process_paths.old_tester_entry([LIVE, old], new) == old


def test_the_current_tester_or_none_is_no_problem() -> None:
    new = r"C:\Program Files\Gremlin-Platforms\Gremlin Input Tester.exe"
    assert process_paths.tester_path_problem([LIVE, new.lower()], new) == ""
    assert process_paths.tester_path_problem([LIVE], new) == ""
    old = r"C:\Old\Gremlin Input Tester.exe"
    assert process_paths.tester_path_problem([old], "") == ""


@pytest.mark.skipif(sys.platform != "win32", reason="Windows process list")
def test_running_images_includes_this_python() -> None:
    images = {os.path.normcase(p) for p in process_paths.running_images()}
    assert os.path.normcase(os.path.realpath(sys.executable)) in images or any(
        p.endswith("python.exe") for p in images
    )


# The page, in the real program ----------------------------------------------

@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("hh_tester_home")
    (home / "Gremlin Platforms").mkdir()
    work = tmp_path_factory.mktemp("hh_tester_work")
    proc = subprocess.run(
        [sys.executable, str(_HERE / "hidhide_tester_page_smoke.py"), str(work)],
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
            # Without fonts no text is laid out (the wrap checks).
            "QT_QPA_FONTDIR": os.path.join(
                os.environ.get("WINDIR", "C:/Windows"), "Fonts"
            ),
        },
    )
    results: dict = {"work": str(work)}
    for line in proc.stdout.splitlines():
        if line.startswith("RESULT "):
            _tag, name, value = line.split(" ", 2)
            results[name] = json.loads(value)
    assert "done" in proc.stdout, proc.stdout[-3000:] + proc.stderr[-3000:]
    assert results.get("open") is True, proc.stdout[-3000:] + proc.stderr[-3000:]
    return results


def _tester(run: dict) -> str:
    return str(pathlib.Path(run["work"]) / "new" / "Gremlin Input Tester.exe")


def test_page_names_the_ptu_copy_and_the_old_tester(run: dict) -> None:
    state = run["open-state"]
    assert state["games"] == [
        f"StarCitizen.exe is running from {PTU}, which isn't on the list"
    ]
    assert len(state["tester"]) == 1 and _tester(run) in state["tester"][0]
    assert "old copy" in state["tester"][0]
    assert state["update"] is True and state["add"] is False
    assert state["last"] == ["Last Status: never run"]


def test_update_path_replaces_the_old_entry(run: dict) -> None:
    res = run["update"]
    assert res["clicked"] is True
    assert _tester(run) in res["whitelist"]
    assert not any("old" in p.lower() and "Input Tester" in p for p in res["whitelist"])
    assert res["tester"] == [] and res["onList"] is True


def test_add_input_tester_puts_it_in_hidhides_list(run: dict) -> None:
    res = run["add"]
    assert _tester(run) not in res["before"]
    assert res["clicked"] is True
    assert _tester(run) in res["whitelist"]
    assert res["addShown"] is False


def test_input_tester_button_calls_the_launcher_and_shows_its_message(
    run: dict,
) -> None:
    res = run["launch"]
    assert res["clicked"] is True and res["launches"] == 1
    assert res["message"] and "isn't built" in res["message"][0]


def test_last_result_line_comes_from_result_json(run: dict) -> None:
    """02 S112 (HS1, HS3): "Last Status:", the result's ✗ and summary (the
    suffix depends on HidHide changes made earlier in the run)."""
    assert len(run["result"]) == 1
    assert run["result"][0].startswith(
        "Last Status: ✗ Problem, 03:14 · "
        "1 stick visible that should be hidden"
    )


@pytest.mark.parametrize("size", ["wide", "narrow"])
def test_last_status_has_its_own_row_and_wraps(run: dict, size: str) -> None:
    """02 S112 (HS2): under the buttons, full width, wrapped, never cut off;
    at a narrow window the whole text shows over more lines."""
    res = run[f"layout-{size}"]
    assert res is not None
    assert res["wrapMode"] == "wrap" and res["elide"] == "none"
    assert res["truncated"] is False
    assert res["below"] is True
    if size == "narrow":
        assert res["lineCount"] > 1
        assert res["height"] > run["layout-wide"]["height"]


def test_a_result_older_than_the_last_hidhide_change_says_so(run: dict) -> None:
    """02 S112 (HS4): written before the last HidHide change: the suffix;
    written after it: none."""
    assert run["stale"] == [
        "Last Status: ✗ Problem, 03:14 · "
        "1 stick visible that should be hidden"
        " (before the last HidHide change: run the Input Tester again)"
    ]
    assert run["fresh"] == ["Last Status: ✓ Pass, 06:30"]


def test_result_line_suffix_only_when_written_before_the_change() -> None:
    """02 S112 (HS4) on the line builder itself."""
    import datetime

    from gremlin.ui import hidhide

    res = {"written": "2026-10-10T08:06:00", "verdict": "fail", "summary": "x"}
    line = "✗ Problem, 08:06 · x"
    later = datetime.datetime(2026, 10, 10, 8, 30)
    earlier = datetime.datetime(2026, 10, 10, 8, 0)
    assert hidhide._result_line(res, later) == (line + hidhide.STALE_RESULT, True)
    assert hidhide._result_line(res, earlier) == (line, True)
    assert hidhide._result_line(res, None) == (line, True)
    assert hidhide._result_line(None, later) == ("never run", False)
