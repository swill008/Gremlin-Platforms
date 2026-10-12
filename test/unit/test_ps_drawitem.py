# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A drawing's handles and pictures in the Device Mapping Editor (07 S140,
S155), checked on the real editor off-screen at 150 % UI scale
(ps_drawitem_smoke.py, its own process and user folder).

- The eight resize handles and the rotate knob are centred on the box's
  edges, corners and grip point at any UI scale.
- Handle hit radii scale with the UI.
- On a skewed item, a press on each drawn handle and on the rotate grip
  hits it.
- A picture fills its box (Stretch).
- Choose Picture… with the new picture's aspect keeps width and centre and
  takes the new shape (a crop's showing part counts); without an aspect the
  box stays as it was.
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
_SCALE = 1.5
_NEAR = 0.75


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    env = dict(os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen")
    env.setdefault(
        "QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    )
    done = proc_tree.run(
        [sys.executable, str(_ROOT / "test" / "unit" / "ps_drawitem_smoke.py")],
        cwd=home,
        env=env,
        text=True,
        timeout=120,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("PSDRAW ")]
    assert lines, smoke_report.explain(done)
    return json.loads(lines[0][len("PSDRAW ") :])


def test_no_qml_warnings(run: dict) -> None:
    assert run["warnings"] == []


def test_resize_handles_centred_at_150_percent(run: dict) -> None:
    h = run["handles"]
    w, ht = h["w"], h["h"]
    want = [
        (0, 0),
        (w, 0),
        (0, ht),
        (w, ht),
        (w / 2, 0),
        (w / 2, ht),
        (0, ht / 2),
        (w, ht / 2),
    ]
    got = h["found"]
    assert len(got) == 8, got
    for g, (x, y) in zip(got, want):
        assert g["size"] == round(8 * _SCALE), g
        assert abs(g["x"] - x) < _NEAR and abs(g["y"] - y) < _NEAR, (g, x, y)


def test_rotate_knob_centred(run: dict) -> None:
    k = run["knob"]
    assert len(k["found"]) == 1, k
    g = k["found"][0]
    assert g["size"] == round(10 * _SCALE)
    assert abs(g["x"] - k["w"] / 2) < _NEAR
    assert abs(g["y"] + run["rotate_offset"]) < _NEAR


def test_hit_radius_scales(run: dict) -> None:
    assert run["hit_near_se"] == "se"


def test_skewed_handles_hit_where_drawn(run: dict) -> None:
    assert run["skew_hits"] == ["nw", "ne", "sw", "se", "n", "s", "w", "e"]
    assert run["skew_rotate_hit"] == ["rotate"]


def test_picture_fills_its_box(run: dict) -> None:
    # Image.Stretch is 0 (PreserveAspectFit is 1).
    assert run["pic_fill"] == [0]


def _ratio(n: dict, space: list) -> float:
    return (n["fw"] * space[0]) / (n["fh"] * space[1])


def test_choose_picture_refits_box(run: dict) -> None:
    b = run["repoint"]["before"]
    a = run["repoint"]["after"]
    assert a["src"] == "pictures/wide.png"
    assert a["fw"] == pytest.approx(b["fw"])
    assert a["fx"] == pytest.approx(b["fx"])
    assert a["fy"] + a["fh"] / 2 == pytest.approx(b["fy"] + b["fh"] / 2)
    assert _ratio(a, run["space"]) == pytest.approx(2.0, rel=1e-3)
    # Half the width cropped away: the showing part is square.
    assert _ratio(run["repoint_crop"], run["space"]) == pytest.approx(1.0, rel=1e-3)
    # No aspect: the box stays.
    n = run["repoint_no_aspect"]
    assert n["src"] == "pictures/other.png"
    assert n["fh"] == pytest.approx(run["repoint_crop"]["fh"])
