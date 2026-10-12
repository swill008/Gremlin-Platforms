# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Choosing a command in the main window's Command Palette (Ctrl+K) runs it
once (01 S65), checked in the running program off-screen
(palette_runs_commands_smoke.py, its own process and user folder). The
Device Mapping Editor has no Command Palette (07 S100):
test_device_mapping_editor_menubar.py.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
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
    done = proc_tree.run(
        [sys.executable, str(_ROOT / "test" / "unit" / _SMOKE)],
        cwd=_ROOT, env=env, text=True, timeout=120,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, done.stdout[-1500:] + done.stderr[-1500:]
    return json.loads(lines[0][len("RESULT "):])


def test_the_main_palette_runs_its_pick_once(run: dict) -> None:
    assert run["main-defined"] is True
    assert run["main-opened"] is True
    assert run["main-lists"] == ["Zq palette test"]
    assert run["main-runs"] is True
    assert run["main-run-count"] == 1
    assert run["main-closed"] is True
