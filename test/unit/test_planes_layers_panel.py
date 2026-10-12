# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Device Mapping Editor's Layers panel with the background and foreground planes
(07 S119, S120, S102, S44; D-07-BACKGROUND-PLANES, D-07-PLANES-ANSWERS P2a,
P4a), checked in the running program off-screen
(planes_layers_panel_smoke.py, its own process and user folder).

- Foreground mode: the list ends with the folded Background row (dmeBgRow).
  Its eye (dmeBgRowEye) hides the background on screen only (the editor's
  bgViewHidden, no Undo step), its lock (dmeBgRowLock) locks every background
  layer (setPlaneLocked), its Opacity slider (dmeBgRowOpacity) is the
  editor's bgViewOpacity, and a double-click edits the background.
- Background mode: only background rows, no Background row, toggles
  Shapes · Lines · Pictures · Text only; no groups.
- No Photo toggle and no "Background photo" row.
- Dragging a row under the last keeps it in its own plane.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest

_ROOT = pathlib.Path(__file__).parents[2]
_PANEL = _ROOT / "qml" / "RigLayersPanel.qml"
_FG_KINDS = ["All", "Chips", "Groups", "Hotspots", "Leaders", "Shapes", "Lines",
             "Pictures", "Text", "Tables"]
_BG_KINDS = ["All", "Shapes", "Lines", "Pictures", "Text"]


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    env = dict(os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen")
    fonts = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    env.setdefault("QT_QPA_FONTDIR", fonts)
    done = proc_tree.run(
        [sys.executable, str(_ROOT / "test" / "unit" / "planes_layers_panel_smoke.py")],
        cwd=_ROOT, env=env, text=True, timeout=120,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, done.stdout[-1500:] + done.stderr[-1500:]
    return json.loads(lines[0][len("RESULT "):])


def test_no_photo_row_or_toggle_in_the_panel_source() -> None:
    text = _PANEL.read_text(encoding="utf-8")
    for word in ("Background photo", "\"photo\"", "setPhotoFlag", "photoHidden",
                 "photoLocked", "label: \"Photo\""):
        assert word not in text, word


def test_no_qml_warnings(run: dict) -> None:
    assert run["warnings"] == []


# --- the real editor ----------------------------------------------------------

def test_real_editor_has_planes(run: dict) -> None:
    assert run["real-has-planes"] is True
    assert run["real-fg-plane"] == "foreground"
    assert run["real-photo-rows"] == 0


def test_real_foreground_ends_with_the_background_row(run: dict) -> None:
    assert run["real-fg-bgrow"] == {"name": "Background", "last": True}
    assert run["real-fg-bgrow-item"] is True
    assert run["real-fg-parts"] == [True, True, True]
    assert run["real-fg-kinds"] == _FG_KINDS


def test_real_eye_slider_and_double_click_reach_the_editor(run: dict) -> None:
    assert run["real-eye"] == [False, True]
    assert run["real-eye-back"] is False
    assert run["real-slider-follows"] == pytest.approx(0.4)
    assert run["real-dblclick-plane"] == "background"


def test_real_background_mode_has_no_background_row_nor_chips(run: dict) -> None:
    assert run["real-bg-bgrow"] is None
    assert run["real-bg-kinds"] == _BG_KINDS
    assert run["real-bg-groups"] == 0


# --- the panel, with a stand-in editor ----------------------------------------

def test_foreground_rows_and_toggles(run: dict) -> None:
    assert run["fg-rows"] == ["Fire", "Box", "Label", "Background"]
    assert run["fg-kinds"] == _FG_KINDS
    # Taller than a layer row: the Opacity slider is its second line.
    assert run["fg-trash-shown"] > run["rowH"]


def test_eye_is_a_view_setting_not_an_edit(run: dict) -> None:
    hidden, calls, line = run["eye"]
    assert hidden is True
    assert calls == []  # no editor call: no Undo step
    assert line == "Background [hidden]"
    assert run["eye-back"] is False


def test_lock_locks_every_background_layer(run: dict) -> None:
    assert run["lock"] == ["setPlaneLocked background true",
                           "setPlaneLocked background false"]
    assert run["lock-lit"] is False


def test_opacity_slider_is_the_editor_setting(run: dict) -> None:
    assert 0.05 < run["slider-low"] < 0.4
    assert run["slider-calls"] == []
    assert run["slider-follows"] == pytest.approx(0.75)


def test_clicking_the_background_row_selects_nothing(run: dict) -> None:
    assert run["bg-click"] == []


def test_double_click_edits_the_background(run: dict) -> None:
    assert run["fg-chip-rows"] == ["Fire", "Background"]
    assert run["dbl-plane"] == "background"


def test_background_mode_lists_only_its_rows_and_kinds(run: dict) -> None:
    assert run["bg-no-bgrow"] is True
    assert run["bg-kinds"] == _BG_KINDS
    # The Chips toggle from Foreground mode doesn't filter the background.
    assert run["bg-lit"] == ["all"]
    assert run["bg-state"] == "all"  # no filter: the panel's plain "all"
    assert run["bg-rows"] == ["Stick photo", "Panel"]
    assert run["bg-pic-rows"] == ["Stick photo"]
    # All turns off this plane's toggles; Foreground keeps its Chips.
    assert run["bg-all-kinds"] == ["chip"]
    assert run["fg-kinds-kept"] == [["chip"], ["chip"]]


def test_dropping_under_the_last_row_stays_in_the_plane(run: dict) -> None:
    assert run["bg-drop"] == ["moveNodeTo p1 0"]
    assert run["fg-drop"] == ["moveNodeTo c1 2"]


def test_row_menu_moves_an_item_to_the_background(run: dict) -> None:
    # 07 S121: the row's right-click menu has Move to Background (and Move to
    # Foreground, hidden while it has nothing to do) before Delete; a click
    # moves the item, and its row leaves the foreground list.
    assert run["real-menu-has-items"] is True
    menu = run["real-menu"]
    move = [i for i, t in enumerate(menu) if t.startswith("Move to Background")]
    delete = [i for i, t in enumerate(menu) if t.startswith("Delete")]
    assert move and delete and move[0] < delete[0], menu
    assert "Ctrl+Shift+B" in menu[move[0]]
    assert run["real-moved"] == [True, "foreground"]
    assert run["real-moved-row"] == -1


def test_background_row_menu_has_no_move_items(run: dict) -> None:
    menu = run["real-bg-menu"]
    assert not any(t.startswith("Move to") for t in menu), menu
