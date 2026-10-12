# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Home card reorder as the Device Bindings rows (D-NEXTLIST-1 item 2, user
answers 3a, 4a): a 4 dp move starts the drag; a picture of the card
(grabToImage) follows the pointer at 0.85; a 2 dp Style.info line shows the
drop spot between the cards; the other cards stay where they are (no
reflow); the drop asks the model for one move. The real Home page off-screen
with real mouse events (home_cards_smoke.py)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import home_cards_smoke  # noqa: E402


def test_dragging_a_card_shows_its_picture_and_a_drop_line(tmp_path: Path) -> None:
    r = home_cards_smoke.run(tmp_path, "drag")

    # A 4 dp move starts it, not a 3 px one.
    assert r["drag-at-3px"] == ""
    assert r["drag-at-5px"] == "a"

    # No reflow: every card stays where it was while one is dragged.
    assert r["during"] == r["before"]

    # The card's picture under the pointer, at 0.85, the card's size.
    visible, opacity, has_source, ready, w, h, x, _y = r["picture"]  # type: ignore[misc]
    assert visible is True and has_source is True and ready is True
    assert abs(opacity - 0.85) < 1e-6
    before = r["before"]
    assert isinstance(before, dict)
    assert [w, h] == before["a"][2:]
    px, _py = r["pointer"]  # type: ignore[misc]
    assert x <= px <= x + w

    # Over card c, right of its middle: the drop spot is before d, and the
    # 2 dp Style.info line stands in the gap between c and d.
    assert r["insert-before"] == "d"
    shown, line_w, is_info, lx, ly, lh = r["line"]  # type: ignore[misc]
    assert shown is True and is_info is True
    assert line_w == r["dp2"]
    c_right = before["c"][0] + before["c"][2]
    assert c_right <= lx + line_w / 2 <= before["d"][0]
    assert ly == before["d"][1] and lh >= before["d"][3]

    # The card stays in its place, dimmed, while its picture moves.
    assert r["dragged-opacity"] < 1

    # One drop: one move asked of the model; the drag is over.
    assert r["calls"] == ["drop a before d"]
    assert r["after-drop"] == ["", 1]


def test_the_old_drag_pieces_are_gone() -> None:
    qml = os.environ.get("HOME_QML_DIR") or Path(__file__).resolve().parents[2] / "qml"
    page = (Path(qml) / "StatusPage.qml").read_text(encoding="utf-8")
    # The dashed stand-in that made room (reflow) and the unused drag-stack state.
    for gone in (
        "SlotGhost",
        "ghostPad",
        "isDragHome",
        "dragStackSlug",
        "insertTravel",
        "dragPhoto",
    ):
        assert gone not in page, gone
    assert "grabToImage" in page
