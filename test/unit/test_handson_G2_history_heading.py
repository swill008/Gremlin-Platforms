# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Hands-on fix G2: History's "Before" heading clear of Restore Before.

At 150 % the History window's "Before" heading touched the "Restore
Before" button (hands-on 08, note O5, s48-created-entry.png): the heading
was squeezed to less than its text, which drew on under the button. Each
side's heading and its Restore button now sit in one row with a gap; the
heading is shortened (…) when there is no room.

The real History window off-screen in its own process
(handson_G2_history_smoke.py) at 100, 150 and 175 %.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

_ROOT = pathlib.Path(__file__).parents[2]


@pytest.fixture(scope="module", params=[100, 150, 175])
def run(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
) -> dict:
    home = tmp_path_factory.mktemp("g2history")
    (home / "Gremlin Platforms").mkdir()
    env = dict(
        os.environ,
        USERPROFILE=str(home),
        QT_QPA_PLATFORM="offscreen",
        HTTPS_PROXY="http://127.0.0.1:9",
    )
    args = [sys.executable, "test/unit/handson_G2_history_smoke.py", str(request.param)]
    if os.environ.get("GREMLIN_SHOT"):
        args.append(os.environ["GREMLIN_SHOT"].replace(".png", f"-{request.param}.png"))
    result = subprocess.run(
        args, cwd=_ROOT, env=env, capture_output=True, text=True, timeout=120
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, result.stdout[-2000:] + result.stderr[-2000:]
    return json.loads(lines[0][len("RESULT ") :])


@pytest.mark.parametrize("side", ["Before", "After"])
def test_heading_ends_before_its_restore_button(run: dict, side: str) -> None:
    at = run[side]
    # The drawn text and the heading's own box, with a gap before the button.
    assert at["text-end"] <= at["button-start"] - at["gap-wanted"] + 0.5, at
    assert at["heading-end"] <= at["button-start"] - at["gap-wanted"] + 0.5, at


@pytest.mark.parametrize("side", ["Before", "After"])
def test_restore_button_inside_its_side(run: dict, side: str) -> None:
    at = run[side]
    assert at["button-end"] <= at["row-end"] + 0.5, at
