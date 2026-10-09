# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Tools > History's Clear History… through the real window, off-screen
(history_clear_ui_smoke.py; 08 S12b, D-08-CLEAR-HISTORY): a red button after
Refresh; it asks first with the real count and size, Cancel the default; Clear
History leaves one red "History cleared" row whose details say nothing before
it can be restored, with no Restore or Previous/Next Change."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

_ROOT = pathlib.Path(__file__).parents[2]


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    env = dict(
        os.environ,
        USERPROFILE=str(home),
        QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1",
        HTTPS_PROXY="http://127.0.0.1:9",
    )
    result = subprocess.run(
        [sys.executable, "test/unit/history_clear_ui_smoke.py"],
        cwd=_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, result.stdout[-2000:] + result.stderr[-2000:]
    return json.loads(lines[0][len("RESULT ") :])


def test_a_red_clear_history_button_after_refresh(run: dict) -> None:
    assert run["has-button"]
    button = run["button"]
    assert button["text"] == "Clear History…"
    assert button["colour"] == run["danger"]
    assert button["after-refresh"] and button["same-row"]


def test_it_asks_first_naming_the_count_and_size(run: dict) -> None:
    assert run["asked"]
    count = run["summary"]["entries"]
    assert count >= 2
    question = run["question"]
    assert question.startswith(f"All {count} changes in History are deleted")
    assert " MB of kept copies used to restore them." in question
    assert "including the Device Library's Undo for this session" in question
    assert "Your profiles, module files and Device Library stay as they are." in (
        question
    )
    assert question.endswith("This can't be undone.")
    # 01 S140: the shared question, its red button named for the action.
    assert run["dialog-title"] == "Clear History?"
    assert run["go"] == {"text": "Clear History", "colour": run["danger"]}


def test_cancel_is_the_default(run: dict) -> None:
    assert run["cancel-focused"]
    after = run["after-enter"]
    assert not after["open"]
    assert after["rows"] == run["rows-before"]
    assert after["entries"] == run["summary"]["entries"]


def test_clearing_leaves_one_red_history_cleared_row(run: dict) -> None:
    after = run["after-clear"]
    assert not after["open"]
    assert after["rows"] == 1
    assert after["module-file"], "the module file itself stays"
    assert run["row"]["found"]
    assert run["row"]["title-colour"] == run["danger-text"]


def test_picking_it_explains_with_no_restore(run: dict) -> None:
    picked = run["picked"]
    assert picked["selected"]
    assert picked["note-shown"]
    assert "Nothing before it can be restored" in picked["note"]
    assert "deleted" in picked["what"]
    for name in ("restore-before", "restore-after", "previous", "next"):
        assert not picked[name], name


def test_the_search_box_is_the_shared_one(run: dict) -> None:
    # 01 S141: Ctrl+F goes to it, "Nothing matches" under it, Esc clears it
    # (and the window stays open).
    search = run["search"]
    assert search["shared"]
    assert search["ctrl-f"]
    assert search["rows"] == 0
    assert search["line-shown"] and search["line"] == "Nothing matches"
    after = search["after-esc"]
    assert after["text"] == ""
    assert after["rows"] >= 1
    assert after["window-open"]
