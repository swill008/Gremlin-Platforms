# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Button Map's side panels (qml/SidePanel.qml, 07 S128-S131), checked
off-screen in a small harness (side_panel_smoke.py, its own process): two
panels, Chips (left, pinned) and Layers (right, unpinned), round a stand-in
map that narrows by each panel's takenWidth, driven by mouse clicks and
drags.

- Folded, each is a slim strip with its name written vertically.
- A strip click unfolds the panel at its width; pinned, the map narrows;
  unpinned, it is drawn over the map and a map click folds it.
- The pin and the fold arrow work; the inner edge resizes it, kept between
  its minimum and maximum width.
- Clicking one strip folds the other if unpinned (the window's wiring).
- available false hides it and it takes no width.
- changed() comes for changes made on the panel, not for direct sets.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest

_HERE = pathlib.Path(__file__).parent
_ROOT = _HERE.parents[1]
_STRIP = 22
_WIN = 1000


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    env = dict(os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen")
    done = proc_tree.run(
        [sys.executable, str(_HERE / "side_panel_smoke.py")],
        cwd=_ROOT, env=env, text=True, timeout=90,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, done.stdout[-1500:] + done.stderr[-1500:]
    out = json.loads(lines[0][len("RESULT "):])
    out["warnings"] = [ln for ln in done.stdout.splitlines() if ln.startswith("WARN ")]
    return out


def test_folded_strips_show_the_name_vertically(run: dict) -> None:
    s = run["0-folded"]
    assert run["strip"]["width"] == _STRIP
    assert run["strip"]["left"] == ["Chips", -90.0, True]
    assert run["strip"]["right"] == ["Layers", 90.0, True]
    assert s["left"]["open"] is False and s["left"]["width"] == _STRIP
    assert s["right"]["x"] == _WIN - _STRIP
    # Only the strips are taken from the map.
    assert s["map"] == [_STRIP, _WIN - 2 * _STRIP]


def test_strip_click_unfolds_pinned_beside_the_map(run: dict) -> None:
    s = run["1-left-unfolded"]["left"]
    assert s["open"] is True and s["overlay"] is False
    assert s["bodyWidth"] == 260
    assert s["takenWidth"] == _STRIP + 260
    assert run["1-left-unfolded"]["map"] == [_STRIP + 260, _WIN - 2 * _STRIP - 260]


def test_unpinned_panel_is_drawn_over_the_map(run: dict) -> None:
    r = run["2-right-overlay"]
    assert r["right"]["open"] is True and r["right"]["overlay"] is True
    # Over the map: the map keeps its width, the panel reaches into it.
    assert r["right"]["takenWidth"] == _STRIP
    assert r["map"] == run["1-left-unfolded"]["map"]
    assert r["right"]["x"] == _WIN - _STRIP - 300


def test_map_click_folds_unpinned_only(run: dict) -> None:
    r = run["3-map-click"]
    assert r["right"]["open"] is False
    assert r["left"]["open"] is True
    assert run["4-left-unpinned"]["left"]["pinned"] is False
    assert run["4-left-unpinned"]["left"]["overlay"] is True
    assert run["4-left-unpinned"]["map"] == [_STRIP, _WIN - 2 * _STRIP]
    assert run["5-map-click-left"]["left"]["open"] is False


def test_pin_and_fold_arrow(run: dict) -> None:
    s = run["6-left-pinned"]["left"]
    assert s["open"] is True and s["pinned"] is True
    s = run["7-left-fold-arrow"]["left"]
    assert s["open"] is False and s["pinned"] is True
    assert s["takenWidth"] == _STRIP


def test_inner_edge_resizes_within_min_and_max(run: dict) -> None:
    assert run["8-left-wider"]["left"]["panelWidth"] == 320
    assert run["8-left-wider"]["map"][0] == _STRIP + 320
    assert run["9-left-max"]["left"]["panelWidth"] == 400
    assert run["10-left-min"]["left"]["panelWidth"] == 180
    # The right panel's inner edge is on its left.
    assert run["11-right-wider"]["right"]["panelWidth"] == 350
    assert run["11-right-wider"]["right"]["x"] == _WIN - _STRIP - 350


def test_content_press_does_not_reach_the_map(run: dict) -> None:
    assert run["12-content-click"] == {"mapClicks": 0, "open": True}


def test_strip_click_folds_the_other_unpinned_panel(run: dict) -> None:
    r = run["13-left-strip-folds-right"]
    assert r["right"]["open"] is False
    assert r["left"]["open"] is False  # It was open: its strip folded it.


def test_changed_only_for_changes_made_on_the_panel(run: dict) -> None:
    # Unfold, then the resize release: two.
    before = run["7-left-fold-arrow"]["leftChanged"]
    assert run["8-left-wider"]["leftChanged"] - before == 2
    assert run["3-map-click"]["rightChanged"] == 2
    assert run["14-direct-sets"] == [0, 0]
    r = run["14-restored"]["left"]
    assert r["panelWidth"] == 222 and r["takenWidth"] == _STRIP + 222


def test_unavailable_hides_it_and_takes_nothing(run: dict) -> None:
    s = run["15-unavailable"]
    assert s["left"]["visible"] is False and s["left"]["takenWidth"] == 0
    assert s["map"][0] == 0
    s = run["16-available"]
    assert s["left"] == run["14-restored"]["left"]


def test_no_qml_warnings(run: dict) -> None:
    assert run["warnings"] == []
