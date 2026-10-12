# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A mouse gesture is one Undo step, made when the mouse is let go, on both
planes; a hover highlight is never a step (07 S55a; D-07-GESTURE-UNDO).

Checked on the real editor off-screen (gesture_undo_smoke.py, its own
process and user folder) with real mouse drags: pressed, moved in several
steps across other items (pictures, a text box, a table), so the item under
the pointer changes on the way, and let go. Each gesture must make exactly
one step, and one Undo must put the map back exactly.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest

_ROOT = pathlib.Path(__file__).parents[2]


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    env = dict(os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen")
    env.setdefault(
        "QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    )
    done = proc_tree.run(
        [sys.executable, str(_ROOT / "test" / "unit" / "gesture_undo_smoke.py")],
        cwd=home,
        env=env,
        text=True,
        timeout=180,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("GESTUREUNDO ")]
    assert lines, done.stdout[-1500:] + done.stderr[-1500:]
    return json.loads(lines[0][len("GESTUREUNDO ") :])


# Gesture -> a field it must have changed ("<item>.<key>", or the print
# area / guides by name); <x> is an id from the smoke's "ids".
_GESTURES = {
    "move_chip": "b3.chipFx",
    "move_multi": "b5.chipFx",
    "move_group": "<grp>.chipFx",
    "move_shape": "<shp>.fx",
    "move_picture": "<pic>.fx",
    "resize_picture_corner": "<pic>.fw",
    "resize_picture_edge": "<pic>.fw",
    "resize_text_corner": "<txt>.fw",
    "resize_text_edge": "<txt>.fw",
    "rotate": "<shp>.rot",
    "crop": "<pic>.crop",
    "skew": "<arr>.skew",
    "leader_end": "b3.leaders",
    "leader_bend": "b3.leaders",
    "hotspot": "b3.hotFx",
    "guide_new": "guidesY",
    "guide_move": "guidesY",
    "print_area_draw": "printArea",
    "print_area_move": "printArea",
    "bg_move_picture": "<bgpic>.fx",
    "bg_resize_picture": "<bgpic>.fw",
}
# Dragged on their own mouse areas (the ruler, the print area's frame), not
# the map's, so the map's hover doesn't follow them.
_NO_HOVER = {"guide_new", "print_area_move"}


def _params() -> list:
    return [name for name in _GESTURES]


def test_no_qml_warnings(run: dict) -> None:
    assert run["warnings"] == []


def test_the_drags_start_on_their_handles(run: dict) -> None:
    # Without these, a gesture could pass by moving something else.
    assert run["group_grab"] is True
    assert run["rotate_hit"] == "rotate"
    assert run["skew_hit"] == "xf-skewX"
    assert run["crop_on"] is True
    assert run["from_hit"] == "from"
    assert run["spine_hit"] == "spine"
    assert run["hot_hit"] == "hot"
    assert run["guide_hit"] is True
    assert run["empty_hit"] == ""


@pytest.mark.parametrize("name", _params())
def test_a_gesture_is_one_undo_step(run: dict, name: str) -> None:
    g = run["gestures"][name]
    want = _GESTURES[name]
    for key, id_ in run["ids"].items():
        want = want.replace(f"<{key}>", id_)
    assert any(w.startswith(want) for w in g["what"]), g
    if name not in _NO_HOVER:
        # The pointer crossed other items: the hover highlight changed.
        assert g["hover_changes"] >= 1, g
    assert g["steps"] == 1, g
    assert g["undo_exact"] is True, g


def test_a_hover_without_a_drag_saves_no_step(run: dict) -> None:
    h = run["hover_only"]
    assert h["hover_changes"] >= 2
    assert h["steps"] == 0
    assert h["changed"] is False


def test_a_run_of_arrow_nudges_is_one_step(run: dict) -> None:
    assert run["nudges"] == {"steps": 1, "changed": True, "undo_exact": True}


def test_esc_during_a_drag_cancels_it(run: dict) -> None:
    # Esc cancels the drag (07 S150): later moves do nothing, the picture
    # goes back to where it was at the press and no undo step is added.
    g = run["gestures"]["esc_move_picture"]
    assert run["esc_drag_kind_after"] == ""
    assert g["changed"] is False, g
    assert g["steps"] == 0, g
    assert g["undo_exact"] is True, g
