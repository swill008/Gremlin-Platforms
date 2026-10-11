# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""07 S126 (D-07-PLANES-FOLLOWUP Q1a): Help's Show me › links into the
Button Map window (show:buttonmap/<name>) go through Main's own Help link
handler: checked without the window open, the window opened on a device,
"Edit the map to see this" outside Edit, and the banner
(Background mode) and the Background row (Layers, Foreground mode) pulsed
while editing; the removed switch (bmPlaneSwitch) is refused (07 S113).
Runs help_showme_buttonmap_smoke.py off-screen in its own
process with a fresh user folder.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SMOKE = _ROOT / "test" / "unit" / "help_showme_buttonmap_smoke.py"
_NAMES = ("bmBgBanner", "bmBgRow")
_EDIT = "Edit the map to see this"


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    env = dict(
        os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1", PYTHONIOENCODING="utf-8",
    )
    result = proc_tree.run(
        [sys.executable, str(_SMOKE)], cwd=_ROOT, env=env,
        text=True, encoding="utf-8", errors="replace", timeout=150,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, f"No RESULT (exit {result.returncode}).\n{result.stderr[-3000:]}"
    out = json.loads(lines[-1][len("RESULT "):])
    assert not out["errors"], out["errors"]
    return out


def test_links_check_without_the_window(run: dict) -> None:
    for name in _NAMES:
        assert run["check"][name] == "", name
    assert run["check"]["noSuchThing"], "a made-up place is accepted"
    # 07 S113, S126: the Foreground | Background switch is gone.
    assert run["check"]["bmPlaneSwitch"], "the removed switch is accepted"


def test_not_editing_opens_the_window_and_says_edit_first(run: dict) -> None:
    assert run["opened"], "Show me didn't open the Button Map"
    assert run["device"], "the Button Map opened on no device"
    assert run["closed"] == _EDIT
    assert run["message"] == _EDIT
    for name in _NAMES:
        assert run["not_editing"][name] == _EDIT, name


def test_editing_pulses_each_place(run: dict) -> None:
    got = run["editing"]
    for name in _NAMES:
        assert got[name]["why"] == "", (name, got[name])
        assert got[name]["pulsed"], (name, got[name])
    assert got["bmBgBanner"]["plane"] == "background"
    assert got["bmBgRow"]["plane"] == "foreground"
    assert got["bmBgRow"]["layers"]
