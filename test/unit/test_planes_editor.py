# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Device Mapping Editor's background and foreground planes (07 S111, S112,
S116, S117-S122, S41, S42, S43, S57, S62; D-07-BACKGROUND-PLANES,
D-07-PLANES-ANSWERS P1a, P6a, P7a), checked on the real editor off-screen
(planes_editor_smoke.py, its own process and user folder).

- Every background node comes first; a table or chip can't be background.
- Foreground mode: the background shows but takes no click; Background
  mode: only the background is hit, band-selected and listed, the
  foreground shows at 25 % (leaders too) or not at all.
- New drawings and pictures go to the plane being edited.
- Stacking, Move to Background / Foreground, Clear Background and the
  Background row's lock each stay in their plane and are one Undo step;
  switching plane and the view settings are none.
- Undo steps hold the nodes, the print area and the guides; no photo.
- A picture's look keeps only what differs from neutral; Reset Shape.
- A chip on a background picture's snap point follows it.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest

_ROOT = pathlib.Path(__file__).parents[2]
_QML = _ROOT / "qml"


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    env = dict(os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen")
    env.setdefault(
        "QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    )
    done = proc_tree.run(
        [sys.executable, str(_ROOT / "test" / "unit" / "planes_editor_smoke.py")],
        cwd=home,
        env=env,
        text=True,
        timeout=120,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("PLANES ")]
    assert lines, done.stdout[-1500:] + done.stderr[-1500:]
    return json.loads(lines[0][len("PLANES ") :])


def test_no_qml_warnings(run: dict) -> None:
    assert run["warnings"] == []


def test_the_photo_layer_is_gone() -> None:
    assert not (_QML / "RigPhotoLayer.qml").exists()
    assert not (_QML / "rig_photo.js").exists()
    text = (_QML / "VkbRigEditor.qml").read_text(encoding="utf-8")
    for word in (
        "RigPhoto",
        "photoScale",
        "photoBag",
        "photoImageRestored",
        "movePhoto",
    ):
        assert word not in text, word


def test_background_comes_first_and_holds_only_drawings(run: dict) -> None:
    order = run["loaded_order"]
    assert order[:2] == [["bgA", "background"], ["bgPic", "background"]]
    assert all(plane == "" for _, plane in order[2:])
    assert run["range_bg"] == {"first": 0, "last": 1}
    assert run["range_fg"] == {"first": 2, "last": len(order) - 1}
    assert run["can_hold"] == {"rect": True, "chip": False, "table": False}
    assert run["chip_lost_plane"] == ""
    assert run["bottom_picture"] == "bgPic"


def test_foreground_mode_cannot_click_the_background(run: dict) -> None:
    assert run["fg_click_bg"] == []
    assert run["fg_hit_bg"] == ""
    assert run["fg_click_fg"] == ["fgR"]


def test_background_mode_hits_only_the_background(run: dict) -> None:
    assert run["bg_mode_selection_cleared"] == []
    assert run["bg_click_bg"] == ["bgA"]
    assert run["bg_click_fg"] == []
    assert run["bg_hit_chip"] == ""
    assert run["band_bg"] == ["bgA", "bgPic"]


def test_faint_foreground_and_leaders(run: dict) -> None:
    assert run["faint"] == {"chip": 0.25, "bg": 1, "leaders": 0.25}
    assert run["faint_off_chip_visible"] is False


def test_layer_rows_follow_the_plane(run: dict) -> None:
    assert run["rows_fg"][-1] == ["", "background", "background"]
    row = run["bg_row"]
    assert row["name"] == "Background" and row["match"] is True
    assert run["counts_fg"]["total"] == run["counts_fg"]["matches"]
    assert run["rows_bg"] == [["bgPic", "picture"], ["bgA", "shape"]]


def test_new_items_go_to_the_plane_being_edited(run: dict) -> None:
    assert run["drawn_plane"] == "background"
    assert run["drawn_top_of_bg"] is True
    pic = run["added_picture"]
    assert pic["plane"] == "background"
    # Fitted to the photo frame (0.125 .. 0.875) at the picture's 2:1 shape.
    assert pic["fx"] == pytest.approx(0.125) and pic["fw"] == pytest.approx(0.75)
    assert pic["fh"] == pytest.approx(0.75 * (32000 / 18000) / 2)


def test_stacking_stays_in_the_plane(run: dict) -> None:
    assert run["front_in_bg"] is True
    assert run["move_to_clamped"] is True
    assert run["back_in_fg"] is True
    assert run["move_to_fg_clamped"] is True


def test_move_to_background_and_back(run: dict) -> None:
    assert run["move_result"] == {
        "moved": ["fgR"],
        "refused": [{"id": "b3", "reason": "Chips stay in the foreground"}],
    }
    assert run["move_steps"] == 1
    assert run["plane_moved_signal"] == "background:1"
    assert run["fgR_after"] == ["background", True]
    assert run["fgR_undone"] == ""
    assert run["back_to_fg"] == ["", True]
    assert run["back_to_fg_moved"] == ["fgR"]


def test_lock_clear_and_view_steps(run: dict) -> None:
    assert run["lock_steps"] == 1
    assert run["plane_locked"] is True
    assert run["bg_row_locked"] is True
    assert run["clear"] == [{"first": 0, "last": -1}, 1]
    assert run["clear_undone"] is True
    assert run["view_steps"] == 0


def test_undo_steps_hold_no_photo(run: dict) -> None:
    assert run["snap_keys"] == ["guidesX", "guidesY", "nodes", "printArea"]


def test_picture_look_and_reset_shape(run: dict) -> None:
    look, opacity, steps = run["look"]
    # Grey is an amount, clamped to 0..1 (7 asked).
    assert look == {"bright": 0.3, "grey": 1}
    assert run["look_url"].endswith('#{"bright":0.3,"contrast":0,"grey":1}')
    assert opacity == 0.6
    assert steps == 1
    assert run["reset_shape"] == [None, None, None, 0]


def test_chip_follows_a_background_picture(run: dict) -> None:
    assert run["chip_followed"] is True


def test_background_row_eye_and_opacity_are_screen_only(run: dict) -> None:
    assert run["bg_hidden_visible"] is False
    assert run["bg_view_opacity"] == pytest.approx(0.5)
    assert run["bg_export_opacity"] == 1
