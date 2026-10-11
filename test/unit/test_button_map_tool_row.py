# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Button Map's tool rows (Properties, Command Palette, Print Area on
the bottom one, Options on the top one) and its side panels (Chips on the
left, Layers on the right, 07 S128; their own end-to-end test is
test_side_panels_e2e.py), checked in the running program off-screen
(button_map_tool_row_smoke.py, its own process and user folder).

- Each button opens and hides its tool; Properties starts open and pinned,
  the others hidden; the Chips side panel starts out and pinned, Layers
  folded.
- Unpinned tools (and the unpinned Layers panel) hide when the map is
  clicked; pinned ones stay.
- An unlocked button moves along the row; a locked one stays.
- A button let go anywhere on the row snaps to the edges, middle or a small
  grid and goes to the nearest free spot; Reset Tool Row centres them again.
- The status line (view, photo size, module file) is one slim row at the
  bottom.
- What is open, pinned and locked, and the order, are saved.
- A second row under the menus, always shown (empty at first), 10 px from
  the map as the bottom row is; a button dragged onto it moves there with
  its panel's dock; a panel on the top row docks under it, resizes by its
  edge (unlocked), and stays when locked; rows, docks and the side panels'
  width, pin and open state are saved; Reset Tool Rows puts everything back
  as it starts, the side panels too (07 S99).
- There are no left or right rows; a saved placement on one loads on the
  bottom row (07 S99, S128).
- The view zooms out to 50%; Zoom to Fit Page still fills the view.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest

_ROOT = pathlib.Path(__file__).parents[2]
_ORDER = ["props", "palette", "printArea"]


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    env = dict(os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen")
    fonts = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    env.setdefault("QT_QPA_FONTDIR", fonts)
    done = proc_tree.run(
        [sys.executable, str(_ROOT / "test" / "unit" / "button_map_tool_row_smoke.py")],
        cwd=_ROOT, env=env, text=True, timeout=120,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, done.stdout[-1500:] + done.stderr[-1500:]
    return json.loads(lines[0][len("RESULT "):])


def _shown(chips: bool, props: bool, layers: bool, palette: bool, order: list) -> dict:
    return {"chips": chips, "props": props, "layers": layers, "palette": palette,
            "order": order}


def test_chips_and_properties_start_open(run: dict) -> None:
    # Chips is the side panel, out and pinned; Properties on the row.
    assert run["0-first-edit"] == _shown(True, True, False, False, _ORDER)


def test_buttons_open_and_hide_their_tools(run: dict) -> None:
    assert run["1-edit"] == _shown(True, False, False, False, _ORDER)
    assert run["2-props-open"] == _shown(True, True, False, False, _ORDER)
    assert run["8-palette"]["palette"] is True
    assert run["9-palette-closed"]["palette"] is False


def test_a_map_click_hides_unpinned_tools(run: dict) -> None:
    assert run["3-map-click"] == _shown(True, False, False, False, _ORDER)
    assert run["4-props-pinned-layers-open"] == _shown(True, True, True, False, _ORDER)
    assert run["5-map-click"] == _shown(True, True, False, False, _ORDER)


def test_unlocked_buttons_move_locked_ones_stay(run: dict) -> None:
    moved = ["palette", "props", "printArea"]
    assert run["6-moved"]["order"] == moved
    assert run["7-locked-move"]["order"] == moved


def test_buttons_go_anywhere_on_the_row(run: dict) -> None:
    gap = run["gap"]
    # Let go near the left edge: snapped to it.
    assert abs(run["palette-left"]["palette"] - gap) < 1
    # Let go onto another button: beside it, not on it.
    places, widths = run["props-onto-palette"], run["widths"]
    spans = sorted((places[t], places[t] + widths[t]) for t in places)
    assert all(a[1] + gap - 1 <= b[0] for a, b in zip(spans, spans[1:]))
    assert all(0 <= x and x + widths[t] <= run["row-width"] for t, x in places.items())
    # Reset: together and centred again.
    assert run["reset"] == run["centred"]


def test_status_line(run: dict) -> None:
    assert run["status-height"] <= 24


def test_the_row_is_saved(run: dict) -> None:
    saved = run["saved"]
    # Options is on the top row (saved in the same order).
    order = [t for t in saved["order"] if t != "options"]
    assert order == ["palette", "props", "printArea"]
    # Chips and Layers are side panels, not row tools.
    assert "chips" not in saved["items"] and "layers" not in saved["items"]
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
    side, dock, top, bottom = run["props-up"]
    assert (side, dock) == ("top", "top")
    assert sorted(top) == ["options", "props"] and "props" not in bottom
    # A top-row panel (Options) reaches the top row, its tab over it.
    assert abs(run["pool-at-top"]) <= 1
    assert run["tab-over-pool"] is True


def test_a_panel_resizes_and_stays_with_its_tab(run: dict) -> None:
    assert abs(run["pool-resized"] - 60) <= 2
    assert run["pool-stays"] == ["top", 0]
    assert run["pool-locked"] == 0


def test_rows_and_docks_are_kept_and_reset(run: dict) -> None:
    assert run["kept"] == ["top", 0]
    items = run["saved-top"]["items"]
    assert items["props"]["side"] == "top" and items["options"]["h"] > 0
    # Each back on the row it starts on (Options on the top one), sizes
    # forgotten.
    assert run["reset-rows"] == [1, True]


def test_side_panel_states_are_kept_and_reset(run: dict) -> None:
    dp = run["dp10"] / 10
    chips, layers = run["sides-kept"]
    assert abs(chips["width"] - 400 * dp) <= 1
    assert not chips["pinned"] and not chips["open"]
    assert abs(layers["width"] - 350 * dp) <= 1 and layers["pinned"] and layers["open"]
    assert set(run["sides-saved"]) >= {"chips", "layers"}
    # Reset Tool Rows: as they start.
    chips, layers = run["sides-reset"]
    assert abs(chips["width"] - 260 * dp) <= 1 and chips["pinned"] and chips["open"]
    assert abs(layers["width"] - 300 * dp) <= 1
    assert not layers["pinned"] and not layers["open"]


def test_no_left_or_right_rows(run: dict) -> None:
    assert run["rows"] == ["bottom", "top"]
    top, bottom = run["row-tools"]
    assert "chips" not in top + bottom and "layers" not in top + bottom
    # Saved on a removed row: loads on the bottom row, no conversion.
    assert run["old-side-rows"] == ["bottom", "bottom"]


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
