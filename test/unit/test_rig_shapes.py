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
