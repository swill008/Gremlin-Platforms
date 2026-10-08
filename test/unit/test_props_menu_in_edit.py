# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""View > Properties in the Button Map is usable only in Edit, so the menu
item is enabled only in Edit and the Command Palette (which lists every
usable command, 07 S100) leaves it out otherwise. Checked in the running
program off-screen (handson_P2_props_menu_smoke.py, its own process and
user folder).
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

_ROOT = pathlib.Path(__file__).parents[2]
_SMOKE = "handson_P2_props_menu_smoke.py"


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


def test_properties_is_disabled_and_unlisted_outside_edit(run: dict) -> None:
    assert run["item-found"] is True
    assert run["view-editing"] is False
    assert run["view-opened"] is True
    assert run["view-enabled"] is False
    assert "Properties" not in run["view-lists"]


def test_properties_is_enabled_listed_and_toggles_in_edit(run: dict) -> None:
    assert run["editing"] is True
    assert run["edit-enabled"] is True
    assert run["edit-lists"][0] == "Properties"
    assert run["edit-toggled"] is True
