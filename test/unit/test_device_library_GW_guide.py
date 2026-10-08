# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""10 S1, S42 (D-10-GUIDE): the Device Library window's Help › Device
Library Guide (F1) opens the User Guide window showing only the Device
Library's topics, as the Button Map Guide does, in the running program.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SMOKE = _ROOT / "test" / "unit" / "device_library_GW_guide_smoke.py"


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    env = dict(
        os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1", PYTHONIOENCODING="utf-8",
    )
    shot = os.environ.get("GW_SHOT")
    if shot:
        env["GW_SHOT"] = shot
    result = subprocess.run(
        [sys.executable, str(_SMOKE)], cwd=_ROOT, env=env,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=150,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, f"No RESULT (exit {result.returncode}).\n{result.stderr[-3000:]}"
    out = json.loads(lines[-1][len("RESULT "):])
    assert out["library_opened"], "the Device Library window did not open"
    return out


def _is_device_library_guide(out: dict, state: dict) -> None:
    titles = state["titles"]
    assert titles, "no topics"
    assert len(titles) == out["dl_count"], "not the Device Library's topics"
    assert len(titles) < out["full_count"], "the whole User Guide"
    assert "Button Map" not in " ".join(titles)


def test_help_menu_has_the_guide_with_f1(run: dict) -> None:
    expected = [{"text": "Device Library Guide", "hint": "F1"}]
    assert run["help_items"] == expected, run["errors"]


def test_menu_opens_the_device_library_guide_once(run: dict) -> None:
    assert run["menu_triggered"], run["errors"]
    assert run["menu"]["count"] == 1
    _is_device_library_guide(run, run["menu"])
    assert run["menu_again"]["count"] == 1, "a second guide window"


def test_f1_opens_the_device_library_guide_once(run: dict) -> None:
    assert run["f1"]["count"] == 1, "F1 did not open the guide"
    _is_device_library_guide(run, run["f1"])
    assert run["f1_again"]["count"] == 1, "a second guide window"


def test_user_guide_still_shows_every_topic(run: dict) -> None:
    assert run["user_guide"]["count"] == 1
    assert len(run["user_guide"]["titles"]) == run["full_count"] > 50
    assert not run["qml_errors"], run["qml_errors"]
