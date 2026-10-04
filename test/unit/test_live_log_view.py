# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Live Log Reader's Debug view draws its lines without a click: after
a long log, a short one used to sit in the right place but blank (Qt's text
edit didn't draw the lines now in view) until the view was clicked. Checked
in the running program off-screen by the pixels drawn
(live_log_view_smoke.py, its own process and user folder)."""

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
    env = dict(
        os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen",
        HTTPS_PROXY="http://127.0.0.1:9",
    )
    fonts = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    env.setdefault("QT_QPA_FONTDIR", fonts)
    done = subprocess.run(
        [sys.executable, str(_ROOT / "test" / "unit" / "live_log_view_smoke.py")],
        cwd=_ROOT, env=env, capture_output=True, text=True, timeout=120,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, done.stdout[-1500:] + done.stderr[-1500:]
    return json.loads(lines[0][len("RESULT "):])


def test_a_short_log_after_a_long_one_is_drawn(run: dict) -> None:
    assert run["long"]["count"] == 400 and run["long"]["lit"] > 0
    short = run["short"]
    assert short["count"] == 4
    assert short["y"] <= 0.5
    assert short["lit"] > 0


def test_the_window_opens_on_the_last_choices(run: dict) -> None:
    again = run["reopened"]
    assert (again["tab"], again["file"], again["fileBox"]) == (2, "qt", "Qt")
    assert (again["level"], again["levelBox"]) == ("Warning", "Warning")
    # Find starts empty and Live off.
    assert again["find"] == "" and again["live"] is False


def test_lines_set_while_the_tab_was_hidden_are_drawn(run: dict) -> None:
    assert run["shown-later"]["lit"] > 0
