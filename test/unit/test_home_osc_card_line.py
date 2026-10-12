# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Home OSC card (D-09-OSC-CARD-LINE): its second line comes from
OscCardStatus (not "Connected · OSC"), in the warning colour when the server
couldn't start; its title's tip is "Open Sound Control (OSC)". Card a beside
it is unchanged. The real Home page off-screen (home_cards_smoke.py)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import home_cards_smoke  # noqa: E402

_A = ["Connected · HID", False, True]


def test_osc_card_line_and_tip(tmp_path: Path) -> None:
    r = home_cards_smoke.run(tmp_path, "osc")
    assert r["closed"] == {"a": _A, "osc": ["Not listening yet", False, True]}
    assert r["tips"] == {"a": [False, ""], "osc": [True, "Open Sound Control (OSC)"]}
    assert r["failed"] == {
        "a": _A,
        "osc": ["Server not started: port 9000 is in use", True, False],
    }
    assert r["message"] == {
        "a": _A,
        "osc": ["From 192.168.1.20: /fader/1 0.75", False, True],
    }
    assert r["warnings"] == [], r["warnings"]
