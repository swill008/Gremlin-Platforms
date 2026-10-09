# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""OSC's server settings (01 S44, D-01-OSC-HOST-CLOSE; since D-09-OSC-FILE
in OSC's Module Setup "Server" tab, saved to OSC's file): a host, port
or delay typed into a box is saved when the window closes with the cursor
still in the box. It was lost once: only Tab or Enter saved it. The section
runs off-screen in its own process (handson_F8_osc_close_smoke.py)."""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SMOKE = _ROOT / "test" / "unit" / "handson_F8_osc_close_smoke.py"


def _run(tmp_path: pathlib.Path) -> dict[str, str]:
    result = subprocess.run(
        [sys.executable, str(_SMOKE)],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(_ROOT),
        env={
            **os.environ,
            "QT_QPA_PLATFORM": "offscreen",
            "GREMLIN_OFFLINE": "1",
            "USERPROFILE": str(tmp_path),
        },
    )
    lines = result.stdout.splitlines()
    assert "done" in lines, result.stdout[-2000:] + result.stderr[-2000:]
    assert [line for line in lines if line.startswith("ERROR")] == []
    ours = ("OscSetupTabs.qml", "OscServerTab.qml")
    warned = [
        line for line in lines
        if line.startswith("WARN") and any(f in line for f in ours)
    ]
    assert warned == [], warned
    return {
        line.split(" ", 2)[1]: line.split(" ", 2)[2] if line.count(" ") >= 2 else ""
        for line in lines
        if line.startswith("RESULT ")
    }


def test_osc_server_boxes_save_to_the_file_when_module_setup_closes(
    tmp_path: pathlib.Path,
) -> None:
    got = _run(tmp_path)
    typed = {
        "host": "studio-pc",
        "port": "9123",
        "autorelease_delay_ms": "400",
    }
    for key, text in typed.items():
        assert got[f"{key}-focus"] == "True", got
        assert got[f"{key}-before"] != text, got
        assert got[f"{key}-after"] == text, got
