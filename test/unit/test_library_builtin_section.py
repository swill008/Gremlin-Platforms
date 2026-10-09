# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""10 S6, D-10-BUILTIN-SECTION: the real Device Library window, off-screen in
its own process (library_builtin_section_smoke.py): Keyboard and OSC are
listed after the devices under a "Built-in inputs" heading; the state filter
chips don't hide them, a search does (and the heading with them); their
right-click menu and details offer only Save, Restore, Export, Rename and
Edit Description, with no Connected / Not connected badge."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

_HERE = pathlib.Path(__file__).parent
_BUILT_INS = ["dev-0000000b", "dev-0000000c"]
_FIVE = [
    "Save to Device Library…",
    "Restore…",
    "Export…",
    "Rename… (F2)",
    "Edit Description",
]


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    out = tmp_path_factory.mktemp("dl_builtin")
    home = tmp_path_factory.mktemp("home")
    proc = subprocess.run(
        [sys.executable, str(_HERE / "library_builtin_section_smoke.py"), str(out)],
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


def test_heading_sits_between_the_sticks_and_the_built_ins(run: dict) -> None:
    got = run["list"]
    assert got["keys"][-2:] == _BUILT_INS
    assert [h["text"] for h in got["headings"]] == ["BUILT-IN INPUTS"]
    heading = got["headings"][0]["y"]
    assert got["lastStick"] < heading < got["keyboard"] < got["osc"]


def test_state_chips_never_hide_the_built_ins(run: dict) -> None:
    got = run["chips-off"]
    assert not got["filters"]["connected"]
    assert not got["filters"]["not_connected"]
    assert not got["filters"]["deleted"]
    assert got["keys"] == _BUILT_INS
    assert len(got["headings"]) == 1


def test_search_hides_them_and_the_heading(run: dict) -> None:
    none = run["search-none"]
    assert none["keys"] and not set(_BUILT_INS) & set(none["keys"])
    assert none["headings"] == []
    keyboard = run["search-keyboard"]
    assert keyboard["keys"] == ["dev-0000000b"]
    assert len(keyboard["headings"]) == 1


def test_built_in_menu_has_only_the_five_items(run: dict) -> None:
    got = run["rc-keyboard"]
    assert got["selected"] == "dev-0000000b"
    assert got["menu"].split("|") == ["Keyboard · Built-in input", *_FIVE]
    # OSC has no saved setup: nothing to restore (hidden, 01 S66).
    osc = [i for i in _FIVE if i != "Restore…"]
    assert run["rc-osc"].split("|") == ["OSC · Built-in input", *osc]


def test_built_in_details_buttons(run: dict) -> None:
    got = run["rc-keyboard"]["buttons"]
    assert got == {
        "save": True,
        "restore": True,
        "copy": False,
        "swap": False,
        "output": False,
        "exportOn": True,
        "remove": False,
    }
