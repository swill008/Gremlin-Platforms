# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Home card sizes +50 % (D-NEXTLIST-1 item 3, user answer 5): a card is
220-1080 wide and 140-780 tall, never wider than the page has room for, and
its picture is decoded for the largest card (1080 x 780 x screen scale). The
real Home page off-screen (home_cards_smoke.py) in an 800 px window."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import home_cards_smoke  # noqa: E402


def test_card_limits_and_picture_decode(tmp_path: Path) -> None:
    r = home_cards_smoke.run(tmp_path, "size")

    # The limits themselves.
    assert r["clamp"] == [1080, 780, 220, 140]

    # The picture is decoded for the largest card.
    dpr = r["dpr"]
    assert isinstance(dpr, (int, float))
    assert r["decode"] == [round(1080 * dpr), round(780 * dpr)]

    # A card saved at 1080 wide in an 800 px window fits the window.
    flow = r["flow-width"]
    assert isinstance(flow, (int, float))
    wide = r["wide-card"]
    assert isinstance(wide, list)
    assert wide[2] <= flow

    # A resize is held to the room the page has, then to 1080.
    assert r["clamp-fit"] == 500
    calls = r["calls"]
    assert isinstance(calls, list) and len(calls) == 1
    _, slug, w, _h = str(calls[0]).split(" ")
    assert slug == "b"
    assert int(w) <= flow
