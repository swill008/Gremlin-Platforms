# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Device Pack window, off-screen (device_pack_window_smoke.py).

Export lists the device's modes (all ticked) and takes a name and a note.
Import shows who made the pack, keeps its list below Open All when every
section is open (it used to draw over the buttons), warns before it
replaces anything (with the option to create missing Logical Device
inputs), and offers Undo Import afterwards.
"""

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
        HTTPS_PROXY="http://127.0.0.1:9",
    )
    args = [sys.executable, "test/unit/device_pack_window_smoke.py"]
    if os.environ.get("GREMLIN_SHOT"):
        args.append(os.environ["GREMLIN_SHOT"])
    result = subprocess.run(
        args,
        cwd=_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, result.stdout[-2000:] + result.stderr[-2000:]
    return json.loads(lines[0][len("RESULT ") :])


def test_export_lists_the_modes_and_takes_notes(run: dict) -> None:
    assert run["export-modes"] == [
        {"name": "Combat", "count": 1},
        {"name": "Default", "count": 2},
    ]
    assert run["export-options"] == {
        "modes": ["Default"],
        "author": "Sam",
        "note": "My setup",
    }
    assert run["show-folder-hidden"] is True


def test_import_shows_who_made_it(run: dict) -> None:
    assert run["notes"].startswith("By Sam")
    assert run["notes"].endswith("My setup")
    assert run["sections"][:3] == ["Input module", "Map settings", "Wires"]


def test_the_list_stays_in_its_own_area(run: dict) -> None:
    assert run["list-below-buttons"] is True
    assert run["import-below-list"] is True


def test_the_warning_says_what_is_replaced(run: dict) -> None:
    warning = run["warning"]
    assert "Import replaces these on pJoy Pro:" in warning
    assert (
        "The wires and actions of pJoy Pro in Default: 3 here, 2 from the pack."
        in warning
    )
    assert "Logical Device inputs that don't exist here: Button 9" in warning
    assert "The previous module file is kept in the imported folder." in warning
    assert "The profile changes on disk only when you save it." in warning
    assert run["create-logical-shown"] is True


def test_replace_then_undo(run: dict) -> None:
    assert "Replaced the wires of pJoy Pro in Default" in run["status-after"]
    assert run["undo-shown"] is True
    assert run["default-after"] == [1, 5]
    assert run["logical-created"] is True
    assert run["default-undone"] == [1, 3, 5]
    assert run["status-undone"].startswith("Undid the import.")
    assert run["undo-hidden"] is True
