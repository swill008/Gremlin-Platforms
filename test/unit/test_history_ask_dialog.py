# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""08 S45a (AD6), in the History window off-screen
(history_ask_dialog_smoke.py): Restore of a whole profile whose folder is
outside the profiles folder and the profile's own folder asks first with
the shared question, its button "Write Here" in red; Cancel writes
nothing, Write Here writes the copy there."""

from __future__ import annotations

import json
import os
import pathlib
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
    )
    result = proc_tree.run(
        [sys.executable, "test/unit/history_ask_dialog_smoke.py"],
        cwd=_ROOT,
        env=env,
        text=True,
        timeout=120,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, smoke_report.explain(result)
    return json.loads(lines[0][len("RESULT ") :])


def test_the_change_is_listed_and_restore_asks_first(run: dict) -> None:
    assert run["in-list"] is True
    assert run["first-confirm"] == "Restore"
    assert run["first-clicked"] is True


def test_an_outside_folder_is_asked_about_with_write_here_in_red(run: dict) -> None:
    ask = run["ask"]
    assert ask["visible"] is True
    assert ask["title"] == "Restore?"
    # Glossary line 45, worded by history_model.restore.
    assert ask["message"] == (
        f"Write the restored profile to {run['outside']}? It is outside your "
        "profiles folder and the profile's own folder."
    )
    assert ask["confirm"] == "Write Here"
    assert ask["destructive"] is True
    assert ask["button-highlighted"] is False
    assert ask["border-is-danger"] is True


def test_nothing_is_written_while_asking(run: dict) -> None:
    assert run["written-while-asking"] == []


def test_cancel_writes_nothing(run: dict) -> None:
    assert run["cancel-clicked"] is True
    assert run["gate-after-cancel"] is False
    assert run["written-after-cancel"] == []
    assert run["message-after-cancel"] == ""


def test_write_here_writes_the_copy(run: dict) -> None:
    assert run["ask-again"]["confirm"] == "Write Here"
    assert run["write-clicked"] is True
    assert run["gate-after-write"] is False
    names = run["written-after-write"]
    assert len(names) == 1 and names[0].startswith("victim (history ")
    assert names[0].endswith(" before).xml")
    assert run["message-after-write"].startswith("Written as ")
