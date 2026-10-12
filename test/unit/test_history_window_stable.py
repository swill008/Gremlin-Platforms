# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The History window keeps still (08 S28, S28a, S30a, S35, S38, S39a;
D-TESTLIST-1 13), off-screen (history_stable_smoke.py): day headings, a
folded run, the plain-words effect with Show full before/after, the
Restore to before / after controls; a restore tags its entry without a new
row, a change saved meanwhile waits behind "N new changes · Show", and the
rows, scroll and selection stay through all of it."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

_ROOT = pathlib.Path(__file__).parents[2]


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    env = dict(
        os.environ,
        USERPROFILE=str(home),
        QT_QPA_PLATFORM="offscreen",
        HTTPS_PROXY="http://127.0.0.1:9",
        PYTHONFAULTHANDLER="1",  # a crash prints every thread's stack
    )
    args = [sys.executable, "test/unit/history_stable_smoke.py"]
    log = home / "smoke-output.txt"
    try:
        result = proc_tree.run(args, cwd=_ROOT, env=env, text=True, timeout=180)
    except subprocess.TimeoutExpired as hung:
        pytest.fail(smoke_report.explain(hung, log))
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, smoke_report.explain(result, log)
    return json.loads(lines[0][len("RESULT ") :])


def test_day_headings_and_a_folded_run(run: dict) -> None:
    # Fold Stick's three saves are one row on top.
    assert run["head-size"] == 3
    assert "Fold Stick" in run["head-title"]
    assert run["today-heading"] is True
    assert run["toggle-visible"] is True
    assert run["count-open"] == run["place-after-show"]["count"] + 2


def test_detail_says_what_restoring_does(run: dict) -> None:
    assert run["effect"]
    assert run["restore-text"] == "Restore to before this change"
    assert run["restore-enabled"] is True
    assert "Restore to after this change" in run["after-link"]
    assert run["full-shown-at-first"] is False
    assert run["full-shown-after-link"] is True


def test_a_restore_tags_the_entry_and_nothing_moves(run: dict) -> None:
    assert run["file-after-restore"] == {"buttons": [1, 2]}
    assert run["place-after-restore"] == run["place-before"]
    assert run["tag"].startswith("Restored · ")
    assert run["new-after-restore"] == 0
    assert run["message"]


def test_a_new_change_waits_behind_the_bar(run: dict) -> None:
    assert run["place-after-new"] == run["place-before"]
    assert run["new-count"] == 1
    assert run["bar-visible"] is True
    assert run["bar-text"].startswith("1 new change · ")
    assert ">Show<" in run["bar-text"]


def test_show_adds_it_and_keeps_the_selection(run: dict) -> None:
    after = run["place-after-show"]
    assert after["count"] == run["place-before"]["count"] + 1
    assert after["selected"] == run["place-before"]["selected"]
    assert run["bar-after-show"] is False
