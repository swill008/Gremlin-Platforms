# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""10 S53, S53a (D-10-STATUS-LAST): the real Device Library window, off-screen
in its own process (library_undo_ui_smoke.py), with the model's Undo/Redo
steps standing in. Edit's items read just "Undo" and "Redo", the change's
name in their tooltip; the status bar shows "Last change: <title>" or, right
after an Undo, "Undone: <title>", nothing before any change, and a long
title is cut with "…" and shown whole in its tooltip."""

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
    out = tmp_path_factory.mktemp("dl_status_last")
    home = tmp_path_factory.mktemp("home")
    proc = subprocess.run(
        [sys.executable, str(_HERE / "library_undo_ui_smoke.py"), str(out)],
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
    results: dict = {"errors": []}
    for line in proc.stdout.splitlines():
        if line.startswith("RESULT "):
            _tag, name, value = line.split(" ", 2)
            value = json.loads(value)
            try:
                value = json.loads(value)
            except (TypeError, ValueError):
                pass
            results[name] = value
        elif line.startswith("ERROR"):
            results["errors"].append(line)
    assert "done" in proc.stdout, proc.stdout[-3000:] + proc.stderr[-3000:]
    return results


def test_no_errors(run: dict) -> None:
    assert run["errors"] == []


def test_edit_reads_plain_undo_and_redo_with_the_name_in_the_tooltip(
    run: dict,
) -> None:
    tips = run["edit-tips"]
    assert "Undo (Ctrl+Z)" in tips["items"]
    assert "Redo (Ctrl+Y)" in tips["items"]
    assert tips["items"].index("Undo (Ctrl+Z)") + 1 == tips["items"].index(
        "Redo (Ctrl+Y)"
    )
    assert tips["undo"] == "Remove HID Remapper ACHB"
    assert tips["redo"] == "Copy to Another Stick"


def test_nothing_before_any_change(run: dict) -> None:
    assert run["status-none"]["text"] == ""
    assert run["status-none"]["shown"] is False


def test_last_change_after_a_change(run: dict) -> None:
    status = run["status-change"]
    assert status["text"] == "Last change: Remove HID Remapper ACHB"
    assert status["shown"] is True
    assert status["cut"] is False


def test_undone_right_after_an_undo(run: dict) -> None:
    assert run["status-undone"]["text"] == "Undone: Remove HID Remapper ACHB"
    # A second Undo: what Redo would put back now.
    assert run["status-undone-older"]["text"] == "Undone: Rename Left throttle"


def test_last_change_again_after_redo_or_a_new_change(run: dict) -> None:
    assert run["status-redone"]["text"] == "Last change: Rename Left throttle"
    assert run["status-new-after-undo"]["text"] == "Last change: Rename Right stick"


def test_a_long_title_is_cut_and_whole_in_its_tooltip(run: dict) -> None:
    status = run["status-long"]
    assert status["text"].startswith("Last change: Copy to Another Stick")
    assert status["cut"] is True
    assert status["width"] < status["full"]
    # The shared tooltip shows on hover with the whole text.
    assert status["tipShown"] is True
    assert status["tip"] == status["text"]
