# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Right-click Hide / Lock rows (D-FIXLIST-B1 item 2, 07 S137), through a
real right-click on the editor run off-screen in its own process
(b1_menu_smoke.py):

- an item's Hide and Lock rows carry the hide / lock command ids, so the
  menu offers the ☆ on them;
- clicking the row still acts on what was right-clicked;
- a Hide favourite hides the whole selection (like Ctrl+Shift+H);
- the hotspot and leader rows act on a part and stay without a command.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

_HERE = pathlib.Path(__file__).parent

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows fonts")


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> dict:
    folder = tmp_path_factory.mktemp("b1_menu")
    home = tmp_path_factory.mktemp("home")
    done = proc_tree.run(
        [sys.executable, str(_HERE / "b1_menu_smoke.py"), str(folder)],
        text=True,
        timeout=120,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "USERPROFILE": str(home)},
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, smoke_report.explain(done)
    return json.loads(lines[0][len("RESULT ") :])


def _cmds(rows: list[dict]) -> dict[str, str]:
    return {r["text"]: r["cmd"] for r in rows}


def test_no_menu_warnings(results: dict) -> None:
    assert results["warnings"] == []


@pytest.mark.parametrize(
    ("menu", "word"), [("chip", "Chip"), ("shape", "Shape"), ("multi", "Selected")]
)
def test_item_rows_are_commands(results: dict, menu: str, word: str) -> None:
    assert _cmds(results[menu]) == {f"Hide {word}": "hide", f"Lock {word}": "lock"}


def test_part_rows_stay_without_command(results: dict) -> None:
    assert results["foundTarget"]
    assert _cmds(results["hotspot"]) == {"Hide Hotspot": "", "Lock Hotspot": ""}
    assert _cmds(results["leader"]) == {"Hide Leader": "", "Lock Leader": ""}


def test_row_acts_on_item_clicked(results: dict) -> None:
    assert results["rowLock"] == {"c": True, "a": False}


def test_hide_favourite_hides_selection(results: dict) -> None:
    assert results["favRows"] == ["Hide"]
    assert results["favHide"] == {"a": True, "b": True}


# The ☆ on a toggle row needs theme/Gremlin/Menus/ContextMenu.qml to drop its
# `it.kind === "action"` condition on _starred (the lead's file).
def test_star_shows_on_hide_and_lock(results: dict) -> None:
    assert results["starHide"] and results["starLock"]
