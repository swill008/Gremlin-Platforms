# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""01 S140-S143 in the Device Library (10 S5, S15, S38, S53a, S54): the real
window, off-screen in its own process (library_shared_pieces_smoke.py), uses
the shared pieces. Its delete question is the shared one (Cancel focused,
Enter cancels, a click on the red button goes ahead); Delete is the red
button; the search box is the shared one (Ctrl+F, "Nothing matches", Esc
clears); the message line and the Undo / Redo bar are the shared ones;
Tidy's list is its own question; the Device Pack chooser opens in
the remembered folder."""

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
    out = tmp_path_factory.mktemp("lib_pieces")
    home = tmp_path_factory.mktemp("home")
    proc = subprocess.run(
        [sys.executable, str(_HERE / "library_shared_pieces_smoke.py"), str(out)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        cwd=str(_HERE.parents[1]),
        env={
            **os.environ,
            "QT_QPA_PLATFORM": "offscreen",
            "PYTHONUNBUFFERED": "1",
            "USERPROFILE": str(home),
        },
    )
    results: dict = {"errors": [], "warnings": [], "calls": []}
    for line in proc.stdout.splitlines():
        if line.startswith("RESULT "):
            _tag, name, value = line.split(" ", 2)
            value = json.loads(value)
            try:
                value = json.loads(value)
            except (TypeError, ValueError):
                pass
            results[name] = value
        elif line.startswith("CALLS "):
            results["calls"] = json.loads(line[6:])
        elif line.startswith("ERROR"):
            results["errors"].append(line)
        elif line.startswith("WARN"):
            results["warnings"].append(line)
    assert "done" in proc.stdout, proc.stdout[-3000:] + proc.stderr[-3000:]
    return results


def _names(run: dict) -> list[str]:
    return [c[0] for c in run["calls"]]


def test_runs_without_errors_or_warnings(run: dict) -> None:
    assert run["errors"] == []
    assert run["warnings"] == []


def test_s140_delete_asks_the_shared_question_and_enter_cancels(run: dict) -> None:
    ask = run["delete-ask"]
    assert ask["open"] is True
    assert ask["title"] == "Delete the saved setup “DCS F-16, Viper layout”?"
    assert ask["text"] == "It is removed from the Device Library."
    assert ask["last"] == "You can restore it from Tools › History."
    assert ask["action"] == "Delete Saved Setup"
    assert ask["cancelFocus"] is True
    assert run["delete-enter"] == {"open": False, "still": True}
    # Only the click on the red button deletes, once.
    assert run["calls"].count(["delete", "set-00000001"]) == 1
    go = run["delete-click-go"]
    assert go["open"] is False and go["message"] == "Deleted."
    assert go["line"] and go["link"]


def test_s140_delete_button_is_the_red_one(run: dict) -> None:
    assert run["delete-button"]["red"] is True


def test_s141_search_box_is_the_shared_one(run: dict) -> None:
    assert run["search-ctrl-f"] == {"field": True, "focus": True}
    none = run["search-none"]
    assert none["count"] == "Nothing matches" and none["shown"] and none["empty"]
    assert run["search-esc"]["text"] == ""


def test_s142_s143_message_line_and_undo_bar(run: dict) -> None:
    assert run["message-failed"] == {"failed": True, "text": "That did not work."}
    assert run["undo-bar"] == {"undo": True, "redo": True}


def test_s38_tidy_list_is_its_own_question(run: dict) -> None:
    # One confirmation (user 2026-10-09): Tidy's list is the question.
    ask = run["tidy-ask"]
    assert ask == {"open": True, "question": False,
                   "remove": "Remove from Library", "cancelFocus": True}
    # Enter cancels: Tidy closes and nothing is tidied.
    assert run["tidy-enter"]["tidyOpen"] is False
    assert "tidied" not in run["tidy-enter"]["message"]
    # A click on the red button removes, with no second question.
    go = run["tidy-go-click"]
    assert go["question"] is False and go["message"] == "Library tidied."


def test_s143_device_pack_chooser_opens_in_the_remembered_folder(run: dict) -> None:
    pick = run["picker"]
    assert pick["open"] == pick["want"]
    assert pick["save"].startswith(pick["want"] + "/")
    assert pick["save"].endswith(".zip")
    assert pick["shown"] is False
