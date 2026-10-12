# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Device Mapping Editor's side panels in the window (07 S99, S128-S131, S135,
D-07-SIDE-PANELS, D-07-SIDE-DRAWER), checked in the running program
off-screen with mouse clicks (side_panels_window_smoke.py, its own process
and user folder).

- There are no tool rows at all.
- Outside Edit the drawers are hidden; editing, Chips starts pinned and out,
  Layers folded to its ajar edge (7 px at 100%) on the window's right edge.
- Pinned, a panel narrows the map; unpinned, it is drawn over the map, and a
  map click or the other strip's click folds it.
- Background mode folds Chips and brings it back.
- A narrow window folds Chips first, then Layers, and brings them back; a
  user's own choice in between stays.
- Properties sits under Layers while something is selected, with a divider
  between them; the divider's share and View > Properties (F4) are kept.
- Width, pin and open are kept in the Device Mapping Editor settings (DeviceMapOptions)
  for the next window; View > Reset Panels puts them, the divider and
  Properties back.
- The status line is one slim row.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

_ROOT = pathlib.Path(__file__).parents[2]
_SMOKE = "side_panels_window_smoke.py"
# The folded drawer's ajar edge at 100% (07 S129, D-07-SIDE-DRAWER).
STRIP = 7


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    env = dict(os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen")
    fonts = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    env.setdefault("QT_QPA_FONTDIR", fonts)
    done = proc_tree.run(
        [sys.executable, str(_ROOT / "test" / "unit" / _SMOKE)],
        cwd=_ROOT, env=env, text=True, timeout=120,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, smoke_report.explain(done)
    return json.loads(lines[0][len("RESULT "):])


def _open(s: dict, side: str) -> tuple[bool, bool]:
    return s[side]["open"], s[side]["pinned"]


def _map_fits(s: dict) -> None:
    # The map area is the row less each panel's taken width (and its margins).
    assert s["leftSlot"] == round(s["chips"]["taken"])
    assert s["rightSlot"] == round(s["layers"]["taken"])
    assert s["map"] == s["row"] - s["leftSlot"] - s["rightSlot"] - 20


def test_no_tool_rows(run: dict) -> None:
    # Left, right, top, bottom: none left (D-07-MENUBAR).
    assert run["tool-rows"] == [False, False, False, False]


def test_folded_layers_is_ajar_on_the_window_edge(run: dict) -> None:
    out_of_edge, edge = run["layers-edge"]
    assert out_of_edge == edge == STRIP


def test_status_line_is_one_slim_row(run: dict) -> None:
    assert run["status-height"] <= 24


def test_only_while_editing(run: dict) -> None:
    s = run["not-editing"]
    assert s["chips"]["shown"] is False and s["layers"]["shown"] is False
    assert s["leftSlot"] == 0 and s["rightSlot"] == 0
    e = run["editing"]
    assert e["chips"]["shown"] is True and e["layers"]["shown"] is True
    assert _open(e, "chips") == (True, True) and e["chips"]["pool"] is True
    assert _open(e, "layers") == (False, False)
    assert e["layers"]["taken"] == STRIP
    _map_fits(e)
    left = run["left-edit"]
    assert left["chips"]["shown"] is False and left["layers"]["shown"] is False
    assert left["leftSlot"] == 0 and left["rightSlot"] == 0


def test_unpinned_is_over_the_map_and_folds_on_a_map_click(run: dict) -> None:
    before, out, after = run["editing"], run["layers-strip"], run["map-click"]
    assert _open(out, "layers") == (True, False)
    assert out["map"] == before["map"]
    _map_fits(out)
    assert _open(after, "layers") == (False, False)
    assert _open(after, "chips") == (True, True)


def test_pinned_narrows_the_map(run: dict) -> None:
    unpinned, pinned = run["chips-unpinned"], run["chips-pinned"]
    assert _open(unpinned, "chips") == (True, False)
    # Pinned it takes its whole width; unpinned only its ajar edge.
    assert pinned["map"] == unpinned["map"] - (260 - STRIP)
    _map_fits(unpinned)
    _map_fits(pinned)
    both = run["both-pinned"]
    assert _open(both, "layers") == (True, True)
    assert both["map"] == pinned["map"] - (300 - STRIP)
    _map_fits(both)


def test_the_other_strip_folds_an_unpinned_panel(run: dict) -> None:
    assert _open(run["other-strip"], "chips") == (False, False)
    assert _open(run["other-strip"], "layers") == (True, False)
    assert _open(run["other-strip-back"], "chips") == (True, False)
    assert _open(run["other-strip-back"], "layers") == (False, False)


def test_background_mode_folds_chips_and_brings_it_back(run: dict) -> None:
    bg, fg = run["bg-mode"], run["fg-mode"]
    assert bg["chips"]["open"] is False and bg["chips"]["pool"] is False
    # Not kept: the next window has Chips as the user left it.
    assert bg["saved"]["chips"]["open"] is True
    assert _open(fg, "chips") == (True, True)


def test_a_narrow_window_folds_chips_first_then_layers(run: dict) -> None:
    mid = run["mid"]
    assert _open(mid, "chips") == (False, False)
    assert _open(mid, "layers") == (True, True)
    _map_fits(mid)
    assert _open(run["mid-wide"], "chips") == (True, True)
    narrow = run["narrow"]
    assert _open(narrow, "chips") == (False, False)
    assert _open(narrow, "layers") == (False, False)
    # The automatic folds aren't kept.
    assert narrow["saved"]["chips"]["pinned"] is True
    assert narrow["saved"]["layers"]["pinned"] is True
    wide = run["wide-again"]
    assert _open(wide, "chips") == (True, True)
    assert _open(wide, "layers") == (True, True)


def test_a_users_own_choice_stays_when_there_is_room(run: dict) -> None:
    assert _open(run["narrow-user-open"], "chips") == (True, False)
    kept = run["wide-user-kept"]
    assert _open(kept, "chips") == (True, False)
    assert _open(kept, "layers") == (True, True)


def test_properties_under_layers_while_something_is_selected(run: dict) -> None:
    none, sel = run["props-none"]["props"], run["props-selected"]["props"]
    assert none["on"] is True and none["shown"] is False
    assert none["panel"] is False and none["divider"] is False
    assert none["layersH"] == none["bodyH"]
    assert sel["shown"] is True and sel["panel"] is True and sel["divider"] is True
    # Layers takes its share above the divider (0.6 at first).
    assert sel["split"] == 0.6
    assert abs(sel["layersH"] - sel["bodyH"] * 0.6) <= 6


def test_the_divider_drag_is_kept(run: dict) -> None:
    dragged = run["props-dragged"]["props"]
    assert abs(dragged["split"] - 0.7) <= 0.02
    assert dragged["savedSplit"] == dragged["split"]
    assert dragged["layersH"] > run["props-selected"]["props"]["layersH"]
    again = run["reopened"]["props"]
    assert again["split"] == dragged["split"]


def test_f4_hides_properties_and_it_is_kept(run: dict) -> None:
    f4 = run["props-f4"]["props"]
    assert f4["on"] is False and f4["shown"] is False and f4["panel"] is False
    assert f4["savedShown"] is False
    assert f4["layersH"] == f4["bodyH"]
    # The next window: still hidden.
    assert run["reopened"]["props"]["on"] is False


def test_kept_for_the_next_window_and_reset_panels(run: dict) -> None:
    again = run["reopened"]
    assert again["layers"]["width"] == 333
    assert _open(again, "layers") == (True, True)
    # Pinned before the narrow window folded it: the pin is kept (07 S131).
    assert _open(again, "chips") == (True, True)
    assert again["saved"]["layers"] == {"width": 333, "pinned": True, "open": True}
    # View > Reset Panels, the menu item.
    assert run["reset-items"] == ["Reset Panels"]
    reset = run["reset"]
    assert _open(reset, "chips") == (True, True)
    assert _open(reset, "layers") == (False, False)
    assert reset["layers"]["width"] == 300
    assert reset["saved"]["chips"] == {"width": 260, "pinned": True, "open": True}
    assert reset["saved"]["layers"] == {"width": 300, "pinned": False, "open": False}
    # The divider and Properties as they start.
    assert reset["props"]["split"] == reset["props"]["savedSplit"] == 0.6
    assert reset["props"]["on"] is True and reset["props"]["savedShown"] is True
    _map_fits(reset)
