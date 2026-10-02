# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Button Map loads only when opened and leaves nothing behind when
closed: the window is destroyed, the shared command list (Gremlin.Menus)
holds none of its commands, and opening it again and again does not make
the program grow."""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys

_HERE = pathlib.Path(__file__).parent


def test_button_map_leaves_nothing_behind() -> None:
    result = subprocess.run(
        [sys.executable, str(_HERE / "button_map_lifecycle_smoke.py")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
    )
    lines = result.stdout.splitlines()
    assert "done" in lines, (result.stderr or "")[-2000:]
    assert not [line for line in lines if line.startswith("ERROR")]
    results = dict(
        line.split(" ", 2)[1:] for line in lines if line.startswith("RESULT ")
    )
    memory = {
        line.split()[1]: float(line.split()[2])
        for line in lines
        if line.startswith("MEM ")
    }
    # The palette lists the window's menu commands only while it is open.
    assert results["palette"] == "True"
    assert int(results["during"]) > 10
    assert results["after-palette"] == "0"
    for cycle in range(3):
        assert results[f"opened{cycle}"] == "True"
        assert results[f"gone{cycle}"] == "True"
        assert results[f"left{cycle}"] == "0"
    # Opening and closing it again does not pile memory up.
    assert memory["closed2"] - memory["closed0"] < 8
