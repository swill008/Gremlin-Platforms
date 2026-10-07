# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Options › OSC (01 S44, D-01-OSC-HOST-CLOSE): a host or port typed into
the OSC boxes is saved when Options closes with the cursor still in the
box, like every other Options text box. It was lost: only Tab or Enter
saved it. The page runs off-screen in its own process
(handson_F8_osc_close_smoke.py)."""

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
    ours = ("OptionOscInputHost.qml", "OptionOscOutputHost.qml")
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


def test_osc_host_and_port_save_when_options_closes(tmp_path: pathlib.Path) -> None:
    got = _run(tmp_path)
    for page in ("input", "output"):
        assert got[f"{page}-focus"] == "True", got
        assert got[f"{page}-port-focus"] == "True", got
        assert got[f"{page}-host-before"] != "127.0.0.5", got
        assert got[f"{page}-host-after"] == "127.0.0.5", got
        assert got[f"{page}-port-before"] != "9123", got
        assert got[f"{page}-port-after"] == "9123", got
