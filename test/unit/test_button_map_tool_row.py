# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Button Map's tool row (Chips, Properties, Layers, Command Palette),
checked in the running program off-screen (button_map_tool_row_smoke.py,
its own process and user folder).

- Each button opens and hides its tool; Properties starts open and pinned,
  the others hidden.
- Unpinned tools hide when the map is clicked; pinned ones stay.
- An unlocked button moves along the row; a locked one stays.
- The status line (view, photo size, module file) is one slim row at the
  bottom, and the pool docks just above the tool row.
- What is open, pinned and locked, and the order, are saved.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

_ROOT = pathlib.Path(__file__).parents[2]
_ORDER = ["chips", "props", "layers", "palette", "exportArea"]


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
    moved = ["palette", "chips", "props", "layers", "exportArea"]
    assert run["6-moved"]["order"] == moved
    assert run["7-locked-move"]["order"] == moved


def test_status_line_and_docked_pool(run: dict) -> None:
    assert run["status-height"] <= 24
    assert run["pool-bottom-gap"] <= 10


def test_the_row_is_saved(run: dict) -> None:
    saved = run["saved"]
    assert saved["order"] == ["palette", "chips", "props", "layers", "exportArea"]
    assert saved["items"]["chips"]["pinned"] is True
    assert saved["items"]["palette"]["locked"] is True
    assert saved["items"]["props"]["pinned"] is True
