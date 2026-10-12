# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""qml/rig_shapes.js: handle drags the Photoshop way (07 S141, S148, S149, S140)."""

from __future__ import annotations

import json
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
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    engine = QtQml.QJSEngine()
    code = _SOURCE.read_text(encoding="utf-8").replace(".pragma library", "")
    result = engine.evaluate(code, str(_SOURCE))
    assert not result.isError(), result.toString()
    yield engine
    del app


def call(engine: QtQml.QJSEngine, expr: str) -> object:
    result = engine.evaluate(f"JSON.stringify({expr})")
    assert not result.isError(), result.toString()
    return json.loads(result.toString())


def resize(js: QtQml.QJSEngine, box: dict, rot: float, handle: str,
           px: float, py: float, **opts: object) -> dict:
    return call(
        js,
        f"boxResize({json.dumps(box)}, {rot}, '{handle}', {px}, {py}, "
        f"{json.dumps(opts)})",
    )


BOX = {"x": 0, "y": 0, "w": 200, "h": 100}


def test_corner_keeps_the_ratio_at_press_not_a_square(js: QtQml.QJSEngine) -> None:
    # The old code made a square (lockAspect); a 2:1 box stays 2:1.
    new = resize(js, BOX, 0, "se", 300, 120, keep=True)
    assert new["w"] / new["h"] == pytest.approx(2)
    assert (new["x"], new["y"]) == pytest.approx((0, 0))
    assert new["w"] == pytest.approx(300)


def test_corner_without_keep_is_free(js: QtQml.QJSEngine) -> None:
    new = resize(js, BOX, 0, "se", 300, 120)
    assert (new["w"], new["h"]) == pytest.approx((300, 120))


def test_side_stretches_one_way_even_with_keep(js: QtQml.QJSEngine) -> None:
    new = resize(js, BOX, 0, "e", 260, 999, keep=True)
    assert new == pytest.approx({"x": 0, "y": 0, "w": 260, "h": 100,
                                 "flipX": False, "flipY": False})


@pytest.mark.parametrize("rot", [0, 30])
def test_alt_resizes_from_the_centre(js: QtQml.QJSEngine, rot: float) -> None:
    centre = (100, 50)
    se = call(js, f"rotatePt(100, 50, {rot})")
    push = call(js, f"rotatePt(20, 10, {rot})")
    px, py = centre[0] + se["x"] + push["x"], centre[1] + se["y"] + push["y"]
    new = resize(js, BOX, rot, "se", px, py, centre=True)
    assert new["w"] == pytest.approx(240)
    assert new["h"] == pytest.approx(120)
    assert (new["x"] + new["w"] / 2, new["y"] + new["h"] / 2) == pytest.approx(centre)


def test_past_the_opposite_edge_mirrors(js: QtQml.QJSEngine) -> None:
    # The right edge dragged 50 px past the left one: a 50 px box on the
    # left of the old left edge, flipped left to right.
    new = resize(js, BOX, 0, "e", -50, 50)
    assert new["flipX"] is True
    assert new["flipY"] is False
    assert (new["x"], new["w"]) == pytest.approx((-50, 50))
    # Not past it: no mirror.
    assert resize(js, BOX, 0, "e", 50, 50)["flipX"] is False


def test_skewed_corner_stays_under_the_pointer(js: QtQml.QJSEngine) -> None:
    kx, ky = 0.5, 0.0
    px, py = 320, 140
    new = resize(js, BOX, 0, "se", px, py, kx=kx, ky=ky)
    cx = new["x"] + new["w"] / 2
    cy = new["y"] + new["h"] / 2
    # The drawn se handle: the corner skewed about the box's middle.
    hx = cx + new["w"] / 2 + kx * new["h"] / 2
    hy = cy + new["h"] / 2 + ky * new["w"] / 2
    assert (hx, hy) == pytest.approx((px, py))


def test_crop_corner_keeps_its_proportions(js: QtQml.QJSEngine) -> None:
    c = call(js, f"cropFromDrag({json.dumps(BOX)}, 0, {{}}, 'se', 100, 40, true)")
    # Half the width cut: half the height too, the 2:1 crop kept.
    assert c["r"] == pytest.approx(0.5)
    assert c["b"] == pytest.approx(0.5)


def test_crop_seen_swaps_the_flipped_sides(js: QtQml.QJSEngine) -> None:
    c = {"l": 0.1, "t": 0.2, "r": 0.3, "b": 0.4}
    assert call(js, f"cropSeen({json.dumps(c)}, true, false)") == pytest.approx(
        {"l": 0.3, "t": 0.2, "r": 0.1, "b": 0.4})
    assert call(js, f"cropSeen({json.dumps(c)}, false, true)") == pytest.approx(
        {"l": 0.1, "t": 0.4, "r": 0.3, "b": 0.2})
    back = call(js, f"cropSeen(cropSeen({json.dumps(c)}, true, true), true, true)")
    assert back == pytest.approx(c)
