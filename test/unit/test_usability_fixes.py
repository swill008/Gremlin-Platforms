# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Usability fixes (3 Oct review, UI4-UI9), checked in the running program
off-screen (usability_smoke.py, its own process and user folder).

- The Output View button over a photo was dark text on see-through in the
  light theme (UI4).
- The Calibration window drew white bars between axes (UI5).
- Escape didn't close About, Options, Help, Manage Modes or Check for
  Updates (UI6).
- The Home cards couldn't be reached with the keyboard (UI7).
- Device Pack's picture width followed its own row's height (UI8).
- Error details didn't wrap and couldn't be copied (UI9).
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

_ROOT = pathlib.Path(__file__).parents[2]


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> tuple[dict, str]:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    env = dict(os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen")
    fonts = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    env.setdefault("QT_QPA_FONTDIR", fonts)
    done = subprocess.run(
        [sys.executable, str(_ROOT / "test" / "unit" / "usability_smoke.py")],
        cwd=_ROOT, env=env, capture_output=True, text=True, timeout=120,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, done.stdout[-1500:] + done.stderr[-1500:]
    return json.loads(lines[0][len("RESULT "):]), done.stderr


def test_output_view_reads_in_the_light_theme(run: tuple[dict, str]) -> None:
    assert run[0]["output-view"] == ["#99000000", "#ffffff"]


def test_calibration_spacer_is_not_a_white_bar() -> None:
    qml = (_ROOT / "qml" / "DialogCalibration.qml").read_text(encoding="utf-8")
    spacer = qml[qml.index("// Spacer at the bottom"):][:200]
    assert "Item {" in spacer and "Rectangle {" not in spacer


def test_escape_closes_the_tool_windows(run: tuple[dict, str]) -> None:
    assert set(run[0]["escape"].values()) == {"closed"}, run[0]["escape"]
    # An open list closes first; the window stays until the next Escape.
    assert run[0]["esc-closes-list-first"] == [True, True, True]


def test_home_cards_by_keyboard(run: tuple[dict, str]) -> None:
    assert run[0]["cards"] > 1
    assert run[0]["arrow-moves"] is True
    assert run[0]["enter-opens"] is True


def test_device_pack_has_no_layout_loop(run: tuple[dict, str]) -> None:
    stderr = run[1]
    pack = stderr[stderr.index("DEVICE-PACK-OPEN"):stderr.index("DEVICE-PACK-DONE")]
    assert "recursive rearrange" not in pack.lower()


def test_error_details_wrap_and_copy(run: tuple[dict, str]) -> None:
    assert run[0]["copy-details-shown"] is True
    assert run[0]["copied"] is True
    assert run[0]["details-wrap"] is True
