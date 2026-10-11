# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Where a dropped leader end hooks (07 S122, gap G30).

The drag snaps the end to a picture's snap point; on release attachNear
must keep it there, never hook a picture as a chip, and only hook items on
the leader's plane. The behaviour runs in test_planes_editor_more.py; these
pin the shape of attachNear so the release and the drag stay in step.
"""

from __future__ import annotations

import pathlib

_ROOT = pathlib.Path(__file__).parents[2]


def _attach_near() -> str:
    src = (_ROOT / "qml/rig_leaders.js").read_text(encoding="utf-8")
    src = src.replace("\r", "")
    start = src.index("function attachNear(")
    return src[start:src.index("\nfunction ", start + 1)]


def test_a_snap_point_wins_like_the_drag() -> None:
    body = _attach_near()
    assert body.startswith("function attachNear(x, y, opts)")
    assert "socketNear(x, y)" in body
    sock = body.index("socketNear(x, y)")
    assert sock < body.index("hotPt(")
    assert "o.altOff ? null : socketNear(x, y)" in body


def test_pictures_are_not_chip_pins() -> None:
    body = _attach_near()
    chip_loop = body[body.index("_chips.itemAt(i)") - 200:]
    assert "isOverlay(list[i])" in chip_loop


def test_only_the_leaders_plane_is_hooked() -> None:
    body = _attach_near()
    assert body.count("planeOf(list[i]) !== plane") == 2
    assert "o.owner ? planeOf(o.owner)" in body


def test_a_free_end_lands_where_the_drag_showed_it() -> None:
    assert "snapPos(x, y, o.altOff)" in _attach_near()
