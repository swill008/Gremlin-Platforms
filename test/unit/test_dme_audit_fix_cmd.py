# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device Mapping Editor menu bar audit fixes (FIX-CMD), in the real window off-screen
(dme_audit_fix_cmd_smoke.py in its own process):

- Esc stops drawing whatever holds the keyboard (07 S134, G45): Insert ›
  Stop Drawing has its own Shortcut, on only while a draw tool is active, so
  it never clashes with Esc leaving Background mode (S113).
- A greyed Move to Background / Foreground row gives the right-click menu's
  reason (RigCommands.whyDisabled, S121).
- The table cell rows grey out when the table target is stale (another
  table's row, a removed extra cell), in the menu bar and the right-click menu.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest

_HERE = pathlib.Path(__file__).parent

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows fonts")


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    done = proc_tree.run(
        [sys.executable, str(_HERE / "dme_audit_fix_cmd_smoke.py")],
        text=True,
        timeout=120,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "USERPROFILE": str(home)},
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, done.stdout[-2000:] + done.stderr[-2000:]
    out = json.loads(lines[0][len("RESULT ") :])
    assert "traceback" not in out, out
    return out


def test_esc_stops_drawing_started_from_the_menu_bar(results: dict) -> None:
    r = results["esc_menu"]
    assert r["tool"] == "rect", r
    assert "RigPointerArea" not in r["focus"], r
    assert r["after"] == "", r


def test_esc_on_the_map_still_stops_drawing(results: dict) -> None:
    r = results["esc_map"]
    assert "RigPointerArea" in r["focus"], r
    assert (r["after"], r["draft"]) == ("", 0), r


def test_esc_in_background_mode_stops_drawing_first(results: dict) -> None:
    r = results["esc_bg"]
    assert r["first"] == {"tool": "", "bg": True}, r
    assert r["second"] == {"bg": False}, r


def test_greyed_plane_moves_say_why(results: dict) -> None:
    r = results["why"]
    # A chip stays in the foreground: both rows greyed.
    assert r["enabled"] == [False, False], r
    assert r["back"] and r["back"] == r["menu"][0], r
    assert r["front"] == "Already in the foreground" == r["menu"][1], r
    assert r["other"] == "", r


def test_stale_table_target_greys_the_cell_rows(results: dict) -> None:
    r = results["stale"]
    assert r["valid"] == {
        "cell.free": True,
        "cell.independent": True,
        "cell.place.left": True,
        "table.deleteCell": False,
    }, r
    assert not any(r["bar"].values()), r
    menu = dict((t, e) for t, e in r["menu"])
    for text in (
        "Free position",
        "Independent of table",
        "Delete This Cell",
        "Place Across",
        "Place Down",
    ):
        assert menu[text] is False, (text, r["menu"])
    assert menu["Spawn Empty Cell"] is True
    assert r["staleExtra"] is False, r


def test_no_qml_warnings(results: dict) -> None:
    assert results["warnings"] == []
