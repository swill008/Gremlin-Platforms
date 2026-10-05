# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Button Map's Options pane, checked in the running program off-screen
(button_map_options_pane_smoke.py, its own process and user folder).

- An Options tool on the top row (hidden at first); Edit > Button Map
  Options... opens the pane, on the live map too, docked under the top row.
- The groups down the left, the chosen group's settings on the right.
- A setting changed in the pane is kept at once; the group shown is kept.
- Library shows the saved styles and templates.
- Joined to its tab, as wide as its settings need; its right edge makes it
  wider (kept).
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
        os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen",
        HTTPS_PROXY="http://127.0.0.1:9",
    )
    fonts = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    env.setdefault("QT_QPA_FONTDIR", fonts)
    script = _ROOT / "test" / "unit" / "button_map_options_pane_smoke.py"
    done = subprocess.run(
        [sys.executable, str(script)],
        cwd=_ROOT, env=env, capture_output=True, text=True, timeout=120,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, done.stdout[-1500:] + done.stderr[-1500:]
    return json.loads(lines[0][len("RESULT "):])


def test_the_menu_opens_the_pane_under_the_top_row(run: dict) -> None:
    assert run["tool"] == ["top", False]
    assert run["menu"] is True
    assert run["open"] == [True, True]
    assert abs(run["under-top-row"]) <= 1
    assert run["at-tab"] is True
    assert run["narrower"] is True


def test_groups_and_their_settings(run: dict) -> None:
    assert run["groups"] == [
        "labels", "editing", "autosave", "view", "colours", "library"]
    assert run["labels-rows"] == [
        "chip-text", "description-first", "several-actions", "unbound"]
    assert len(run["editing-rows"]) == 6
    assert run["library"] is True


def test_a_change_is_kept_and_so_is_the_group(run: dict) -> None:
    before, now, saved = run["switch"]
    assert now is (not before) and saved is now
    assert run["kept-group"] == "editing"


def test_a_tab_dragged_off_its_row_floats(run: dict) -> None:
    assert run["floated"] == [True, True, "top"]
    assert run["title"] == [True, True, True, True]
    assert run["near-drop"] == [True, True]
    assert run["tab-mark"] is True


def test_a_floating_panel_moves_and_resizes(run: dict) -> None:
    assert run["moved"] == [-50, 30]
    assert run["corner"] == [40, 30]
    # The left edge: further left and wider by as much.
    assert run["left-edge"] == [-30, 30]
    assert run["locked-still"] is True


def test_closing_keeps_it_floating_where_it_was(run: dict) -> None:
    assert run["closed"] == [False, True]
    assert run["reopened-same"] is True
    floating, place = run["kept-floating"]
    assert floating is True and '"x":' in place


def test_it_docks_again(run: dict) -> None:
    assert run["docked-bottom"] == [False, "bottom"]
    assert run["double-click"] == [False, "bottom"]
    assert run["reset"] == [False, "top"]


def test_print_area_never_floats(run: dict) -> None:
    assert run["print-area"] == [False, True]
    assert run["print-area-floating"] is False


def test_its_right_edge_resizes_it(run: dict) -> None:
    assert abs(run["wider"] - 40) <= 3
    assert '"w":' in run["size-kept"]
