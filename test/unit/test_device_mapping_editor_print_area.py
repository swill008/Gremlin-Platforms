# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Device Mapping Editor's print area, checked in the running program off-screen
(device_mapping_editor_print_area_smoke.py, its own process and user folder).

- Alt+drag on an empty part of the map sets the area and shows its frame
  (its Print Area tool opens); Save keeps it with the map.
- An export takes only the area (its size follows the area), and the whole
  page again once the area is cleared.
- The frame's handle resizes it; locked, Alt+drag leaves it as it is.
- Its tool follows the tool row's rules: pinned it stays when the map is
  clicked, unpinned it hides.
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
        [sys.executable,
         str(_ROOT / "test" / "unit" / "device_mapping_editor_print_area_smoke.py")],
        cwd=_ROOT, env=env, text=True, timeout=150,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, smoke_report.explain(done)
    return json.loads(lines[0][len("RESULT "):])


def _near(a: float, b: float) -> bool:
    return abs(a - b) < 0.02


def test_alt_drag_sets_and_shows_the_area(run: dict) -> None:
    area = run["area"]
    assert _near(area["fx"], 0.3) and _near(area["fy"], 0.3)
    assert _near(area["fw"], 0.3) and _near(area["fh"], 0.4)
    assert run["shown"] == [True, True]


def test_show_print_area_hides_and_shows_it(run: dict) -> None:
    # View > Show Print Area (07 S135); a click on the map keeps it shown.
    assert run["after-map-click"] is True
    assert run["menu-hides"] == [False, False]
    assert run["menu-shows"] == [True, True]


def test_set_print_area_arms_the_next_drag(run: dict) -> None:
    assert run["set-arms"] is True


def test_the_area_is_saved_with_the_map(run: dict) -> None:
    # Written by Save, not when drawn (07 Q1, GL-173): the stand-in stick
    # has no module file until then (S96).
    assert run["file-before-save"] is False
    assert run["saved"] == run["area"]


def test_an_export_takes_only_the_area(run: dict) -> None:
    want = [run["pixels"]["w"], run["pixels"]["h"]]
    assert all(abs(got - w) <= 1 for got, w in zip(run["export"], want))
    # No photo: 100% is the page 1920 px wide, so the area its share of that.
    assert abs(run["export"][0] - run["area"]["fw"] * 1920) <= 2


def test_the_handle_resizes_it(run: dict) -> None:
    # No lock once the tool rows are gone (07 S93).
    assert run["resized"]["fw"] > run["area"]["fw"]
    assert run["resized"]["fh"] > run["area"]["fh"]


def test_the_frame_shows_only_while_editing(run: dict) -> None:
    assert run["frame-editing"] is True
    assert run["frame-live"] == [False, False, False]
    assert run["frame-edit-again"] is True


def test_cleared_the_whole_page_again(run: dict) -> None:
    assert run["cleared"][0] == "null"
    assert abs(run["cleared"][1] - 1920) <= 2
    assert abs(run["cleared"][2] - 1080) <= 2


def test_the_area_keeps_the_papers_shape(run: dict) -> None:
    letter = 8.0 / 10.5
    got, want = run["letter-aspect"]
    assert abs(want - letter) < 0.001 and abs(got - letter) < 0.01
    assert abs(run["letter-drawn-aspect"] - letter) < 0.01
    got, want = run["landscape-aspect"]
    assert abs(want - 10.5 / 8.0) < 0.001 and abs(got - want) < 0.01


def test_scale_and_saving(run: dict) -> None:
    half, full = run["scale-50"], run["scale-100"]
    assert abs(half["w"] * 2 - full["w"]) <= 2 and abs(half["h"] * 2 - full["h"]) <= 2
    assert run["saved-print"] == {
        "paper": "letter", "landscape": True, "margin": "quarter", "scale": 100,
        "light": False, "includeBg": True}
