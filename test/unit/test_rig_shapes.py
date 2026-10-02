# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""qml/rig_shapes.js: the Button Map editor's pure shape maths."""

from __future__ import annotations

import json
import math
import pathlib
from collections.abc import Iterator

import pytest
from PySide6 import (
    QtCore,
    QtQml,
)

_SOURCE = pathlib.Path(__file__).parents[2] / "qml" / "rig_shapes.js"


@pytest.fixture(scope="module")
def js() -> Iterator[QtQml.QJSEngine]:
    # A QJSEngine without an application object ends the process; keep the
    # one made here alive for as long as the engine.
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    engine = QtQml.QJSEngine()
    # ".pragma library" is QML syntax; plain JavaScript does not know it.
    code = _SOURCE.read_text(encoding="utf-8").replace(".pragma library", "")
    result = engine.evaluate(code, str(_SOURCE))
    assert not result.isError(), result.toString()
    yield engine
    del app


def call(engine: QtQml.QJSEngine, expr: str) -> object:
    result = engine.evaluate(f"JSON.stringify({expr})")
    assert not result.isError(), result.toString()
    return json.loads(result.toString())


@pytest.mark.parametrize("shape", ["arrow", "arrow2"])
def test_block_arrow_stays_in_its_box(js: QtQml.QJSEngine, shape: str) -> None:
    for w, h in [(200, 60), (40, 100), (300, 300)]:
        points = call(js, f'blockArrow("{shape}", {w}, {h})')
        assert all(0 <= x <= w and 0 <= y <= h for x, y in points)
        # Symmetric about the middle line.
        ys = sorted(round(y, 6) for _, y in points)
        assert ys == sorted(round(h - y, 6) for y in ys)
        # A tip touches the right edge in the middle.
        assert [w, h / 2] in points


def test_double_arrow_points_both_ways(js: QtQml.QJSEngine) -> None:
    points = call(js, 'blockArrow("arrow2", 200, 60)')
    assert [0, 30] in points and [200, 30] in points


def test_dash_lengths_do_not_grow_with_width(js: QtQml.QJSEngine) -> None:
    assert call(js, 'dashFor("", 3)') == []
    assert call(js, 'dashFor("solid", 3)') == []
    for width in (1, 2, 4, 6):
        dash, gap = call(js, f'dashFor("dash", {width})')
        # Qt multiplies by the width: the drawn lengths stay 8 and 6.
        assert dash * width == pytest.approx(8)
        assert gap * width == pytest.approx(6)
        dot, dot_gap = call(js, f'dashFor("dot", {width})')
        assert dot_gap * width == pytest.approx(4)


def test_line_box_round_trips_its_ends(js: QtQml.QJSEngine) -> None:
    for ax, ay, bx, by in [(10, 20, 110, 20), (50, 50, 50, 200), (300, 10, 20, 90)]:
        box = call(js, f"lineBox({ax}, {ay}, {bx}, {by}, 12)")
        ends = call(js, f"lineEnds({json.dumps(box['ends'])}, {box['w']}, {box['h']})")
        assert box["x"] + ends["ax"] == pytest.approx(ax)
        assert box["y"] + ends["ay"] == pytest.approx(ay)
        assert box["x"] + ends["bx"] == pytest.approx(bx)
        assert box["y"] + ends["by"] == pytest.approx(by)
        # 12 of margin on every side, so a flat line still has height.
        assert box["w"] == pytest.approx(abs(bx - ax) + 24)
        assert box["h"] == pytest.approx(abs(by - ay) + 24)


def test_margin_fits_the_head(js: QtQml.QJSEngine) -> None:
    for width in (1, 2, 4, 6, 12):
        margin = call(js, f"lineMargin({width})")
        assert margin >= call(js, f"headSize({width})") / 2 + width / 2


def test_arrow_head_shape(js: QtQml.QJSEngine) -> None:
    head = call(js, "arrowHead(100, 50, 0, 50, 20)")
    assert head["tip"] == [100, 50]
    assert head["base"] == [80, 50]
    # The back corners sit on either side of the base, half the size apart.
    assert sorted([head["left"], head["right"]]) == [[80, 40], [80, 60]]
    # A head never runs past the other end of a short line.
    short = call(js, "arrowHead(10, 0, 0, 0, 20)")
    assert short["base"] == [0, 0]
    assert call(js, "arrowHead(5, 5, 5, 5, 20)") is None


def test_distance_to_segment(js: QtQml.QJSEngine) -> None:
    assert call(js, "distToSegment(50, 10, 0, 0, 100, 0)") == pytest.approx(10)
    assert call(js, "distToSegment(-30, 40, 0, 0, 100, 0)") == pytest.approx(50)
    assert call(js, "distToSegment(130, 0, 0, 0, 100, 0)") == pytest.approx(30)
    assert call(js, "distToSegment(3, 4, 0, 0, 0, 0)") == pytest.approx(5)


def test_angle_snap_keeps_length(js: QtQml.QJSEngine) -> None:
    p = call(js, "snapAngle(0, 0, 100, 8, 15)")
    assert p["x"] == pytest.approx(100.32, abs=0.01) and p["y"] == pytest.approx(0)
    p = call(js, "snapAngle(10, 10, 80, 70, 15)")
    angle = math.degrees(math.atan2(p["y"] - 10, p["x"] - 10))
    assert angle == pytest.approx(45)
    assert math.hypot(p["x"] - 10, p["y"] - 10) == pytest.approx(math.hypot(70, 60))


def _corner(box: dict, rot: float, sx: int, sy: int, js: QtQml.QJSEngine) -> tuple:
    """Screen position of a box corner (sx, sy in -1/0/1) when turned by rot."""
    p = call(js, f"rotatePt({sx * box['w'] / 2}, {sy * box['h'] / 2}, {rot})")
    return (box["x"] + box["w"] / 2 + p["x"], box["y"] + box["h"] / 2 + p["y"])


@pytest.mark.parametrize("rot", [0, 30, 90, 135, 250])
@pytest.mark.parametrize(
    "handle, sx, sy",
    [("se", 1, 1), ("nw", -1, -1), ("ne", 1, -1), ("e", 1, 0), ("n", 0, -1)],
)
def test_rotated_resize_keeps_the_opposite_side(
    js: QtQml.QJSEngine, rot: float, handle: str, sx: int, sy: int
) -> None:
    box = {"x": 100, "y": 80, "w": 120, "h": 60}
    fixed = _corner(box, rot, -sx, -sy, js)
    # Drag the handle to a point 40 px further out along the box's own axes.
    start = _corner(box, rot, sx, sy, js)
    push = call(js, f"rotatePt({sx * 40}, {sy * 40}, {rot})")
    px, py = start[0] + push["x"], start[1] + push["y"]
    new = call(
        js,
        f"rotatedResize({json.dumps(box)}, {rot}, '{handle}', {px}, {py}, 8, 8, false)",
    )
    assert _corner(new, rot, -sx, -sy, js) == pytest.approx(fixed, abs=1e-6)
    assert new["w"] == pytest.approx(box["w"] + (40 if sx else 0))
    assert new["h"] == pytest.approx(box["h"] + (40 if sy else 0))


def test_rotated_resize_minimum_and_aspect(js: QtQml.QJSEngine) -> None:
    box = {"x": 0, "y": 0, "w": 100, "h": 50}
    # Dragged past the opposite corner: the minimum size, not a negative one.
    small = call(
        js, f"rotatedResize({json.dumps(box)}, 0, 'se', -50, -50, 8, 8, false)"
    )
    assert (small["w"], small["h"]) == (8, 8)
    # Keeping the aspect: 2 to 1 stays 2 to 1.
    kept = call(js, f"rotatedResize({json.dumps(box)}, 45, 'se', 300, 300, 8, 8, true)")
    assert kept["w"] / kept["h"] == pytest.approx(2)


def test_unturned_resize_matches_a_plain_one(js: QtQml.QJSEngine) -> None:
    box = {"x": 10, "y": 20, "w": 100, "h": 50}
    new = call(js, f"rotatedResize({json.dumps(box)}, 0, 'se', 150, 90, 8, 8, false)")
    assert new == pytest.approx({"x": 10, "y": 20, "w": 140, "h": 70})


def test_handle_angle_and_snap(js: QtQml.QJSEngine) -> None:
    # Straight up is 0, growing clockwise on screen.
    assert call(js, "handleAngle(0, 0, 0, -10)") == pytest.approx(0)
    assert call(js, "handleAngle(0, 0, 10, 0)") == pytest.approx(90)
    assert call(js, "handleAngle(0, 0, 0, 10)") == pytest.approx(180)
    assert call(js, "handleAngle(0, 0, -10, 0)") == pytest.approx(270)
    assert call(js, "snapDeg(52, 15)") == pytest.approx(45)
    assert call(js, "snapDeg(359, 15)") == pytest.approx(0)
    assert call(js, "normDeg(-90)") == pytest.approx(270)


@pytest.mark.parametrize("rot", [0, 35, 180])
def test_crop_keeps_what_stays_visible_in_place(
    js: QtQml.QJSEngine, rot: float
) -> None:
    box = {"x": 50, "y": 40, "w": 200, "h": 100}
    c0 = {"l": 0, "t": 0, "r": 0, "b": 0}
    c1 = {"l": 0.25, "t": 0.1, "r": 0, "b": 0.2}
    new = call(
        js, f"cropBox({json.dumps(box)}, {rot}, {json.dumps(c0)}, {json.dumps(c1)})"
    )
    # Half of the old width and 70% of the height remain, at the same scale.
    assert new["w"] == pytest.approx(150)
    assert new["h"] == pytest.approx(70)
    # The new box's bottom-right corner is where the old one's was, less the
    # cut-off bottom strip: picture content did not move.
    old_corner = _corner(box, rot, 1, 1, js)
    lift = call(js, f"rotatePt(0, {-0.2 * 100}, {rot})")
    assert _corner(new, rot, 1, 1, js) == pytest.approx(
        (old_corner[0] + lift["x"], old_corner[1] + lift["y"]), abs=1e-6
    )


def test_crop_back_to_none_restores_the_box(js: QtQml.QJSEngine) -> None:
    box = {"x": 10, "y": 10, "w": 120, "h": 60}
    c = {"l": 0.1, "t": 0.2, "r": 0.3, "b": 0}
    cropped = call(js, f"cropBox({json.dumps(box)}, 20, {{}}, {json.dumps(c)})")
    back = call(js, f"cropBox({json.dumps(cropped)}, 20, {json.dumps(c)}, {{}})")
    assert back == pytest.approx(box)


def test_crop_from_drag_and_clamp(js: QtQml.QJSEngine) -> None:
    box = {"x": 0, "y": 0, "w": 200, "h": 100}
    # Drag the right edge 50 px in: a quarter of the picture is cut off.
    c = call(js, f"cropFromDrag({json.dumps(box)}, 0, {{}}, 'e', 150, 50)")
    assert c == pytest.approx({"l": 0, "t": 0, "r": 0.25, "b": 0})
    # Dragging outwards past the picture's edge uncrops only to nothing.
    c = call(js, f"cropFromDrag({json.dumps(box)}, 0, {{}}, 'e', 400, 50)")
    assert c["r"] == 0
    assert call(js, "clampCrop({l: 0.7, r: 0.7})") == pytest.approx(
        {"l": 0.7, "t": 0, "r": 0.28, "b": 0}
    )


def test_callout_pointer_leaves_the_side_facing_its_tip(js: QtQml.QJSEngine) -> None:
    w, h = 100, 40
    below = call(js, f"calloutOutline({w}, {h}, 30, 90, 20)")
    assert [30, 90] in below
    # The pointer's base sits on the bottom edge, 20 wide, round x = 30.
    base = [p for p in below if p[1] == h and 0 < p[0] < w]
    assert sorted(x for x, _ in base) == [20, 40]
    right = call(js, f"calloutOutline({w}, {h}, 160, 20, 20)")
    assert [160, 20] in right
    assert all(p[0] == w for p in right if p[1] not in (0, h) and p != [160, 20])
    above = call(js, f"calloutOutline({w}, {h}, 50, -30, 20)")
    left = call(js, f"calloutOutline({w}, {h}, -50, 20, 20)")
    assert [50, -30] in above and [-50, 20] in left


def test_callout_base_stays_on_its_side(js: QtQml.QJSEngine) -> None:
    # A tip far to one side: the base slides to the end of the side, and is
    # never wider than a third of it.
    pts = call(js, "calloutOutline(60, 40, 70, 500, 40)")
    base = sorted(x for x, y in pts if y == 40 and 0 < x < 60)
    assert base[0] >= 0 and base[-1] <= 60
    assert base[-1] - base[0] <= 20 + 1e-9


def test_callout_tip_inside_is_just_the_box(js: QtQml.QJSEngine) -> None:
    assert call(js, "calloutOutline(100, 40, 50, 20, 20)") == [
        [0, 0], [100, 0], [100, 40], [0, 40]
    ]


def test_simplify_path_keeps_corners_and_drops_wobble(js: QtQml.QJSEngine) -> None:
    # A wobbly line to (100, 0), then straight up: the corner and both ends stay.
    wobble = [[x, 0.4 if x % 20 else 0] for x in range(0, 101, 5)]
    pts = [*wobble, [100, 50], [100, 100]]
    kept = call(js, f"simplifyPath({json.dumps(pts)}, 1)")
    assert kept[0] == [0, 0] and kept[-1] == [100, 100]
    assert [100, 0] in kept
    assert len(kept) == 3
    assert call(js, "simplifyPath([[0, 0], [5, 5]], 1)") == [[0, 0], [5, 5]]


def test_path_box_and_fractions(js: QtQml.QJSEngine) -> None:
    box = call(js, "pathBox([[10, 20], [50, 20], [30, 60]], 5)")
    assert (box["x"], box["y"], box["w"], box["h"]) == (5, 15, 50, 50)
    assert box["rel"][0] == [0.1, 0.1]
    assert box["rel"][2] == [0.5, 0.9]


def test_distance_to_path_and_inside(js: QtQml.QJSEngine) -> None:
    square = "[[0, 0], [10, 0], [10, 10], [0, 10]]"
    assert call(js, f"distToPath(5, -3, {square}, false)") == 3
    # Open, the left side is not part of the path; closed, it is.
    assert call(js, f"distToPath(-2, 5, {square}, false)") > 2
    assert call(js, f"distToPath(-2, 5, {square}, true)") == 2
    assert call(js, f"insidePolygon(5, 5, {square})") is True
    assert call(js, f"insidePolygon(15, 5, {square})") is False


def test_invert_lightness(js: QtQml.QJSEngine) -> None:
    assert call(js, 'invertLightness("#000000")') == "#FFFFFF"
    assert call(js, 'invertLightness("#FFF")') == "#000000"
    # The editor's dark chip and light text swap.
    dark = call(js, 'invertLightness("#18181B")')
    assert int(dark[1:3], 16) > 0xE0
    # A dark red stays red, now light; alpha is kept.
    red = call(js, 'invertLightness("#807F1D1D")')
    assert red.startswith("#80")
    r, g, b = (int(red[i:i + 2], 16) for i in (3, 5, 7))
    assert r > g and r > b and min(r, g, b) >= 0x80
    # Twice is the start (to rounding).
    back = call(js, 'invertLightness(invertLightness("#22C55E"))')
    assert all(abs(int(back[i:i + 2], 16) - int("#22C55E"[i:i + 2], 16)) <= 2
               for i in (1, 3, 5))
    assert call(js, 'invertLightness("transparent")') == "transparent"


def test_arrow_outline_unshaped_is_the_block_arrow(js: QtQml.QJSEngine) -> None:
    for shape in ("arrow", "arrow2"):
        assert call(js, f'arrowOutline("{shape}", 200, 60, {{}}, 0)') == call(
            js, f'blockArrow("{shape}", 200, 60)'
        )


def test_arrow_outline_shaped(js: QtQml.QJSEngine) -> None:
    adj = "{headLen: 0.25, headW: 0.8, shaft: 0.3}"
    pts = call(js, f'arrowOutline("arrow", 200, 60, {adj}, 0)')
    rounded = [[round(x, 3), round(y, 3)] for x, y in pts]
    # Head 80% of the thickness, shaft 30%, both about the middle line.
    assert sorted({y for _, y in rounded}) == [6, 21, 30, 39, 54]
    assert [200, 30] in rounded
    assert {x for x, y in rounded if y in (6, 54)} == {150}


def test_bent_arrow_keeps_inside_its_box_and_its_tips(js: QtQml.QJSEngine) -> None:
    for bend in (0.3, -0.3):
        pts = call(js, f'arrowOutline("arrow2", 300, 100, {{}}, {bend})')
        assert all(-0.5 <= x <= 300.5 and -0.5 <= y <= 100.5 for x, y in pts)
        rounded = [[round(x, 2), round(y, 2)] for x, y in pts]
        assert [0, 50] in rounded and [300, 50] in rounded


def test_shape_outlines(js: QtQml.QJSEngine) -> None:
    tri = call(js, 'shapeOutline({shape: "triangle", adj: {apex: 0.25}}, 100, 50)')
    assert tri["pts"][0] == [25, 0]
    ell = call(js, 'shapeOutline({shape: "ellipse"}, 100, 50)')
    assert ell["smooth"] is True and len(ell["pts"]) == 12
    rr = call(js, 'shapeOutline({shape: "roundrect", adj: {r: 0.5}}, 100, 50)')
    assert len(rr["pts"]) == 12
    assert call(js, "roundRadius({adj: {r: 0.2}}, 100, 50)") == 10
    assert call(js, "skewPt(50, 0, 100, 50, 0.5, 0)") == [37.5, 0]
