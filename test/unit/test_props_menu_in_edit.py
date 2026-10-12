# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""View > Properties (F4) in the Device Mapping Editor is usable only in Edit, so the
menu item is enabled only in Edit; there it and F4 show or hide Properties
under Layers (07 S133, S135). Checked in the running
program off-screen (handson_P2_props_menu_smoke.py, its own process and
user folder).
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
_SMOKE = "handson_P2_props_menu_smoke.py"


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
    assert lines, smoke_report.explain(done)
    return json.loads(lines[0][len("RESULT "):])


def test_properties_is_disabled_outside_edit(run: dict) -> None:
    assert run["item-found"] is True
    assert run["view-editing"] is False
    assert run["view-enabled"] is False
    assert run["view-hint"] == "F4"


def test_properties_is_enabled_and_toggles_in_edit(run: dict) -> None:
    assert run["editing"] is True
    assert run["edit-enabled"] is True
    assert run["edit-toggled"] is True
    assert run["checked-follows"] is True
    assert run["f4-toggled"] is True
