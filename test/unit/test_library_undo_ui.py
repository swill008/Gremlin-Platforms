# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""10 S53-S55, D-10-UNDO-REDO: the real Device Library window, off-screen in
its own process (library_undo_ui_smoke.py), with the model's Undo/Redo steps
standing in: Edit shows "Undo <change>" (Ctrl+Z) and "Redo <change>" (Ctrl+Y)
only when there is one; the keys run them, but not while typing; Undo / Redo
buttons sit beside the right-click menu's title; after Remove the message
line ends with an Undo link; the Delete key asks to delete a saved setup or
remove a device not plugged in, and does nothing on a plugged-in stick, a
built-in input or while typing."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

_HERE = pathlib.Path(__file__).parent
_UNDO = "Undo Remove HID Remapper ACHB"
_REDO = "Redo Copy to Another Stick"


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    out = tmp_path_factory.mktemp("dl_undo_ui")
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
    results: dict = {"errors": [], "warnings": []}
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
        elif line.startswith("WARN"):
            results["warnings"].append(line)
    assert "done" in proc.stdout, proc.stdout[-3000:] + proc.stderr[-3000:]
    return results


def test_runs_without_errors_or_warnings(run: dict) -> None:
    assert run["errors"] == []
    assert run["warnings"] == []


def test_edit_shows_undo_and_redo_only_when_there_is_one(run: dict) -> None:
    """S53 and 01 S66: named items, hidden when there is nothing to do."""
    assert not any(i.startswith(("Undo", "Redo")) for i in run["edit-none"])
    assert f"{_UNDO} (Ctrl+Z)" in run["edit-undo"]
    assert not any(i.startswith("Redo") for i in run["edit-undo"])
    both = run["edit-both"]
    assert both.index(f"{_UNDO} (Ctrl+Z)") + 1 == both.index(f"{_REDO} (Ctrl+Y)")


def test_ctrl_z_and_ctrl_y_run_them_but_not_while_typing(run: dict) -> None:
    assert run["keys"] == ["undo", "redo"]
    assert run["keys-in-search"] == ["undo", "redo"]


def test_undo_and_redo_beside_the_right_click_menus_title(run: dict) -> None:
    assert run["header"]["header"] == [["Undo", True], ["Redo", True]]
    assert run["header-run"] == ["undo", "redo", "undo", "redo"]
    # Nothing to undo: the buttons are there but off (as other menus).
    assert run["header-none"] == [["Undo", False], ["Redo", False]]


def test_the_delete_key(run: dict) -> None:
    """S55: Delete… on a saved setup, Remove from Library… on a device not
    plugged in, asking first; nothing on a plugged-in stick, a built-in
    input or while a text box has the focus."""
    assert run["del-key-setup"]["open"] is True
    assert run["del-key-setup"]["title"].startswith("Delete the saved setup")
    assert run["del-key-not-connected"]["open"] is True
    assert run["del-key-not-connected"]["title"].startswith("Remove ")
    for name in ("del-key-connected", "del-key-builtin", "del-key-in-search"):
        assert run[name]["open"] is False, name


def test_the_message_line_has_an_undo_link_after_remove(run: dict) -> None:
    """S54: after Remove the line ends with Undo, which does Edit › Undo; a
    change that isn't a remove/delete has none."""
    assert run["remove-link"]["link"] is True
    assert run["remove-link"]["message"]
    click = run["remove-link-click"]
    assert click["calls"][-1] == "undo"
    assert click["calls"].count("undo") == 3
    assert click["link"] is False
    assert run["export-no-link"] is False
