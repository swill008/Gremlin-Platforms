# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""More of the Device Mapping Editor's background and foreground planes (07 S94,
S118, S122; D-07-BACKGROUND-PLANES), checked on the real editor off-screen
(planes_editor_more_smoke.py, its own process and user folder).

- Align and Distribute in Background mode line up and space out background
  items only; a foreground item can't join the selection there.
- Zoom (wheel, zoom to page, zoom to selection, 50% to 600%) is the same in
  both modes, and switching plane keeps the zoom and pan.
- In Foreground mode a leader end dragged near a background picture's snap
  point snaps to it, the same as to a foreground picture's.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest

_ROOT = pathlib.Path(__file__).parents[2]


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    env = dict(os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen")
    env.setdefault(
        "QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    )
    done = proc_tree.run(
        [sys.executable, str(_ROOT / "test" / "unit" / "planes_editor_more_smoke.py")],
        cwd=home,
        env=env,
        text=True,
        timeout=120,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("PLANESMORE ")]
    assert lines, done.stdout[-1500:] + done.stderr[-1500:]
    return json.loads(lines[0][len("PLANESMORE ") :])


def test_no_qml_warnings(run: dict) -> None:
    assert run["warnings"] == []


def test_background_mode_selects_only_background_items(run: dict) -> None:
    # Shift-click on a foreground item adds nothing (S118, S116).
    assert run["bg_selected"] == ["bgA", "bgB", "bgC"]
    assert run["can_align"] is True and run["can_distribute"] is True
    assert run["menu_has_align"] is True


def test_align_and_distribute_in_background_mode(run: dict) -> None:
    assert len(set(run["left_xs"])) == 1
    assert len(set(run["top_ys"])) == 1
    gap_a, gap_b = run["gaps_h"]
    assert gap_a == pytest.approx(gap_b, abs=1)
    # The foreground stays where it was and everything keeps its plane.
    assert run["fg_moved"] is False
    assert run["chip_moved"] is False
    assert run["planes_after_align"] == ["background"] * 3 + [""]


def test_zoom_is_the_same_in_both_modes(run: dict) -> None:
    fg, bg = run["zoom"]["foreground"], run["zoom"]["background"]
    assert fg == bg
    assert fg["once"] > fg["page"]
    zmin, zmax, fit = run["zoom_limits"]
    # 50% to 600% of the fitted page (S94).
    assert bg["min"] == pytest.approx(zmin, abs=0.01)
    assert bg["max"] == pytest.approx(zmax, abs=0.01)
    assert zmin / fit == pytest.approx(0.5) and zmax / fit == pytest.approx(6)
    assert bg["to_selection"][0] is True
    assert bg["to_selection"][1] > bg["page"]


def test_switching_plane_keeps_the_zoom(run: dict) -> None:
    before, mid, after = run["zoom_kept"]
    assert before == mid == after == {"zoom": 3, "pan": [-40, -30]}


def test_leader_end_snaps_to_a_background_snap_point_while_dragging(
    run: dict,
) -> None:
    assert run["plane_while_snapping"] == "foreground"
    assert run["leader_bg"]["hit"] == "to"
    assert run["leader_bg"]["during"] == [0, 0]
    # The same as a foreground picture's snap point.
    assert run["leader_fg"]["during"] == run["leader_bg"]["during"]


def test_leader_end_stays_on_a_background_snap_point_after_drop(run: dict) -> None:
    assert run["leader_bg"]["after"] == [0, 0]
    assert run["leader_bg"]["to"]["type"] == "free"
    # A foreground picture's snap point keeps the end the same way (G30).
    assert run["leader_fg"]["after"] == [0, 0]
    assert run["leader_fg"]["to"]["type"] == "free"
