# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""01 S134 (D-01-LEAVE-TEXT) for the Button Map's rename boxes (saved style
and template renames in Options > Library, the template rename in Manage
Templates), end to end: the real program off-screen with the program-wide
leave-text owner in place (leave_text_button_map_smoke.py), real clicks and
keys. These boxes have no cancel, so a click away or Esc saves the rename
as Enter does, ends rename mode, and a rename is saved once."""

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
    home = tmp_path_factory.mktemp("leave_text_bmap_home")
    (home / "Gremlin Platforms").mkdir()
    proc = subprocess.run(
        [sys.executable, str(_HERE / "leave_text_button_map_smoke.py")],
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
    results: dict = {"errors": []}
    for line in proc.stdout.splitlines():
        if line.startswith("RESULT "):
            _tag, name, value = line.split(" ", 2)
            results[name] = json.loads(value)
        elif line.startswith("ERROR"):
            results["errors"].append(line)
    assert "done" in proc.stdout, proc.stdout[-3000:] + proc.stderr[-3000:]
    return results


def _left_and_saved(res: dict) -> None:
    assert res["row"] and res["shown"] and res["focused"], res
    assert res["focus"] is False
    assert res["renaming"] == ""
    assert res["window"] is True


def test_runs_without_errors(run: dict) -> None:
    assert run["errors"] == []


@pytest.mark.parametrize("how", ["click-away", "esc", "enter"])
def test_library_style_rename_saved_once(run: dict, how: str) -> None:
    res = run[f"style-{how}"]
    _left_and_saved(res)
    old, new = {"click-away": ("Style A", "Style B"), "esc": ("Style B", "Style C"),
                "enter": ("Style C", "Style D")}[how]
    assert res["names"] == [new]
    assert res["calls"] == [[old, new]]


@pytest.mark.parametrize("how", ["click-away", "esc", "enter"])
def test_library_template_rename_saved_once(run: dict, how: str) -> None:
    res = run[f"lib-template-{how}"]
    _left_and_saved(res)
    new = {"click-away": "Tmpl B", "esc": "Tmpl C", "enter": "Tmpl D"}[how]
    assert new in res["names"]
    assert not any(n.startswith("Tmpl") and n != new for n in res["names"])
    # Saved twice would try the old name again and say the rename failed.
    assert res["failed"] is False


@pytest.mark.parametrize(
    "how",
    [
        "esc",
        "enter",
        "click-away",
    ],
)
def test_manage_templates_rename_saved_once(run: dict, how: str) -> None:
    res = run[f"dlg-template-{how}"]
    _left_and_saved(res)
    old, new = {"esc": ("Esc A", "Esc B"), "enter": ("Enter A", "Enter B"),
                "click-away": ("Away A", "Away B")}[how]
    assert new in res["names"] and old not in res["names"]
    assert res["failed"] is False
    # Esc only leaves the box: the dialog (closed by Esc) stays open.
    assert res["open"] is True
