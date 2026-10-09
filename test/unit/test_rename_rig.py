# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""01 S135 (D-01-ONE-RENAME) in the Button Map editor, real key and mouse
events off-screen: the Layers panel's rename (the shared RenameField) opens
focused with the whole name selected; Enter or a click away saves once, one
undo step; Esc cancels; an empty name keeps the old one. A chip's rename on
the map (its own two-row box for now) is held to the same: opens with the
name selected, Enter or a click on the map saves once, Esc cancels, and an
empty name brings back the default label (the user, 2026-10-08).
Runs rename_rig_smoke.py in its own process.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

_HERE = pathlib.Path(__file__).parent

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows fonts")


@pytest.fixture(scope="module")
def run() -> dict:
    done = subprocess.run(
        [sys.executable, str(_HERE / "rename_rig_smoke.py")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        cwd=str(_HERE.parents[1]),
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "PYTHONUNBUFFERED": "1"},
    )
    results: dict = {}
    for line in done.stdout.splitlines():
        if line.startswith("RESULT "):
            _tag, name, value = line.split(" ", 2)
            results[name] = json.loads(value)
    assert "done" in done.stdout, done.stdout[-3000:] + done.stderr[-3000:]
    return results


# --- Layers panel -------------------------------------------------------


def test_layer_opens_focused_with_name_selected(run: dict) -> None:
    assert run["layer-enter"]["opened"] == {"typing": True, "selected": "Rectangle"}


def test_layer_enter_saves_once(run: dict) -> None:
    res = run["layer-enter"]
    assert res["renamed"]
    assert res["steps-enter"] == 1
    assert res["steps-leave"] == 0


def test_layer_click_away_saves_once(run: dict) -> None:
    res = run["layer-click-away"]
    assert res["renamed"]
    assert res["typing"] is False
    assert res["steps"] == 1
    assert res["steps-after"] == 0


def test_layer_rename_is_one_undo_step(run: dict) -> None:
    assert run["layer-undo"] == {"back": True, "gone": True}


def test_layer_esc_cancels(run: dict) -> None:
    assert run["layer-esc"] == {"kept": True, "typed": False, "steps": 0}


def test_layer_empty_brings_back_the_default(run: dict) -> None:
    # D-01-CANVAS-EXEMPT: the rig editor keeps today's empty-name reset.
    assert run["layer-empty"] == {"kept": False, "steps": 1}


# --- A chip on the map --------------------------------------------------


def test_chip_opens_focused_with_name_selected(run: dict) -> None:
    opened = run["chip-enter"]["opened"]
    assert opened["open"]
    assert opened["typing"]
    assert opened["selected"]
    assert opened["selected"] == opened["draft"]


def test_chip_enter_saves_once(run: dict) -> None:
    res = run["chip-enter"]
    assert res["name"] == "Fire"
    assert res["open"] is False
    assert res["steps-enter"] == 1
    assert res["steps-leave"] == 0


def test_chip_click_away_saves_once(run: dict) -> None:
    res = run["chip-click-away"]
    assert res["name"] == "Jump"
    assert res["open"] is False
    assert res["steps"] == 1


def test_chip_rename_is_one_undo_step(run: dict) -> None:
    assert run["chip-undo"]["name"] == "Fire"


def test_chip_esc_cancels(run: dict) -> None:
    res = run["chip-esc"]
    assert res["name"] == res["before"]
    assert res["open"] is False
    assert res["steps"] == 0


def test_chip_empty_name_brings_back_the_default_label(run: dict) -> None:
    # The user's call (2026-10-08): on a chip an empty name isn't refused,
    # it clears the chip's own name so its default label shows again.
    res = run["chip-empty"]
    assert res["before"] == "Fire"
    assert res["name"] == ""


def test_no_qml_warnings(run: dict) -> None:
    assert run["warnings"] == []
