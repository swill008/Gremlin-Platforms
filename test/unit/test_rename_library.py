# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""01 S135 (D-01-ONE-RENAME) in the Device Library end to end: the real
program off-screen (rename_library_smoke.py) with real key and mouse
events. F2 or the rename button opens the shared Rename box with the cursor
in it and the whole name selected, so typing replaces it; Enter or a click
away saves once (10 S7: through the Library's own rename); Esc cancels; an
empty or unchanged name is not saved and the old name stays."""

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
    home = tmp_path_factory.mktemp("rename_library_home")
    (home / "Gremlin Platforms").mkdir()
    proc = subprocess.run(
        [sys.executable, str(_HERE / "rename_library_smoke.py")],
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
        },
    )
    results: dict = {"errors": [], "calls": None}
    for line in proc.stdout.splitlines():
        if line.startswith("RESULT "):
            _tag, name, value = line.split(" ", 2)
            results[name] = json.loads(value)
        elif line.startswith("ERROR"):
            results["errors"].append(line)
        elif line.startswith("CALLS "):
            results["calls"] = json.loads(line[6:])
    assert "done" in proc.stdout, proc.stdout[-3000:] + proc.stderr[-3000:]
    return results


def test_runs_without_errors(run: dict) -> None:
    assert run["errors"] == []
    assert run["open"]["name"]


def test_library_uses_the_shared_rename_box() -> None:
    # S135: one shared Rename box, not a TextField of the Library's own.
    qml = (_HERE.parents[1] / "qml" / "WindowDeviceLibrary.qml").read_text("utf-8")
    assert "RenameField {" in qml
    assert "finishRename" not in qml


def test_f2_opens_focused_with_the_whole_name_selected(run: dict) -> None:
    res = run["f2"]
    assert res["open"] is True
    assert res["focused"], "F2 did not put the cursor in the Rename box"
    assert res["text"] == run["open"]["name"]
    assert res["selected"] == run["open"]["name"]


def test_typing_replaces_the_name(run: dict) -> None:
    assert run["typed"]["text"] == "alpha"


def test_enter_saves_once(run: dict) -> None:
    res = run["enter"]
    key = run["open"]["key"]
    assert res["calls"] == [[key, "alpha"]]
    assert res["name"] == "alpha"
    assert res["open"] is False
    assert res["visible"] is True


def test_click_away_saves_once(run: dict) -> None:
    res = run["click-away"]
    key = run["open"]["key"]
    assert res["calls"] == [[key, "alpha"], [key, "beta"]]
    assert res["name"] == "beta"
    assert res["open"] is False


def test_esc_cancels(run: dict) -> None:
    res = run["esc"]
    assert len(res["calls"]) == 2
    assert res["name"] == "beta"
    assert res["open"] is False
    assert res["visible"] is True


def test_empty_keeps_the_old_name(run: dict) -> None:
    res = run["empty"]
    assert res["typed"] == ""
    assert len(res["calls"]) == 2
    assert res["name"] == "beta"
    assert res["open"] is False


def test_unchanged_is_not_saved(run: dict) -> None:
    res = run["unchanged"]
    assert len(res["calls"]) == 2
    assert res["name"] == "beta"
    assert res["open"] is False


def test_rename_button_opens_it_the_same_way(run: dict) -> None:
    res = run["button"]
    assert res["focused"]
    assert res["selected"] == "beta"
    assert len(res["calls"]) == 2
