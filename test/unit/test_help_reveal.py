# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""01 S139 (D-01-HELP-LINKS): Help's links to the program, through the main
window's Style.helpLinks. Show me drops a menu down and pulses the item
without choosing it, and pulses toolbar and mode-bar buttons; Open runs only
allowed commands; unknown targets give a reason. Runs the program off-screen
in its own process.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SMOKE = _ROOT / "test" / "unit" / "help_reveal_smoke.py"


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    env = dict(
        os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1", PYTHONIOENCODING="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(_SMOKE)], cwd=_ROOT, env=env,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=150,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, f"No RESULT (exit {result.returncode}).\n{result.stderr[-3000:]}"
    out = json.loads(lines[-1][len("RESULT "):])
    assert not out["errors"], out["errors"]
    return out


def test_main_window_sets_the_bridge(run: dict) -> None:
    assert run["bridge"], "Style.helpLinks not set by the main window"


def test_check_finds_real_targets_and_names_unknown_ones(run: dict) -> None:
    for key in ("check_menu", "check_menu_dots", "check_toolbar", "check_toolbar_tip",
                "check_modebar", "check_modebar_btn", "check_open_allowed"):
        assert run[key] == "", (key, run[key])
    assert run["check_unknown"] == "No such menu item: File/No Such Thing"
    for key in ("check_toolbar_bad", "check_option_bad", "check_open_denied"):
        assert run[key], (key, "no reason given")


def test_menu_drops_down_with_the_item_pulsing_and_nothing_chosen(run: dict) -> None:
    assert run["reveal_menu"] == ""
    now = run["menu_now"]
    assert now["toolsOpen"], "Tools menu not open"
    assert now["setupOpen"], "Device Setup submenu not open"
    assert now["current"], "Calibration not highlighted"
    assert now["pulsing"], "Calibration not pulsing"
    assert "Calibration" not in run["menu_titles"], "Calibration was opened"
    assert run["menu_titles"] == run["start_titles"]
    assert not run["menu_later"]["pulsing"], "pulse still there after ~3 s"


def test_toolbar_and_mode_bar_buttons_pulse(run: dict) -> None:
    assert run["reveal_toolbar"] == ""
    assert run["reveal_modebar"] == ""
    assert run["toolbar_pulsing"]
    assert run["modebar_pulsing"]
    assert run["after_pulse_titles"] == run["start_titles"], "a window opened"
    assert run["toolbar_pulse_gone"]


def test_open_runs_only_allowed_commands(run: dict) -> None:
    assert run["reveal_denied"], "a disallowed open: gave no reason"
    assert "Save Diagnostics" not in run["denied_titles"]
    assert run["reveal_allowed"] == ""
    assert "vJoy Viewer" in run["allowed_titles"]
    assert not run["qml_errors"], run["qml_errors"]


def test_option_link_found_without_opening_options(run: dict) -> None:
    assert run["option_label"], "Options lists no settings"
    assert run["check_option"] == "", run["check_option"]
    assert "Options" not in run["option_titles_before"], "check() showed Options"
    assert run["reveal_option"] == "", run["reveal_option"]
    assert "Options" in run["option_titles"]
