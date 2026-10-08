# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""10 S44: the Device Library's row menus reach the main window in the
running program (device_library_open.js toMain -> Main.qml libraryAction):
Show on Home selects the card on Home, Open Button Map and Open Module
Setup open their windows, a device with no card says so, and nothing
calls itself (the bare-name trap of 7912a47b)."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SMOKE = _ROOT / "test" / "unit" / "device_library_CU_main_smoke.py"


def test_row_menus_reach_main(tmp_path: pathlib.Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    env = dict(
        os.environ,
        USERPROFILE=str(home),
        QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1",
        PYTHONIOENCODING="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(_SMOKE)],
        cwd=_ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, f"No RESULT (exit {result.returncode}).\n{result.stderr[-3000:]}"
    out = json.loads(lines[-1][len("RESULT ") :])
    assert out["card"]
    assert out["home"]["ok"] and out["focused"] == out["card"]
    assert out["room"] == "status"
    assert out["map"]["ok"] and out["mapOpened"]
    assert out["setup"]["ok"] and out["setupOpened"]
    assert not out["noCard"]["ok"] and "no card on Home" in out["noCard"]["error"]
    assert not out["recursion"] and out["errors"] == []
