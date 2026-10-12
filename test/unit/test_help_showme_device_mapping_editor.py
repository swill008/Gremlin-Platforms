# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""07 S126 (D-07-PLANES-FOLLOWUP Q1a): Help's Show me › links into the
Device Mapping Editor window (show:devicemappingeditor/<name>) go through Main's own
Help link handler: checked without the window open, the window opened on a device,
"Edit the map to see this" outside Edit, and the banner
(Background mode) and the Background row (Layers, Foreground mode) pulsed
while editing; the removed switch (dmePlaneSwitch) is refused (07 S113).
One link per area (user 2026-10-11): each menu's title in the menu bar
(File, Edit, View, Format and Help also outside Edit; Insert, Arrange and
Leader only while editing), the Chips and Layers side panels brought out,
and Properties under Layers ("Select an item to see Properties" with
nothing selected).
Runs help_showme_device_mapping_editor_smoke.py off-screen in its own
process with a fresh user folder.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SMOKE = _ROOT / "test" / "unit" / "help_showme_device_mapping_editor_smoke.py"
_FREE_MENUS = (
    "dmeMenuFile", "dmeMenuEdit", "dmeMenuView", "dmeMenuFormat", "dmeMenuHelp"
)
_EDIT_MENUS = ("dmeMenuInsert", "dmeMenuArrange", "dmeMenuLeader")
_PLACES = ("chipsSide", "layersSide", "propsPanel", "dmeBgBanner", "dmeBgRow")
_NAMES = (*_FREE_MENUS, *_EDIT_MENUS, *_PLACES)
_EDIT = "Edit the map to see this"
_SELECT = "Select an item to see Properties"


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    env = dict(
        os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1", PYTHONIOENCODING="utf-8",
    )
    result = proc_tree.run(
        [sys.executable, str(_SMOKE)], cwd=_ROOT, env=env,
        text=True, encoding="utf-8", errors="replace", timeout=150,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, smoke_report.explain(result)
    out = json.loads(lines[-1][len("RESULT "):])
    assert not out["errors"], out["errors"]
    return out


def test_links_check_without_the_window(run: dict) -> None:
    for name in _NAMES:
        assert run["check"][name] == "", name
    assert run["check"]["noSuchThing"], "a made-up place is accepted"
    # 07 S113, S126: the Foreground | Background switch is gone.
    assert run["check"]["dmePlaneSwitch"], "the removed switch is accepted"


def test_not_editing_opens_the_window_and_says_edit_first(run: dict) -> None:
    assert run["opened"], "Show me didn't open the Device Mapping Editor"
    assert run["device"], "the Device Mapping Editor opened on no device"
    assert run["closed"] == _EDIT
    assert run["message"] == _EDIT
    for name in (*_EDIT_MENUS, *_PLACES):
        got = run["not_editing"][name]
        assert got["why"] == _EDIT, (name, got)
        assert not got["pulsed"], (name, got)


def test_not_editing_pulses_the_menus_that_work_outside_edit(run: dict) -> None:
    for name in _FREE_MENUS:
        got = run["not_editing"][name]
        assert got["why"] == "", (name, got)
        assert got["pulsed"], (name, got)
        # The pulse is on that menu's title in the bar.
        assert got["text"] and got["text"] == got["title"], (name, got)


def test_properties_with_nothing_selected_says_select(run: dict) -> None:
    got = run["props_unselected"]
    assert got["why"] == _SELECT, got
    assert not got["pulsed"], got


def test_editing_pulses_each_place(run: dict) -> None:
    got = run["editing"]
    for name in _NAMES:
        assert got[name]["why"] == "", (name, got[name])
        assert got[name]["pulsed"], (name, got[name])
    assert got["dmeBgBanner"]["plane"] == "background"
    assert got["dmeBgRow"]["plane"] == "foreground"
    assert got["dmeBgRow"]["layers"]
    for name in (*_FREE_MENUS, *_EDIT_MENUS):
        bar = got[name]
        assert bar["text"] and bar["text"] == bar["title"], (name, bar)
    # Chips comes out, in the foreground (it folds in Background mode, 07 S130).
    assert got["chipsSide"]["chips"] and got["chipsSide"]["plane"] == "foreground"
    assert got["layersSide"]["layers"]
    # Properties hidden and Layers folded before: both brought out.
    assert got["propsPanel"]["layers"] and got["propsPanel"]["props"]
