# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device Mapping Editor: a 4 px dead zone (screen pixels) before a chip, group member
or drawing move-drag starts (D-FIXLIST-B1 item 3). A press and release with
less movement only selects: nothing moves, no undo step. Past 4 px the item
follows the pointer from where it was pressed, with no jump. Real mouse
events on the off-screen editor, zoomed to 200 % so screen and map pixels
differ, in its own process (b1_drag_smoke.py).
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
    folder = tmp_path_factory.mktemp("b1_drag")
    home = tmp_path_factory.mktemp("home")
    done = proc_tree.run(
        [sys.executable, str(_HERE / "b1_drag_smoke.py"), str(folder)],
        text=True,
        timeout=120,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "USERPROFILE": str(home)},
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, smoke_report.explain(done)
    return json.loads(lines[0][len("RESULT ") :])


def test_zoomed_so_screen_and_map_pixels_differ(results: dict) -> None:
    assert results["screen_px_per_editor_px"] == pytest.approx(2.0)


@pytest.mark.parametrize(
    "case", ["chip_click", "chip_3px", "draw_click", "draw_3px", "member_3px"]
)
def test_small_press_only_selects(results: dict, case: str) -> None:
    r = results[case]
    assert r["same_nodes"], f"{case}: the item moved"
    assert r["hist_added"] == 0, f"{case}: an undo step was added"
    assert r["histAt_moved"] == 0
    assert r["selected"], f"{case}: nothing was selected"


@pytest.mark.parametrize("case", ["chip_drag", "draw_drag"])
def test_drag_starts_past_4px_without_a_jump(results: dict, case: str) -> None:
    r = results[case]
    # 3 px: still; 5 px (2.5 map px at 200 %): follows; 30 px: follows.
    (x3, y3), (x5, y5), (x30, y30) = r["seen"]
    assert (x3, y3) == (0, 0)
    assert x5 == pytest.approx(5, abs=1) and y5 == pytest.approx(0, abs=1)
    assert x30 == pytest.approx(30, abs=1) and y30 == pytest.approx(0, abs=1)
    assert not r["same_nodes"]
    assert r["hist_added"] == 1


def test_member_drag_moves_as_one_step(results: dict) -> None:
    assert results["member_found"]
    r = results["member_drag"]
    assert not r["same_nodes"]
    assert r["hist_added"] == 1


def test_no_qml_warnings(results: dict) -> None:
    assert results["warnings"] == []
