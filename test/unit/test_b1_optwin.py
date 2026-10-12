# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Fix list item 4 (D-FIXLIST-B1): Device Map Options and Keyboard
Shortcuts, checked in the running program off-screen (b1_optwin_smoke.py,
its own process and user folder), at 100% and at a large UI scale.

- Both windows ask for a × the way Windows draws one for a Tool window
  (WindowSystemMenuHint with the close hint). Whether the × is drawn can
  only be seen on a real screen.
- Options has a pin, kept for next time; Reset Panels keeps it. Unpinned,
  going back to the Device Mapping Editor closes it; pinned, it stays.
- Its group list starts wide enough for every group name; the divider
  drags, the width is kept, and it stays between a short name and half the
  pane.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

from gremlin.ui import device_map_options as bmo

_ROOT = pathlib.Path(__file__).parents[2]


def _run(home: pathlib.Path, scale: int | None) -> dict:
    (home / "Gremlin Platforms").mkdir()
    env = dict(
        os.environ,
        USERPROFILE=str(home),
        QT_QPA_PLATFORM="offscreen",
        HTTPS_PROXY="http://127.0.0.1:9",
    )
    args = [sys.executable, str(_ROOT / "test" / "unit" / "b1_optwin_smoke.py")]
    if scale is not None:
        # The UI scale slider only counts with Windows scaling off.
        env["QT_ENABLE_HIGHDPI_SCALING"] = "0"
        args.append(str(scale))
    fonts = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    env.setdefault("QT_QPA_FONTDIR", fonts)
    done = proc_tree.run(args, cwd=_ROOT, env=env, text=True, timeout=120)
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, smoke_report.explain(done)
    return json.loads(lines[0][len("RESULT ") :])


@pytest.fixture(scope="module", params=[None, 175], ids=["100", "175"])
def run(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
) -> dict:
    return _run(tmp_path_factory.mktemp("home"), request.param)


def test_both_windows_ask_for_a_close_button(run: dict) -> None:
    want = {
        "Tool": True,
        "WindowTitleHint": True,
        "WindowSystemMenuHint": True,
        "WindowCloseButtonHint": True,
    }
    assert run["flags"] == {"options": want, "shortcuts": want}


def test_options_pin_is_kept_and_survives_reset_panels(run: dict) -> None:
    assert run["pin-shown"] is True
    assert run["pin-clicked"] is True
    assert run["pin-kept"] is True
    assert run["reset-keeps-pin"] == [True, True]
    assert run["unpin-kept"] is False


def test_options_closes_on_a_click_elsewhere_unless_pinned(run: dict) -> None:
    assert run["closed-by-shortcuts"] is True
    assert run["open-before-pin"] is True
    assert run["activated-map"] is True
    assert run["pinned-stays"] is True
    assert run["unpinned-closes-own"] is True
    # As a transient child of the Device Mapping Editor (how it opens) its `active`
    # stays true; its own focus going away closes it.
    assert run["unpinned-closes"] is True


def test_group_list_fits_every_name(run: dict) -> None:
    assert run["names-fit"] and all(run["names-fit"].values()), run["names-fit"]


def test_divider_drags_is_kept_and_clamped(run: dict) -> None:
    assert run["divider"] is True
    start, wider = run["drag-wider"]
    assert wider > start + 30
    kept, shown = run["kept-width"]
    assert abs(kept - shown) <= 1
    widest, half = run["drag-max"]
    assert widest <= half + 1 and widest > wider
    narrowest, least = run["drag-min"]
    assert abs(narrowest - least) <= 1
    assert run["min-shows-labels"] is True


def test_groups_width_store_clamps() -> None:
    try:
        bmo.set_options_groups_width(150.4)
        assert bmo.options_groups_width() == 150
        assert bmo.set_options_groups_width("x") is False
        bmo.set_options_groups_width(-5)
        assert bmo.options_groups_width() == 0
        bmo.set_options_groups_width(10**9)
        assert bmo.options_groups_width() == bmo.OPTIONS_GROUPS_WIDTH_MAX
        bmo.set_side_panel_state("options", {"pinned": True})
        bmo.set_side_panel_state("chips", {"width": 400})
        bmo.reset_panels()
        assert bmo.side_panel_state("options")["pinned"] is True
        assert bmo.side_panel_state("chips")["width"] == 260
    finally:
        bmo.set_options_groups_width(0)
        bmo.set_side_panel_state("options", {"pinned": False})
