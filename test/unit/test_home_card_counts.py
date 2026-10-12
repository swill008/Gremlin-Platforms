# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Home card's "N buttons N axes N hats" line (03 S73): the Keyboard, OSC
and Logical Device cards hold many kinds of input and show no count line; a
stick, a vJoy and the Xbox card still do. The real Home page off-screen
(home_cards_smoke.py)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import home_cards_smoke  # noqa: E402


def test_count_line_hidden_on_keyboard_osc_logical(tmp_path: Path) -> None:
    r = home_cards_smoke.run(tmp_path, "counts")
    counts = r["counts"]
    assert isinstance(counts, dict)
    for slug in ("a", "vjoy-1", "xbox"):
        assert counts[slug] is not None, slug
        assert counts[slug][0] is True, (slug, counts[slug])
        assert "buttons" in counts[slug][1], (slug, counts[slug])
    for slug in ("keyboard", "osc", "logical"):
        assert counts[slug] is not None, slug
        assert counts[slug][0] is False, (slug, counts[slug])
    assert r["warnings"] == [], r["warnings"]
