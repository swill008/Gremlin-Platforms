# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""01 S134 (D-01-LEAVE-TEXT) in the Button Map editor: with the program-wide
leave-text filter installed, real key and mouse events off-screen.

The Layers panel's inline rename keeps the typed name when left by a click
outside (as Enter does); its Esc still cancels and the focus loss after the
Esc doesn't save. A Properties number box applies what was typed when left
by a click outside or Esc, and Enter applies it once (one undo step).
Runs leave_text_rig_smoke.py in its own process.
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
        [sys.executable, str(_HERE / "leave_text_rig_smoke.py")],
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


def _value(lines: list, label: str) -> str:
    for line in lines:
        text = line if isinstance(line, str) else json.dumps(line)
        if text.startswith(label + ":") or text.startswith(label + " "):
            return text
    raise AssertionError(f"no {label!r} in {lines!r}")


def test_rename_click_away_keeps_the_name(run: dict) -> None:
    res = run["rename-click-away"]
    assert res["started"]
    assert res["typing"] is False
    assert res["renamed"] is True
    assert res["old"] is False


def test_rename_esc_still_cancels(run: dict) -> None:
    res = run["rename-esc"]
    assert res["started"]
    assert res["typing"] is False
    assert res["kept"] is True
    assert res["typed"] is False


def test_rename_enter_still_saves(run: dict) -> None:
    res = run["rename-enter"]
    assert res["started"]
    assert res["typing"] is False
    assert res["renamed"] is True


def test_number_click_away_applies(run: dict) -> None:
    res = run["props-click-away"]
    assert res["focused"]
    assert res["typing"] is False
    assert _value(res["after"], "X") != _value(res["before"], "X")
    assert "5" in _value(res["after"], "X")


def test_number_esc_applies(run: dict) -> None:
    res = run["props-esc"]
    assert res["focused"]
    assert res["typing"] is False
    assert "10" in _value(res["after"], "Y")


def test_number_enter_applies_once(run: dict) -> None:
    res = run["props-enter"]
    assert res["focused"]
    assert "15" in _value(res["after"], "Width")
    assert res["steps-enter"] == 1
    assert res["steps-leave"] == 0


def test_no_qml_warnings(run: dict) -> None:
    assert run["warnings"] == []
