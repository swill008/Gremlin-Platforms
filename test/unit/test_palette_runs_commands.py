# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Choosing a command in the Command Palette runs it (07 S100, 01 S65),
checked in the running program off-screen (palette_runs_commands_smoke.py,
its own process and user folder).

- The Button Map's palette, not pinned, while editing: View > Properties
  toggles Properties, both ways. Closing the palette takes the window's
  commands away, so the pick must still run after that.
- The main window's palette (Ctrl+K) runs its pick once.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

_ROOT = pathlib.Path(__file__).parents[2]
_SMOKE = "palette_runs_commands_smoke.py"


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    env = dict(os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen")
    fonts = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    env.setdefault("QT_QPA_FONTDIR", fonts)
    done = subprocess.run(
        [sys.executable, str(_ROOT / "test" / "unit" / _SMOKE)],
        cwd=_ROOT, env=env, capture_output=True, text=True, timeout=120,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, done.stdout[-1500:] + done.stderr[-1500:]
    return json.loads(lines[0][len("RESULT "):])


def test_the_button_map_palette_runs_properties(run: dict) -> None:
    assert run["editing"] is True
    assert run["pinned"] is False
    assert run["map-opened"] is True
    assert run["map-lists"][0] == "Properties"
    assert run["props-toggled"] is True
    assert run["map-closed"] is True
    assert run["props-toggled-back"] is True


def test_the_main_palette_runs_its_pick_once(run: dict) -> None:
    assert run["main-defined"] is True
    assert run["main-opened"] is True
    assert run["main-lists"] == ["Zq palette test"]
    assert run["main-runs"] is True
    assert run["main-run-count"] == 1
    assert run["main-closed"] is True
