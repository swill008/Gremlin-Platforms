# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Home compact view (D-03-COMPACT-THUMB, 03 S73): each card shows a 40 x 40
DeviceThumb beside its text, the card's picture or the device icon glyph as
the Device Library rows; the big picture isn't decoded while compact and
loads again in full view. The real Home page off-screen
(home_cards_smoke.py)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import home_cards_smoke  # noqa: E402

# The Device Library rows' device icon (WindowDeviceLibrary.qml).
_DEVICE_GLYPH = ""


def test_compact_thumb_and_big_picture(tmp_path: Path) -> None:
    r = home_cards_smoke.run(tmp_path, "compact")
    url = r["url"]
    full, compact, again = r["full"], r["compact"], r["full-again"]
    assert isinstance(full, dict) and isinstance(compact, dict)
    assert isinstance(again, dict)

    # Full view: no thumb, the big picture as before.
    assert full["a"]["thumb"] is False and full["b"]["thumb"] is False
    assert full["b"]["photoSource"] == url and full["b"]["photoReady"] is True

    # Compact: a 40 x 40 thumb with the picture, or the glyph without one.
    dp40 = r["dp40"]
    assert compact["b"]["thumb"] is True
    assert compact["b"]["thumbSize"] == [dp40, dp40]
    assert compact["b"]["thumbPicture"] is True and compact["b"]["glyph"] == ""
    assert compact["a"]["thumb"] is True
    assert compact["a"]["thumbPicture"] is False
    assert compact["a"]["glyph"] == _DEVICE_GLYPH
    # The big picture isn't decoded while compact.
    assert compact["b"]["photoSource"] == ""
    # Card height about as before: the thumb fits beside the text lines.
    assert compact["a"]["height"] == compact["b"]["height"]

    # Back to full view: the big picture loads again, no thumb.
    assert again["b"]["photoSource"] == url and again["b"]["photoReady"] is True
    assert again["b"]["thumb"] is False
    assert r["warnings"] == [], r["warnings"]
