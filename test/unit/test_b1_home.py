# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""D-FIXLIST-B1 items 6 and 10 in the running program off-screen
(b1_home_smoke.py, its own process and user folder):

6: Home's page bar puts Compact view, Layout and its list together on the
   left right after the divider (01 S58a), at a wide and the narrowest
   window, 100 % and 150 % UI scale; no Undo bar (D-03-HOME-BAND).
10: Home Undo / Redo: card size, order and stacks, card picture (the file
   comes back), Reset Card Layout, Compact view, Layout and the divider;
   one action is one step; Ctrl+Z, Ctrl+Y, Ctrl+Shift+Z (not while typing),
   the empty-space menu's and the card menu's header pairs; about 50 steps;
   another profile clears them. Hide Selected Cards and Reset Size of
   Selected Cards are one step each (D-03-HOME-BAND)."""

from __future__ import annotations

import importlib.util
import pathlib
from typing import Any

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SMOKE = _ROOT / "test" / "unit" / "b1_home_smoke.py"


def _harness() -> Any:  # noqa: ANN401
    spec = importlib.util.spec_from_file_location(
        "_b1_home_harness", _ROOT / "test" / "journeys" / "_harness.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def runs(tmp_path_factory: pytest.TempPathFactory) -> dict:
    harness = _harness()
    found = {}
    for scale in (100, 150):
        home = tmp_path_factory.mktemp(f"b1-home-{scale}")
        found[scale] = harness.run_journey(_SMOKE, home, str(scale))
    return found


def _get(out: dict, key: str) -> Any:  # noqa: ANN401
    why = f"{out.get('error')}\n{out.get('traceback', '')}\n{out.get('_stderr', '')}"
    assert key in out, why
    return out[key]


@pytest.mark.parametrize("scale", [100, 150])
@pytest.mark.parametrize("width", ["barWide", "barNarrow"])
def test_page_bar_controls_sit_left_after_the_divider(
    runs: dict, scale: int, width: str
) -> None:
    out = runs[scale]
    assert _get(out, "uiScale") == scale
    bar = _get(out, width)
    assert bar["compact"] is not None and bar["divider"] is not None, bar
    # Right after the divider: its margin and the row's spacing, no spacer.
    assert 0 <= bar["compact"] - bar["divider"] <= bar["dp40"], bar
    # Together, with the row's gap; no Undo bar (D-03-HOME-BAND).
    assert 0 <= bar["labelLeft"] - bar["compactRight"] <= bar["dp16"], bar
    assert 0 <= bar["layoutLeft"] - bar["labelRight"] <= bar["dp16"], bar
    assert bar["undoBar"] is False, bar


def test_compact_view_undo_and_redo_keys(runs: dict) -> None:
    seen = _get(runs[100], "compact")
    assert seen["after"] is True and seen["steps"] == 1
    assert seen["last"] == "Compact View On"
    assert seen["ctrlZ"] is False and seen["boxAfterUndo"] is False
    assert seen["undone"] == "Compact View On"
    assert seen["ctrlY"] is True
    assert seen["ctrlShiftZ"] is True


def test_typing_keeps_ctrl_z(runs: dict) -> None:
    typing = _get(runs[100], "typing")
    assert typing["compact"] is True and typing["steps"] == typing["before"]
    assert typing["afterFieldGone"] is False


def test_layout_and_divider_undo(runs: dict) -> None:
    lay = _get(runs[100], "layout")
    assert lay["after"] == "vertical"
    assert lay["emptyHeader"] == '[["Undo",true],["Redo",false]]'
    assert lay["tip"] == "Layout: Side by side"
    assert lay["undone"] == "none" and lay["redone"] == "vertical"
    div = lay["divider"]
    assert div["moved"] == pytest.approx(0.3) and div["steps"] == 1
    assert div["undone"] == pytest.approx(div["start"])


def test_card_size_order_and_stack_undo(runs: dict) -> None:
    cards = _get(runs[100], "cards")
    leaders = _get(runs[100], "leaders")
    a, b, c = leaders[:3]
    assert cards["sized"] == 400 and cards["sizeUndone"] == 0
    assert cards["reset"] == 0 and cards["resetUndone"] == 400
    assert cards["resetAll"] == 0 and cards["resetAllUndone"] == 400
    assert cards["dragged"] == [c, a, b] and cards["dragSteps"] == 1
    assert cards["dragUndone"] == [a, b, c]
    assert cards["stacked"] == [a, b] and cards["unstacked"] == [a]
    assert cards["unstackUndone"] == [a, b]
    assert cards["unstackAll"] == [a] and cards["unstackAllUndone"] == [a, b]
    assert cards["cleared"] == [[a], 0] and cards["clearSteps"] == 1
    assert cards["clearUndone"] == [[a, b], 400]


def test_hide_and_reset_size_of_selected_cards_are_one_step(runs: dict) -> None:
    sel = _get(runs[100], "selected")
    assert sel["reset"] == [0, 0] and sel["resetSteps"] == 1
    assert sel["resetTip"] == "Reset Size of Selected Cards"
    assert sel["resetUndone"] == [400, 420]
    assert sel["hidden"] == sel["ab"] and sel["shownAfterHide"] == []
    assert sel["hideSteps"] == 1
    assert sel["hideTip"] == "Hide Selected Cards"
    assert sel["hiddenUndone"] == [] and sorted(sel["shownUndone"]) == sel["ab"]
    assert sel["hiddenRedone"] == sel["ab"]


def test_undo_of_hide_selected_brings_back_only_its_cards(runs: dict) -> None:
    sel = _get(runs[100], "selected")
    assert sel["onlyStepUndone"] == sel["c"]
    assert sel["onlyStepRedone"] == sel["abc"]


def test_card_picture_undo_brings_the_file_back(runs: dict) -> None:
    pic = _get(runs[100], "picture")
    assert pic["added"] and pic["photo"] and pic["files"]
    assert pic["addTip"] == "Add Image"
    assert pic["removed"] and not pic["photoRemoved"] and pic["filesRemoved"] == {}
    assert pic["filesBack"] == pic["files"] and pic["photoBack"]
    assert pic["filesAddUndone"] == {} and not pic["photoAddUndone"], pic
    assert pic["filesRedone"] == pic["files"] and pic["photoRedone"]
    # Not even once while the card was still reading the picture.
    assert pic["logged"] == []


def test_card_menu_has_undo_redo_beside_its_title(runs: dict) -> None:
    menu = _get(runs[100], "menu")
    assert menu["header"] == '[["Undo",true],["Redo",true]]'
    assert menu["stepsAfter"] == menu["stepsBefore"] - 1


def test_about_fifty_steps_and_a_profile_switch_clears(runs: dict) -> None:
    assert _get(runs[100], "cap") == 50
    assert _get(runs[100], "afterProfile") == {"steps": 0, "canRedo": False}
