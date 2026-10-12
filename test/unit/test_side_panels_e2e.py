# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Device Mapping Editor's side panels, end to end in the running program
off-screen (side_panels_e2e_smoke.py, its own process and user folder),
with real clicks and drags (07 S99, S128-S131, D-07-SIDE-PANELS,
D-07-SIDE-DRAWER).

- Chips is the left side panel, Layers the right one (S128).
- Outside Edit no drawers; editing brings them as they were left (S130).
- Folded, a drawer is its own frame left ajar on its window edge (S129).
- Chips' drawer click brings it out at its width; unpinned it lies over the
  map, pinned the map narrows by exactly its width (S129).
- Unpinned Layers lies over the map and folds on a map click or the other
  drawer's click (S129).
- The inner edge resizes, up to the maximum; the width, pin and open state
  are kept in the Device Mapping Editor settings after closing and reopening the
  window (S99, S131).
- Background mode folds Chips and brings it back, without saving the fold
  (S130).
- A narrow window folds Chips first, then Layers; they come back when there
  is room (S131).
- View > Reset Panels puts the side panels back as they start (S99).
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


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    env = dict(os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen")
    fonts = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    env.setdefault("QT_QPA_FONTDIR", fonts)
    done = proc_tree.run(
        [sys.executable, str(_ROOT / "test" / "unit" / "side_panels_e2e_smoke.py")],
        cwd=_ROOT, env=env, text=True, timeout=150,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, smoke_report.explain(done)
    out = json.loads(lines[0][len("RESULT "):])
    assert out["found"] == ["left", "right"], out
    return out


def _near(a: float, b: float, tol: float = 2) -> bool:
    return abs(a - b) <= tol


def test_chips_left_layers_right(run: dict) -> None:
    assert run["titles"] == ["Chips", "Layers"]
    assert run["layers-holds-panel"] is True


def test_no_strips_outside_edit(run: dict) -> None:
    for got in run["before-edit"] + run["after-edit"]:
        assert got["available"] is False and got["visible"] is False, got
        assert got["takenWidth"] == 0


def test_editing_shows_the_strips_chips_out_and_pinned(run: dict) -> None:
    chips, layers = run["edit"]
    assert chips["available"] and chips["visible"]
    assert layers["available"] and layers["visible"]
    assert chips["open"] and chips["pinned"]
    assert not layers["open"]
    # As they start (put there when the window is up).
    assert _near(chips["panelWidth"], 260 * run["dp"], 1)
    assert _near(layers["panelWidth"], 300 * run["dp"], 1)
    # Folded: only its ajar edge (7 px at 100%).
    assert _near(layers["takenWidth"], 7 * run["dp"], 0.5)
    # Pinned and out: exactly its width, no strip beside it.
    assert _near(chips["takenWidth"], chips["shownWidth"], 0.5)


def test_folded_layers_is_its_frame_ajar_on_the_window_edge(run: dict) -> None:
    out_of_edge, frame_w, edge = run["layers-ajar"]
    assert _near(out_of_edge, edge, 0.5) and _near(edge, 7 * run["dp"], 0.5)
    # The whole drawer's frame, not a separate strip.
    assert _near(frame_w, run["edit"][1]["shownWidth"], 0.5)


def test_strip_brings_chips_out_at_its_width_over_the_map(run: dict) -> None:
    assert run["unpinned"]["pinned"] is False
    assert run["folded"]["open"] is False
    opened = run["strip-open"]
    assert opened["open"] and opened["overlay"]
    assert _near(run["strip-body-w"], opened["panelWidth"])
    # Over the map: the map keeps the width it had folded.
    assert _near(run["host-overlay"]["w"], run["host-folded"]["w"])
    # Folding gave the map the panel's room back.
    assert run["host-folded"]["w"] > run["host-edit"]["w"] + 0.5 * opened["panelWidth"]


def test_pinned_chips_narrow_the_map(run: dict) -> None:
    pinned = run["pinned"]
    assert pinned["pinned"] and pinned["open"] and not pinned["overlay"]
    # Folded it took its ajar edge; pinned it takes its whole width (no
    # strip beside it).
    grown = pinned["shownWidth"] - run["edit"][1]["takenWidth"]
    narrowed = run["host-folded"]["w"] - run["host-pinned"]["w"]
    assert _near(narrowed, grown, 1), (narrowed, pinned)
    assert _near(pinned["takenWidth"], pinned["shownWidth"], 0.5)
    # Nothing covered: the map starts after the panel.
    assert _near(run["host-pinned"]["x"] - run["host-folded"]["x"], grown, 1)


def test_unpinned_layers_lie_over_the_map(run: dict) -> None:
    layers = run["layers-open"]
    assert layers["open"] and layers["overlay"] and not layers["pinned"]
    host, body = run["host-layers"], run["layers-body"]
    assert _near(host["w"], run["host-pinned"]["w"])
    assert body["x"] < host["x"] + host["w"] and body["w"] > 0


def test_a_map_click_folds_unpinned_layers(run: dict) -> None:
    chips, layers = run["map-click"]
    assert layers["open"] is False
    assert chips["open"] is True  # pinned: stays


def test_the_other_drawer_folds_unpinned_layers(run: dict) -> None:
    assert run["layers-again"] is True
    # Chips folded by its arrow: Layers stays out.
    chips, layers = run["chips-folded"]
    assert chips["open"] is False and layers["open"] is True
    # Chips' drawer clicked: it comes out, Layers folds.
    chips, layers = run["other-strip"]
    assert chips["open"] is True
    assert layers["open"] is False


def test_the_inner_edge_resizes_up_to_the_maximum(run: dict) -> None:
    before, after = run["resized"]
    assert _near(after - before, 40, 3), run["resized"]
    width, top = run["at-max"]
    assert _near(width, top, 1)
    assert run["edit"][0]["minWidth"] < run["edit"][0]["maxWidth"]
    # Kept in logical px at 100%.
    assert _near(run["saved-sides"]["chips"]["width"], width / run["dp"], 1)


def test_background_mode_folds_chips_and_brings_it_back(run: dict) -> None:
    bg, chips = run["bg"]
    assert bg is True and chips["open"] is False
    # The automatic fold is not the user's: not saved.
    assert run["bg-saved"]["chips"]["open"] is True
    fg, chips = run["fg"]
    assert fg is False and chips["open"] is True


def test_a_narrow_window_folds_chips_then_layers(run: dict) -> None:
    start = run["narrow-start"]
    assert all(p["open"] and p["pinned"] for p in start), start
    sweep = run["sweep"]
    # Never Layers folded while Chips is still out.
    assert all(s["chips"] <= s["layers"] for s in sweep), sweep
    # Chips goes first.
    first = next((s for s in sweep if not (s["chips"] and s["layers"])), None)
    assert first is not None, sweep
    assert first["chips"] is False and first["layers"] is True, sweep
    # Narrowest: Layers goes too.
    assert sweep[-1]["layers"] is False, sweep
    # Room again: both back as they were.
    assert all(p["open"] and p["pinned"] for p in run["wide-again"]), run["wide-again"]


def test_kept_after_closing_and_reopening(run: dict) -> None:
    chips, layers = run["reopened"]
    assert _near(chips["panelWidth"], run["kept-width"], 1)
    assert chips["open"] and chips["pinned"]
    assert not layers["open"] and not layers["pinned"]


def test_reset_panels_resets_the_side_panels(run: dict) -> None:
    assert run["reset-items"] == 1
    chips, layers = run["reset"]
    dp = run["dp"]
    assert _near(chips["panelWidth"], 260 * dp, 1) and chips["pinned"] and chips["open"]
    assert _near(layers["panelWidth"], 300 * dp, 1)
    assert not layers["pinned"] and not layers["open"]
