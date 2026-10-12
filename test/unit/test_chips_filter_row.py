# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Chips panel's filter row (07 S132), checked in the running program
off-screen (chips_filter_row_smoke.py, its own process and user folder):
the filter box has the whole top row and Reset and the Chip only tick sit
on the row under it, at the panel's narrowest and widest; typing filters,
Reset clears, Chip only sets the option.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

_ROOT = pathlib.Path(__file__).parents[2]
_SMOKE = "chips_filter_row_smoke.py"


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    env = dict(os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen")
    fonts = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    env.setdefault("QT_QPA_FONTDIR", fonts)
    done = proc_tree.run(
        [sys.executable, str(_ROOT / "test" / "unit" / _SMOKE)],
        cwd=_ROOT, env=env, text=True, timeout=120,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, smoke_report.explain(done)
    return json.loads(lines[0][len("RESULT "):])


@pytest.mark.parametrize("width", ["min", "start", "mid", "max"])
def test_the_box_has_the_top_row_and_the_rest_sits_under_it(
    run: dict, width: str
) -> None:
    g = run[width]
    box, reset, tick = g["box"], g["reset"], g["tick"]
    assert box["shown"] and reset["shown"] and tick["shown"]
    # The whole row: the panel's width less the column's side margins.
    assert abs(box["w"] - (g["panel"] - g["margins"])) <= 1, g
    for item in (reset, tick):
        assert item["y"] >= box["y"] + box["h"], g
        # Inside the panel, not pushed past its edge.
        assert item["x"] >= 0 and item["x"] + item["w"] <= g["panel"], g
    # Reset and the tick share the second row.
    assert reset["y"] + reset["h"] > tick["y"] and tick["y"] + tick["h"] > reset["y"], g
    # "Chip only" is never cut short: the panel's minimum leaves it its whole
    # width (D-07-SIDE-LOOK follow-up, Chips minimum 210).
    assert tick["w"] >= tick["iw"] - 1, g


def test_typing_filters_and_reset_clears(run: dict) -> None:
    assert run["all"] > 0
    assert run["typed"] == "zzzq"
    assert run["filtered"] == 0
    assert run["reset"] == ""
    assert run["after-reset"] == run["all"]


def test_chip_only_still_sets_the_option(run: dict) -> None:
    before, after = run["chip-only"]
    assert after is (not before)
