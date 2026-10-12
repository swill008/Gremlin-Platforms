# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A right-click on a Home card shows it as picked (the white box), as a
left click does, before its menu opens; a card in a Shift selection keeps
the selection (the menu can act on all of it). Checked in the running
program off-screen (home_right_click_smoke.py, its own process and user
folder)."""

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
    env = dict(
        os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen",
        HTTPS_PROXY="http://127.0.0.1:9",
    )
    fonts = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    env.setdefault("QT_QPA_FONTDIR", fonts)
    done = proc_tree.run(
        [sys.executable, str(_ROOT / "test" / "unit" / "home_right_click_smoke.py")],
        cwd=_ROOT, env=env, text=True, timeout=120,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, smoke_report.explain(done)
    return json.loads(lines[0][len("RESULT "):])


def test_a_right_click_picks_the_card(run: dict) -> None:
    a, b, _c = run["slugs"]
    assert run["left-a"]["focused"] == [a]
    assert run["right-b"]["focused"] == [b]


def test_a_right_click_in_a_selection_keeps_it(run: dict) -> None:
    before, after = run["right-in-selection"]
    assert len(before["selected"]) >= 2
    assert after == before
