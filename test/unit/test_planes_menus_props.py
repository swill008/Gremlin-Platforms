# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device Mapping Editor planes: menus and properties (07 S42, S43, S112, S121, S124;
D-07-BACKGROUND-PLANES).

Right-click › Arrange offers Move to Background (Ctrl+Shift+B) and Move to
Foreground, greyed out with the reason for what can't go; a picture puts its
shape back with Reset Shape; the Properties panel has a Look section for
pictures; a picture over 4000 px is drawn on screen from a screen-sized copy
and at its own size when printing. Runs the editor off-screen in its own
process.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest

_HERE = pathlib.Path(__file__).parent

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows fonts")


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> dict:
    folder = tmp_path_factory.mktemp("planes_menus")
    home = tmp_path_factory.mktemp("home")
    done = proc_tree.run(
        [sys.executable, str(_HERE / "planes_menus_props_smoke.py"), str(folder)],
        text=True, timeout=120,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "USERPROFILE": str(home)},
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, done.stdout[-2000:] + done.stderr[-2000:]
    return json.loads(lines[0][len("RESULT "):])


def test_chip_cannot_go_to_the_background(results: dict) -> None:
    menu = results["menu-chip"]
    back = menu["dmeMoveToBackground"]
    assert back["section"] == "arrange"
    assert back["text"] == "Move to Background"
    assert back["enabled"] is False
    assert back["tip"] == "Chips stay in the foreground"
    front = menu["dmeMoveToForeground"]
    assert front["enabled"] is False
    assert front["tip"] == "Already in the foreground"


def test_shape_and_picture_offer_move_to_background(results: dict) -> None:
    for key in ("menu-rect", "menu-pic"):
        back = results[key]["dmeMoveToBackground"]
        assert back["enabled"] is True, key
        assert back["hint"] == "Ctrl+Shift+B"
        assert back["tip"] == ""
        assert results[key]["dmeMoveToForeground"]["enabled"] is False


def test_move_to_background_and_back_from_the_menu(results: dict) -> None:
    assert results["rect-after-move"] == "background"
    # One Undo step; it lands on top of the background.
    assert results["move-steps"] == 1
    assert results["order-after-move"][:2] == ["pbg", "rect1"]
    menu = results["menu-rect-bg"]
    assert menu["dmeMoveToForeground"]["enabled"] is True
    assert menu["dmeMoveToBackground"]["enabled"] is False
    assert menu["dmeMoveToBackground"]["tip"] == "Already in the background"
    assert results["rect-after-back"] == ""


def test_reset_shape_on_a_turned_picture(results: dict) -> None:
    assert results["menu-pic-reset"] == {"section": "transform", "enabled": True}
    assert results["pic-after-reset"] == {"rot": 0, "flipH": False}


def test_picture_properties_have_a_look(results: dict) -> None:
    lines = results["props-pic"]
    at = lines.index("Look")
    assert lines[at + 1:at + 5] == [
        "Brightness: 0%", "Contrast: 0%", "Greyscale: 0%", "Opacity: 100%"]
    after = results["props-pic-after"]
    assert "Brightness: 25%" in after
    assert "Greyscale: 40%" in after
    # Greyscale is an amount 0..1, like brightness and contrast.
    assert results["pic-look"] == {"bright": 0.25, "grey": 0.4}
    # Not on a shape.
    assert "Look" not in results["props-rect"]
    assert not any(ln.startswith("Brightness") for ln in results["props-rect"])


def test_big_picture_drawn_from_a_screen_copy(results: dict) -> None:
    side = results["screen-side"]
    big = results["pictures"]["pbg"]
    assert (big["natW"], big["natH"]) == (6000, 3000)
    assert big["capped"] is True
    assert max(big["loadW"], big["loadH"]) <= max(side, 1)
    assert abs(big["loadW"] / big["loadH"] - 2) < 0.01
    # Printing lifts the cap, and it comes back after.
    full = results["big-full"]
    assert full["capped"] is False and (full["loadW"], full["loadH"]) == (6000, 3000)
    assert results["big-capped-again"]["capped"] is True
    small = results["pictures"]["pic"]
    assert small["capped"] is False and (small["loadW"], small["loadH"]) == (200, 100)


def test_look_copy_shown_and_missing_picture_placeholder(results: dict) -> None:
    pics = results["pictures"]
    assert pics["plk"]["source"].endswith("look.png")
    assert pics["pic"]["source"].endswith("small.png")
    assert pics["pgone"]["missingShown"] is True
    assert pics["pic"]["missingShown"] is False
    assert results["warnings"] == []
