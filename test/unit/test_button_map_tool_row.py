# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Button Map's tool row (Chips, Properties, Layers, Command Palette),
checked in the running program off-screen (button_map_tool_row_smoke.py,
its own process and user folder).

- Each button opens and hides its tool; Chips (so a new user sees the
  pool) and Properties start open and pinned, the others hidden.
- Unpinned tools hide when the map is clicked; pinned ones stay.
- An unlocked button moves along the row; a locked one stays.
- A button let go anywhere on the row snaps to the edges, middle or a small
  grid and goes to the nearest free spot; Reset Tool Row centres them again.
- The status line (view, photo size, module file) is one slim row at the
  bottom, and the pool docks just above the tool row.
- What is open, pinned and locked, and the order, are saved.
- A second row under the menus, always shown (empty at first), 10 px from
  the map as the bottom row is; a button dragged onto it moves there with
  its panel's dock; the chip pool docks under it, can be dragged to the
  other edge on its own (unlocked), and stays when locked; rows and docks
  are saved; Reset Tool Rows puts everything on the bottom row again.
- The view zooms out to 50%; Zoom to Fit Page still fills the view.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

_ROOT = pathlib.Path(__file__).parents[2]
_ORDER = ["chips", "props", "layers", "palette", "printArea"]


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    env = dict(os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen")
    fonts = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    env.setdefault("QT_QPA_FONTDIR", fonts)
    done = subprocess.run(
        [sys.executable, str(_ROOT / "test" / "unit" / "button_map_tool_row_smoke.py")],
        cwd=_ROOT, env=env, capture_output=True, text=True, timeout=120,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, done.stdout[-1500:] + done.stderr[-1500:]
    return json.loads(lines[0][len("RESULT "):])


def _shown(chips: bool, props: bool, layers: bool, palette: bool, order: list) -> dict:
    return {"chips": chips, "props": props, "layers": layers, "palette": palette,
            "order": order}


def test_chips_and_properties_start_open(run: dict) -> None:
    assert run["0-first-edit"] == _shown(True, True, False, False, _ORDER)


def test_buttons_open_and_hide_their_tools(run: dict) -> None:
    assert run["1-edit"] == _shown(False, True, False, False, _ORDER)
    assert run["2-chips-open"] == _shown(True, True, False, False, _ORDER)
    assert run["8-palette"]["palette"] is True
    assert run["9-palette-closed"]["palette"] is False


def test_a_map_click_hides_unpinned_tools(run: dict) -> None:
    assert run["3-map-click"] == _shown(False, True, False, False, _ORDER)
    assert run["4-chips-pinned-layers-open"] == _shown(True, True, True, False, _ORDER)
    assert run["5-map-click"] == _shown(True, True, False, False, _ORDER)


def test_unlocked_buttons_move_locked_ones_stay(run: dict) -> None:
    moved = ["palette", "chips", "props", "layers", "printArea"]
    assert run["6-moved"]["order"] == moved
    assert run["7-locked-move"]["order"] == moved


def test_buttons_go_anywhere_on_the_row(run: dict) -> None:
    gap = run["gap"]
    # Let go near the left edge: snapped to it.
    assert abs(run["palette-left"]["palette"] - gap) < 1
    # Let go onto another button: beside it, not on it.
    places, widths = run["chips-onto-palette"], run["widths"]
    spans = sorted((places[t], places[t] + widths[t]) for t in places)
    assert all(a[1] + gap - 1 <= b[0] for a, b in zip(spans, spans[1:]))
    assert all(0 <= x and x + widths[t] <= run["row-width"] for t, x in places.items())
    # Reset: together and centred again.
    assert run["reset"] == run["centred"]


def test_status_line_and_docked_pool(run: dict) -> None:
    assert run["status-height"] <= 24
    assert run["pool-bottom-gap"] <= 10


def test_the_row_is_saved(run: dict) -> None:
    saved = run["saved"]
    # Options is on the top row (saved in the same order).
    order = [t for t in saved["order"] if t != "options"]
    assert order == ["palette", "chips", "props", "layers", "printArea"]
    assert saved["items"]["chips"]["pinned"] is True
    assert saved["items"]["palette"]["locked"] is True
    assert saved["items"]["props"]["pinned"] is True


def test_the_top_row_is_always_there(run: dict) -> None:
    assert run["top-row"]["visible"] is True
    assert run["top-row"]["height"] >= 24
    # Options starts there; the rest on the bottom row.
    assert run["top-row"]["tools"] == 1
    # 10 px between the map and each row.
    assert all(abs(g - run["dp10"]) <= 1 for g in run["gaps"]), run["gaps"]


def test_a_button_moves_to_the_top_row_with_its_panel(run: dict) -> None:
    side, dock, top, bottom = run["chips-up"]
    assert (side, dock) == ("top", "top")
    assert sorted(top) == ["chips", "options"] and "chips" not in bottom
    # The pool reaches the top row, its tab over it.
    assert abs(run["pool-at-top"]) <= 1
    assert run["tab-over-pool"] is True


def test_the_pool_resizes_and_stays_with_its_tab(run: dict) -> None:
    assert abs(run["pool-resized"] - 60) <= 2
    assert run["pool-stays"] == ["top", 0]
    assert run["pool-locked"] == 0


def test_rows_and_docks_are_kept_and_reset(run: dict) -> None:
    assert run["kept"] == ["top", 0]
    items = run["saved-top"]["items"]["chips"]
    assert items["side"] == "top" and items["h"] > 0
    # Each back on the row it starts on (Options on the top one), sizes
    # forgotten.
    assert run["reset-rows"] == [1, True]


def test_side_rows_hold_tabs_with_their_panels(run: dict) -> None:
    rows = run["side-rows"]
    assert rows["visible"] == [True, True]
    assert all(24 <= w <= 34 for w in rows["width"])
    # 10 px between the map and each side row; the side rows run between
    # the top and bottom rows.
    assert all(abs(g - run["dp10"]) <= 1 for g in rows["gaps"]), rows["gaps"]
    assert rows["between"] == [0, 0]
    # A tab dragged onto the left row: there, upright; its panel beside it,
    # joined, resized by its edge facing the map; Reset puts it back.
    assert run["layers-left"] == ["left", ["layers"]]
    assert run["tab-upright"] is True
    assert abs(run["layers-pane"]["joined"]) <= 1
    assert run["layers-pane"]["beside-tab"] is True
    assert abs(run["layers-wider"] - 40) <= 3
    assert run["layers-reset"] == "bottom"


def test_the_view_zooms_out_to_half(run: dict) -> None:
    zoom, pct = run["page-zoom"]
    assert zoom == 1 and abs(pct - 0.75) < 0.001
    assert run["out-most"] == 50


def test_pin_and_lock_have_their_icons() -> None:
    # The icons are font characters, kept as \u escapes: written out, they
    # were lost once in an edit and the buttons showed no pin or lock.
    import re

    row = (_ROOT / "qml" / "ToolRow.qml").read_text(encoding="utf-8")
    for flag in ("pinned", "locked"):
        found = re.search(rf'text: _btn\.{flag} \? "([^"]*)" : "([^"]*)"', row)
        assert found, flag
        icons = found.groups()
        assert all(re.fullmatch(r"\\u[0-9A-F]{4}", icon) for icon in icons), flag
