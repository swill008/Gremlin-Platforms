# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Device Mapping Editor's side panels (qml/SidePanel.qml, 07 S128-S131,
D-07-SIDE-DRAWER), checked off-screen in a small harness
(side_panel_smoke.py, its own process): two panels, Chips (left, pinned)
and Layers (right, unpinned), round a stand-in map that narrows by each
panel's takenWidth, driven by mouse clicks, drags and moves.

- Folded, each is a drawer left ajar: its own frame (colour, border, the
  rounded corners on the map side) peeks 7 px out of its window edge; no
  header, no strip beside it (S129).
- Hovering the folded drawer slides it out to a slice showing its bold name
  and its pin, with a hand pointer; the slice's pin pins without opening;
  moving off slides it back. The layout doesn't move.
- A click slides it all the way out at its width; pinned and open it takes
  exactly that width from the map (no strip beside it); unpinned it is
  drawn over the map and a map click folds it.
- Folding slides it back to the ajar edge. takenWidth, the width and the
  map's place take their final value at once; only the drawer slides.
- The pin and the fold arrow work; the inner edge resizes it, kept between
  its minimum and maximum width.
- Clicking one drawer folds the other if unpinned (the window's wiring).
- available false hides it and it takes no width.
- changed() comes for changes made on the panel, not for direct sets.
- No QML warnings.
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
_EDGE = 7  # The ajar edge at 100% (Style.dp(7)).
_WIN = 1000
_HAND = 13  # Qt.PointingHandCursor
_PIN_ON = "\uF4EC"
_PIN_OFF = "\uF4EB"


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


def test_folded_is_the_drawers_own_frame_left_ajar(run: dict) -> None:
    s = run["0-folded"]
    left, right = run["edge"]["left"], run["edge"]["right"]
    # Its own frame, as wide as the open panel, all but the edge behind the
    # window's edge.
    assert left["frame"] == [_EDGE - 260, _EDGE]
    assert right["frame"] == [_WIN - _EDGE, _WIN - _EDGE + 300]
    assert left["out"] == right["out"] == _EDGE
    assert left["frameVisible"] is True and right["frameVisible"] is True
    assert left["border"] == right["border"] == 1
    # Rounded on the map side only.
    assert left["radius"] == [0, 6] and right["radius"] == [6, 0]
    # No header and no name while ajar.
    assert left["header"] is False and right["header"] is False
    assert left["slice"] == right["slice"] == 0
    # Only the ajar edges are taken from the map.
    for side in ("left", "right"):
        assert s[side]["open"] is False
        assert s[side]["width"] == s[side]["takenWidth"] == _EDGE
    assert s["right"]["x"] == _WIN - _EDGE
    assert s["map"] == [_EDGE, _WIN - 2 * _EDGE]


def test_hover_slides_out_to_the_name_and_pin_with_a_hand(run: dict) -> None:
    for name, title, pin in (("left", "Chips", _PIN_ON), ("right", "Layers", _PIN_OFF)):
        before = run["hover"][name]["before"]
        over = run["hover"][name]["over"]
        assert before["out"] == _EDGE and before["slice"] == 0
        # Out to the slice: further than the edge, its bold name and pin in it.
        assert over["out"] == over["hoverWidth"] > _EDGE
        assert over["slice"] == 1
        assert over["title"] == [title, True, True]
        assert over["pin"] == [pin, True] and over["pinInSlice"] is True
        assert over["areaCursor"] == _HAND and over["windowCursor"] == _HAND
        # Drawn over the map: the layout stays.
        assert over["takenWidth"] == _EDGE and over["open"] is False
        assert over["map"] == before["map"] == [_EDGE, _WIN - 2 * _EDGE]
    after = run["hover"]["after"]
    assert after["out"] == _EDGE and after["slice"] == 0
    assert after["windowCursor"] != _HAND


def test_the_slices_pin_pins_without_opening(run: dict) -> None:
    # [pinned, open, takenWidth] after each click on Layers' slice pin.
    assert run["hover"]["slicePin"] == [[True, False, _EDGE], [False, False, _EDGE]]


def test_click_slides_fully_out_with_the_layout_final_at_once(run: dict) -> None:
    sl = run["slide"]
    # What the window reads is final straight after the click.
    assert sl["takenAtOnce"] == sl["widthAtOnce"] == sl["mapAtOnce"] == 260
    assert sl["takenMid"] == 260
    # The drawer slides out from its edge to fully out.
    start, mid, end = sl["bodyX"]
    assert end == 0
    assert start < mid < end
    # The right one: its place is final at once, the drawer slides left.
    assert sl["rightXAtOnce"] == _WIN - 300
    assert sl["rightTakenAtOnce"] == _EDGE
    start, mid, end = sl["rightBodyX"]
    assert end == _WIN - 300
    assert start > mid > end


def test_open_shows_its_header(run: dict) -> None:
    assert run["openHeader"] == {"title": True, "pin": True, "fold": True}


def test_fold_slides_back_to_the_ajar_edge(run: dict) -> None:
    sl = run["slide"]
    assert sl["foldTakenAtOnce"] == _EDGE and sl["foldMapAtOnce"] == _EDGE
    # Mid-slide: between fully out and the edge.
    assert _EDGE < sl["foldMid"] < 260
    assert sl["foldEnd"] == _EDGE
    assert sl["foldHeader"] is False


def test_pinned_and_open_takes_its_width_and_no_strip_beside(run: dict) -> None:
    s = run["1-left-unfolded"]["left"]
    assert s["open"] is True and s["overlay"] is False
    assert s["bodyWidth"] == s["out"] == 260
    assert s["takenWidth"] == s["width"] == 260
    assert run["1-left-unfolded"]["map"] == [260, _WIN - 260 - _EDGE]


def test_unpinned_panel_is_drawn_over_the_map(run: dict) -> None:
    r = run["2-right-overlay"]
    assert r["right"]["open"] is True and r["right"]["overlay"] is True
    # Over the map: the map keeps its width, the drawer reaches into it.
    assert r["right"]["takenWidth"] == _EDGE
    assert r["map"] == run["1-left-unfolded"]["map"]
    assert r["right"]["x"] == _WIN - 300 and r["right"]["out"] == 300


def test_map_click_folds_unpinned_only(run: dict) -> None:
    r = run["3-map-click"]
    assert r["right"]["open"] is False and r["right"]["out"] == _EDGE
    assert r["left"]["open"] is True
    assert run["4-left-unpinned"]["left"]["pinned"] is False
    assert run["4-left-unpinned"]["left"]["overlay"] is True
    assert run["4-left-unpinned"]["map"] == [_EDGE, _WIN - 2 * _EDGE]
    assert run["5-map-click-left"]["left"]["open"] is False


def test_pin_and_fold_arrow(run: dict) -> None:
    s = run["6-left-pinned"]["left"]
    assert s["open"] is True and s["pinned"] is True
    s = run["7-left-fold-arrow"]["left"]
    assert s["open"] is False and s["pinned"] is True
    assert s["takenWidth"] == _EDGE and s["out"] == _EDGE


def test_inner_edge_resizes_within_min_and_max(run: dict) -> None:
    assert run["8-left-wider"]["left"]["panelWidth"] == 320
    assert run["8-left-wider"]["map"][0] == 320
    assert run["9-left-max"]["left"]["panelWidth"] == 400
    assert run["10-left-min"]["left"]["panelWidth"] == 180
    # The right panel's inner edge is on its left.
    assert run["11-right-wider"]["right"]["panelWidth"] == 350
    assert run["11-right-wider"]["right"]["x"] == _WIN - 350


def test_content_press_does_not_reach_the_map(run: dict) -> None:
    assert run["12-content-click"] == {"mapClicks": 0, "open": True}


def test_a_drawer_click_folds_the_other_unpinned_panel(run: dict) -> None:
    # Folding Chips by its arrow leaves Layers out.
    assert run["13-left-folded-right-stays"]["right"]["open"] is True
    r = run["13-left-strip-folds-right"]
    assert r["left"]["open"] is True
    assert r["right"]["open"] is False


def test_changed_only_for_changes_made_on_the_panel(run: dict) -> None:
    # Unfold, then the resize release: two.
    before = run["7-left-fold-arrow"]["leftChanged"]
    assert run["8-left-wider"]["leftChanged"] - before == 2
    # Layers: its drawer click and the map click's fold.
    assert run["3-map-click"]["rightChangedSinceOpen"] == 2
    assert run["14-direct-sets"] == [0, 0]
    r = run["14-restored"]["left"]
    assert r["panelWidth"] == 222 and r["takenWidth"] == 222


def test_unavailable_hides_it_and_takes_nothing(run: dict) -> None:
    s = run["15-unavailable"]
    assert s["left"]["visible"] is False and s["left"]["takenWidth"] == 0
    assert s["map"][0] == 0
    s = run["16-available"]
    assert s["left"] == run["14-restored"]["left"]


def test_no_qml_warnings(run: dict) -> None:
    assert run["warnings"] == []
