# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Button Map on the shared pieces (01 S140-S143; 07 S20, S61, S80,
S102): button_map_shared_pieces_smoke.py drives the window off-screen with
real key and mouse events, in its own process."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

_HERE = pathlib.Path(__file__).parent


@pytest.fixture(scope="module")
def seen(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("bmap_pieces")
    run = subprocess.run(
        [sys.executable, str(_HERE / "button_map_shared_pieces_smoke.py"),
         str(home / "out")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=150,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "PYTHONIOENCODING": "utf-8",
             "USERPROFILE": str(home)},
    )
    lines = run.stdout.splitlines()
    assert "done" in lines, run.stdout[-2000:] + run.stderr[-2000:]
    out: dict = {
        "warnings": [line for line in lines if line.startswith(("WARN", "ERROR"))],
    }
    for line in lines:
        if line.startswith("RESULT "):
            _, name, value = line.split(" ", 2)
            out[name] = json.loads(value)
    return out


def test_no_qml_warnings(seen: dict) -> None:
    assert seen["warnings"] == []


def test_save_says_so_on_the_message_line(seen: dict) -> None:
    # 07 S20, 01 S142: plain, on the window's line, no box to close.
    assert seen["save-message"] == (
        "messageLine|Saved to the module file.|false|true|false")


def test_the_undo_bar_takes_the_change_back(seen: dict) -> None:
    # 01 S143: shown while editing; a click on Undo; Redo then available.
    assert seen["undo-bar"] == [True, True, 1, 0, True]


def test_reset_layout_asks_the_shared_question(seen: dict) -> None:
    # 07 S61, 01 S140: Enter cancels; only the red button resets.
    reset = seen["reset"]
    assert reset["asked"][0] == "Reset the layout?"
    assert reset["asked"][2] == "Ctrl+Z brings the layout back."
    assert reset["asked"][3] == "Reset Layout"
    assert reset["enter"] == [True, True]
    assert reset["red"] == 0


def test_template_delete_is_red_and_asks(seen: dict) -> None:
    # 07 S80, 01 S140: Esc cancels; the red button deletes.
    gone = seen["template-delete"]
    assert gone["red"] is True
    assert gone["asked"] == ["Delete template “Smoke T”?",
                             "Layouts made from it are not changed.",
                             "This can't be undone.", "Delete Template"]
    assert gone["esc"] == [True, "Smoke T"]
    assert gone["deleted"] == ""


def test_options_library_delete_is_red_and_asks(seen: dict) -> None:
    gone = seen["library-delete"]
    assert gone["red"] is True
    assert gone["asked"][3] == "Delete Template"
    assert gone["enter"] == [True, "Lib T"]
    assert gone["deleted"] == ""
    assert gone["heading"] is True


def test_choosers_open_in_the_remembered_folder(seen: dict) -> None:
    # 01 S143: pictures, exports and templates each remember their folder.
    assert seen["picker"] == ["picture", "picture", "export save", "template", True]


def test_layers_search_is_the_shared_box(seen: dict) -> None:
    # 07 S102, 01 S141: Ctrl+F goes to it, Esc clears it.
    assert seen["layers-search"] == [True, "rect", "", "searchClear", "searchField"]
