# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Home's selection box (D-03-HOME-BAND, 03 S146-S148): a left-drag on empty
space draws a box in the Device Mapping Editor's look and selects the cards
it touches (a stack whole); the drag doesn't scroll, the wheel does, and the
page scrolls at the edge; Shift adds, a click or Esc clears; Hide Selected
Cards and Reset Size of Selected Cards in the card menu; Undo / Redo in the
empty-space menu. The real Home page off-screen with real mouse events
(home_cards_smoke.py)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import home_cards_smoke  # noqa: E402


@pytest.fixture(scope="module")
def r(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return home_cards_smoke.run(tmp_path_factory.mktemp("band"), "band")


def test_the_box_selects_the_cards_it_touches_and_whole_stacks(r: dict) -> None:
    assert r["scrollable"] is True and r["start-empty"] is True
    visible, warn, w, h = r["band"]
    assert visible is True and warn is True and w > 0 and h > 0
    # From right of e to the middle of b's stack: b, its stacked c, d, e.
    assert r["band-selected"] == "b,c,d,e"
    assert r["band-after"] == [False, "b,c,d,e"]


def test_the_drag_does_not_scroll_but_the_wheel_does(r: dict) -> None:
    assert r["band-scrolled"] == 0
    assert r["wheel-scrolled"] > 0


def test_the_page_scrolls_at_the_edge_and_the_box_grows(r: dict) -> None:
    assert r["edge-scrolled"] > 0
    held, after = r["edge-selected"]
    assert after > held


def test_shift_adds_click_and_esc_clear(r: dict) -> None:
    assert r["only-e"] == "e"
    # The Shift box runs from right of i to f: f, g, h and i join e.
    assert r["shift-added"] == "e,f,g,h,i"
    assert r["click-cleared"] == ""
    assert r["esc"] == ["", False]


def test_card_menu_hides_or_resets_the_selection(r: dict) -> None:
    rows = r["card-rows"]
    assert "Stack Selected Cards" in rows
    assert "Hide Selected Cards" in rows
    assert "Reset Size of Selected Cards" in rows
    assert r["after-reset"] == "b,c,d,e"
    assert r["menu-calls"] == ["reset b,c,d,e", "hide b,c,d,e"]
    assert r["after-hide"] == ""


def test_empty_space_menu_has_undo_and_redo(r: dict) -> None:
    assert r["empty-header"] == '[["Undo",true],["Redo",false]]'
    assert r["empty-undo"] == "undo"


def test_no_qml_warnings(r: dict) -> None:
    assert r["warnings"] == []
