# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""10 S2, 03 S88: Home's Device Library... button and the card menu reach
Main's openDeviceLibrary and open the window, in the running program.

Found by hand (2026-10-08): Main's handler called openDeviceLibrary(...),
which inside the Home page's handler is the page's own signal, so it fired
itself until the stack ran out and the window never opened.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SMOKE = _ROOT / "test" / "unit" / "device_library_main_smoke.py"


def test_home_and_tools_open_the_device_library(tmp_path: pathlib.Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    env = dict(
        os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1", PYTHONIOENCODING="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(_SMOKE)], cwd=_ROOT, env=env,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=120,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, f"No RESULT (exit {result.returncode}).\n{result.stderr[-3000:]}"
    out = json.loads(lines[-1][len("RESULT "):])
    button = out["button"]
    assert not button["recursion"], "openDeviceLibrary called itself"
    assert button["too_many_arguments"] == 0
    assert button["opened"], "the Device Library window did not open"
    tools = out["tools"]
    assert tools["opened"], f"Tools > Device Library did not open it: {tools}"
    assert not tools["recursion"] and not tools["errors"], tools
