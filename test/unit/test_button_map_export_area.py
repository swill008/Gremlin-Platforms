# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Button Map's export area, checked in the running program off-screen
(button_map_export_area_smoke.py, its own process and user folder).

- Alt+drag on an empty part of the map sets the area and shows its frame
  (its Export Area tool opens); it is saved with the map.
- An export takes only the area (its size follows the area), and the whole
  page again once the area is cleared.
- The frame's handle resizes it; locked, Alt+drag leaves it as it is.
- Its frame stays on screen until its button is clicked again (a click on
  the map leaves it).
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

_ROOT = pathlib.Path(__file__).parents[2]


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    env = dict(os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen")
    fonts = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    env.setdefault("QT_QPA_FONTDIR", fonts)
    done = subprocess.run(
        [sys.executable,
         str(_ROOT / "test" / "unit" / "button_map_export_area_smoke.py")],
        cwd=_ROOT, env=env, capture_output=True, text=True, timeout=150,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, done.stdout[-1500:] + done.stderr[-1500:]
    return json.loads(lines[0][len("RESULT "):])


def _near(a: float, b: float) -> bool:
    return abs(a - b) < 0.02


def test_alt_drag_sets_and_shows_the_area(run: dict) -> None:
    area = run["area"]
    assert _near(area["fx"], 0.3) and _near(area["fy"], 0.3)
    assert _near(area["fw"], 0.3) and _near(area["fh"], 0.4)
    assert run["shown"] == [True, True]


def test_it_stays_until_its_button_is_clicked(run: dict) -> None:
    assert run["after-map-click"] is True
    assert run["after-button"] is False


def test_the_area_is_saved_with_the_map(run: dict) -> None:
    assert run["saved"] == run["area"]


def test_an_export_takes_only_the_area(run: dict) -> None:
    page_w, page_h, scale = run["page"]
    area = run["area"]
    want = [area["fw"] * page_w * scale, area["fh"] * page_h * scale]
    assert all(abs(got - w) <= 2 for got, w in zip(run["export"], want))


def test_the_handle_resizes_and_lock_keeps_it(run: dict) -> None:
    assert run["resized"]["fw"] > run["area"]["fw"]
    assert run["resized"]["fh"] > run["area"]["fh"]
    assert run["locked"] == run["resized"]


def test_cleared_the_whole_page_again(run: dict) -> None:
    page_w, page_h, scale = run["page"]
    assert run["cleared"][0] == "null"
    assert abs(run["cleared"][1] - page_w * scale) <= 2
    assert abs(run["cleared"][2] - page_h * scale) <= 2
